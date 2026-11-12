# Standalone analyses

These cases are grouped by purpose, not classified as obsolete. Their scripts,
inputs, outputs and local files were moved together without changing contents.

| Case | Entry point / notes |
| --- | --- |
| Raster smoothing experiment | `bilateral_filter/bilateral_filter.py`; own README |
| Product metadata formatting | `resolution_extraction/format_product_jsons.py`; reads sibling CSV/JSON |
| Gas product resolution comparison | `resolution_comparison_07_08/resolution_comparison.py`; old absolute external paths require review before running |
| Vulnerability export analysis | `vulnerability_reports/vulnerability_report_parsing.py --help` |

`resolution_extraction/main.py` is a retained IDE sample, not the analysis entry
point. The bilateral-filter output defaults to the current working directory;
select the case directory as the working directory to keep outputs with the case.
These scripts are not a combined workflow and have different dependencies.

Old `workflows/<case>/` paths remain symlinks to these directories. Existing IDE
working directories can still resolve. Use this canonical location for discovery.
