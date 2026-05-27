# Model

## Multi-Tenancy

The prototype uses row-level tenancy. `Client` owns `DataSource`, `IngestionBatch`, `EmissionRecord`, and `AuditLog` rows. API calls default to a demo client, but the model is designed so a real authenticated request could resolve the client from a user account or token.

This keeps tenancy simple and explainable for a prototype while avoiding separate databases or schemas per tenant.

## Source Of Truth

`DataSource` records the enterprise origin of a file: SAP fuel/procurement, utility electricity, or corporate travel. `IngestionBatch` records the exact upload event and original filename. `EmissionRecord.source_record_id` stores the source identifier, such as SAP document number or travel booking reference.

Every row also stores `raw_data` as JSON. This is important because normalized ESG values must remain traceable back to the original export.

The prototype does not allow analysts to edit source values directly. Instead, it records review decisions separately through `review_status`, `reviewed_by`, `reviewed_at`, and `AuditLog.before` / `AuditLog.after`. That means the original source row remains the system of record, while any review change is visible as an audit event.

## Normalization

Parser modules convert source-specific fields into a common `EmissionRecord` shape:

- activity date
- source type
- scope
- category
- normalized quantity and unit
- kg CO2e
- flags and validation errors

SAP fuel rows normalize units into liters. Utility rows normalize electricity into kWh. Travel rows normalize distance-based categories into kilometers and hotel rows into nights.

## Audit Trail

`AuditLog` stores batch upload and record review events. Review changes capture `before` and `after` JSON so an analyst decision can be reconstructed later. Raw source rows are never overwritten during review.

Approved records are marked `locked_for_audit` with a `locked_at` timestamp. This keeps the prototype simple while making the handoff from analyst review to audit-ready data explicit.

## Scope Mapping

- SAP fuel/procurement exports map to `SCOPE_1`.
- Utility electricity exports map to `SCOPE_2`.
- Corporate travel exports map to `SCOPE_3`.

The scope is stored on each emission record so reporting can aggregate across sources without re-running parser logic.
