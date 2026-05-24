from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

from django.db import migrations


SAP_PLANTS = {
    "1000": "Delhi Manufacturing",
    "2000": "Mumbai Depot",
    "3000": "Bengaluru Assembly",
    "PL001": "Delhi Manufacturing",
    "PL002": "Mumbai Depot",
    "PL003": "Bengaluru Assembly",
}

SAP_FACTORS = {
    "DIESEL-500": Decimal("2.68"),
    "HFO-MARINE": Decimal("2.68"),
    "PETROL-91": Decimal("2.31"),
    "LPG": Decimal("1.56"),
}

SAP_LITER_UNITS = {
    "L": Decimal("1"),
    "LTR": Decimal("1"),
    "LITER": Decimal("1"),
    "LITRE": Decimal("1"),
    "KL": Decimal("1000"),
}

SAP_KG_UNITS = {
    "KG": Decimal("1"),
    "KGS": Decimal("1"),
    "KILOGRAM": Decimal("1"),
    "KILOGRAMS": Decimal("1"),
    "MT": Decimal("1000"),
    "TON": Decimal("1000"),
    "TONNE": Decimal("1000"),
}

def decimal_value(value):
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null", "n/a", "na", "-", "--"}:
        return None
    text = re.sub(r"[^\d,.\-()]", "", text)
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    if "," in text and "." in text:
        text = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        text = "".join(parts) if len(parts[-1]) == 3 and all(part.isdigit() for part in parts) else text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def date_value(value):
    if not value:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def normalize_plant(value):
    text = (value or "").strip().upper()
    if text in SAP_PLANTS:
        return text
    match = re.search(r"\b(\d{4})(?:\.0)?\b", text)
    if match:
        return match.group(1)
    match = re.search(r"\bPL[-\s]?(\d{3})\b", text)
    if match:
        return f"PL{match.group(1)}"
    return text


def recompute_sap(record):
    row = record.raw_data or {}
    flags = []
    errors = []
    document = str(row.get("Dokument") or "").strip()
    raw_plant = str(row.get("Werks") or "").strip()
    plant = normalize_plant(raw_plant)
    material = str(row.get("Material") or "").strip().upper()
    unit = str(row.get("Einheit") or "").strip().upper()
    quantity = decimal_value(row.get("Menge"))
    posting_date = date_value(row.get("Buchungsdatum"))

    if not document:
        flags.append("missing_document_number")
    if plant not in SAP_PLANTS:
        flags.append("unknown_plant_code")
    if quantity is None:
        errors.append("missing_or_invalid_quantity")
        flags.append("missing_or_invalid_quantity")
    elif quantity <= 0:
        flags.append("zero_or_negative_quantity")
    if unit not in SAP_LITER_UNITS and unit not in SAP_KG_UNITS:
        flags.append("unsupported_or_inconsistent_unit")
    if material not in SAP_FACTORS:
        flags.append("unknown_fuel_material")
    if posting_date is None:
        flags.append("invalid_posting_date")

    normalized_quantity = None
    normalized_unit = ""
    emissions = Decimal("0")
    if quantity is not None and material in SAP_FACTORS:
        if unit in SAP_LITER_UNITS:
            normalized_quantity = quantity * SAP_LITER_UNITS[unit]
            normalized_unit = "L"
        elif unit in SAP_KG_UNITS:
            normalized_quantity = quantity * SAP_KG_UNITS[unit]
            normalized_unit = "kg"
        if normalized_quantity is not None:
            emissions = max(normalized_quantity, Decimal("0")) * SAP_FACTORS[material]

    record.category = material
    record.activity_date = posting_date
    record.quantity = normalized_quantity
    record.unit = normalized_unit
    record.emissions_kg_co2e = emissions
    record.normalized_data = {
        "plant_code": plant,
        "raw_plant_code": raw_plant,
        "plant_name": SAP_PLANTS.get(plant),
        "movement_type": row.get("Bewegungsart"),
        "material": material,
        "normalized_quantity": str(normalized_quantity) if normalized_quantity is not None else None,
        "normalized_unit": normalized_unit,
        "cost_center": row.get("Kostenstelle"),
        "document_number": document,
        "emission_factor": str(SAP_FACTORS.get(material, "")),
    }
    record.flags = flags
    record.validation_errors = errors
    record.suspicious = bool(flags or errors)


def recompute_existing_records(apps, schema_editor):
    EmissionRecord = apps.get_model("ingestion", "EmissionRecord")
    IngestionBatch = apps.get_model("ingestion", "IngestionBatch")

    changed_batches = set()
    queryset = EmissionRecord.objects.filter(source_type="SAP_FUEL").select_related("ingestion_batch")
    for record in queryset.iterator():
        recompute_sap(record)
        record.save(
            update_fields=[
                "activity_date",
                "category",
                "quantity",
                "unit",
                "emissions_kg_co2e",
                "normalized_data",
                "suspicious",
                "flags",
                "validation_errors",
            ]
        )
        changed_batches.add(record.ingestion_batch_id)

    for batch in IngestionBatch.objects.filter(id__in=changed_batches):
        records = list(batch.records.all())
        batch.total_rows = len(records)
        batch.accepted_rows = len([record for record in records if not record.validation_errors])
        batch.suspicious_rows = len([record for record in records if record.suspicious])
        batch.rejected_rows = len([record for record in records if record.validation_errors])
        batch.save(update_fields=["total_rows", "accepted_rows", "suspicious_rows", "rejected_rows"])


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0002_emissionrecord_locked_at_and_more"),
    ]

    operations = [
        migrations.RunPython(recompute_existing_records, migrations.RunPython.noop),
    ]
