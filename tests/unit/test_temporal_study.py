"""Scientific boundaries tested with small, explicitly synthetic observations."""

from copy import deepcopy
from contextlib import closing
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from sklearn.metrics import f1_score
from threadpoolctl import threadpool_limits

from reddit_sna.data.normalize import month_boundary
from reddit_sna.evaluation.activity_forecast import evaluate_activity_predictions
from reddit_sna.contracts import shift_month
from reddit_sna.evaluation.study_labels import audit_labels, prepare_review
from reddit_sna.evaluation.temporal_protocol import EVENTS, FIELDS, SETTINGS, load_temporal_protocol
from reddit_sna.features.activity import activity_features
from reddit_sna.models.activity_forecast import feature_matrix, fit_activity_model, predict_activity_model, select_activity_model
from reddit_sna.pipelines.temporal_study import _definitions
from reddit_sna.tracking.ged import transitions


def training_rows():
    return [dict(reference_id='synthetic-r',label_reference_id='synthetic-label',
        feature_month=shift_month(f'2015-{month:02d}',-1),label_month=f'2015-{month:02d}',
        community_id=f'c{index}',size=index+2,record_log_growth=index-2.,label=label)
        for month in range(1,7) for index,label in enumerate(EVENTS)]


def label_fixture(source,target):
    groups={'2015-01':source,'2015-02':target}
    weights={m:{cid:dict.fromkeys(users,1.) for cid,users in partition.items()} for m,partition in groups.items()}
    _,events,reasons,pairs=transitions(source,target,weights['2015-01'],weights['2015-02'])
    pairs=[dict(feature_month='2015-01',label_month='2015-02',**p) for p in pairs]
    rows=[dict(feature_month='2015-01',label_month='2015-02',community_id=cid,
               label=event.value if event else '',eligible=int(event is not None),reason=reasons[cid],size=len(source[cid]))
          for cid,event in events.items()]
    rows.extend(dict(feature_month='2015-02',label_month='2015-03',community_id=cid,
                     label='',eligible=0,reason='final_snapshot_censored',size=len(users)) for cid,users in target.items())
    return groups,weights,rows,pairs


class ActivityFeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'metadata.sqlite'
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE records(id TEXT,user_id TEXT,root TEXT,parent TEXT,timestamp REAL,month TEXT,kind TEXT,corpus TEXT)')
            db.execute('CREATE TABLE provenance(key TEXT,value TEXT)')
            db.execute("INSERT INTO provenance VALUES('end_month_exclusive','2016-01')")
            rows=[('p0','b','2015-01',1,None,'Ask_Politics'),('j1','a','2015-01',15,'p0','Ask_Politics'),
                  ('p1','b','2015-02',1,None,'Conservative'),('p2','a','2015-02',2,None,'Conservative'),
                  ('f1','a','2015-02',23,'p1','Conservative'),('f2','b','2015-02',24,'f1','Conservative')]
            db.executemany('INSERT INTO records VALUES(?,?,?,?,?,?,?,?)',[
                (rid,user,'root',parent,month_boundary(month)+(day-1)*86400,month,'post' if parent is None else 'comment',corpus)
                for rid,user,month,day,parent,corpus in rows])
        self.groups={'g':{'a','b'},'empty':{'c'}}

    def test_hand_calculated_activity_and_fixed_membership_dynamics(self):
        row=activity_features(self.path,'2015-02',self.groups)['g']
        expected=dict(records_per_member_log=math.log(3),active_day_fraction=4/28,
            recent_record_fraction=.5,top_member_fraction=.5,internal_reply_fraction=1.,weighted_reciprocity=1.,
            returning_member_fraction=1.,past_active_month_fraction=1/3,record_log_growth=math.log(5/3),
            reply_log_growth=math.log(3/2),repeated_dyad_fraction=1.,context_drift_js=math.log(2),
            past_window_fraction=1/3,activity_missing=0,reply_missing=0,context_history_missing=0,previous_reply_missing=0)
        for name,value in expected.items():
            with self.subTest(field=name):self.assertAlmostEqual(row[name],value)

    def test_missing_activity_history_and_reply_flags(self):
        row=activity_features(self.path,'2015-02',self.groups)['empty']
        self.assertEqual(row['activity_missing'],1)
        self.assertEqual(row['reply_missing'],1)
        self.assertEqual(row['context_history_missing'],1)
        self.assertEqual(row['previous_reply_missing'],1)
        self.assertTrue(all(math.isfinite(v) for v in row.values()))

    def test_future_record_and_thread_completion_invariance(self):
        before=activity_features(self.path,'2015-02',self.groups)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?,?)',
                       ('future','a','root','f2',month_boundary('2015-03'),'2015-03','comment','Conservative'))
        self.assertEqual(before,activity_features(self.path,'2015-02',self.groups))

    def test_overlap_and_out_of_cutoff_rejected(self):
        with self.assertRaises(ValueError):activity_features(self.path,'2015-02',{'g':{'a'},'h':{'a'}})
        with self.assertRaises(ValueError):activity_features(self.path,'2016-01',self.groups)

    def test_context_divergence_is_identical_across_process_hash_seeds(self):
        program=('from collections import Counter; from reddit_sna.features.activity import _js; '
                 'import random,hashlib,json; rng=random.Random(123); '
                 'values=[_js(Counter({str(i):rng.randint(0,10000) for i in range(15)}),'
                 'Counter({str(i):rng.randint(0,10000) for i in range(15)})).hex() for _ in range(100)]; '
                 'print(hashlib.sha256(json.dumps(values).encode()).hexdigest())')
        previous=os.environ.get('PYTHONHASHSEED')
        fingerprints=[]
        try:
            for seed in ('1','2','42'):
                os.environ['PYTHONHASHSEED']=seed
                fingerprints.append(subprocess.check_output([sys.executable,'-c',program],text=True).strip())
        finally:
            if previous is None:os.environ.pop('PYTHONHASHSEED',None)
            else:os.environ['PYTHONHASHSEED']=previous
        self.assertEqual(len(set(fingerprints)),1,fingerprints)


class ActivityModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.limits=threadpool_limits(limits=1)
        cls.limits.__enter__()

    @classmethod
    def tearDownClass(cls):cls.limits.__exit__(None,None,None)

    def test_frozen_equal_grids_and_controls(self):
        self.assertEqual({k:len(v) for k,v in SETTINGS.items()},{'lr':8,'hgb':8})
        self.assertEqual([r[0] for r in _definitions()],
            ['flat_lr_dynamic','hier_hgb_static','hier_hgb_dynamic','hier_lr_dynamic'])
        self.assertTrue(set(FIELDS['static'])<set(FIELDS['dynamic']))

    def test_flat_hierarchical_probabilities_and_absent_training_classes(self):
        rows=training_rows()
        for estimator in ('lr','hgb'):
            for hierarchy in (False,True):
                with self.subTest(estimator=estimator,hierarchy=hierarchy):
                    model=fit_activity_model(rows,('size','record_log_growth'),SETTINGS[estimator][0],hierarchy)
                    guessed,values,_=predict_activity_model(model,rows)
                    self.assertEqual(len(guessed),len(rows))
                    self.assertTrue(np.allclose(np.asarray(values).sum(axis=1),1))
        rows=[r for r in rows if r['label']!='stable']
        fitted=fit_activity_model(rows,('size',),SETTINGS['lr'][0],True)
        self.assertTrue(all(v[EVENTS.index('stable')]==0 for v in predict_activity_model(fitted,rows)[1]))

    def test_single_class_and_empty_conditional_head(self):
        for label in ('dissolve','grow'):
            rows=[dict(r,label=label) for r in training_rows()[:3]]
            for hierarchy in (False,True):
                model=fit_activity_model(rows,('size',),SETTINGS['lr'][0],hierarchy)
                guessed,values,flags=predict_activity_model(model,rows)
                self.assertEqual(guessed,[label]*len(rows))
                self.assertEqual(flags,[1]*len(rows))
                self.assertTrue(np.allclose(np.asarray(values).sum(axis=1),1))

    def test_signed_dynamics_unchanged_by_count_compression(self):
        values=feature_matrix([dict(size=3,record_log_growth=-2)],('size','record_log_growth'),dict(transform='log_counts'))
        np.testing.assert_allclose(values,[[math.log(4),-2]])
        with self.assertRaises(ValueError):feature_matrix([dict(size=-1)],('size',),{})
        with self.assertRaises(ValueError):feature_matrix([dict(size=float('nan'))],('size',),{})

    def test_scaler_fit_on_train_only(self):
        train=training_rows()[:12]
        fitted=fit_activity_model(train,('size',),SETTINGS['lr'][0],False)
        before=fitted['flat'].named_steps['standardscaler'].mean_.copy()
        predict_activity_model(fitted,[dict(train[0],size=1e9)])
        np.testing.assert_equal(before,fitted['flat'].named_steps['standardscaler'].mean_)
        np.testing.assert_allclose(before,[np.mean([r['size'] for r in train])])

    def test_future_labels_do_not_affect_earlier_temporal_selection(self):
        rows=training_rows()
        origins=['2015-04','2015-05','2015-06']
        chosen,evidence=select_activity_model(rows,('size','record_log_growth'),'lr',True,origins)
        future=[dict(rows[0],label_month='2018-01',label='not-an-event',size=1e12)]
        again,second=select_activity_model(rows+future,('size','record_log_growth'),'lr',True,origins)
        self.assertEqual(chosen,again)
        self.assertEqual(evidence,second)
        for candidate in chosen['candidates']:
            self.assertTrue(all(f['latest_train_label']<f['month'] for f in candidate['folds']))

    def test_invalid_candidates_labels_and_empty_folds_fail(self):
        rows=training_rows()
        with self.assertRaises(ValueError):fit_activity_model([],('size',),SETTINGS['lr'][0])
        with self.assertRaises(ValueError):fit_activity_model([dict(rows[0],label='unknown')],('size',),SETTINGS['lr'][0])
        with self.assertRaises(ValueError):select_activity_model(rows,('size',),'lr',False,['2018-01'])


