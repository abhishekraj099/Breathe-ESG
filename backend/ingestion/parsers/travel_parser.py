from decimal import Decimal

from .common import ParsedRecord, get_value, has_any_column, parse_date, parse_decimal, read_csv

REQUIRED_COLUMNS = {
    "report_id": ["report_id", "Report ID", "Expense Report ID"],
    "employee_id": ["employee_id", "Employee ID", "Employee"],
    "cost_center": ["cost_center", "Cost Center", "CostCenter"],
    "expense_type": ["expense_type", "Expense Type", "Category", "Travel Category"],
    "travel_date": ["travel_date", "Travel Date", "Transaction Date", "Expense Date"],
    "origin": ["origin", "Origin", "From", "Origin Airport"],
    "destination": ["destination", "Destination", "To", "Destination Airport"],
    "distance_km": ["distance_km", "Distance KM", "Distance (km)", "Distance"],
    "amount": ["amount", "Amount", "Amount INR", "Amount (INR)", "Total Amount", "Transaction Amount"],
    "currency": ["currency", "Currency"],
    "vendor": ["vendor", "Vendor", "Merchant", "Supplier"],
    "booking_ref": ["booking_ref", "Booking Ref", "Booking Reference", "PNR", "Invoice Number"],
}

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

    missing = [label for label, aliases in REQUIRED_COLUMNS.items() if rows and not has_any_column(rows[0], aliases)]
    if missing:
        file_errors.append(f"Missing travel columns: {', '.join(missing)}")

    for row in rows:
        flags = []
        errors = []
        expense_type = (get_value(row, REQUIRED_COLUMNS["expense_type"]) or "").strip().upper()
        origin = (get_value(row, REQUIRED_COLUMNS["origin"]) or "").strip().upper()
        destination = (get_value(row, REQUIRED_COLUMNS["destination"]) or "").strip().upper()
        distance = parse_decimal(get_value(row, REQUIRED_COLUMNS["distance_km"]))
        amount = parse_decimal(get_value(row, REQUIRED_COLUMNS["amount"]))
        travel_date = parse_date(
            get_value(row, REQUIRED_COLUMNS["travel_date"]),
            ["%Y%m%d", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y"],
        )

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
                flags.append("missing_distance")
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

        source_record_id = (
            get_value(row, REQUIRED_COLUMNS["booking_ref"]) or get_value(row, REQUIRED_COLUMNS["report_id"]) or ""
        )
        normalized = {
            "report_id": get_value(row, REQUIRED_COLUMNS["report_id"]),
            "employee_id": get_value(row, REQUIRED_COLUMNS["employee_id"]),
            "cost_center": get_value(row, REQUIRED_COLUMNS["cost_center"]),
            "expense_type": expense_type,
            "origin": origin,
            "destination": destination,
            "distance_km": str(distance) if distance is not None else None,
            "distance_source": distance_source,
            "amount": str(amount) if amount is not None else None,
            "currency": get_value(row, REQUIRED_COLUMNS["currency"]),
            "vendor": get_value(row, REQUIRED_COLUMNS["vendor"]),
            "booking_ref": get_value(row, REQUIRED_COLUMNS["booking_ref"]),
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
