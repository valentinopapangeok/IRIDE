# Historical reporting guidance, archived 2026-11-02

Superseded wording retained for provenance. Read current root guidance for updates.

## Original README.md

# S5-02 operational performance

For every future reporting update, start with [REPORTING_CHECKLIST.md](REPORTING_CHECKLIST.md) and [POPULATION_RULES.md](POPULATION_RULES.md). These contain the client-aligned field meanings, screenshot and hyperlink requirements, and verification steps.

Fixed internal workbook: [SVC_OPS_Plan_S5-02_internal.xlsx](SVC_OPS_Plan_S5-02_internal.xlsx). Keep using this file for ongoing updates. The official/client workbook is a separate reference; do not replace the internal workbook with it.

Before screenshot-driven updates, read [AGENTS.md](AGENTS.md), [REPORTING_CHECKLIST.md](REPORTING_CHECKLIST.md), and [POPULATION_RULES.md](POPULATION_RULES.md).

Daily updates: archive original screenshots under evidence/YYYY-MM-DD by observation date. Add SOM, Prefect and other evidence without replacing earlier captures. Extract product, reference dates, schedule/item IDs, production UTC timestamps and each separate status. Link each observation to its evidence. Deduplicate by product + reference date + schedule; preserve later status changes as dated observations. Update the report run log and linked issue rows, retaining existing activation-plan dates and identifiers.

The initial batch contains 15 screenshots and 14 unique modal runs. Captures 09.53.39 and 09.54.15 both show schedule 772. Dates on SOM are MM/DD/YYYY; production header timestamps are explicitly UTC. Workflow-panel times display two hours later; use the UTC header for durations. Do not infer root cause, SLA compliance, delivered counts, or success from schedule completion alone. Unknown means details were collapsed or absent. N/A is preserved exactly. Void is separate from successful non-void production.

Coverage is partial: five products, reference dates 1–4 October 2026, with gaps. Missing screenshots are not failures. Background list rows are not included as fully evidenced runs. No performance target was supplied, so SLA compliance remains unassessed.

Original template is retained under templates. Structured run records are in data/som_runs.json. The workbook SOM_Run_Log is the daily reporting detail; OPS_Issue_S5-02 contains observed failures and delivery/void items awaiting review. Issue IDs are local tracking IDs, not SOM-assigned incidents. Prefect evidence should supply causes and recovery details before closing issues.

Match procurement and schedules by the ISS-domain activation ID from the catalog path and activation context. The schedule-number + 1 rule was withdrawn by the user on 7 October 2026. Do not assign individual plans or inherit reference dates from numbering.

Always copy and categorise every screenshot, including duplicates. Categorised copies are under evidence/categorised/YYYY-MM-DD/product/type. The complete manifest is data/evidence_manifest.csv (and JSON). Keep MISSING_EVIDENCE.md current and tell the user what remains missing after each batch.

Updated screenshot policy: do not save duplicates, including equivalent overviews with the same plan, ICRs and statuses. Keep existing archived material; record skipped submissions. Latest procurement batch saved 10 new captures and skipped 13.

User correction: supplied schedules are the produced runs. Other schedules are not yet produced; prior missing-coverage requests are superseded. Deadline confirmed as end of reference date + target days in Europe/Rome.

Monthly deadline confirmed by user: products 07/08 are due by end of the 9th day of the following month, Europe/Rome. October 2026 reference products are due 9 November 2026. This supersedes earlier pending monthly-anchor notes.

SOM activation reference ID format confirmed by user: activation ID + /c, e.g. ISS-domain_S5-303/c. Stored as reference text in OPS_Issue_S5-02; no absolute URL was supplied for this reference format.

Match procurement and schedules by the ISS-domain activation ID from the catalog path and activation context. The schedule-number + 1 rule was withdrawn by the user on 7 October 2026. Do not assign individual plans or inherit reference dates from numbering.

Current internal workbook: ../outputs/01a11037-f7cc-7470-9e1d-a321aeb89406/SVC_OPS_Plan_S5-02_internal.xlsx. Follow POPULATION_RULES.md for future updates; client date-field conventions supersede earlier interpretations.

