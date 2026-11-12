import json
import shutil
from pathlib import Path

root = Path('/Volumes/Extreme/IRIDE/MKPL/operational_performance')
desktop = Path('/Users/valentinopapandrea/Desktop')
items = [
    ('09.30.58', 'OU-S5-02-05', 'OMC_KPI'),
    ('09.33.32', 'OU-S5-02-01_10', 'SOM_procurement'),
    ('09.33.42', 'OU-S5-02-01_10', 'SOM_schedule'),
    ('09.36.46', 'OU-S5-02-05', 'SOM_procurement'),
    ('09.47.59', 'OU-S5-02-01_02_05_09', 'OMC_KPI'),
    ('09.49.13', 'OU-S5-02-01_10', 'SOM_schedule'),
    ('09.50.07', 'OU-S5-02-02_11', 'SOM_schedule'),
]
for time, product, category in items:
    name = f'Screenshot 2026-10-16 at {time}.png'
    source = desktop / name
    original = root / 'evidence/2026-10-16' / name
    categorised = root / 'evidence/categorised/2026-10-16' / product / category / name
    for destination in (original, categorised):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

data_path = root / 'data/issues_2026-10-16.json'
data = json.loads(data_path.read_text())
issue752 = next(issue for issue in data['issues'] if issue['schedule'] == 752)
issue752['kpi_breach_shown'] = True
issue752['related_kpi_event_id'] = 'KPI-20261016-752'
issue752['omc_issue'] = 'Reported last-input timestamp selection bug: KPI starts at the green mandatory input (14 Oct 02:01:09 local / 00:01:09 UTC), rather than later optional MISSING_DATA (16 Oct 02:09:14 local) that preceded workflow start (16 Oct 00:09:19 UTC). The panel records a 2d production-time breach against a 1d target. Timestamp alignment supports the interpretation; OMC implementation is not independently verified.'
issue752['evidence'] += ['Screenshot 2026-10-16 at 09.30.58.png', 'Screenshot 2026-10-16 at 09.36.46.png']
issue654 = next(issue for issue in data['issues'] if issue['schedule'] == 654)
issue654['observed_production'] = 'Latest event panel shows only PRODUCTIONS_PLANNED; deliveries 1417/1418 are IN_PROGRESS and awaiting events. An earlier modal showed Scheduled and workflow unavailable.'
issue654['kpi_breach_shown'] = True
issue654['related_kpi_event_id'] = 'KPI-20261016-01-PT'
issue654['kpi_breach'] = 'OMC dashboard shows OU-S5-02-01 production time 2d vs 1d, event 16 October 00:00:33 UTC. User maps this breach to schedule 654.'
issue654['evidence'] += ['Screenshot 2026-10-16 at 09.47.59.png', 'Screenshot 2026-10-16 at 09.49.13.png']
if not any(issue['schedule'] == 654 for issue in data['issues']):
    data['issues'].append({
        'id': 'OPS-20261016-654',
        'schedule': 654,
        'procurement_plan': 655,
        'activation': 'ISS-domain_S5-296',
        'products': ['OU-S5-02-01', 'OU-S5-02-10'],
        'reference_date': '2026-10-08',
        'category': 'scheduled production did not start',
        'observed_production': 'Scheduled; production start/end N/A; workflow unavailable',
        'mandatory_icrs_completed': [2280, 2281],
        'optional_icrs_completed': [2276, 2277],
        'optional_icr_sent': 2278,
        'optional_icr_error': 2279,
        'optional_icr_error_result': None,
        'cause_established': False,
        'kpi_breach_shown': False,
        'evidence': ['Screenshot 2026-10-16 at 09.33.32.png', 'Screenshot 2026-10-16 at 09.33.42.png']
    })
data_path.write_text(json.dumps(data, indent=2) + '\n')

