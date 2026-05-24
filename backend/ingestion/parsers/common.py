import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation


@dataclass
class ParsedRecord:
    source_record_id: str
    scope: str
    activity_date: object
    category: str
    quantity: Decimal | None
    unit: str
    emissions_kg_co2e: Decimal
    raw_data: dict
    normalized_data: dict
    suspicious: bool = False
    flags: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)


def read_csv(uploaded_file):
    content = uploaded_file.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(content)))


def normalized_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def get_value(row, aliases, default=""):
    lookup = {normalized_key(key): value for key, value in row.items()}
    for alias in aliases:
        value = lookup.get(normalized_key(alias))
        if value is not None:
            return value
    return default


def has_any_column(row, aliases):
    keys = {normalized_key(key) for key in row}
    return any(normalized_key(alias) in keys for alias in aliases)


def parse_decimal(value):
    if value is None or str(value).strip() == "":
        return None
    normalized = str(value).strip()
    if normalized.lower() in {"nan", "none", "null", "n/a", "na", "-", "--"}:
        return None
    normalized = re.sub(r"[^\d,.\-()]", "", normalized)
    if normalized.startswith("(") and normalized.endswith(")"):
        normalized = f"-{normalized[1:-1]}"
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(",", "")
    elif "," in normalized:
        parts = normalized.split(",")
        if len(parts[-1]) == 3 and all(part.isdigit() for part in parts):
            normalized = "".join(parts)
        else:
            normalized = normalized.replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def parse_date(value, formats):
    if not value:
        return None
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None
