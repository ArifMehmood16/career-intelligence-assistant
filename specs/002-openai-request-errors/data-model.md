# Data model

No persistent entities change. Input response contracts remain the source of truth.
Their adapted copy requires all fields, retains non-nullable collection types and
preserves already-explicit nullable types.

A provider failure diagnostic contains fixed provider/operation, configured model,
HTTP status, fixed category, allowlisted vendor code and parameter. It retains no
response body/message, endpoint, request content, header or credential. Existing
worker job failure and publication rules remain unchanged.
