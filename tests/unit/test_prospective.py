"""Synthetic archive and pre-acquisition declaration boundary tests."""

from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from reddit_sna.data.archive import digest_file
from reddit_sna.data.prospective import receive_archive, validate_archive
from reddit_sna.pipelines.prospective import CANDIDATE, CORPORA, FLAT_CONTROL, declare, load_protocol
from reddit_sna.evaluation.temporal_protocol import COMPACT_BASELINES, PRIMARY

PROJECT=Path(__file__).parents[2]
PROTOCOL=PROJECT/'configs/prospective.toml'


def archive_bytes():
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_STORED) as archive:
        archive.writestr('utterances.jsonl','{"id":"synthetic-payload"}\n')
    return buffer.getvalue()


class ProspectiveTests(unittest.TestCase):
    def test_fixed_candidate_and_baseline_roles_before_acquisition(self):
        protocol,definitions,_=load_protocol(PROTOCOL)
        self.assertEqual(tuple(protocol['corpora']),CORPORA)
        self.assertEqual(len(definitions),9)
        self.assertTrue(set(COMPACT_BASELINES)<=set(definitions))
        full,pruned,flat=definitions[PRIMARY],definitions[CANDIDATE],definitions[FLAT_CONTROL]
        self.assertEqual(len(full['fields']),37)
        self.assertEqual(len(pruned['fields']),35)
        self.assertEqual(set(full['fields'])-set(pruned['fields']),{'record_log_growth','reply_log_growth'})
        self.assertEqual(full['settings'],pruned['settings'])
        self.assertEqual(pruned['fields'],flat['fields'])
        self.assertEqual(pruned['settings'],flat['settings'])
        self.assertTrue(pruned['hierarchical'])
        self.assertFalse(flat['hierarchical'])

    def test_protocol_rejects_changed_size_cohort_or_schedule(self):
        original=PROTOCOL.read_text()
        for old,new in (('228362409','1'),('Anarchism','AnotherCorpus'),('2018-01','2017-01')):
            with self.subTest(new=new),tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'changed.toml'
                path.write_text(original.replace(old,new),encoding='utf-8')
                with self.assertRaises(ValueError):load_protocol(path)

    def test_declaration_precedes_raw_input_and_refuses_drift(self):
        protocol,definitions,model_path=load_protocol(PROTOCOL)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            declare(root,protocol,definitions,PROTOCOL,model_path)
            declared=json.loads((root/'declaration.json').read_text())
            self.assertFalse(declared['candidate_outcome_records_read'])
            self.assertFalse(declared['raw_archives_present'])
            self.assertFalse((root/'raw').exists())
            before=(root/'declaration.json').read_bytes()
            declare(root,protocol,definitions,PROTOCOL,model_path)
            self.assertEqual(before,(root/'declaration.json').read_bytes())
            changed=deepcopy(definitions)
            changed[CANDIDATE]['fields'].pop()
            with self.assertRaises(ValueError):declare(root,protocol,changed,PROTOCOL,model_path)

    def test_preexisting_payload_cannot_be_declared_unread(self):
        protocol,definitions,model_path=load_protocol(PROTOCOL)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'raw').mkdir()
            with self.assertRaises(ValueError):declare(root,protocol,definitions,PROTOCOL,model_path)

    def test_archive_name_and_origin_cannot_escape_allowlist(self):
        protocol,_,_=load_protocol(PROTOCOL)
        item=protocol['archives']['Anarchism']
        validate_archive('Anarchism',item)
        for name,url in (('../Anarchism',item['url']),('Anarchism',item['url'].replace('https:','http:')),
                         ('Anarchism',item['url'].replace('zissou.infosci.cornell.edu','example.org')),
                         ('Anarchism',item['url']+'?token=synthetic'),
                         ('Anarchism',item['url'].replace('/corpus-zipped/','/corpus-zipped/../'))):
            with self.subTest(url=url),self.assertRaises(ValueError):
                validate_archive(name,dict(url=url,bytes=item['bytes']))

    def test_receive_exact_bytes_crc_and_observed_hash(self):
        payload=archive_bytes()
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'fixture.zip'
            result=receive_archive(io.BytesIO(payload),target,len(payload),0)
            self.assertEqual(result['sha256'],digest_file(target))
            self.assertEqual(result['crc'],'passed')
            self.assertFalse(target.with_suffix('.zip.partial').exists())
            with self.assertRaises(FileExistsError):receive_archive(io.BytesIO(payload),target,len(payload),0)

    def test_truncated_oversized_and_crc_failure_remain_partial(self):
        payload=archive_bytes()
        corrupted=bytearray(payload)
        corrupted[payload.index(b'synthetic-payload')] ^= 1
        variants=[(payload[:-1],len(payload)),(payload,len(payload)-1),(bytes(corrupted),len(payload))]
        for blob,size in variants:
            with self.subTest(size=size),tempfile.TemporaryDirectory() as directory:
                target=Path(directory)/'fixture.zip'
                with self.assertRaises((ValueError,zipfile.BadZipFile)):
                    receive_archive(io.BytesIO(blob),target,size,0)
                self.assertFalse(target.exists())
                self.assertTrue(target.with_suffix('.zip.partial').exists())

    def test_resource_stop_preserves_partial_without_success(self):
        payload=archive_bytes()
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'fixture.zip'
            with self.assertRaises(RuntimeError):receive_archive(io.BytesIO(payload),target,len(payload),10**9)
            self.assertFalse(target.exists())
            self.assertTrue(target.with_suffix('.zip.partial').exists())


if __name__=='__main__':unittest.main()
