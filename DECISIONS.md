# Decisions

## Why CSV Over PDF/API

CSV is the most defensible prototype format because all three source systems commonly support exports, and CSV can be inspected, tested, and reprocessed easily. It also keeps the focus on ingestion, normalization, review, and auditability instead of integration plumbing.

Real APIs would be the long-term direction, but API credentials, vendor-specific schemas, and rate-limit behavior would add noise to a four-day prototype.

## Why Flat-File SAP Export

SAP MB51-style flat files are realistic for fuel and procurement movement data. The German headers reflect how SAP exports often preserve implementation-local field labels. A flat file also makes plant code handling, movement types, units, material codes, and document numbers easy to discuss in an interview.

## Why Row-Level Tenancy

Row-level tenancy keeps the database model simple while still showing tenant isolation. Every operational table includes a `client_id`, which makes filtering explicit and audit-friendly.

Separate schemas or databases would be valid for stricter isolation, but they would add setup complexity without improving the prototype's core ESG ingestion story.

## Why Audit Logs

ESG reporting needs defensible numbers. Audit logs show who uploaded data, what was normalized, what was flagged, and who approved or rejected records. This creates a lightweight evidence trail without building a full workflow engine.

## Source Subsets Chosen

- SAP: MB51-style flat-file fuel/procurement movements, not IDoc/BAPI/OData.
- Utility: portal CSV billing export, not PDF bill extraction or direct utility API.
- Travel: expense export with route fields, not direct Concur/Navan API pull.

These choices keep the prototype runnable while still exposing realistic ESG ingestion issues: inconsistent units, plant lookups, billing-period mismatch, missing kWh, missing amount, and route distance fallback.

## Questions For The PM

- Which emission-factor methodology should be the source of truth?
- Should approved rows become immutable, or can senior analysts reopen them?
- Are we ingesting one client at a time during onboarding, or should clients self-serve uploads?
- What minimum evidence does the auditor expect for each approved record?
- Which SAP export variant is most common among target customers?
