# Current S5-02 issues observed on 14 October 2026

The active `OPS_Issue_S5-02` tab contains only non-DL problems visible in the 14 October screenshots. Older observations remain in the historical logs and evidence archive. The user confirmed the DL issues are solved.

| Product | Schedule / reference date | Issue and input check |
| --- | --- | --- |
| 01 LST / 10 Downscaled LST | 652 / 6 Oct | Product 01 failed during input ingestion because a STAC JSON lacked the required `type` field. Its workflow was Void; no delivery is shown for product 10. All six requests in plan 653 completed, so the exact malformed JSON and its source remain unidentified. |
| 09 Aerosols | 812 / 10 Oct | Product workflow was Void and no ET products were delivered. Mandatory MCD19A2 ICR 2740 completed with `MISSING_DATA`. The provider tracker inferred 10 Oct missing from its latest 9 Oct result; a direct NASA CMR query found zero 10 Oct granules over the Italian area at the time checked. The evidence supports provider absence at that time rather than a demonstrated DCO download failure. |

The [online input availability tracker](https://valentinopapangeok.github.io/iride-input-availability/latest.json) ran at **2026-10-13 23:09:43 UTC**. Its 10 October MCD19A2 `missing` row is explicitly `inferred_from_latest`; the [NASA CMR query](https://cmr.earthdata.nasa.gov/search/granules.umm_json?short_name=MCD19A2&version=061&temporal=2026-10-10T00%3A00%3A00Z%2C2026-10-10T23%3A59%3A59Z&bounding_box=4.5%2C35.27%2C22.88%2C47.81&page_size=100) independently returned zero granules during this review. Availability may change after the check.

The other reviewed schedules (627, 687, 721, 750, and 783) completed with normal product deliveries. Their paired procurement plans (628, 688, 722, 751, and 784) show completed input requests. Plan 653 also shows completed requests despite the LST ingestion error.


## 20 October 2026 updates

Schedules 693, 756, and 818 are now recorded with their procurement and production evidence. Schedules 693 and 756 have linked production-time KPI breaches; schedule 818 has an optional-input issue with no KPI breach shown. Provider-side availability for the 16 October GCOM-C SST, VIIRS snow, and GCOM-C AOD inputs remains to be checked.


## 21 October 2026 updates

Added OPS-only records for schedules 694, 757, and 819. The 21 October KPI Values screenshot shows no KPI events. Procurement ICRs report missing inputs; provider-side availability at activation time has not yet been independently verified. Schedule 819/product 09 was Void after mandatory MCD19A2 returned MISSING_DATA.


## 22 October 2026 updates

Added OPS-only records for schedules 695 and 820; the KPI screenshot shows no events. Procurement ICRs report missing inputs. Provider-side availability has not been independently verified. Schedule 820/product 09 was Void after mandatory MCD19A2 returned MISSING_DATA.


## 22 October 2026 recovery runs

Recorded recovery activation `ISS-domain_S5-431` and schedules 1170–1173 for product 05 reference dates 13–16 October, including product item/delivery IDs 2274–2277 and UTC run times. The screenshots show completed runs and ET OK; schedule 1170 shows Datalake N/A, while 1171–1173 show Datalake OK. No procurement or input-availability audit evidence was included, and final delivery-channel timestamps are not shown, so provider availability and delivery timeliness remain unassessed.


## 23 October 2026 updates

Added four OPS-only issue records for schedules 661, 696, 730 and 821. The user reported no KPI breaches; no KPI rows were added. Screenshots and input-audit run evidence are archived for the 15, 19 and 21 October reference periods.

Input availability was checked against timestamped daily workflow logs in the public [IRIDE input availability repository](https://github.com/valentinopapangeok/iride-input-availability/actions). For product 01/10, the audit found and downloaded Sentinel-3 LST through 15 October at 23:24 UTC on 16 October, before mandatory ICR 2322 completed with MISSING_DATA at 02:46 UTC on 17 October; this supports a likely DCO retrieval failure. GCOM-C LST remained at 14 October through the 17 October audit, consistent with the optional input being unavailable upstream for the 15 October reference day. For product 04, H SAF H40B was found/downloaded through 21 October 23:40 UTC in the 21 October 23:52 UTC audit; optional ICR 2589 later completed MISSING_DATA on 23 October 02:45 UTC, supporting a likely DCO retrieval failure. GCOM-C SST for product 02/11 was not found by the 20 October audit and its last reported date on 18 October was 14 October, consistent with provider unavailability for reference day 19. For product 09, GCOM-C aerosol was not found in 20/22 October audits. MODIS AOD latest audited dates were 16 October on 20 October and 20 October on 22 October; the audit did not establish 19 October availability for the issue area/tile, so this cause remains unverified. The dated run snapshots do not prove the provider state at all ICR completion times or per-area coverage.


## 26 October 2026 updates

Added ten schedule-level OPS records for schedules 662, 663, 697, 698, 699, 761, 794, 822, 823 and 824. Procurement plans 663, 664, 698–700, 762, 795 and 823–825 are connected to schedules by shared ISS activation, product scope and the corresponding daily product-reference date. Since plan screenshots are collapsed, the date alignment was cross-checked against the sequential schedule records; plan numbers were not used as schedule keys. Optional-input misses are recorded even when products completed successfully, while missing mandatory inputs are noted for VOID/error cases.

Added 18 explicit OMC delivery-timeliness breach events for schedules 695–697 (products 02/11), 729–731 (04), 758–760 (05), 791–793 (06) and 820–822 (09). Their displayed values exceed their targets: 5d vs 4d for products 02/11, 05 and 09, and 3d vs 2d for products 04 and 06. These are KPI rows because the OMC cards explicitly show BREACH (Expired). KPI cards did not display exact event timestamps except schedule 791, so other event-time cells are left blank. Same-schedule OPS links are recorded where a separate OPS issue row exists; the link does not assert a causal connection.

The refreshed online availability audit ran at 2026-10-25 23:44:25 UTC and covers 18–24 October (25 inputs: 22 found, 3 over threshold, 3 missing). It reports Sentinel-3 WST for product 02/11, H SAF H40B for 04, Sentinel-3 OLCI and VIIRS snow for 05, MTG Cloud Mask for 06, and Sentinel-3 SYNERGY AOD for 09 present throughout that window. The product 02/11 GCOM-C SST and product 09 GCOM-C aerosol checks failed with JSONDecodeError and zero files; these are audit/query errors and do not prove provider absence. MODIS AOD is latest found on 22 October, but exact daily/AOI coverage is not established; CAMS was not checked daily. The breach sample therefore is not explained only by missing inputs: breaches for 04/05/06 overlap dates with audited required inputs present. Missing-input causation remains unproven, especially where plan-to-date matching or audit coverage is incomplete.

All 37 submitted images were catalogued; the 09:07:08 attachment is only 12×8 pixels and unreadable, so it was retained but not used. Exact duplicate captures were skipped if any were identical.

### S5-296 KPI timeline investigation (26 October)

Added OPS issue `OPS-20261026-660` for schedule 660 and appended the same evidence note to the existing OPS issues for schedules 661 and 662. The schedule screenshots show Delivery Timeliness (Systematic) marked BREACH (Expired), 9d vs an 8d target, for both product cards. Schedule 660 has DL/ET OK events before the displayed 23 October SLA+T2 cutoff; schedule 661 is VOID with DL OK and ET N/A before the 24 October cutoff; schedule 662 has DL/ET OK before the 25 October cutoff. The KPI dashboard shows product 01 twice for each reference date, while the schedule cards list products 01 and 10. This is recorded as a KPI event/deadline attribution discrepancy for investigation; the cause is unconfirmed.

Trace: [ISS-domain_S5-296](https://omc.iride.earth/#/monitoring/trace?requestId=ISS-domain_S5-296). Evidence: [schedule 660](evidence/categorised/2026-10-26/OU-S5-02-01_10/OMC_KPI/Screenshot%202026-10-26%20at%2012.17.03.png), [schedule 661](evidence/categorised/2026-10-26/OU-S5-02-01_10/OMC_KPI/Screenshot%202026-10-26%20at%2012.17.10.png), [schedule 662](evidence/categorised/2026-10-26/OU-S5-02-01_10/OMC_KPI/Screenshot%202026-10-26%20at%2012.17.17.png).


### S5-297 KPI timeline review (26 October)

Added the three OMC timeline screenshots for existing OPS schedules 695–697 and linked KPI events (products 02 and 11). Each shows Delivery Timeliness (Systematic) BREACH (Expired), 5d vs 4d, while the product cards show DL and ET events before the displayed SLA+T2 cutoff. The explanatory text says no delivery arrived by that cutoff. Recorded this mismatch for investigation; the cause is unconfirmed. No duplicate OPS issues were added.

Trace: [ISS-domain_S5-297](https://omc.iride.earth/#/monitoring/trace?requestId=ISS-domain_S5-297). Evidence: [schedule 695](evidence/categorised/2026-10-26/OU-S5-02-02_11/OMC_KPI/Screenshot%202026-10-26%20at%2012.22.30.png), [schedule 696](evidence/categorised/2026-10-26/OU-S5-02-02_11/OMC_KPI/Screenshot%202026-10-26%20at%2012.22.37.png), [schedule 697](evidence/categorised/2026-10-26/OU-S5-02-02_11/OMC_KPI/Screenshot%202026-10-26%20at%2012.22.45.png).


### S5-299 KPI timeline review (26 October)

Added OMC timeline evidence for schedules 729–731, product 04. The existing OPS issue for schedule 730 was updated; new OPS issues were added for schedules 729 and 731. Schedule 729's expanded card identifies the 20 Oct reference end and 23 Oct SLA+T2 cutoff, but shows DL/ET events on 22 Oct before the cutoff while reporting a 3d vs 2d expired breach. Schedule 730's timeline shows WF/VOID then WF/KO, DL/OK with PRODUCTION_KO, production time 18m58s OK and a 3d vs 2d delivery-timeliness breach; its reference date is confirmed as 21 Oct by procurement plan 731. Schedule 731 shows WF/ET/DL OK and a 3d vs 2d breach, but its capture does not show the reference period or cutoff, so no deadline comparison is recorded. Root cause is unconfirmed.

Trace: [ISS-domain_S5-299](https://omc.iride.earth/#/monitoring/trace?requestId=ISS-domain_S5-299). Evidence: [schedule 729](evidence/categorised/2026-10-26/OU-S5-02-04/OMC_KPI/Screenshot%202026-10-26%20at%2013.04.08.png), [schedule 730](evidence/categorised/2026-10-26/OU-S5-02-04/OMC_KPI/Screenshot%202026-10-26%20at%2013.04.11.png), [schedule 731](evidence/categorised/2026-10-26/OU-S5-02-04/OMC_KPI/Screenshot%202026-10-26%20at%2013.03.56.png).

### S5-300 KPI timeline review (26 October)

Three OMC screenshots show Delivery Timeliness (Systematic) BREACH (Expired), 5d vs 4d, for schedules 758–760 (product 05). Each expanded card gives a reference-period end and an SLA+T2 cutoff, but its explanation says no delivery arrived by that cutoff even though the same schedule card shows DL and ET timestamps before the cutoff. Production time and WF/DL/ET are shown OK in all three captures. This records the visible mismatch; its cause is unconfirmed.

- Schedule 758 / delivery 1577; reference date 18 Oct 2026; cutoff 23 Oct 23:59 UTC; DL 22 Oct 00:15:49, ET 22 Oct 00:41:27 UTC. [Screenshot](evidence/categorised/2026-10-26/OU-S5-02-05/OMC_KPI/Screenshot%202026-10-26%20at%2014.53.29.png)
- Schedule 759 / delivery 1578; reference date 19 Oct 2026; cutoff 24 Oct 23:59 UTC; DL 23 Oct 00:33:59, ET 23 Oct 01:40:34 UTC. [Screenshot](evidence/categorised/2026-10-26/OU-S5-02-05/OMC_KPI/Screenshot%202026-10-26%20at%2014.53.36.png)
- Schedule 760 / delivery 1579; reference date 20 Oct 2026; cutoff 25 Oct 23:59 UTC; DL 24 Oct 00:08:34, ET 24 Oct 00:41:04 UTC. [Screenshot](evidence/categorised/2026-10-26/OU-S5-02-05/OMC_KPI/Screenshot%202026-10-26%20at%2014.53.41.png)

Trace: [ISS-domain_S5-300](https://omc.iride.earth/#/monitoring/trace?requestId=ISS-domain_S5-300). OPS records OPS-20261026-758, OPS-20261026-759 and OPS-20261026-760 are linked to their corresponding existing KPI issue records.

### KPI register cleanup (26 October)

Following the OMC correction, KPI issues with event dates on or after 20 October 2026 were removed from the KPI register. This includes the 20 October production-time entries and the later delivery-timeliness entries recorded from schedules 695–697, 729–731, 758–760, 791–793 and 820–822. Their linked OPS records and supporting screenshots remain in the OPS register and evidence archive; their KPI links and flags have been cleared. Twelve KPI records dated before 20 October remain.


## 27 October 2026 updates

Added three orange OPS-only records for schedules 665 (19 Oct reference date), 700 (23 Oct) and 825 (23 Oct). Procurement plans 666, 701 and 826 show optional GCOM-C requests with ICR completed-with-errors counters; the affected schedules completed and delivered normally. The user reports that the GCOM provider portal was down. No KPI issue rows were added; the 27 October KPI Values screenshot is empty for its selected filters. Procurement screenshots do not expose their input reference dates, so the schedule association is based on the visible shared ISS activation and affected product and is flagged as unconfirmed by date. No GPORTAL or external availability audit was consulted.

## 2026-10-28

Added orange OPS-only records for schedules 666, 701 and 826. Plans 667, 702 and 827 show optional GCOM-C inputs with ICR `MISSING_DATA`; the displayed input dates match the schedule reference dates (20 Oct for 666; 24 Oct for 701 and 826). All three schedules completed with normal delivery and exploitation products. The user reports the GCOM provider portal was down. The KPI Values capture is empty for 27–29 October, so no KPI records were added. No GPORTAL or external availability audit was consulted.


## 29 October 2026

Added orange OPS-only entries for schedules 667 and 827. Schedule 667/product 01 completed normally and plan 668 shows optional GCOM-C SGLI LST (ICR 2355) and MOD11A1 (ICR 2357) error counters; schedule 827/product 09 completed normally and plan 828 shows an optional GCOM-C SGLI AOD (ICR 2801) error counter. The plan captures are collapsed: exact ICR result statuses and input reference dates are not visible, so same-activation/product association is recorded but exact input-date matching remains unconfirmed. The cause of the MOD11A1 error is unconfirmed. The KPI Values view for 28–29 October is empty, so no KPI issues were added. GPORTAL was not accessed, consistent with the user's instruction.


## 30 October 2026

Added orange OPS-only entries for schedule 766 (product 05) and schedule 828 (product 09), both for reference date 26 October. Plan 767 shows optional VIIRS VNP10A1F ICR 2662 `MISSING_DATA`; the user confirmed the provider did not have the data. Plan 829 shows optional GCOM-C SGLI AOD ICR 2805 `MISSING_DATA`; the user reports the data were available and requested DCO investigation. The audit capture shows a related GCOM-C product for product 09 downloaded on 27 October, but it does not establish an exact collection-level match to the AOD request. Both schedules completed with normal workflow, datalake and exploitation-tool statuses. KPI Values is empty for 29–31 October, so no KPI issues were added.


## 30 October 2026 — service requests

Recorded systematic requests ISS-domain_S5-443 through ISS-domain_S5-448 on the first tab from the SOM list screenshot. The screenshot shows each request subject, product, status and opening timestamp but no calendar reference dates; the reference-period cells are left blank. Evidence: [service-request list](evidence/categorised/2026-10-30/OU-S5-02/SOM_service_request/Screenshot%202026-10-30%20at%2010.13.46.png).


## 2 November 2026

Added seven OPS observations for schedules 670, 740, 767–769, 829 and 830. Schedule 740 was still running after approximately 8h17m in Prefect; completion, final deliveries and cause are unconfirmed. Plans 671, 768–770 and 830–831 show ICR errors but collapsed input details do not show reference dates, exact result codes, completion timestamps or batches. Same-activation/product plan candidates remain unconfirmed at date level; no MISSING_DATA or provider absence is inferred. Products 01/10 in schedule 670 and product 09 in 829 are VOID with DL OK and expected ET N/A. The other affected schedules show WF/DL/ET OK. The KPI view for 31 Oct–3 Nov is empty; the KPI register is unchanged. Schedule-740 activation is inherited from existing product-04 context, not visible in its submitted panel. All 16 screenshots retained.


### 2 November input-availability attribution

Updated six existing OPS notes and seven run-log notes. Historical audits downloaded exact 24 Oct Sentinel-3 LST on 25 Oct and exact 27 Oct MODIS AOD on 29 Oct, supporting likely DCO retrieval problems before the affected production runs. VIIRS VNP10A1F latest remains 26 Oct; NASA CMR returns zero granules over the audit Italy area for 27–29 Oct, supporting provider delay. Exact-date Sentinel-3 AOD and GCOM-C ARNP are present in today's audit, but original ICR-time availability remains unresolved. For schedule 740, 31 Oct radar and H40B inputs are present; workflow cause remains unknown. Exact plan dates, ICR times and full tile coverage remain unverified. Details: data/input_availability_assessment_2026-11-02.json. The removed schedule-740 OPS row was not restored; its existing run-log entry was updated. KPI register unchanged.


## 3 November 2026

Added OPS-20261103-707 (products 02/11, reference 30 Oct) and OPS-20261103-672 (01/10, reference 26 Oct). Both completed WF/DL/ET OK despite optional MISSING_DATA. Expanded ICR input dates confirm the respective plan-to-schedule associations. CMEMS 30 Oct was downloaded in the 31 Oct 01:34 UTC audit, before ICR 2537 failed on 2 Nov 00:45 UTC. ERA5-Land 26 Oct was downloaded in the 31 Oct 16:08 UTC audit, before ICR 2386 failed on 3 Nov 00:45 UTC. Both support likely DCO retrieval issues, subject to exact DCO file/coverage equivalence; the ERA5-Land audit sampled skin temperature at 10:00. Today's latest audit is 3 Nov 03:17:03 UTC. No KPI breaches shown for 2–4 Nov; KPI register unchanged. Archived all five screenshots and audit snapshot. Historical audit excerpts and URLs are retained in data/issues_2026-11-03.json.
