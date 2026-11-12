import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
spec=importlib.util.spec_from_file_location('downloader',Path(__file__).with_name('download_viirs_oco_samples.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class DownloaderTests(unittest.TestCase):
 def test_six_inputs(self):self.assertEqual(len(m.INPUTS),6)
 def test_valid_and_invalid_downloads(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'sample.nc';p.write_bytes(b'\x89HDF\r\n\x1a\n1234')
   self.assertEqual(m.verify_file(p)['bytes'],12)
   for body in (b'',b'<html>Login required</html>'):
    p.write_bytes(body)
    with self.assertRaises(ValueError):m.verify_file(p)
 def test_query_preserves_version_and_bbox(self):
  response=Mock();response.json.return_value={'feed':{'entry':[{'id':'G123'}]}}
  with patch.object(m.requests,'get',return_value=response) as get:
   self.assertEqual(m.discover('VJ121A1D','002',m.BBOX)['id'],'G123')
   self.assertEqual(get.call_args.kwargs['params']['version'],'002')
   self.assertIn('bounding_box',get.call_args.kwargs['params'])
   response.raise_for_status.assert_called_once()
 def test_snow_uses_cmr_version_two(self):
  self.assertEqual(m.INPUTS['viirs_snow'][2],'2')
 def test_empty_query(self):
  response=Mock();response.json.return_value={'feed':{'entry':[]}}
  with patch.object(m.requests,'get',return_value=response):self.assertIsNone(m.discover('a',None,None))
 def test_credentials_environment_wins(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'config.json';p.write_text(json.dumps({'providers':{'earthdata':{'env':{'EARTHDATA_USER':'file-user','EARTHDATA_PASSWORD':'file-password'}}}}))
   with patch.dict(m.os.environ,{'EARTHDATA_USERNAME':'env-user','EARTHDATA_PASSWORD':'env-password'},clear=True):
    m.load_credentials(p);self.assertEqual(m.os.environ['EARTHDATA_USERNAME'],'env-user');self.assertEqual(m.os.environ['EARTHDATA_PASSWORD'],'env-password')
if __name__=='__main__':unittest.main()
