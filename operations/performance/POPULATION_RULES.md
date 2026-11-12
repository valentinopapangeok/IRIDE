# Reporting population rules

Use `SVC_OPS_Plan_S5-02_internal.xlsx` here. Preserve internal evidence,
timeliness, delivery-logic tabs and existing records. Read actual headers before
editing; column positions in old references/builders are not authoritative.

## Activation tab: OPS_S5-02

- Display the activation ID with its native SOM hyperlink. Preserve the exact
  known destination, including returnUrl; never append `/c` to that URL.
- Data submission is the activation submission date. Data Ref. Start/End are the
  actual activation reference period, including monthly products. Neither field
  comes from screenshot observation dates or delivery deadlines.
- Preserve event-reference notes and internal issue links. Blank client Issue
  cells do not authorize removing internal traceability.

## Issue tab: OPS_Issue_S5-02

- Retain established `OPS-YYYYMMDD-schedule` IDs; never renumber historical rows.
- Match activation, product and reference-date evidence; schedule + 1 is invalid.
  An activation can group multiple plans without proving individual pairing.
- Link the activation reference using its exact known SOM URL. Preserve separate
  reference/recovery activation and schedule/delivery IDs only when evidenced.
  If supplied as reference text, `ISS-domain_.../c` is not an absolute URL.
- Inherit submission and activation period by activation ID. Production Ref.
  Date is the affected product date from the schedule. Observation date belongs
  in evidence/run logs. Store dates as dates and display dd/mm/yyyy.
- Follow DELIVERY_LOGIC.md for notes. Record KPI references/DT/PT only when
  explicitly evidenced and requested. Separate OMC events use KPI_Issue_S5-02.
- On 16 October the issue schema expanded to 21 columns. Use current headers,
  not the former L/M or later Q/U positions copied from historical descriptions.

## Preserved reconciliation decisions

- The 12 October reference corrects OPS-20261006-618 to 3 October 2026.
- OPS-20261006-679: reference calls SST_MED mandatory; archived plan 680 says
  optional. Preserve the recorded conflict until evidence resolves it.
- Preserve supplied separate activation values for older issues 328/330/332;
  do not infer one-to-one remediation. On 12 October the user limited the active
  issue map to that day's non-DL issues; historical evidence remains archived.
- Schedules 972/973 and plans 975/976 share ISS-domain_S5-328; this establishes
  activation grouping, not individual plan-to-schedule pairing.

Historical wording is in `docs/history/`; consult it only for a specific prior
record discrepancy. Current workbook headers and the latest user instruction win.
