from decimal import Decimal
import re

from .common import ParsedRecord, get_value, has_any_column, parse_date, parse_decimal, read_csv

REQUIRED_COLUMNS = {
    "Werks": ["Werks", "Plant", "Plant Code"],
    "Buchungsdatum": ["Buchungsdatum", "Posting Date", "PostingDate"],
    "Bewegungsart": ["Bewegungsart", "Movement Type", "MovementType"],
    "Material": ["Material", "Material Code", "Fuel Type"],
    "Menge": ["Menge", "Quantity", "Qty"],
    "Einheit": ["Einheit", "Unit", "UOM"],
    "Kostenstelle": ["Kostenstelle", "Cost Center", "CostCenter"],
    "Dokument": ["Dokument", "Document", "Document Number", "Material Document"],
}

PLANTS = {
    "1000": "Delhi Manufacturing",
    "2000": "Mumbai Depot",
    "3000": "Bengaluru Assembly",
    "PL001": "Delhi Manufacturing",
    "PL002": "Mumbai Depot",
    "PL003": "Bengaluru Assembly",
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

UNIT_TO_KG = {
    "KG": Decimal("1"),
    "KGS": Decimal("1"),
    "KILOGRAM": Decimal("1"),
    "KILOGRAMS": Decimal("1"),
    "MT": Decimal("1000"),
    "TON": Decimal("1000"),
    "TONNE": Decimal("1000"),
}


def normalize_plant_code(value):
    text = (value or "").strip().upper()
    if text in PLANTS:
        return text

    match = re.search(r"\b(\d{4})(?:\.0)?\b", text)
    if match:
        return match.group(1)

    match = re.search(r"\bPL[-\s]?(\d{3})\b", text)
    if match:
        return f"PL{match.group(1)}"

    return text


def parse(uploaded_file):
    rows = read_csv(uploaded_file)
    seen_documents = set()
    records = []
    file_errors = []

    missing = [label for label, aliases in REQUIRED_COLUMNS.items() if rows and not has_any_column(rows[0], aliases)]
    if missing:
        file_errors.append(f"Missing SAP columns: {', '.join(missing)}")

    for row in rows:
        flags = []
        errors = []
        document = (get_value(row, REQUIRED_COLUMNS["Dokument"]) or "").strip()
        raw_plant = (get_value(row, REQUIRED_COLUMNS["Werks"]) or "").strip()
        plant = normalize_plant_code(raw_plant)
        material = (get_value(row, REQUIRED_COLUMNS["Material"]) or "").strip().upper()
        unit = (get_value(row, REQUIRED_COLUMNS["Einheit"]) or "").strip().upper()
        quantity = parse_decimal(get_value(row, REQUIRED_COLUMNS["Menge"]))
        posting_date = parse_date(
            get_value(row, REQUIRED_COLUMNS["Buchungsdatum"]),
            [
                "%Y%m%d",
                "%Y-%m-%d",
                "%d.%m.%Y",
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%m/%d/%Y",
                "%m-%d-%Y",
            ],
        )

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
        if unit not in UNIT_TO_LITERS and unit not in UNIT_TO_KG:
            flags.append("unsupported_or_inconsistent_unit")
        if material not in MATERIAL_FACTORS:
            flags.append("unknown_fuel_material")
        if posting_date is None:
            flags.append("invalid_posting_date")

        normalized_quantity = None
        normalized_unit = ""
        emissions = Decimal("0")
        if quantity is not None and material in MATERIAL_FACTORS:
            if unit in UNIT_TO_LITERS:
                normalized_quantity = quantity * UNIT_TO_LITERS[unit]
                normalized_unit = "L"
            elif unit in UNIT_TO_KG:
                normalized_quantity = quantity * UNIT_TO_KG[unit]
                normalized_unit = "kg"
            if normalized_quantity is not None:
                emissions = max(normalized_quantity, Decimal("0")) * MATERIAL_FACTORS[material]

        normalized = {
            "plant_code": plant,
            "raw_plant_code": raw_plant,
            "plant_name": PLANTS.get(plant),
            "movement_type": get_value(row, REQUIRED_COLUMNS["Bewegungsart"]),
            "material": material,
            "normalized_quantity": str(normalized_quantity) if normalized_quantity is not None else None,
            "normalized_unit": normalized_unit,
            "cost_center": get_value(row, REQUIRED_COLUMNS["Kostenstelle"]),
            "document_number": document,
            "emission_factor": str(MATERIAL_FACTORS.get(material, "")),
        }

        records.append(
            ParsedRecord(
                source_record_id=document,
                scope="SCOPE_1",
                activity_date=posting_date,
                category=material,
                quantity=normalized_quantity,
                unit=normalized_unit,
                emissions_kg_co2e=emissions,
                raw_data=row,
                normalized_data=normalized,
                suspicious=bool(flags or errors),
                flags=flags,
                validation_errors=errors,
            )
        )

    return records, file_errors
