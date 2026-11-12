#!/usr/bin/env python3
"""Run one UTC acquisition day in an isolated, persistent validation workdir."""
import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from s5validation.cli import main


def window(value):
    day=date.fromisoformat(value)
    start=datetime(day.year,day.month,day.day,tzinfo=timezone.utc)
    return start.isoformat(),(start+timedelta(days=1)).isoformat()


def main_daily(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',required=True,help='Acquisition date in UTC, YYYY-MM-DD')
    parser.add_argument('--workdir',required=True,type=Path,help='Persistent daily state, separate from the full campaign')
    parser.add_argument('--product',help='Optional S5-02 product restriction')
    parser.add_argument('--product04-evidence-workdir',action='append',type=Path,default=[],
                        help='Existing verified product-04 evidence workdir; may be repeated')
    args=parser.parse_args(argv)
    try:
        lower,upper=window(args.date)
    except ValueError as exc:
        parser.error(f'invalid UTC date: {exc}')
    base=Path(__file__).resolve().parents[1]
    config=base/'config/validation.json'
    if args.product04_evidence_workdir:
        roots=[p.expanduser().resolve() for p in args.product04_evidence_workdir]
        for root in roots:
            if not (root/'results/S5-02-04').is_dir():
                parser.error(f'product-04 evidence results missing: {root}')
        data=json.loads(config.read_text(encoding='utf-8'))
        data['precipitation']['uncertainty_adjustment']['additional_evidence_workdirs']=[str(p) for p in roots]
        args.workdir.mkdir(parents=True,exist_ok=True)
        config=args.workdir/'daily_config.json'
        config.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    parameters=['--run','--base-dir',str(base),'--workdir',str(args.workdir),
                '--config',str(config),'--acquired-from',lower,'--acquired-before',upper]
    if args.product:parameters.extend(['--product',args.product])
    return main(parameters,default_base=base)


if __name__=='__main__':
    raise SystemExit(main_daily())