kpi_path = root / 'kpi/breach_events_2026-10-16.json'
kpi_path.write_text(json.dumps({
    'source_type': 'OMC KPI Values dashboard screenshot and corroborating SOM schedule/procurement screenshots; not a CSV export',
    'events': [{
        'id': 'KPI-20261016-752',
        'schedule': 752,
        'delivery': 1571,
        'product': 'OU-S5-02-05',
        'kpi_code': 'KPI-01-03-01',
        'name': 'Service Timeliness - Production time',
        'displayed_value_hours': 48,
        'target_hours': 24,
        'status': 'BREACH Expired',
        'kpi_start_shown': '2026-10-14 00:01:09',
        'kpi_deadline_shown': '2026-10-16 00:01:09',
        'input_recorded_as_start': {'icr': 2633, 'dataset': 'S3_OLCI_L2LFR', 'status': 'COLLECTED', 'local_time': '2026-10-14 02:01:09'},
        'later_input': {'icr': 2634, 'dataset': 'dc_viirs_vnp10a1f', 'status': 'MISSING_DATA', 'local_time': '2026-10-16 02:09:14'},
        'workflow_start_utc': '2026-10-16 00:09:19',
        'systematic_delivery_kpi': '3d 17m 53s OK',
        'reported_diagnosis': 'OMC used the earlier green input as last-received-input start; user says it should use the later missing-input event immediately before workflow start. Supported by timestamp alignment; implementation not independently verified.',
        'related_ops_issue_id': 'OPS-20261016-752',
        'evidence': ['Screenshot 2026-10-16 at 09.30.58.png', 'Screenshot 2026-10-16 at 09.36.46.png', 'Screenshot 2026-10-16 at 09.17.02.png']
    }, {
        'id': 'KPI-20261016-01-PT',
        'schedule': 654,
        'activation': 'ISS-domain_S5-296',
        'product': 'OU-S5-02-01',
        'kpi_code': 'KPI-01-03-01',
        'displayed_value': '2d',
        'target': '1d',
        'status': 'BREACH Expired',
        'event_time_utc': '2026-10-16 00:00:33',
        'schedule_evidence': 'Only PRODUCTIONS_PLANNED is shown; deliveries 1417/1418 are IN_PROGRESS awaiting events.',
        'match_basis': 'User identifies schedule 654 for the product 01 breach; activation and product also match.',
        'related_ops_issue_id': 'OPS-20261016-654',
        'evidence': ['Screenshot 2026-10-16 at 09.47.59.png', 'Screenshot 2026-10-16 at 09.49.13.png']
    }, {
        'id': 'KPI-20261016-01-DT',
        'activation': 'ISS-domain_S5-296',
        'schedule': None,
        'product': 'OU-S5-02-01',
        'kpi_code': 'KPI-01-03-02-01',
        'displayed_value': '9d',
        'target': '8d',
        'status': 'BREACH Expired',
        'output_reference_start_utc': '2026-10-06 00:00:00',
        'output_reference_end_utc': '2026-10-06 23:59:00',
        'event_time_utc': '2026-10-15 23:59:00',
        'match_basis': 'Direct dashboard row; no schedule match evidenced.',
        'related_ops_issue_id': None,
        'evidence': ['Screenshot 2026-10-16 at 09.47.59.png']
    }, {
        'id': 'KPI-20261015-003',
        'schedule': 687,
        'activation': 'ISS-domain_S5-297',
        'product': 'OU-S5-02-02',
        'kpi_code': 'KPI-01-03-01',
        'displayed_value': '2d',
        'target': '1d',
        'status': 'BREACH Expired',
        'event_time_utc': '2026-10-14 00:00:31',
        'user_schedule_mapping': True,
        'conflict': 'KPI Values shows breach; schedule 687 card shows production-time KPI 13m 37s OK.',
        'evidence': ['Screenshot 2026-10-16 at 09.47.59.png', 'Screenshot 2026-10-16 at 09.50.07.png']
    }]
}, indent=2) + '\n')
