#!/usr/bin/env python3
"""Resume cached product 04 comparisons while asynchronous gauges are prepared.

Run main.py --product S5-02-04 first to cache production deliveries. This helper
never downloads production again, retains all local references, and updates the
report after each reference batch. Remote archiving requires an explicit config
opt-in; it never deletes local data. --once is a bounded single refresh cycle.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from s5validation.bootstrap import initialize
from s5validation.downloads import save_json
from s5validation.models import Delivery,Outcome
from s5validation.pipeline import parse_time
from s5validation.precipitation import PrecipitationAdapter
from s5validation.references.regional_gauges import refresh_regional_gauges,reference_receipts,exclusive_lock
from s5validation.registry import Registry
from s5validation.report import generate


def cached_delivery(item,workdir):
    folder=workdir/'cache/s5'/item['product']/item['delivery_id']/item['revision']
    path=folder/'download_receipt.json'
    if not path.is_file():return None
    receipt=json.loads(path.read_text())
    if receipt.get('status')!='DOWNLOADED' or receipt.get('revision')!=item['revision']:return None
    primary=next((a for a in receipt['assets'] if a['key']==item['primary_key'] and a.get('status')=='DOWNLOADED'),None)
    if not primary or not Path(primary['local_path']).is_file():return None
    return Delivery(item['product'],item['delivery_id'],item['revision'],primary['local_path'],item['acquired_at'])


def snapshot(registry,workdir):
    path=workdir/'registry_snapshot.db';temporary=path.with_suffix('.db.part')
    connection=sqlite3.connect(temporary);registry.db.backup(connection);connection.close();temporary.replace(path)
    save_json(workdir/'current_results.json',[dict(r) for r in registry.rows('S5-02-04')])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'config/validation.json')
    parser.add_argument('--base-dir',type=Path,default=ROOT)
    parser.add_argument('--workdir',type=Path,default=ROOT/'validation')
    parser.add_argument('--inventory-file',type=Path)
    parser.add_argument('--registry-file',type=Path,help='Optional local SQLite path when the workdir is on an external/network volume')
    parser.add_argument('--poll-seconds',type=int,default=60)
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--retry-network-errors',action='store_true',help='Keep retrying connection/time-out errors; ambiguous submissions and scientific/provider errors still stop')
    args=parser.parse_args(argv)
    if not 15<=args.poll_seconds<=60:parser.error('poll-seconds must be 15–60')
    base=args.base_dir.expanduser().resolve();workdir=args.workdir.expanduser().resolve()
    config=json.loads(args.config.expanduser().read_text())
    # Registry lives in the chosen workdir, never in a private hard-coded path.
    config['delivery']['manifest']=str(workdir/'deliveries.json');initialize(config,base,workdir)
    inventory=args.inventory_file or workdir/'inventory/campaign_products.json'
    source=json.loads(inventory.read_text())
    if source.get('errors'):raise ValueError('Resolve inventory errors before continuing the campaign')
    items=[i for i in source['items'] if i['product']=='S5-02-04' and parse_time(config['campaign']['start'])<=parse_time(i['acquired_at'])<parse_time(config['campaign']['end'])]
    if not items:raise ValueError('No product 04 deliveries in inventory')
    queue=[Delivery(i['product'],i['delivery_id'],i['revision'],'unused',i['acquired_at']) for i in items]
    with exclusive_lock(workdir/'inventory/precipitation_continuation.lock'):
        registry_path=(args.registry_file or workdir/'precipitation_continuation.db').expanduser();registry_path.parent.mkdir(parents=True,exist_ok=True)
        registry=Registry(registry_path);adapter=PrecipitationAdapter(config,base)
        completed={};consecutive_errors=0
        try:
            for delivery in queue:
                registry.discover(delivery)
                registry.record(delivery,Outcome('PENDING_REFERENCE','Waiting for cached production and complete gauge reference','NOT_AVAILABLE'))
            while True:
                progress={'updated_at':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),'deliveries':len(items),'state':'RUNNING'}
                try:
                    refresh=refresh_regional_gauges(config,base,workdir,queue);consecutive_errors=0
                except BlockingIOError:
                    if args.once:return 1
                    # A normal main.py refresh can coexist; never race its index writer.
                    time.sleep(args.poll_seconds);continue
                except Exception as exc:
                    consecutive_errors+=1
                    intent=workdir/'cache/reference/regional_gauges/submission_intent.json'
                    import requests
                    retry_network=args.retry_network_errors and isinstance(exc,(requests.ConnectionError,requests.Timeout)) and not isinstance(exc,requests.exceptions.SSLError)
                    progress.update(state='NEEDS_ATTENTION' if intent.exists() or (consecutive_errors>=3 and not retry_network) else 'RETRYING',error_type=type(exc).__name__,consecutive_errors=consecutive_errors)
                    save_json(workdir/'inventory/precipitation_continuation.json',progress)
                    print(json.dumps(progress),flush=True)
                    if progress['state']=='NEEDS_ATTENTION' or args.once:return 1
                    time.sleep(args.poll_seconds);continue
                index_path=workdir/'cache/reference/regional_gauges/index.json'
                index=json.loads(index_path.read_text()) if index_path.exists() else {'jobs':[]}
                for item in items:
                    identity=item['delivery_id'],item['revision']
                    delivery=cached_delivery(item,workdir)
                    if not delivery:continue
                    screened=config['precipitation'].get('screening',{}).get('enabled',False)
                    receipts=reference_receipts(index,parse_time(delivery.acquired_at),config['precipitation']['networks'],require_all=not screened)
                    if not receipts:
                        plan_path=workdir/'inventory/precipitation_screening.json'
                        if screened and plan_path.exists():
                            plan=json.loads(plan_path.read_text())
                            if not any(r['selected'] and r['delivery_id']==delivery.delivery_id for r in plan['rows']):
                                registry.record(delivery,Outcome('NOT_SELECTED','Product-first screening deferred this hour; no dry control selected','NOT_REQUESTED'))
                        continue
                    signature=tuple(sorted((r['sha256'],tuple(sorted(r['payload']['dataset_names']))) for r in receipts))
                    if completed.get(identity)==signature:continue
                    registry.discover(delivery)
                    with registry.db:registry.db.execute('UPDATE deliveries SET uri=? WHERE product=? AND delivery_id=? AND revision=?',(delivery.uri,delivery.product,delivery.delivery_id,delivery.revision))
                    outcome=adapter.validate(delivery,config['products']['S5-02-04'],workdir);registry.record(delivery,outcome)
                    if outcome.status in ('DIAGNOSTIC','PROCESSED','COMPLETE','REJECTED_QA'):completed[identity]=signature
                generate(registry,config,workdir,'S5-02-04');snapshot(registry,workdir)
                progress.update(completed_deliveries=len(completed),reference_refresh=refresh,
                    evaluated_dates=sorted({r['acquired_at'][:10] for r in registry.rows('S5-02-04') if r['status']=='DIAGNOSTIC'}))
                if len(completed)==len(items):progress['state']='COMPLETE'
                elif config['precipitation'].get('screening',{}).get('enabled',False) and refresh.get('selection_complete'):progress['state']='COMPLETE_SELECTED'
                elif refresh.get('blocked_reference_quota'):progress['state']='NEEDS_QUOTA'
                save_json(workdir/'inventory/precipitation_continuation.json',progress);print(json.dumps(progress),flush=True)
                if progress['state'] in ('COMPLETE','COMPLETE_SELECTED','NEEDS_QUOTA') or args.once:return 0 if progress['state']!='NEEDS_QUOTA' else 1
                time.sleep(args.poll_seconds)
        except Exception as exc:
            save_json(workdir/'inventory/precipitation_continuation.json',{'updated_at':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),'state':'NEEDS_ATTENTION','error_type':type(exc).__name__})
            raise
        finally:registry.close()


if __name__=='__main__':raise SystemExit(main())
