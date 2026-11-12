#!/usr/bin/env python3
"""Download one latest sample for each of six input families, independently of audit.
Dependencies: pip install requests earthaccess
Run directly in PyCharm, or use --only viirs_snow oco2_forward.
Credentials: adjacent config.json (audit schema), or EARTHDATA_USERNAME / PASSWORD.
Defaults to primary VIIRS products; --fallback permits the named fallback only
when the primary catalogue search returns no granules (not on service errors).
Existing audit downloads are never erased. Each invocation gets a new directory.
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,os,sys,time
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent
BBOX=(4.5,35.27,22.88,47.81)
# name: (product, primary short name, version, fallback short name, fallback version, bbox)
INPUTS={
 'viirs_lst':('01','VJ121A1D','002','VJ221A1D','002',BBOX),
 'viirs_sst':('02','VIIRS_N20-STAR-L2P-v2.80',None,'N21-VIIRS-L2P-ACSPO-v2.80',None,None),
 'viirs_snow':('05','VJ110A1F','2','VJ210A1F','2',BBOX),
 'viirs_aod':('09','VJ119A2','002','VJ219A2','002',BBOX),
 'oco2_forward':('08','OCO2_L2_Fwd_FP','11.3',None,None,None),
 'oco3_forward':('08','OCO3_L2_Fwd_FP','11',None,None,None),
}
def load_credentials(path):
 if path.is_file():
  env=json.loads(path.read_text()).get('providers',{}).get('earthdata',{}).get('env',{})
  for k in ('EARTHDATA_USER','EARTHDATA_USERNAME','EARTHDATA_PASSWORD'):
   if env.get(k):os.environ.setdefault(k,str(env[k]))
 if not os.environ.get('EARTHDATA_USERNAME') and os.environ.get('EARTHDATA_USER'):
  os.environ['EARTHDATA_USERNAME']=os.environ['EARTHDATA_USER']
 if not all(os.environ.get(k) for k in ('EARTHDATA_USERNAME','EARTHDATA_PASSWORD')):
  raise RuntimeError('Earthdata credentials missing: supply config.json or environment variables')

def discover(short_name,version,bbox):
 params={'short_name':short_name,'page_size':1,'sort_key':'-start_date'}
 if version:params['version']=version
 if bbox:params['bounding_box']=','.join(map(str,bbox))
 r=requests.get('https://cmr.earthdata.nasa.gov/search/granules.json',params=params,timeout=(20,90));r.raise_for_status()
 rows=r.json()['feed']['entry'];return rows[0] if rows else None

def verify_file(path):
 """Reject empty/error pages and require an expected HDF/NetCDF container signature."""
 path=Path(path)
 if not path.is_file() or not path.stat().st_size:raise ValueError('Empty or missing download')
 with path.open('rb') as f:magic=f.read(8)
 if not (magic.startswith(b'\x89HDF\r\n\x1a\n') or magic.startswith(b'CDF') or magic.startswith(b'\x0e\x03\x13\x01')):
  raise ValueError('Download is not a recognized HDF/NetCDF file')
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return {'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':h.hexdigest()}

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--config',type=Path,default=BASE/'config.json')
 p.add_argument('--output',type=Path,default=BASE/'downloads'/'viirs_oco_samples')
 p.add_argument('--only',nargs='+',choices=list(INPUTS),default=list(INPUTS))
 p.add_argument('--fallback',action='store_true')
 a=p.parse_args(argv)
 import earthaccess
 try:
  load_credentials(a.config);auth=earthaccess.login(strategy='environment',persist=False)
  if not auth.authenticated:raise RuntimeError('Earthdata authentication failed')
 except Exception as exc:
  print(f'Authentication/configuration failed ({type(exc).__name__}); verify Earthdata credentials.',flush=True);return 1
 out=a.output.resolve()/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ');out.mkdir(parents=True)
 print(f'Download folder: {out}',flush=True);results=[]
 for name in a.only:
  product,short,version,fallback,fv,bbox=INPUTS[name];start=time.monotonic()
  row={'input':name,'product':product,'dataset':short,'version':version,'bbox':bbox,'status':'query_error','checked_at':dt.datetime.now(dt.timezone.utc).isoformat()}
  try:
   entry=discover(short,version,bbox)
   if entry is None and a.fallback and fallback:
    short,version=fallback,fv;row.update(dataset=short,version=version,fallback_used=True);entry=discover(short,version,bbox)
   if entry is None:row['status']='no_data_found'
   else:
    row.update(status='download_error',latest_date=entry.get('time_start'),granule_id=entry['id'],granule_name=entry.get('producer_granule_id') or entry.get('title'))
    print(f'{name}: found {row["latest_date"]}; downloading exact granule...',flush=True)
    granules=earthaccess.search_data(concept_id=entry['id'])
    if len(granules)!=1:raise ValueError('Exact granule lookup did not return one result')
    dest=out/name;dest.mkdir()
    files=earthaccess.download(granules,local_path=dest,threads=1,show_progress=False)
    if not files:raise ValueError('No downloaded files returned')
    row['files']=[verify_file(f) for f in files];row['status']='downloaded'
  except Exception as exc:
   # Do not serialize signed URLs, tokens or credential-bearing exception messages.
   row['error_type']=type(exc).__name__
  row['seconds']=round(time.monotonic()-start,1);results.append(row)
  (out/'results.json').write_text(json.dumps(results,indent=2))
  print(f'{name:16} {row["status"]:18} {row.get("latest_date","-")} ({row["seconds"]}s)',flush=True)
 print(f'Report: {out / "results.json"}',flush=True)
 return 0 if all(r['status']=='downloaded' for r in results) else 1
if __name__=='__main__':sys.exit(main())
