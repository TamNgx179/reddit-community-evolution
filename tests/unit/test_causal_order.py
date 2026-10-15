"""Past-only detector ordering independent of ordinal IDs and CSV row order."""

from contextlib import closing
import hashlib
import importlib.util
import json
import random
import unittest

from reddit_sna.data.normalize import normalize_archives, open_readonly
from reddit_sna.detection.leiden import detect_snapshots
from reddit_sna.evaluation.causality import compare_causal_prefix
from reddit_sna.graphs.provenance import ORDERED_GRAPH_PROTOCOL, EDGE_COLUMNS, snapshot_inventory, ordered_nodes
from reddit_sna.graphs.snapshots import build_snapshots, write_csv
from reddit_sna.reporting.pilot import read_csv
from reddit_sna.reporting.validation import graph_from_rows
from tests.corpus_support import CorpusCase, archive, record


class CausalOrderTests(CorpusCase):
    def test_future_records_and_renumbered_users_preserve_past_anchor_order(self):
        early = archive(self.marker.parent/"a.corpus.zip", [
            record("p", "A", day="2014-12-01"),record("x","B",parent="p"),
            record("f","F",root="f",day="2015-02-01"),
            record("0a","A",root="0a",day="2015-02-02")])
        later = archive(self.marker.parent/"z.corpus.zip", [
            record("q","C",root="q",day="2014-12-01"),record("y","D",root="q",parent="q")])
        for name, end in (("short","2015-02"),("long","2015-04")):
            target=self.root/name; target.mkdir()
            normalize_archives([early,later],target/"normalized.sqlite",end,self.quiet)
            build_snapshots(target/"normalized.sqlite",target/"snapshots","2015-01",end)
        with closing(open_readonly(self.root/"short/normalized.sqlite")) as short, closing(open_readonly(self.root/"long/normalized.sqlite")) as long:
            a=dict(short.execute("SELECT id,user_id FROM records")); b=dict(long.execute("SELECT id,user_id FROM records"))
        self.assertNotEqual(a["t3_q"],b["t3_q"])
        alignment={uid:b[rid] for rid,uid in a.items() if uid is not None}
        left=read_csv(self.root/"short/snapshots/2015-01/node_order.csv")
        right=read_csv(self.root/"long/snapshots/2015-01/node_order.csv")
        self.assertEqual({alignment[r['user_id']]:r['order_key'] for r in left},
                         {r['user_id']:r['order_key'] for r in right})
        # The lexical-min future post by A must not change A's January anchor.
        akey=next(r['order_key'] for r in left if r['user_id']==a['t3_p'])
        self.assertEqual(akey,hashlib.sha256(b'causal-record-anchor-v1:t3_p').hexdigest())
        if importlib.util.find_spec("leidenalg"):
            for name in ("short","long"):
                detect_snapshots(self.root/name/"snapshots",self.root/name/"memberships",name,
                                 graph_protocol=ORDERED_GRAPH_PROTOCOL)
            result=compare_causal_prefix(self.root/"short/snapshots",self.root/"long/snapshots","2015-01",
                left_user_map=alignment,right_user_map={v:v for v in alignment.values()},
                left_memberships=self.root/"short/memberships",right_memberships=self.root/"long/memberships")
            self.assertTrue(result["graph_invariant"])
            self.assertTrue(result["partition_invariant"])

    @unittest.skipUnless(importlib.util.find_spec("leidenalg"),"install [graph]")
    def test_csv_order_edge_orientation_and_user_renaming_preserve_partition(self):
        rng=random.Random(123)
        logical=[(a,b) for a in range(18) for b in range(a+1,18) if rng.random()<.19 or b==a+1]
        names=[f"u{i:02d}" for i in range(18)]
        remap={name:f"v{17-i:02d}" for i,name in enumerate(names)}
        sources=[]
        for label,mapping in (("a",{n:n for n in names}),("b",remap)):
            directory=self.root/label/"2015-01"; directory.mkdir(parents=True)
            rows=[("2015-01",mapping[names[a]],mapping[names[b]],1+(a+b)%3) for a,b in logical]
            if label=="b": rows=[(m,v,u,w) for m,u,v,w in reversed(rows)]
            write_csv(directory/"R.csv",EDGE_COLUMNS,rows)
            write_csv(directory/"node_order.csv",["month","user_id","order_key"],
                      [("2015-01",mapping[n],hashlib.sha256(n.encode()).hexdigest()) for n in reversed(names)])
            sources.append(directory)
            detect_snapshots(directory.parent,self.root/(label+"-members"),"fixture",graph_protocol=ORDERED_GRAPH_PROTOCOL)
        orders=[ordered_nodes(p,set(names) if i==0 else set(remap.values()),"2015-01") for i,p in enumerate(sources)]
        first,_=graph_from_rows(read_csv(sources[0]/"R.csv"),node_order=orders[0])
        second,_=graph_from_rows(read_csv(sources[1]/"R.csv"),node_order=orders[1])
        self.assertEqual(first.get_edgelist(),second.get_edgelist())
        self.assertEqual(first.es['weight'],second.es['weight'])
        for seed in (0,1,2):
            partitions=[]
            for label in ("a","b"):
                groups={}
                inverse={v:k for k,v in remap.items()}
                for r in read_csv(self.root/(label+"-members")/"2015-01"/f"membership-seed{seed}.csv"):
                    groups.setdefault(r['community_id'],set()).add(r['user_id'] if label=='a' else inverse[r['user_id']])
                partitions.append({frozenset(v) for v in groups.values()})
            self.assertEqual(*partitions)

    def test_ordered_protocol_rejects_missing_duplicate_or_malformed_sidecars(self):
        directory=self.root/"g/2015-01"; directory.mkdir(parents=True)
        write_csv(directory/"R.csv",EDGE_COLUMNS,[("2015-01","a","b",1)])
        with self.assertRaises(FileNotFoundError):
            snapshot_inventory(directory.parent,protocol=ORDERED_GRAPH_PROTOCOL)
        key=lambda x:hashlib.sha256(x.encode()).hexdigest()
        for rows in ([('2015-01','a',key('a'))],
                     [('2015-01','a',key('a')),('2015-01','a',key('b'))],
                     [('2015-01','a',key('a')),('2015-01','b',key('a'))],
                     [('2015-01','a',key('a')),('2015-02','b','bad')]):
            path=directory/'node_order.csv'
            if path.exists(): path.unlink()  # Temporary synthetic test file only.
            write_csv(path,['month','user_id','order_key'],rows)
            with self.assertRaisesRegex(ValueError,'Causal node order'):
                snapshot_inventory(directory.parent,protocol=ORDERED_GRAPH_PROTOCOL)

    def test_order_keys_are_bound_to_graph_fingerprint(self):
        directory=self.root/"g/2015-01"; directory.mkdir(parents=True)
        write_csv(directory/"R.csv",EDGE_COLUMNS,[("2015-01","a","b",1)])
        path=directory/'node_order.csv'
        write_csv(path,['month','user_id','order_key'],[('2015-01','a','0'*64),('2015-01','b','1'*64)])
        first=snapshot_inventory(directory.parent,protocol=ORDERED_GRAPH_PROTOCOL)
        text=path.read_text().replace('1'*64,'2'*64); path.write_text(text)
        second=snapshot_inventory(directory.parent,protocol=ORDERED_GRAPH_PROTOCOL)
        self.assertNotEqual(first['graph_reference'],second['graph_reference'])
