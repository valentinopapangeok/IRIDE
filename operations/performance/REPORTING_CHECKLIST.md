# Batch reporting checklist

Read AGENTS.md and the field meanings in POPULATION_RULES.md once per task.
Use the current workbook headers and preserve the active workbook's layout.

## Capture and match

- [ ] Extract only the submitted issue evidence: activation, product, frequency,
      AOI, schedule/delivery IDs, product reference date, UTC production times,
      normal/VOID state, DL/ET result and procurement mandatory/optional statuses.
- [ ] Match plan and schedule by activation plus product/date evidence. Preserve
      uncertainty where expanded details or exact associations are absent.
- [ ] Copy original and categorised evidence; skip exact/equivalent unchanged
      submissions, record skips, retain meaningful later status changes.
- [ ] Add only requested issue rows; apply DELIVERY_LOGIC.md. Separate KPI events
      require actual breach evidence and user scope permitting KPI updates.

## Save and verify

- [ ] Verify stable IDs, activation dates, product dates, notes and recovery links.
- [ ] Verify native hyperlinks and exact destinations after export.
- [ ] Store dates as dates (dd/mm/yyyy) and production timestamps as UTC.
- [ ] Update relevant issue JSON, run/procurement logs and both evidence manifests.
- [ ] Keep all columns visible and preserve prior records, formulas and internal
      tabs. For OPS-only batches, verify KPI data is unchanged.
- [ ] Update MISSING_EVIDENCE.md for actual investigation gaps; do not request
      screenshots for runs not yet produced. Verify changed values and layout.

## Delivery timeliness, when requested

Actual delivery timestamps are required; production completion is not delivery.
Use Delivery_Targets/Delivery_Timeliness tabs and `data/delivery_targets.json`.
Daily deadlines are end of reference date + target days in Europe/Rome:
03/04/06 = 2 days, 02/05/09/11 = 4, 01/10 = 8. Monthly 07/08 are due at the end
of the 9th day of the following month. Do not assign a verdict without evidence.
