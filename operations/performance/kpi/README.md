# S5-02 KPI reference — 15 October 2026

The first three tabs of the internal workbook are `OPS_S5-02`, `OPS_Issue_S5-02`, and `KPI_Issue_S5-02`. The second tab records SOM operational issues; the third has four individual OMC KPI breaches. KPI definitions remain in `KPI_Definitions`. Source CSVs, screenshots, the 15 October flow log, and the client workbook are archived under `source/2026-10-15/`. The machine-readable KPI records are `definitions_2026-10-15.json`, `breach_events_2026-10-15.json`, and `breach_events_2026-10-16.json`.

| Product | Delivery target (hours / UI days) | Production target |
| --- | ---: | ---: |
| OU-S5-02-01 LST | 192 / 8d | 24h |
| OU-S5-02-02 SST | 96 / 4d | 24h |
| OU-S5-02-03 Solar Radiation | 48 / 2d | 24h |
| OU-S5-02-04 Precipitation amount | 48 / 2d | 24h |
| OU-S5-02-05 Snow cover | 96 / 4d | 24h |
| OU-S5-02-06 Cloud Cover | 48 / 2d | 24h |
| OU-S5-02-07 Methane column | 216 / 9d | 24h |
| OU-S5-02-08 Carbon Dioxide column | 216 / 9d | 24h |
| OU-S5-02-09 Aerosols | 96 / 4d | 24h |
| OU-S5-02-10 LST Downscale | 192 / 8d | 24h |
| OU-S5-02-11 SST Downscale | 96 / 4d | 24h |

The KPI codes are `KPI-01-03-02-01` for systematic delivery timeliness and `KPI-01-03-01` for production time. Both show MGP 90%. Product assignments are confirmed by the corresponding screenshots, with values matched to the downloaded CSV reports. The workbook's older `Delivery_Timeliness` values of 5 days for SST and SST Downscale were corrected to link to the 4-day targets in `Delivery_Targets`.

The breach export contains three **production-time event rows**: two for activation `ISS-domain_S5-303` / Aerosols and one for `ISS-domain_S5-297` / SST. Each displays `48 h` against `24 h`, status `BREACH Expired`. The export omits the start reference, output reference dates, schedule IDs, and event timezone. Treat 48 hours as the exported KPI expiry value, not verified production runtime. Subsequent screenshots directly identify the Aerosols events as schedules 813 (15 October) and 812 (14 October). The SST event at 14 October 00:00:31 was initially correlated to schedule 685; the user later identifies schedule 687. Its schedule card shows production time 13m 37s OK, while KPI Values shows the 2d breach. The internal record now reflects schedule 687 and flags this unresolved conflict. Two screenshots repeat schedule 813; they are not distinct events.

The 16 appended OPS issue rows reproduce the updated client workbook, including its notes and issue identifiers. They are SOM operational observations. Two internal OPS issues were added from the new schedule evidence: `OPS-20261015-688` for SST/SST Downscale (02/11) and `OPS-20261015-813` for Aerosols (09). Schedule 688 has an Error/failed workflow, SST Void, DL OK, and ET N/A. Procurement plan 689 has four completed requests, including the mandatory S3 input. The supplied Prefect log identifies a STACTypeError during SST input ingestion: a referenced JSON lacks its required `type` field. The exact malformed JSON path and origin are not logged; the product-11 panel is collapsed, so its outcome is not established by these screenshots. Schedule 813 was Void with mandatory MCD19A2 request ICR 2744 in plan 814 returning `MISSING_DATA`; provider-side publication state remains unverified. Older SOM issues, including `OPS-20261014-812` and `OPS-20261012-685`, remain unchanged. The erroneous duplicate `OPS-20261015-812` was removed.

`KPI_Issue_S5-02` records six OMC breach rows individually: two for product 09 (schedules 813 and 812), one for product 02 (schedule 687 per user mapping, with conflicting schedule-level KPI evidence), one for product 05 (schedule 752), and two product 01 rows shown in the 16 October dashboard. The product 01 production-time row is linked to schedule 654; its systematic delivery-timeliness row has no schedule link because the screenshot gives output dates 6 October and no schedule ID. Product 11 is affected by the earlier SST failure in SOM evidence but has no separate OMC KPI row. The new 15 October OPS issue for schedule 688 remains distinct from the earlier product 02 OMC event.

The exports do not define the KPI clock's start point or the MGP denominator and aggregation window. The monthly products' displayed 9-day KPI target does not, by itself, establish their operational calendar deadline. Use the separately documented delivery deadline rule when assessing individual deliveries, and obtain actual delivery timestamps before declaring a delivery breach.

The 16 October client workbook adds KPI issue-reference cells to its expanded OPS issue sheet, including `KPI-20261015-688`. These are client references and are preserved in the internal OPS sheet. They are not additional rows in the supplied three-event OMC export. The user now provides screenshots only for observed issues; no screenshot for another run or KPI does not establish compliance.

On 16 October, schedule 752/product 05 completed successfully with WF/DL/ET OK, yet OMC displayed a 2-day production-time `BREACH Expired` against a 1-day target. Plan 753 shows mandatory S3 ICR 2633 collected at 14 October 02:01:09 local, matching the KPI's 14 October 00:01:09 start after timezone conversion. Optional VIIRS ICR 2634 ended `MISSING_DATA` at 16 October 02:09:14 local, just before the workflow started at 16 October 00:09:19 UTC. The user identifies this as an OMC last-input timestamp selection bug: the KPI used the earlier green input, whereas the later missing-input event should be the relevant trigger. The timestamps support this account; the OMC implementation is not independently verified. The separate delivery-timeliness KPI was `3d 17m 53s OK`.

Schedule 654/products 01 and 10 is a separate SOM issue. An earlier modal showed Scheduled with no production start or workflow; a later event panel shows only `PRODUCTIONS_PLANNED`, with deliveries 1417/1418 `IN_PROGRESS` and awaiting events. Plan 655 has completed mandatory inputs, one optional ICR still sent, and another completed with errors; the error detail and exact reason production did not start are not shown. The 16 October OMC dashboard shows a product 01 production-time breach, which the user maps to schedule 654. The KPI row is now linked to that OPS issue. The same dashboard shows a product 01 systematic delivery-timeliness breach for 6 October output references; no schedule match is evidenced.
