"""
Tolerant CSV parser for German bank exports.

Real bank CSVs are messy: preamble lines before the header, semicolons,
latin-1 encoding, "1.234,56" amounts, separate Soll/Haben columns. This parser
normalises all of that into `ParsedRow` objects without needing per-bank
configuration – the column mapping is done by fuzzy header matching.
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

logger = logging.getLogger(__name__)

DELIMITERS = [";", ",", "\t", "|"]

# Canonical field -> header fragments (lower case, umlauts normalised).
COLUMN_HINTS: dict[str, tuple[str, ...]] = {
    "booking_date": (
        "buchungstag", "buchungsdatum", "valutadatum", "wertstellung", "datum",
        "booking date", "value date", "date", "transaktionsdatum",
    ),
    "amount": (
        "betrag", "umsatz", "amount", "value",
    ),
    "debit": ("soll", "belastung", "ausgang"),
    "credit": ("haben", "gutschrift", "eingang"),
    "sign": ("soll/haben", "soll-haben", "s/h", "haben/soll"),
    "counterparty": (
        "beguenstigter", "zahlungspflichtiger", "auftraggeber", "empfaenger",
        "zahlungsbeteiligter", "name", "partner name", "payee", "beteiligter",
        "kontoinhaber", "gegenkonto inhaber",
    ),
    "purpose": (
        "verwendungszweck", "payment reference", "beschreibung", "description",
        "reference", "referenz", "vwz",
    ),
    "booking_text": ("buchungstext", "umsatzart", "vorgang", "transaction type", "buchungsart"),
    "currency": ("waehrung", "currency"),
    "external_id": (
        "kundenreferenz", "mandatsreferenz", "transaktions-id", "transaction id",
        "id", "referenznummer",
    ),
    "iban": ("iban", "kontonummer", "gegenkonto", "account", "partner iban"),
}

DATE_FORMATS = (
    "%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
    "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
)

UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


class CsvParseError(Exception):
    """Raised when a file cannot be interpreted as a transaction export."""


@dataclass
class ParsedRow:
    booking_date: date
    amount: Decimal
    counterparty: str = ""
    purpose: str = ""
    external_id: str = ""
    currency: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def fingerprint(self, account_id: str) -> str:
        """Stable hash used to skip rows that were already imported."""
        payload = "|".join(
            [
                str(account_id),
                self.booking_date.isoformat(),
                f"{self.amount:.2f}",
                normalise(self.counterparty)[:80],
                normalise(self.purpose)[:120],
                self.external_id.strip(),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:48]

    def describe(self) -> str:
        parts = [self.counterparty.strip(), self.purpose.strip()]
        return " – ".join(part for part in parts if part) or "Buchung"


def normalise(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).strip().lower().translate(UMLAUTS)
    return re.sub(r"\s+", " ", text)


def decode(raw: bytes) -> str:
    """Best effort decoding – German bank exports are rarely UTF-8."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        from charset_normalizer import from_bytes

        best = from_bytes(raw).best()
        if best is not None:
            return str(best)
    except Exception:  # pragma: no cover - optional dependency path
        pass
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def detect_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(DELIMITERS))
        return dialect.delimiter
    except csv.Error:
        counts = {d: sample.count(d) for d in DELIMITERS}
        return max(counts, key=counts.get) if any(counts.values()) else ";"


def find_header(rows: list[list[str]]) -> int:
    """
    Index of the header row.

    Banks like to put account information above the actual table, so we look
    for the first row that mentions a date column and has at least three cells.
    """
    for index, row in enumerate(rows[:40]):
        if len(row) < 3:
            continue
        cells = [normalise(cell) for cell in row]
        has_date = any(
            any(hint in cell for hint in COLUMN_HINTS["booking_date"]) for cell in cells
        )
        has_money = any(
            any(hint in cell for hint in COLUMN_HINTS["amount"] + COLUMN_HINTS["debit"]
                + COLUMN_HINTS["credit"])
            for cell in cells
        )
        if has_date and has_money:
            return index
    raise CsvParseError(
        "In der Datei wurde keine Kopfzeile mit Datums- und Betragsspalte gefunden."
    )


# Money columns must never be stolen by a date column ("Wertstellung").
MONEY_FIELDS = ("amount", "debit", "credit")


def _score(cell: str, hints: tuple[str, ...]) -> int:
    """
    How well a header cell matches a field.

    An exact match beats a prefix match beats a substring match, and within one
    field the earlier hint wins – that is what makes "Verwendungszweck" rank
    above "Buchungstext" when a bank exports both.
    """
    best = 0
    for rank, hint in enumerate(hints):
        if cell == hint:
            quality = 1000
        elif cell.startswith(hint):
            quality = 600
        elif hint in cell:
            quality = 300 + len(hint)
        else:
            continue
        best = max(best, quality + len(hints) - rank)
    return best


