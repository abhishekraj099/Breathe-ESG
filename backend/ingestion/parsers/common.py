import csv
import io
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


def parse_decimal(value):
    if value is None or str(value).strip() == "":
        return None
    normalized = str(value).strip().replace(",", ".")
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
