import csv
import hashlib
import json
from pathlib import Path

root = Path('/Volumes/Extreme/IRIDE/MKPL/operational_performance')
items = [
    ('09.15.03', 'SOM_procurement', 'OU-S5-02-02_11', 689, 690, '2026-10-12'),
    ('09.15.15', 'SOM_schedule', 'OU-S5-02-02_11', 689, 690, '2026-10-12'),
    ('09.17.02', 'SOM_schedule', 'OU-S5-02-05', 752, 753, '2026-10-12'),
    ('09.17.09', 'SOM_procurement', 'OU-S5-02-05', 752, 753, '2026-10-12'),
    ('09.30.58', 'OMC_KPI', 'OU-S5-02-05', 752, 753, '2026-10-12'),
    ('09.33.32', 'SOM_procurement', 'OU-S5-02-01_10', 654, 655, '2026-10-08'),
    ('09.33.42', 'SOM_schedule', 'OU-S5-02-01_10', 654, 655, '2026-10-08'),
    ('09.36.46', 'SOM_procurement', 'OU-S5-02-05', 752, 753, '2026-10-12'),
    ('09.47.59', 'OMC_KPI', 'OU-S5-02-01_02_05_09', None, None, None),
    ('09.49.13', 'SOM_schedule', 'OU-S5-02-01_10', 654, 655, '2026-10-08'),
    ('09.50.07', 'SOM_schedule', 'OU-S5-02-02_11', 687, None, None),
]
new = []
for time, category, product, schedule, plan, reference_date in items:
    filename = f'Screenshot 2026-10-16 at {time}.png'
    original = f'evidence/2026-10-16/{filename}'
    categorized = f'evidence/categorised/2026-10-16/{product}/{category}/{filename}'
    path = root / original
    new.append({
        'filename': filename,
        'observed_on': '2026-10-16',
        'category': category,
        'product': product,
        'reference_date': reference_date,
        'schedule': schedule,
        'procurement_plan': plan,
        'duplicate_capture': False,
        'original_archive': original,
        'categorised_copy': categorized,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    })

json_path = root / 'data/evidence_manifest.json'
records = json.loads(json_path.read_text())
existing = {record['filename'] for record in records}
records += [record for record in new if record['filename'] not in existing]
json_path.write_text(json.dumps(records, indent=2) + '\n')

csv_path = root / 'data/evidence_manifest.csv'
with csv_path.open(newline='') as file:
    reader = csv.DictReader(file)
    fields = reader.fieldnames
    csv_records = list(reader)
csv_existing = {record['filename'] for record in csv_records}
with csv_path.open('w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(csv_records)
    writer.writerows({key: record.get(key) for key in fields} for record in new if record['filename'] not in csv_existing)

(root / 'evidence/2026-10-16/manifest.json').write_text(json.dumps(new, indent=2) + '\n')
