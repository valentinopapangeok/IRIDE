# S5-02 operational performance

Active workbook: [SVC_OPS_Plan_S5-02_internal.xlsx](SVC_OPS_Plan_S5-02_internal.xlsx).
Use this file for ongoing updates. Client workbooks, templates, backups and files
in `../outputs/` are references or prior exports, not the active working copy.

Start with [AGENTS.md](AGENTS.md). Read supporting documents once as needed:

| Need | File |
| --- | --- |
| Field meanings and historical reconciliation | [POPULATION_RULES.md](POPULATION_RULES.md) |
| Save and verify a batch | [REPORTING_CHECKLIST.md](REPORTING_CHECKLIST.md) |
| Normal/VOID and DL/ET expectations | [DELIVERY_LOGIC.md](DELIVERY_LOGIC.md) |
| Open evidence gaps | [MISSING_EVIDENCE.md](MISSING_EVIDENCE.md) |
| Structured runs | `data/som_runs.json` |
| Issue observations by submission day | `data/issues_YYYY-MM-DD.json` |
| Evidence index | `data/evidence_manifest.json` and `.csv` |
| Originals | `evidence/YYYY-MM-DD/` |
| Categorised copies | `evidence/categorised/YYYY-MM-DD/product/type/` |

The user supplies screenshots for observed issues. Missing screenshots establish
neither success nor failure. Match procurement plans to schedules by activation
and product/reference-date evidence, never by adjacent numbers. Preserve later
status changes; skip duplicate submissions and log skipped captures.

Search `data/` for a specific issue/date first, then open only its evidence.
`.ignore` omits backups, templates, categorised copies and inspection dumps from
ordinary ripgrep discovery; every file remains directly accessible. Avoid dumping
the full evidence manifest or workbook into chat. Keep a short task-specific
checkpoint of completed writes and pending steps during long updates.

Earlier wording, including obsolete workbook paths and schema positions, is
retained in `docs/history/reporting_guidance_before_2026-11-02.md` for provenance.
