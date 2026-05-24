from decimal import Decimal

from .common import ParsedRecord, parse_date, parse_decimal, read_csv

REQUIRED_COLUMNS = [
    "report_id",
    "employee_id",
    "cost_center",
    "expense_type",
    "travel_date",
    "origin",
    "destination",
    "distance_km",
    "amount",
    "currency",
    "vendor",
    "booking_ref",
]

ROUTE_DISTANCE_KM = {
    ("DEL", "BOM"): Decimal("1138"),
    ("BOM", "DEL"): Decimal("1138"),
    ("DEL", "BLR"): Decimal("1740"),
    ("BLR", "DEL"): Decimal("1740"),
    ("BOM", "SIN"): Decimal("3920"),
    ("SIN", "BOM"): Decimal("3920"),
}

FACTORS = {
    "AIR": Decimal("0.115"),
    "RAIL": Decimal("0.035"),
    "CAR": Decimal("0.180"),
    "HOTEL": Decimal("30.000"),
}


def parse(uploaded_file):
    rows = read_csv(uploaded_file)
    records = []
    file_errors = []

    missing = [col for col in REQUIRED_COLUMNS if rows and col not in rows[0]]
    if missing:
        file_errors.append(f"Missing travel columns: {', '.join(missing)}")

    for row in rows:
        flags = []
        errors = []
        expense_type = (row.get("expense_type") or "").strip().upper()
        origin = (row.get("origin") or "").strip().upper()
        destination = (row.get("destination") or "").strip().upper()
        distance = parse_decimal(row.get("distance_km"))
        amount = parse_decimal(row.get("amount"))
        travel_date = parse_date(row.get("travel_date"), ["%Y-%m-%d", "%d/%m/%Y"])

        if amount is None:
            errors.append("missing_or_invalid_amount")
        if expense_type not in FACTORS:
            flags.append("unknown_expense_type")
        if travel_date is None:
            flags.append("invalid_travel_date")

        distance_source = "provided"
        if distance is None and expense_type in {"AIR", "RAIL", "CAR"}:
            distance = ROUTE_DISTANCE_KM.get((origin, destination))
            distance_source = "route_lookup"
            if distance is None:
                flags.append("missing_international_or_unknown_distance")
        if expense_type == "HOTEL":
            quantity = Decimal("1")
            emissions = FACTORS["HOTEL"]
            unit = "night"
        else:
            quantity = distance
            emissions = max(distance or Decimal("0"), Decimal("0")) * FACTORS.get(
                expense_type, Decimal("0")
            )
            unit = "km"

        source_record_id = row.get("booking_ref") or row.get("report_id") or ""
        normalized = {
            "report_id": row.get("report_id"),
            "employee_id": row.get("employee_id"),
            "cost_center": row.get("cost_center"),
            "expense_type": expense_type,
            "origin": origin,
            "destination": destination,
            "distance_km": str(distance) if distance is not None else None,
            "distance_source": distance_source,
            "amount": str(amount) if amount is not None else None,
            "currency": row.get("currency"),
            "vendor": row.get("vendor"),
            "booking_ref": row.get("booking_ref"),
            "emission_factor": str(FACTORS.get(expense_type, "")),
        }

        records.append(
            ParsedRecord(
                source_record_id=source_record_id,
                scope="SCOPE_3",
                activity_date=travel_date,
                category=expense_type,
                quantity=quantity,
                unit=unit,
                emissions_kg_co2e=emissions,
                raw_data=row,
                normalized_data=normalized,
                suspicious=bool(flags or errors),
                flags=flags,
                validation_errors=errors,
            )
        )

    return records, file_errors
