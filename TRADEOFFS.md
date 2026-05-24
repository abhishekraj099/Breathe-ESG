# Tradeoffs

## Real SAP Integration Skipped

The prototype skips direct SAP integration because real SAP access usually requires customer-specific credentials, RFC/OData configuration, authorization roles, and network allowlisting. A flat MB51-style CSV keeps the exercise realistic while staying runnable by reviewers.

## PDF Parsing Skipped

PDF parsing is intentionally skipped because it is brittle and layout-dependent. Utility bills and travel invoices may be PDFs in production, but portal CSV exports are a better prototype source because they keep validation focused on business data rather than OCR/layout failure modes.

## Emission-Factor Versioning Skipped

Emission factors are hard-coded in parser modules for clarity. Production systems should version factors by geography, methodology, effective date, and source publication. That was skipped to keep the prototype readable and to avoid pretending that a full factor-management system exists.

## Background Jobs Skipped

Uploads are parsed synchronously. This is acceptable for small prototype files and avoids Celery/Redis complexity. Production would move large uploads to background processing with progress tracking.

## Full Immutability Skipped

Approved rows are marked as locked for audit, but the database does not enforce a hard immutability rule. Production should block edits to locked records except through an explicit reopen workflow with elevated permissions and audit logging.