def map_columns(header: list[str]) -> dict[str, int]:
    """Map canonical field names to column indices, best match wins."""
    mapping: dict[str, int] = {}
    cells = [normalise(cell) for cell in header]
    date_like = [
        any(hint in cell for hint in COLUMN_HINTS["booking_date"]) for cell in cells
    ]
    for field_name, hints in COLUMN_HINTS.items():
        best_index: int | None = None
        best_score = 0
        for index, cell in enumerate(cells):
            if not cell or index in mapping.values():
                continue
            if field_name in MONEY_FIELDS and date_like[index]:
                continue
            score = _score(cell, hints)
            if score > best_score:
                best_index, best_score = index, score
        if best_index is not None:
            mapping[field_name] = best_index
    if "booking_date" not in mapping:
        raise CsvParseError("Es wurde keine Datumsspalte erkannt.")
    if not {"amount", "debit", "credit"} & set(mapping):
        raise CsvParseError("Es wurde keine Betragsspalte erkannt.")
    return mapping


def parse_date(value: str) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    match = re.search(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})", text)
    if match:
        day, month, year = (int(part) for part in match.groups())
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def parse_amount(value: str) -> Decimal | None:
    """Handles '1.234,56', '-1234.56', '1 234,56 EUR' and '(123,45)'."""
    text = (value or "").strip()
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^\d,.\-+]", "", text.strip("()"))
    if not text or text in {"-", "+", ".", ","}:
        return None

    if "," in text and "." in text:
        # The right-most separator is the decimal one.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")

    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    return -amount if negative else amount


def _combine(*parts: str) -> str:
    """Join purpose and booking text without repeating identical content."""
    seen: list[str] = []
    for part in parts:
        cleaned = (part or "").strip()
        if cleaned and normalise(cleaned) not in {normalise(item) for item in seen}:
            seen.append(cleaned)
    return " · ".join(seen)


def _cell(row: list[str], mapping: dict[str, int], key: str) -> str:
    index = mapping.get(key)
    if index is None or index >= len(row):
        return ""
    return (row[index] or "").strip()


def parse_rows(content: bytes | str) -> tuple[list[ParsedRow], dict[str, Any]]:
    """Parse a CSV export into normalised rows plus a small report."""
    text = decode(content) if isinstance(content, bytes) else content
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise CsvParseError("Die Datei ist leer.")

    delimiter = detect_delimiter(text[:8000])
    reader = csv.reader(io.StringIO(text), delimiter=delimiter, quotechar='"')
    raw_rows = [row for row in reader if any((cell or "").strip() for cell in row)]
    if not raw_rows:
        raise CsvParseError("Die Datei enthält keine Datenzeilen.")

    header_index = find_header(raw_rows)
    header = raw_rows[header_index]
    mapping = map_columns(header)

    rows: list[ParsedRow] = []
    skipped = 0
    for raw in raw_rows[header_index + 1:]:
        booking_date = parse_date(_cell(raw, mapping, "booking_date"))
        if booking_date is None:
            skipped += 1
            continue

        amount = parse_amount(_cell(raw, mapping, "amount"))
        if amount is None:
            debit = parse_amount(_cell(raw, mapping, "debit"))
            credit = parse_amount(_cell(raw, mapping, "credit"))
            if debit is not None and debit != 0:
                amount = -abs(debit)
            elif credit is not None and credit != 0:
                amount = abs(credit)
        if amount is None or amount == 0:
            skipped += 1
            continue

        sign = normalise(_cell(raw, mapping, "sign"))
        if sign in {"s", "soll"}:
            amount = -abs(amount)
        elif sign in {"h", "haben"}:
            amount = abs(amount)

        rows.append(
            ParsedRow(
                booking_date=booking_date,
                amount=amount,
                counterparty=_cell(raw, mapping, "counterparty"),
                purpose=_combine(
                    _cell(raw, mapping, "purpose"), _cell(raw, mapping, "booking_text")
                ),
                external_id=_cell(raw, mapping, "external_id"),
                currency=_cell(raw, mapping, "currency"),
                raw={
                    (header[i] if i < len(header) else f"col{i}"): cell
                    for i, cell in enumerate(raw)
                },
            )
        )

    if not rows:
        raise CsvParseError(
            "Es konnten keine Buchungen gelesen werden. "
            "Bitte den CSV-Export der Bank unverändert hochladen."
        )

    report = {
        "delimiter": delimiter,
        "header_row": header_index + 1,
        "columns": {key: header[index] for key, index in mapping.items() if index < len(header)},
        "rows_total": len(raw_rows) - header_index - 1,
        "rows_parsed": len(rows),
        "rows_skipped": skipped,
    }
    return rows, report


def chunked(items: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]
