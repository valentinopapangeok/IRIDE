# Delivery logic

Mandatory data present: normal delivery to both DL and ET is required, even when optional data are missing. Missing optional data is non-blocking.

Mandatory data missing: normal production is blocked; VOID delivery to DL is required and ET delivery is not required. Failed VOID delivery to DL is blocking. ET N/A on VOID is expected.

Do not classify N/A as failed delivery without further evidence. Procurement errors indicate input problems; expanded evidence is needed to establish exact missing data.

Confirmed input ingestion/processing failure is a separate blocking category. Downstream products can be blocked by an upstream product failure. Keep optional missing data non-blocking; do not infer it caused a parser failure without evidence.
