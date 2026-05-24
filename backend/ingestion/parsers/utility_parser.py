from decimal import Decimal

from .common import ParsedRecord, parse_date, parse_decimal, read_csv

REQUIRED_COLUMNS = [
    "account_number",
    "meter_id",
    "site_name",
    "bill_start",
    "bill_end",
    "kwh_consumed",
    "peak_demand_kw",
    "unit",
    "tariff_code",
    "supplier",
]

SUPPLIERS = {"BSES Yamuna", "Tata Power", "MSEDCL", "BESCOM"}
GRID_FACTOR_KG_PER_KWH = Decimal("0.716")


def parse(uploaded_file):
    rows = read_csv(uploaded_file)
    records = []
    file_errors = []

    missing = [col for col in REQUIRED_COLUMNS if rows and col not in rows[0]]
    if missing:
        file_errors.append(f"Missing utility columns: {', '.join(missing)}")

    for row in rows:
        flags = []
        errors = []
        kwh = parse_decimal(row.get("kwh_consumed"))
        peak_kw = parse_decimal(row.get("peak_demand_kw"))
        bill_start = parse_date(row.get("bill_start"), ["%Y-%m-%d", "%d/%m/%Y"])
        bill_end = parse_date(row.get("bill_end"), ["%Y-%m-%d", "%d/%m/%Y"])
        unit = (row.get("unit") or "").strip().lower()
        supplier = (row.get("supplier") or "").strip()

        if kwh is None:
            errors.append("missing_or_invalid_kwh")
        elif kwh <= 0:
            flags.append("zero_or_negative_kwh")
        if unit not in {"kwh", "kwhr"}:
            flags.append("unexpected_electricity_unit")
        if supplier not in SUPPLIERS:
            flags.append("unknown_supplier")
        if not bill_start or not bill_end or (bill_start and bill_end and bill_end < bill_start):
            flags.append("invalid_billing_period")

        emissions = max(kwh or Decimal("0"), Decimal("0")) * GRID_FACTOR_KG_PER_KWH
        source_record_id = f"{row.get('account_number', '')}:{row.get('meter_id', '')}:{row.get('bill_start', '')}"
        normalized = {
            "account_number": row.get("account_number"),
            "meter_id": row.get("meter_id"),
            "site_name": row.get("site_name"),
            "bill_start": row.get("bill_start"),
            "bill_end": row.get("bill_end"),
            "kwh_consumed": str(kwh) if kwh is not None else None,
            "peak_demand_kw": str(peak_kw) if peak_kw is not None else None,
            "supplier": supplier,
            "tariff_code": row.get("tariff_code"),
            "emission_factor_kg_per_kwh": str(GRID_FACTOR_KG_PER_KWH),
        }

        records.append(
            ParsedRecord(
                source_record_id=source_record_id,
                scope="SCOPE_2",
                activity_date=bill_end,
                category="Purchased electricity",
                quantity=kwh,
                unit="kWh",
                emissions_kg_co2e=emissions,
                raw_data=row,
                normalized_data=normalized,
                suspicious=bool(flags or errors),
                flags=flags,
                validation_errors=errors,
            )
        )

    return records, file_errors
