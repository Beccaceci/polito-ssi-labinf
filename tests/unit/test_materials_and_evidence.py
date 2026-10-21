import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from labinf.materials import import_materials,find_original
from labinf.verification import Recorder,Failed
from labinf.topology import specification


class MaterialTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'project with spaces';self.root.mkdir()
        self.source=Path(self.tmp.name)/'originals';self.source.mkdir()
        (self.source/'IHA.sh').write_text('original content')

    def test_import_is_content_addressed_and_checksums_are_enforced(self):
        one=import_materials(self.root,'02',self.source)
        two=import_materials(self.root,'02',self.source)
        self.assertEqual(one,two)
        self.assertEqual(find_original(self.root,'02','IHA.sh').read_text(),'original content')
        (one/'IHA.sh').write_text('modified')
        with self.assertRaisesRegex(ValueError,'checksum'):find_original(self.root,'02','IHA.sh')
        self.assertEqual((self.source/'IHA.sh').read_text(),'original content')

    def test_conflicting_revisions_do_not_silently_choose_an_original(self):
        import_materials(self.root,'02',self.source)
        (self.source/'IHA.sh').write_text('different original')
        import_materials(self.root,'02',self.source)
        with self.assertRaisesRegex(ValueError,'Conflicting'):find_original(self.root,'02','IHA.sh')

    def test_archive_traversal_is_rejected_without_publishing_partial_import(self):
        archive=self.root/'unsafe.zip'
        with zipfile.ZipFile(archive,'w') as z:
            z.writestr('good.txt','ok');z.writestr('../escape','bad')
        with self.assertRaisesRegex(ValueError,'Unsafe'):import_materials(self.root,'03',archive)
        self.assertFalse((self.root/'workspace/materials/escape').exists())
        self.assertEqual(list((self.root/'workspace/materials/lab03').iterdir()),[])

    def test_directory_symlinks_are_rejected(self):
        (self.source/'link').symlink_to(self.source/'IHA.sh')
        with self.assertRaisesRegex(ValueError,'symlinks'):import_materials(self.root,'02',self.source)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name)
        class LocalEnvironment:
            def exec(self,node,script,**kwargs):
                kwargs.pop('root',None)
                script=script.replace('/workspace',str(base/'private')).replace('/exchange',str(base/'exchange'))
                return subprocess.run(['bash','-seuo','pipefail'],input=script,text=True,**kwargs)
        self.recorder=Recorder(LocalEnvironment(),base/'run'/'lab03')

    def test_earlier_failure_and_pipeline_failure_cannot_be_hidden(self):
        for command in ('false\nprintf hidden-success','false | true\nprintf hidden-success'):
            with self.assertRaises(Failed):self.recorder.run('alice',command)
            record=self.recorder.records[-1]
            self.assertFalse(record['passed']);self.assertNotIn('hidden-success',record['stdout'])
            self.assertNotEqual(record['exit_status'],0)

    def test_intended_failure_requires_exact_expected_exit(self):
        self.recorder.run('alice','printf rejected >&2\nexit 2',expect=2)
        data=json.loads((self.recorder.out/'commands.jsonl').read_text().splitlines()[-1])
        self.assertTrue(data['passed']);self.assertEqual(data['stderr'],'rejected')
        with self.assertRaises(Failed):self.recorder.run('alice','exit 0',expect=2)


class ScenarioTests(unittest.TestCase):
    def test_routed_nodes_have_no_common_bypass_network(self):
        spec=specification('04','routed',Path('/tmp/project with spaces'))
        a=set(spec['services']['alice']['networks']);b=set(spec['services']['bob']['networks'])
        self.assertFalse(a&b)
        self.assertEqual(a|b,set(spec['services']['frank']['networks']))
        private=[spec['services'][n]['volumes'][0]['source'] for n in ('alice','bob','frank')]
        self.assertEqual(len(set(private)),3)
        self.assertNotEqual(spec['services']['alice']['volumes'][0]['target'],'/exchange')

    def test_site_contains_two_gateways_and_separate_endpoint_networks(self):
        spec=specification('05','site')
        self.assertEqual(set(spec['services']),{'alice','bob','gwa','gwb'})
        self.assertFalse(set(spec['services']['alice']['networks'])&set(spec['services']['bob']['networks']))

    def test_invalid_scenario_is_an_error(self):
        with self.assertRaises(ValueError):specification('03','routed')


if __name__=='__main__':unittest.main()
