# Sources

## Real-World Formats Researched

The data shapes are based on common enterprise export patterns:

- SAP material movement / MB51-style exports with plant, posting date, movement type, material, quantity, unit, cost center, and document number.
- Utility electricity billing portal exports with account number, meter id, site, bill period, kWh, peak demand, tariff, and supplier.
- Concur/Navan-style corporate travel expense exports with report id, employee id, cost center, expense type, travel date, route, amount, currency, vendor, and booking reference.

The included files are simplified but intentionally keep naming and validation issues that show up in real source data.

## Assumptions Made

- SAP fuel records are Scope 1.
- Purchased electricity records are Scope 2.
- Corporate travel records are Scope 3.
- Diesel, petrol, and LPG factors are fixed as requested.
- HFO marine is treated as diesel-like for the prototype because no separate factor was provided.
- Utility electricity uses one placeholder grid factor of `0.716 kg CO2e/kWh`.
- Travel distance fallback is route-table based for DEL-BOM, DEL-BLR, and BOM-SIN.
- Hotel emissions use a simple per-night placeholder factor.

## What Would Break In Production

- Hard-coded emission factors would not support methodology changes.
- CSV headers may vary by SAP variant, utility portal, or travel administrator.
- Large files should not be parsed synchronously in the request cycle.
- Authentication and authorization are not implemented.
- Duplicate detection is file-local for the prototype and would need broader source-system rules.
- Travel routes need a real distance service and international route handling.
- Utility emission factors should vary by grid, market instrument, and reporting period.
