"""Technical assessment provenance and actual per-case evidence boundaries."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.structural_assessment import complete_assessment
from reddit_sna.pipelines.study_preparation import seal
from reddit_sna.pipelines.study_resources import json_write


class StructuralAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.panel=self.root/'panel'
        (self.panel/'reviewer').mkdir(parents=True)
        (self.panel/'coordinator').mkdir()
        json_write(self.panel/'reviewer/cases.json',[
            dict(case_id='synthetic-1',source_size=2,targets=[dict(shared=2)]),
            dict(case_id='synthetic-2',source_size=3,targets=[])])
        json_write(self.panel/'coordinator/answers.json',[
            dict(case_id='synthetic-1',label='stable'),dict(case_id='synthetic-2',label='dissolve')])
        payload_hash=digest_file(self.panel/'reviewer/cases.json')
        json_write(self.panel/'manifest.json',dict(payload_sha256=payload_hash,source_manifest_sha256='synthetic-source'))
        seal(self.panel,dict(status='complete',stage='synthetic-panel'))
        self.submission=dict(reviewer_id='technical-synthetic',reviewer_type='automated',
            provenance='Synthetic technical assessment fixture, not human validation',payload_sha256=payload_hash,
            submitted_utc=datetime.now(timezone.utc).isoformat(),machine_answers_not_seen=True,model_predictions_not_seen=True,
            judgments=[dict(case_id='synthetic-1',label='stable',confidence='high',
                evidence=dict(source_size=2,overlapping_targets=1,largest_shared=2),
                rationale='Both observed members continue into the same size target.'),
                dict(case_id='synthetic-2',label='unresolved',confidence='low',
                evidence=dict(source_size=3,overlapping_targets=0,largest_shared=0),
                rationale='No observed overlap is available, so social continuity cannot be resolved.')])

    def submit(self,data):
        path=self.root/'submission.json'
        json_write(path,data)
        return complete_assessment(self.panel,path,self.root/'result')

    def test_complete_technical_assessment_preserves_disagreement(self):
        result=self.submit(self.submission)
        self.assertEqual(result['cases'],2)
        self.assertEqual(result['discrepancies'],1)
        self.assertEqual(result['technical_machine_concordance'],.5)
        self.assertEqual(result['independent_human_submissions'],0)
        self.assertIsNone(result['human_agreement'])
        self.assertEqual(result['human_review'],'pending')

    def test_human_identity_or_type_cannot_be_manufactured(self):
        for field,value in (('reviewer_type','human'),('reviewer_id','human-reviewer-a'),('reviewer_id','human-reviewer-b')):
            data=deepcopy(self.submission)
            data[field]=value
            with self.subTest(value=value),self.assertRaises(ValueError):self.submit(data)

    def test_blank_partial_or_duplicate_judgments_are_rejected(self):
        for mode in ('blank','partial','duplicate','rationale'):
            data=deepcopy(self.submission)
            if mode=='blank':data['judgments']=[]
            elif mode=='partial':data['judgments'].pop()
            elif mode=='duplicate':data['judgments'].append(data['judgments'][0])
            else:data['judgments'][0]['rationale']=''
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.submit(data)

    def test_actual_numeric_case_evidence_is_required(self):
        data=deepcopy(self.submission)
        data['judgments'][0]['evidence']['largest_shared']=99
        with self.assertRaises(ValueError):self.submit(data)

    def test_changed_payload_or_untruthful_blinding_attestation_rejected(self):
        for field,value in (('payload_sha256','different'),('machine_answers_not_seen',False),('submitted_utc','2026-01-01')):
            data=deepcopy(self.submission)
            data[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.submit(data)


if __name__=='__main__':unittest.main()
