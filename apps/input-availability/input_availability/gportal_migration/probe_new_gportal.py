"""Local migration probe; deliberately not connected to the production audit.
Search: --start YYYY-MM-DD --end YYYY-MM-DD --dataset 10003027
Download a CSW-confirmed SFTP path: --remote-path /... --key /private/key
Requires requests, paramiko. Host must be pre-verified in SSH known_hosts.
No passwords, auto-trusted SSH hosts, or disabled TLS verification.
"""
import argparse,datetime as dt,json,os,posixpath,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
CSW='https://csw.gportal.jaxa.jp/csw'
SFTP='sftp.gportal.jaxa.jp'
def search(dataset,start,end):
 params={'service':'CSW','version':'3.0.0','request':'GetRecords','outputFormat':'application/atom+xml','datasetId':dataset,'startTime':start+'T00:00:00Z','endTime':end+'T23:59:59Z'}
 r=requests.get(CSW,params=params,timeout=(15,60));r.raise_for_status()
 root=ET.fromstring(r.content)
 if root.tag.split('}')[-1]!='feed':raise ValueError('Expected Atom feed; refusing to treat an unknown response as no data')
 ns={'a':'http://www.w3.org/2005/Atom'}
 entries=[]
 for e in root.findall('a:entry',ns):
  entries.append({'id':e.findtext('a:id',namespaces=ns),'title':e.findtext('a:title',namespaces=ns),'published':e.findtext('a:published',namespaces=ns),'updated':e.findtext('a:updated',namespaces=ns),'links':[dict(l.attrib) for l in e.findall('a:link',ns)]})
 # Preserve pagination; this probe does not claim the first page is latest.
 return r.text,entries,[dict(l.attrib) for l in root.findall('a:link',ns)]
def download(remote,key,user,out):
 import paramiko
 if not key or not Path(key).is_file():raise ValueError('JAXA-issued private key required')
 if not user:raise ValueError('GPORTAL_USER required')
 name=posixpath.basename(remote)
 if not remote.startswith('/') or name in ('','.','..'):raise ValueError('Expected absolute CSW-confirmed SFTP path')
 dest=out/name
 if dest.exists():raise FileExistsError('Refusing to overwrite existing file')
 ssh=paramiko.SSHClient();ssh.load_system_host_keys();ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
 partial=out/(name+'.part')
 try:
  ssh.connect(SFTP,port=22,username=user,key_filename=str(key),passphrase=os.getenv('GPORTAL_KEY_PASSPHRASE'),look_for_keys=False,allow_agent=False,timeout=30,auth_timeout=30,banner_timeout=30)
  with ssh.open_sftp() as sftp:
   size=sftp.stat(remote).st_size;sftp.get(remote,str(partial))
   if size<=0 or partial.stat().st_size!=size:raise ValueError('Incomplete file')
   partial.rename(dest)
 finally:
  ssh.close()
  if partial.exists():partial.unlink()
 return str(dest)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--start',required=True);p.add_argument('--end',required=True);p.add_argument('--dataset',default='10003027,10003026');p.add_argument('--key',type=Path);p.add_argument('--remote-path');p.add_argument('--output',type=Path,default=Path(__file__).parent/'results');a=p.parse_args()
 assert dt.date.fromisoformat(a.start)<=dt.date.fromisoformat(a.end)
 a.output.mkdir(parents=True,exist_ok=True)
 result={'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'endpoint':CSW,'dataset':a.dataset,'start':a.start,'end':a.end}
 try:
  xml,entries,links=search(a.dataset,a.start,a.end);(a.output/'response.xml').write_text(xml);result.update(status='search_ok',entries=entries,feed_links=links)
  if a.remote_path:result['download']=download(a.remote_path,a.key,os.getenv('GPORTAL_USER'),a.output)
 except requests.HTTPError as e:result.update(status='provider_http_error',http_status=e.response.status_code)
 except Exception as e:result.update(status='error',error_type=type(e).__name__)
 (a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));return 0 if result['status']=='search_ok' else 1
if __name__=='__main__':sys.exit(main())
