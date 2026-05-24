from decimal import Decimal

from .common import ParsedRecord, parse_date, parse_decimal, read_csv

REQUIRED_COLUMNS = [
    "Werks",
    "Buchungsdatum",
    "Bewegungsart",
    "Material",
    "Menge",
    "Einheit",
    "Kostenstelle",
    "Dokument",
]

PLANTS = {
    "1000": "Delhi Manufacturing",
    "2000": "Mumbai Depot",
    "3000": "Bengaluru Assembly",
}

MATERIAL_FACTORS = {
    "DIESEL-500": Decimal("2.68"),
    "HFO-MARINE": Decimal("2.68"),  # Prototype assumption: treated as diesel-like liquid fuel.
    "PETROL-91": Decimal("2.31"),
    "LPG": Decimal("1.56"),
}

UNIT_TO_LITERS = {
    "L": Decimal("1"),
    "LTR": Decimal("1"),
    "LITER": Decimal("1"),
    "LITRE": Decimal("1"),
    "KL": Decimal("1000"),
}


def parse(uploaded_file):
    rows = read_csv(uploaded_file)
    seen_documents = set()
    records = []
    file_errors = []

    missing = [col for col in REQUIRED_COLUMNS if rows and col not in rows[0]]
    if missing:
        file_errors.append(f"Missing SAP columns: {', '.join(missing)}")

    for row in rows:
        flags = []
        errors = []
        document = (row.get("Dokument") or "").strip()
        plant = (row.get("Werks") or "").strip()
        material = (row.get("Material") or "").strip().upper()
        unit = (row.get("Einheit") or "").strip().upper()
        quantity = parse_decimal(row.get("Menge"))
        posting_date = parse_date(row.get("Buchungsdatum"), ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"])

        if not document:
            flags.append("missing_document_number")
        elif document in seen_documents:
            flags.append("duplicate_document_number")
        seen_documents.add(document)

        if plant not in PLANTS:
            flags.append("unknown_plant_code")
        if quantity is None:
            errors.append("missing_or_invalid_quantity")
        elif quantity <= 0:
            flags.append("zero_or_negative_quantity")
        if unit not in UNIT_TO_LITERS:
            flags.append("unsupported_or_inconsistent_unit")
        if material not in MATERIAL_FACTORS:
            flags.append("unknown_fuel_material")
        if posting_date is None:
            flags.append("invalid_posting_date")

        liters = None
        emissions = Decimal("0")
        if quantity is not None and unit in UNIT_TO_LITERS and material in MATERIAL_FACTORS:
            liters = quantity * UNIT_TO_LITERS[unit]
            emissions = max(liters, Decimal("0")) * MATERIAL_FACTORS[material]

        normalized = {
            "plant_code": plant,
            "plant_name": PLANTS.get(plant),
            "movement_type": row.get("Bewegungsart"),
            "material": material,
            "quantity_liters": str(liters) if liters is not None else None,
            "cost_center": row.get("Kostenstelle"),
            "document_number": document,
            "emission_factor_kg_per_l": str(MATERIAL_FACTORS.get(material, "")),
        }

        records.append(
            ParsedRecord(
                source_record_id=document,
                scope="SCOPE_1",
                activity_date=posting_date,
                category=material,
                quantity=liters,
                unit="L",
                emissions_kg_co2e=emissions,
                raw_data=row,
                normalized_data=normalized,
                suspicious=bool(flags or errors),
                flags=flags,
                validation_errors=errors,
            )
        )

    return records, file_errors
