"""Post-report processing-geometry evidence, separate from thematic KPIs.

Evidence files are optional JSON records under workdir/positional/evidence.
The absence of a record is UNASSESSED, never a zero displacement or a pass.
"""
from __future__ import annotations

import csv
import html
import json
from pathlib import Path

HOURLY = {'S5-02-03', 'S5-02-04', 'S5-02-06'}
STATUSES = {'MEASURED_LINEAGE', 'GRID_ONLY', 'CODE_BOUND', 'UNASSESSED'}


def _selected(report: Path, delivery_rows=()) -> list[dict]:
    dates_path = report / 'kpi_dates.json'
    if not dates_path.exists():
        return []
    dates = json.loads(dates_path.read_text(encoding='utf-8'))
    passing_dates = {(row['product'], row['date'], row['area']) for row in dates if row.get('passes') is True}
    revisions = {}
    for delivery in delivery_rows:
        key = (delivery['product'], delivery['acquired_at'][:10])
        revisions.setdefault(key, set()).add(delivery['revision'])
    selected = []
    for row in dates:
        if row.get('passes') is not True or row['product'] in HOURLY:
            continue
        candidates = revisions.get((row['product'], row['date']), set())
        selected.append({'product': row['product'], 'date': row['date'],
                         'area': row['area'], 'hour_start_utc': None,
                         'revision': next(iter(candidates)) if len(candidates) == 1 else None})
    hourly_path = report / 'hourly_scores.csv'
    if hourly_path.exists():
        with hourly_path.open(newline='', encoding='utf-8') as stream:
            for row in csv.DictReader(stream):
                if row['product'] not in HOURLY or row['passes'].lower() != 'true':
                    continue
                if (row['product'], row['hour_start_utc'][:10], row['area']) not in passing_dates:
                    continue
                selected.append({'product': row['product'], 'date': row['hour_start_utc'][:10],
                                 'area': row['area'], 'hour_start_utc': row['hour_start_utc'],
                                 'revision': row['revision']})
    return selected


def _evidence_key(row: dict) -> str:
    stamp = row['hour_start_utc'][:13].replace('-', '').replace('T', '') if row['hour_start_utc'] else row['date'].replace('-', '')
    return f"{row['product']}_{stamp}_{row['area'].replace(' ', '_')}.json"


def write_summary(workdir: Path, delivery_rows=()) -> tuple[Path, list[dict]]:
    report = workdir / 'report'
    records = []
    for item in _selected(report, delivery_rows):
        evidence_path = workdir / 'positional' / 'evidence' / _evidence_key(item)
        status = 'UNASSESSED'
        evidence = {}
        if evidence_path.exists():
            evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
            status = evidence.get('status', 'UNASSESSED')
            if status not in STATUSES:
                raise ValueError(f'Invalid geometry status: {evidence_path}')
            if evidence.get('product') != item['product'] or evidence.get('date') != item['date'] or evidence.get('area') != item['area']:
                raise ValueError(f'Geometry evidence key mismatch: {evidence_path}')
            if item['revision'] is None or evidence.get('revision') != item['revision']:
                status = 'UNASSESSED'
                evidence = {'reason': 'Delivery revision is ambiguous or evidence belongs to another revision'}
        records.append({**item, 'status': status,
                        'kpi_status': evidence.get('kpi_status'),
                        'quantity': evidence.get('quantity'), 'max_m': evidence.get('max_m'),
                        'assessed_cells': evidence.get('assessed_cells'),
                        'conforming_fraction': evidence.get('conforming_fraction'),
                        'tolerance_m': evidence.get('tolerance_m'),
                        'centre_below_1000_pct': (evidence.get('centre_distance') or {}).get('below_1000_pct'),
                        'footprint_below_1000_pct': (evidence.get('footprint_distance') or {}).get('below_1000_pct'),
                        'inside_footprint_pct': (evidence.get('footprint_distance') or {}).get('inside_footprint_pct'),
                        'reason': evidence.get('reason'),
                        'evidence_file': str(evidence_path) if evidence_path.exists() else None})
    report.mkdir(parents=True, exist_ok=True)
    path = report / 'positional_geometry.json'
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)
    return path, records


def comparison_html(workdir: Path, delivery_rows=()) -> str:
    _, records = write_summary(workdir, delivery_rows)
    counts = {status: sum(r['status'] == status for r in records) for status in sorted(STATUSES)}
    cells = ''.join(
        '<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in
                          (r['product'], r['date'], r['hour_start_utc'] or '', r['area'],
                          r['status'], r.get('kpi_status') or '', r['quantity'] or '',
                          r.get('centre_below_1000_pct') if r.get('centre_below_1000_pct') is not None else '',
                          r.get('conforming_fraction') * 100 if r.get('conforming_fraction') is not None else '',
                          r.get('footprint_below_1000_pct') if r.get('footprint_below_1000_pct') is not None else '',
                          r.get('inside_footprint_pct') if r.get('inside_footprint_pct') is not None else '',
                          r['max_m'] if r['max_m'] is not None else '',
                          r['assessed_cells'] if r['assessed_cells'] is not None else '', r['reason'] or '')) + '</tr>'
        for r in records
    )
    return ('<section><h2>Processing geometry on thematic-passing dates/hours</h2>'
            '<p>Products 01, 02, 03 and 05 positional accuracy are official processing-geometry KPIs on traceable contributors/grids. Product 05 optional VIIRS replacement occurs on the OLCI grid and does not alter its positional geometry. All positional results remain separate from thematic sample coverage and contractual campaign acceptance. GRID_ONLY and UNASSESSED do not establish final-value displacement. '
            '<a href="positional_geometry.json">Download records</a>.</p>'
            f'<p>{html.escape(str(counts))}</p><div class="scroll"><table><thead><tr>'
            '<th>Product</th><th>Date</th><th>Hour UTC</th><th>Area</th><th>Status</th>'
            '<th>KPI</th><th>Quantity</th><th>Centre &lt;1,000%</th><th>Within tolerance%</th><th>Footprint &lt;1,000%</th><th>Inside footprint%</th><th>Maximum m</th><th>Cells</th><th>Reason</th></tr></thead>'
            f'<tbody>{cells}</tbody></table></div></section>')