As of 16 October, the client issue sheet uses 21 columns with separate reference/recovery IDs and KPI references. The internal workbook follows that layout in `OPS_Issue_S5-02`; `KPI_Issue_S5-02` remains a separate tab for actual OMC breach events. The user now sends screenshots only for observed issues, so a missing screenshot must never be interpreted as a healthy run. The 16 October evidence adds non-blocking optional-input issues for schedules 689 and 752; both show successful workflows and DL/ET delivery. See `data/issues_2026-10-16.json` for precise inputs and evidence.


## Original POPULATION_RULES.md

# Reporting population rules

Adopted from the client-corrected report supplied on 6 October 2026. These rules supersede earlier date-field interpretations and builders.

## Authoritative internal workbook

Use `SVC_OPS_Plan_S5-02_internal.xlsx` in this directory for future updates. Preserve internal evidence, timeliness and delivery-logic tabs. Do not rerun earlier builders that use the previous issue schema.

## Activation tab: OPS_S5-02

- SOM Activation Id Link: display the activation ID, e.g. ISS-domain_S5-303, with its native hyperlink to the corresponding SOM activation request. Preserve the exact client-supplied destination, including returnUrl. Do not append /c. Inspect underlying hyperlinks as well as cell values.
- Data submission: activation submission date, not screenshot collection or reporting date.
- Data Ref. Start and Data Ref. End: activation reference period from the activation plan. October 2026 is 1–31 October, including monthly products. Do not put delivery deadlines here.
- Preserve existing event-reference notes and internal issue links. The client left Issue blank; this does not establish that internal traceability links should be removed.

## Issue tab: OPS_Issue_S5-02