class LabelAuditTests(unittest.TestCase):
    def test_equal_size_changed_membership_is_operational_stable(self):
        groups,weights,rows,pairs=label_fixture({'s':set('abcd')},{'t':set('abce')})
        self.assertEqual(rows[0]['label'],'stable')
        self.assertEqual(audit_labels(rows,pairs,groups,weights)['support'],{'stable':1})

    def test_two_user_disappearance_weak_overlap_and_many_to_many(self):
        fixtures=[({'s':set('ab')},{'t':set('cd')},'dissolve'),
                  ({'s':set('abcd')},{'t':set('abef')},''),
                  ({'s':set('abcdefgh'),'q':{'x'}},{'t':set('abcde'),'u':set('fghx')},'')]
        for source,target,expected in fixtures:
            groups,weights,rows,pairs=label_fixture(source,target)
            self.assertEqual(next(r['label'] for r in rows if r['community_id']=='s'),expected)
            audit_labels(rows,pairs,groups,weights)

    def test_overlap_importance_and_label_tampering_rejected(self):
        groups,weights,rows,pairs=label_fixture({'s':set('abcd')},{'t':set('abce')})
        for field,value in [('shared_members',2),('inclusion_forward',.8)]:
            bad=deepcopy(pairs);bad[0][field]=value
            with self.assertRaises(ValueError):audit_labels(rows,bad,groups,weights)
        bad=deepcopy(rows);bad[0]['label']='grow'
        with self.assertRaises(ValueError):audit_labels(bad,pairs,groups,weights)

    def test_complete_pair_inventory_and_source_size_are_required(self):
        groups,weights,rows,pairs=label_fixture({'s':set('abcd')},{'t':set('abce')})
        for bad in ([],pairs+pairs):
            with self.assertRaises(ValueError):audit_labels(rows,bad,groups,weights)
        bad=deepcopy(rows);bad[0]['size']=99
        with self.assertRaises(ValueError):audit_labels(bad,pairs,groups,weights)
        bad=deepcopy(rows);bad[-1].update(label='dissolve',eligible=1)
        with self.assertRaises(ValueError):audit_labels(bad,pairs,groups,weights)

    def test_blinded_packet_has_blank_forms_and_separate_answers(self):
        groups,weights,rows,pairs=label_fixture({'s':set('abcd')},{'t':set('abce')})
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'review'
            prepare_review(rows,groups,output,weights=weights)
            from reddit_sna.pipelines.study_samples import read_csv
            forms=read_csv(output/'reviewer/annotations.csv')
            self.assertEqual(len(forms),2)
            self.assertTrue(all(not r['human_label'] for r in forms))
            cases=json.loads((output/'reviewer/cases.json').read_text())
            self.assertNotIn('label',cases[0])
            self.assertIn('current_importance',cases[0])
            self.assertIn('pending_human',json.loads((output/'status.json').read_text())['status'])


