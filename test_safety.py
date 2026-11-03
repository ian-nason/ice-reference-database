"""Small regressions for source integrity, output preservation and disk guards."""
from pathlib import Path
from unittest import mock
from collections import namedtuple
import hashlib,io,json,os,subprocess,sys,tempfile,unittest,zipfile
import acquire_sources as acquire
import build_safety as safety

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.test_parent=(Path(__file__).resolve().parent/'evidence').resolve()
        self.test_parent.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(prefix='.safety-test-',dir=self.test_parent)
        self.root=Path(self.tmp.name).resolve()
        # These fixtures write at most a few bytes. Mock capacity so integrity
        # regressions test the intended branch; separate tests exercise reserve failures.
        disk=namedtuple('disk','total used free')
        self.capacity=mock.patch.object(acquire.shutil,'disk_usage',return_value=disk(2*1024**3,0,2*1024**3))
        self.capacity.start()
    def tearDown(self):
        self.capacity.stop()
        if self.root.parent!=self.test_parent or not self.root.name.startswith('.safety-test-'):
            raise RuntimeError('Refuse cleanup outside this test-owned workspace directory')
        self.tmp.cleanup()
    def spec(self,data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    def test_existing_database_manifest_and_orphan_wal_are_preserved(self):
        for suffix in ('','.wal','.manifest.json'):
            with self.subTest(suffix=suffix):
                output=self.root/('candidate'+suffix.replace('.','_')+'.duckdb')
                path=output.with_suffix('.manifest.json') if suffix=='.manifest.json' else Path(str(output)+suffix)
                path.write_bytes(b'existing user data')
                with self.assertRaises(FileExistsError):safety.refuse_existing(output)
                self.assertEqual(path.read_bytes(),b'existing user data')
    def test_closed_working_size_and_free_reserve_are_enforced(self):
        (self.root/'db').write_bytes(b'12345')
        disk=namedtuple('disk','total used free')
        with mock.patch.object(safety.shutil,'disk_usage',return_value=disk(100,50,50)):
            with self.assertRaises(RuntimeError):safety.check_budget(self.root,self.root,4,10)
            with self.assertRaises(RuntimeError):safety.check_budget(self.root,self.root,6,51)
            self.assertEqual(safety.check_budget(self.root,self.root,6,50)['work_bytes'],5)
    def test_integrity_check_survives_optimized_python(self):
        result=subprocess.run([sys.executable,'-O','-c','from build_safety import require; require(False,"bad source hash")'],cwd=Path(__file__).resolve().parent,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('bad source hash',result.stderr)
    def test_valid_source_publishes_and_cache_is_verified(self):
        path=self.root/'source';data=b'PAR1 valid fixture'
        acquire.publish_stream(io.BytesIO(data),path,self.spec(data));self.assertEqual(path.read_bytes(),data)
        acquire.verify(path,self.spec(data))
        path.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):acquire.publish_stream(io.BytesIO(data),path,self.spec(data))
        self.assertEqual(path.read_bytes(),b'corrupt')
    def test_wrong_length_and_hash_never_publish(self):
        for label,data,spec in [('short',b'a',self.spec(b'aa')),('long',b'aaa',self.spec(b'aa')),('hash',b'bb',self.spec(b'aa'))]:
            with self.subTest(label=label):
                path=self.root/label
                with self.assertRaises(ValueError):acquire.publish_stream(io.BytesIO(data),path,spec)
                self.assertFalse(path.exists())
    def test_late_competing_source_is_not_overwritten(self):
        path=self.root/'source';link=os.link
        def competitor(src,dst):
            Path(dst).write_bytes(b'competitor')
            return link(src,dst)
        with mock.patch.object(acquire.os,'link',side_effect=competitor):
            with self.assertRaises(FileExistsError):acquire.publish_stream(io.BytesIO(b'ok'),path,self.spec(b'ok'))
        self.assertEqual(path.read_bytes(),b'competitor')
    def test_paths_and_unexpected_archive_members_are_rejected(self):
        with self.assertRaises(ValueError):acquire.safe_path(self.root,'../outside')
        archive=self.root/'sources.zip'
        with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape',b'bad')
        spec=self.spec(archive.read_bytes())|{'local_path':'sources.zip','url':'https://example.invalid/not-requested'}
        (self.root/'source-lock.json').write_text(json.dumps({'downloads':[spec],'tables':[{'file':'expected.parquet','local_path':'sources/expected.parquet','bytes':3,'sha256':hashlib.sha256(b'bad').hexdigest()}]}))
        with mock.patch.object(acquire.urllib.request,'urlopen',side_effect=AssertionError('No network expected')):
            with self.assertRaises(ValueError):acquire.acquire(self.root)
    def test_download_reserve_is_checked_before_writing(self):
        disk=namedtuple('disk','total used free');path=self.root/'source'
        with mock.patch.object(acquire.shutil,'disk_usage',return_value=disk(100,100,0)):
            with self.assertRaises(ValueError):acquire.publish_stream(io.BytesIO(b'ok'),path,self.spec(b'ok'))
        self.assertFalse(path.exists())

    def test_nested_budget_and_disappearing_wal(self):
        nested=self.root/'spill';nested.mkdir();(nested/'chunk').write_bytes(b'12345')
        with self.assertRaises(RuntimeError):safety.check_budget(self.root,self.root,4,0)
        vanished=mock.Mock();vanished.is_file.return_value=True;vanished.stat.side_effect=FileNotFoundError
        with mock.patch.object(Path,'rglob',return_value=[vanished]):
            self.assertEqual(safety.check_budget(self.root,self.root,0,0)['work_bytes'],0)
    def test_validation_report_never_overwrites(self):
        report=self.root/'already-reviewed.json';report.write_bytes(b'preserve report')
        result=subprocess.run([sys.executable,str(Path(__file__).resolve().parent/'build_database.py'),'--validate-only','--report',str(report)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('FileExistsError',result.stderr)
        self.assertEqual(report.read_bytes(),b'preserve report')
    def test_smoke_rejects_bad_catalog_and_rows_with_optimization(self):
        root=Path(__file__).resolve().parent
        dataset=json.loads((root/'source-lock.json').read_text())['id']
        for bad_catalog in (True,False):
            with self.subTest(bad_catalog=bad_catalog):
                program="""import runpy,sys,types
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root))
dp=types.ModuleType('datapond');registry=types.ModuleType('datapond.registry');dp.registry=registry
dp.list=lambda: [] if sys.argv[3]=='True' else [sys.argv[2]]
class Connection:
 def execute(self,*args):return self
 def fetchone(self):return (0,)
 def close(self):pass
dp.connect=lambda *a,**k:Connection()
sys.modules.update({'datapond':dp,'datapond.registry':registry,'duckdb':types.ModuleType('duckdb')})
sys.argv=['smoke_python.py','http://not-contacted.invalid/registry.json',str(root/'evidence'/'mock-cache')]
runpy.run_path(str(root/'smoke_python.py'),run_name='__main__')
"""
                env=os.environ.copy();env['PYTHONOPTIMIZE']='2'
                result=subprocess.run([sys.executable,'-c',program,str(root),dataset,str(bad_catalog)],env=env,capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('Smoke check failed',result.stderr)


if __name__=='__main__':unittest.main()