- Issue ID retains OPS-YYYYMMDD-schedule. The client clarified the header, but retained existing IDs; do not reinterpret or renumber historical IDs.
Match procurement and schedules by the ISS-domain activation ID from the catalog path and activation context. The schedule-number + 1 rule was withdrawn by the user on 7 October 2026. Do not assign individual plans or inherit reference dates from numbering.
- The activation reference in column D must be clickable, displaying the activation ID and using the exact known activation hyperlink from the activation tab/client source. The 12 October active reference places separate activation IDs in column E for selected older issues (328, 330, 332) and leaves the other cells blank; preserve those supplied values without inferring a one-to-one remediation result. Verify native hyperlinks survive every export; do not infer absence of links from plain-looking labels.
- Data submission and Data Ref. Start/End inherit the matching activation record by activation ID. Do not derive them from issue observation time or timeliness targets.
- Production Ref. Date (the active reference's current column L label) is the product reference day affected by the issue, taken from the SOM schedule. Keep it separate from the activation period and screenshot observation date.
- Note is in column M, after Production Ref. Date in column L. Preserve evidence-based blocking/non-blocking and normal/VOID delivery logic.
- Store dates as spreadsheet dates and display dd/mm/yyyy. Retain observation dates in the internal evidence/run logs.

## Reference reconciliation

The 12 October active reference lists 3 October 2026 for issue OPS-20261006-618, matching schedule evidence. Its new issue OPS-20261006-679 calls SST_MED mandatory, while archived plan 680 labels the dataset optional; the internal note records the conflict for follow-up.

## Scope of adoption

Adopt field meanings and column structure. Future reference periods must come from the actual activation, not a hardcoded October example. Other products not yet produced remain outside produced-run coverage. Continue deduplicating screenshots and reporting missing investigation evidence. On 12 October, the user confirmed all DL problems resolved and clarified that the active issue map should include only non-DL problems shown in that day's screenshots. Historical run and procurement evidence remains in its source tabs and archive; older issue rows and links are outside the active issue map.
## Corrected matching rule — 7 October 2026

Use ISS-domain activation ID. Schedules 972/973 and plans 975/976 belong to ISS-domain_S5-328. This establishes an activation-level grouping, not an individual one-to-one pairing. Match individual plans only when dates, input details or explicit evidence establish the association.


## Original REPORTING_CHECKLIST.md

# Operational reporting checklist

Use this checklist for future S5-02 reporting updates together with [POPULATION_RULES.md](POPULATION_RULES.md) and [DELIVERY_LOGIC.md](DELIVERY_LOGIC.md). Adopted from the client-corrected report and user-confirmed workflow on 6 October 2026.

## Activation information

- [ ] SOM activation ID and full activation URL.
- [ ] Product, frequency and AOI.
- [ ] Activation submission date.
- [ ] Activation reference-period start and end.
- [ ] Calendar-event reference, where applicable.

Display the activation ID as clickable text in SOM Activation Id Link. Preserve the exact known URL, including returnUrl.

## Screenshots supplied for issues

From 16 October 2026, the user sends screenshots only when an issue is observed. Do not treat a run without a screenshot as healthy, complete, or KPI compliant. Update the issue evidence for the submitted runs and preserve earlier records.

- [ ] Schedule screenshot: schedule number, product, product reference date, production timestamps and status.
- [ ] Expanded product panel: normal/VOID state, DL status, ET status and package details.
- [ ] Procurement-plan screenshot: plan number, catalog path, input names, mandatory/optional flags and ICR statuses.
- [ ] Expanded error details when an input or delivery fails; add Prefect evidence if needed.

Match procurement and schedules by the ISS-domain activation ID from the catalog path and activation context. The schedule-number + 1 rule was withdrawn by the user on 7 October 2026. Do not assign individual plans or inherit reference dates from numbering.

## Issue-row fields

- [ ] Unique issue ID using the established OPS-YYYYMMDD-schedule convention.
- [ ] Year and month of the reporting period.
- [ ] Activation reference: clickable activation ID, using the matching SOM URL.
- [ ] Reference activation ID, reference schedule/delivery IDs when shown, recovery activation/schedule/delivery IDs when supplied, product, frequency and AOI.
- [ ] Data submission: activation submission date.
- [ ] Data Ref. Start / End: activation reference period.
- [ ] Production Ref. Date: affected product day from the schedule.
- [ ] Client KPI issue ID and KPI DT/PT markers when explicitly supplied; leave blank if no KPI breach evidence is shown.
- [ ] Note describing the problem, expected delivery and observed outcome.

Do not use screenshot dates or delivery deadlines in activation reference-period fields. The 16 October client schema has 21 columns: Production Ref. Date is Q, KPI issue reference is R, KPI DT/PT are S/T, and Note is U. Match fields by header and records by stable IDs when updating. The separate `KPI_Issue_S5-02` tab records individual OMC breach events.

## Rules for the note

| Condition | Expected result |
| --- | --- |
| Mandatory data present | Normal delivery to DL and ET |
| Optional data missing | Non-blocking input issue; normal delivery to DL and ET |
| Mandatory data missing | Blocking normal production; VOID to DL, no ET required |
| Expected DL delivery fails | Blocking DL issue, including failed VOID delivery |
| Expected ET delivery fails | Blocking ET issue; does not apply to VOID |

Record N/A or unknown as unverified rather than automatically treating it as a delivery failure. Procurement errors indicate input problems; expanded details are needed to confirm exact absence. One run can have multiple issue categories.

## Before saving

- [ ] Copy and categorise new screenshots by observation date, product and evidence type; skip exact duplicates and equivalent captures with unchanged inputs/statuses.
- [ ] Update the evidence manifest and record skipped submissions. Preserve meaningful status changes as new observations.
- [ ] Match each issue to its schedule, procurement plan and activation.
- [ ] Preserve exact hyperlink destinations and verify native hyperlinks remain clickable after export.
- [ ] Store dates as dates and display dd/mm/yyyy.
- [ ] Keep internal logs, evidence tabs and existing issue links.
- [ ] Flag source discrepancies rather than copying them blindly.
- [ ] Update MISSING_EVIDENCE.md and tell the user what investigation evidence remains missing. Do not request screenshots for runs not yet produced.
- [ ] Verify affected values, formulas and layout before delivery.

## Delivery timeliness

Collect actual delivery timestamps for the required channels. Production completion timestamps are not delivery timestamps.

- Daily deadlines: end of reference date + target days, Europe/Rome.
- Monthly products 07/08: end of the 9th day of the following month, Europe/Rome.
- Targets: products 03/04/06 = 2 days; 02/05/09/11 = 4 days; 01/10 = 8 days; monthly 07/08 = 9th of following month.

Use the workbook Delivery_Targets and Delivery_Timeliness tabs and data/delivery_targets.json. Do not assign a delivery-timeliness verdict without the required delivery evidence.