class EvaluationTests(unittest.TestCase):
    def predictions(self):
        return [dict(reference_id='r',label_reference_id='l',feature_month=shift_month(f'2018-{m:02d}',-1),
            label_month=f'2018-{m:02d}',community_id=f'c{i}',size=2 if i<3 else 20,model=model,seed=seed,
            y_true=label,y_pred=label if model=='baseline' else 'dissolve',fallback=0)
            for model in ('proposed','baseline') for seed in (42,43,44) for m in range(1,10) for i,label in enumerate(EVENTS)]

    def evaluate(self,rows):
        return evaluate_activity_predictions(rows,[42,43,44],['proposed','baseline'],
            [f'2018-{m:02d}' for m in range(1,10)],'proposed','baseline',['baseline'],draws=30)

    def test_sklearn_agreement_and_negative_superiority(self):
        rows=self.predictions();result=self.evaluate(rows)
        subset=[r for r in rows if r['model']=='proposed' and r['seed']==42]
        independent=f1_score([r['y_true'] for r in subset],[r['y_pred'] for r in subset],labels=list(EVENTS),average='macro',zero_division=0)
        self.assertAlmostEqual(result['mean_macro_f1']['proposed'],independent)
        self.assertEqual(result['superiority'],'not_demonstrated')
        self.assertLess(result['delta_vs_strongest'],0)
        self.assertEqual(result['intervals'],self.evaluate(rows)['intervals'])

    def test_missing_duplicate_truth_and_reference_controls(self):
        rows=self.predictions()
        for bad in (rows[:-1],rows+[rows[0]]):
            with self.assertRaises(ValueError):self.evaluate(bad)
        for field,value in [('y_true','grow'),('reference_id','wrong'),('label_month','2018-10')]:
            bad=deepcopy(rows);bad[0][field]=value
            with self.assertRaises(ValueError):self.evaluate(bad)

    def test_matched_component_control_blocks_broad_superiority(self):
        # Proposed beats the named baseline by a clear time-consistent margin,
        # but the matched flat control is perfect. The hierarchy cannot claim
        # broad superiority merely because the control is called an ablation.
        rows=[]
        for source in self.predictions():
            row=dict(source)
            row['y_pred']=row['y_true'] if row['model']=='proposed' else 'dissolve'
            if row['model']=='proposed' and row['y_true']==EVENTS[0]:
                row['y_pred']=EVENTS[1]
            rows.append(row)
            if row['model']=='proposed':
                rows.append(dict(row,model='A_flat_matched',y_pred=row['y_true']))
        arguments=([42,43,44],['proposed','baseline','A_flat_matched'],
            [f'2018-{m:02d}' for m in range(1,10)],'proposed','baseline',['baseline'])
        result=evaluate_activity_predictions(rows,*arguments,draws=30)
        self.assertGreater(result['delta_vs_champion'],.02)
        self.assertGreater(result['intervals']['baseline']['low'],0)
        self.assertFalse(result['beats_all_matched_component_controls'])
        self.assertEqual(result['superiority'],'not_demonstrated')
        without_control=[r for r in rows if r['model']!='A_flat_matched']
        ordinary=self.evaluate(without_control)
        self.assertEqual(ordinary['superiority'],'supported_on_this_operational_target')

    def test_absent_classes_keep_six_class_denominator(self):
        rows=[r for r in self.predictions() if r['y_true']=='dissolve']
        result=self.evaluate(rows)
        self.assertAlmostEqual(result['mean_macro_f1']['baseline'],1/6)
        self.assertEqual(result['metrics']['baseline:42']['per_class']['stable']['support'],0)

    def test_protocol_rejects_retuned_schedule(self):
        source=Path(__file__).parents[2]/'configs/temporal_study.toml'
        self.assertEqual(load_temporal_protocol(source)['test_start'],'2018-01')
        with tempfile.TemporaryDirectory() as temporary:
            bad=Path(temporary)/'bad.toml'
            bad.write_text(source.read_text().replace('block_length = 3','block_length = 2'))
            with self.assertRaises(ValueError):load_temporal_protocol(bad)


if __name__=='__main__':unittest.main()
