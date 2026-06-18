import csv
import difflib
import json
import os
import unicodedata
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from db import SessionLocal
from services import synchronize_customer


DATA_DIR = Path(os.getenv("ETL_DATA_DIR", "data"))
DEFAULT_INPUT_FILE = DATA_DIR / "customers_feed.csv"
DEFAULT_REJECTS_FILE = DATA_DIR / "customers_rejected.csv"
DEFAULT_CITY_DICTIONARY_FILE = DATA_DIR / "polskie_miejscowosci.json"
CITY_REJECT_DECISION = "__reject__"
CITY_AUTO_MATCH_THRESHOLD = 0.90
CITY_UNCERTAIN_MATCH_THRESHOLD = 0.78
CITY_AUTO_MATCH_MIN_GAP = 0.05
CITY_MAX_SUGGESTIONS = 5
POLISH_CHARACTER_TRANSLATION = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
        "Ą": "a",
        "Ć": "c",
        "Ę": "e",
        "Ł": "l",
        "Ń": "n",
        "Ó": "o",
        "Ś": "s",
        "Ź": "z",
        "Ż": "z",
    }
)


@dataclass
class CustomerRecord:
    row_number: int

    imie: str
    nazwisko: str
    email: str
    telefon: int

    miejscowosck: str
    ulica: str
    kodpocztowyk: str
    krajk: str


@dataclass
class RejectedRow:
    row_number: int
    reason: str
    source: dict


@dataclass
class CityCorrection:
    row_number: int
    original_city: str
    corrected_city: str
    match_type: str
    confidence: float | None = None


@dataclass
class PendingCityMatch:
    row_number: int
    original_city: str
    suggestions: list[dict]


@dataclass
class EtlResult:
    extracted: int = 0
    transformed: int = 0
    loaded: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    rejected_file: str | None = None
    city_corrections: int = 0
    city_correction_details: list[dict] = field(default_factory=list)
    pending_city_matches: int = 0
    pending_city_match_details: list[dict] = field(default_factory=list)
    needs_city_confirmation: bool = False

    def summary(self):

        lines = [
            f"Extracted rows:        {self.extracted}",
            f"Transformed customers: {self.transformed}",
            f"Skipped rows:          {self.skipped}",
            f"City corrections:      {self.city_corrections}",
            f"Pending city matches:  {self.pending_city_matches}",
        ]

        if self.loaded:
            lines.extend([
                f"Loaded customers:      {self.loaded}",
                f"Inserted customers:    {self.inserted}",
                f"Updated customers:     {self.updated}",
            ])

        return lines


def normalize_text(value):
    return " ".join(str(value or "").strip().split())


def normalize_city_key(value):
    text = normalize_text(value).casefold()
    text = text.translate(POLISH_CHARACTER_TRANSLATION)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    return " ".join(
        "".join(
            character if character.isalnum() else " "
            for character in text
        ).split()
    )


@lru_cache(maxsize=4)
def load_city_dictionary(dictionary_file=str(DEFAULT_CITY_DICTIONARY_FILE)):
    dictionary_file = Path(dictionary_file)

    with dictionary_file.open("r", encoding="utf-8") as file:
        source_rows = json.load(file)

    cities_by_key = {}

    for row in source_rows:
        canonical_city = normalize_text(row.get("Name"))
        city_key = normalize_city_key(canonical_city)

        if not canonical_city or not city_key:
            continue

        city_record = {
            "city": canonical_city,
            "type": normalize_text(row.get("Type")),
            "province": normalize_text(row.get("Province")),
            "district": normalize_text(row.get("District")),
            "commune": normalize_text(row.get("Commune")),
        }

        existing_record = cities_by_key.get(city_key)

        if (
            not existing_record
            or (
                existing_record["type"] != "city"
                and city_record["type"] == "city"
            )
        ):
            cities_by_key[city_key] = city_record

    if not cities_by_key:
        raise ValueError(
            f"City dictionary is empty: {dictionary_file}"
        )

    return {
        "cities_by_key": cities_by_key,
        "keys": list(cities_by_key.keys()),
    }


def city_candidate_to_dict(city_key, city_record, confidence):
    return {
        "city": city_record["city"],
        "type": city_record["type"],
        "province": city_record["province"],
        "district": city_record["district"],
        "commune": city_record["commune"],
        "confidence": round(confidence, 3),
        "city_key": city_key,
    }


def get_city_candidates(city_key, city_dictionary):
    candidate_keys = difflib.get_close_matches(
        city_key,
        city_dictionary["keys"],
        n=CITY_MAX_SUGGESTIONS,
        cutoff=CITY_UNCERTAIN_MATCH_THRESHOLD
    )

    candidates = []

    for candidate_key in candidate_keys:
        confidence = SequenceMatcher(
            None,
            city_key,
            candidate_key
        ).ratio()
        city_record = city_dictionary["cities_by_key"][candidate_key]
        candidates.append(
            city_candidate_to_dict(
                candidate_key,
                city_record,
                confidence
            )
        )

    return sorted(
        candidates,
        key=lambda candidate: (
            candidate["confidence"],
            candidate["type"] == "city",
        ),
        reverse=True
    )


def is_clear_fuzzy_match(candidates):
    if not candidates:
        return False

    best_confidence = candidates[0]["confidence"]
    second_confidence = (
        candidates[1]["confidence"]
        if len(candidates) > 1
        else 0
    )

    return (
        best_confidence >= CITY_AUTO_MATCH_THRESHOLD
        and best_confidence - second_confidence >= CITY_AUTO_MATCH_MIN_GAP
    )


def normalize_city_decisions(city_decisions):
    if not city_decisions:
        return {}

    return {
        int(row_number): decision
        for row_number, decision in city_decisions.items()
    }


def correct_city(
    city,
    city_dictionary,
    row_number,
    city_decisions=None
):
    original_city = normalize_text(city)
    city_key = normalize_city_key(original_city)
    city_decisions = normalize_city_decisions(city_decisions)

    if not original_city:
        raise ValueError("missing city")

    if city_key in city_dictionary["cities_by_key"]:
        corrected_city = city_dictionary["cities_by_key"][city_key]["city"]

        correction = None
        if corrected_city != original_city:
            correction = CityCorrection(
                row_number=row_number,
                original_city=original_city,
                corrected_city=corrected_city,
                match_type="normalized exact",
                confidence=1.0
            )

        return corrected_city, correction, None

    decision = city_decisions.get(row_number)

    if decision:
        if decision == CITY_REJECT_DECISION:
            raise ValueError(
                f"city '{original_city}' rejected by user"
            )

        decision_key = normalize_city_key(decision)
        city_record = city_dictionary["cities_by_key"].get(decision_key)

        if not city_record:
            raise ValueError(
                f"confirmed city '{decision}' not found in dictionary"
            )

        corrected_city = city_record["city"]

        return corrected_city, CityCorrection(
            row_number=row_number,
            original_city=original_city,
            corrected_city=corrected_city,
            match_type="user confirmed",
            confidence=1.0
        ), None

    candidates = get_city_candidates(city_key, city_dictionary)

    if is_clear_fuzzy_match(candidates):
        corrected_city = candidates[0]["city"]

        return corrected_city, CityCorrection(
            row_number=row_number,
            original_city=original_city,
            corrected_city=corrected_city,
            match_type="fuzzy auto",
            confidence=candidates[0]["confidence"]
        ), None

    if candidates:
        return None, None, PendingCityMatch(
            row_number=row_number,
            original_city=original_city,
            suggestions=candidates
        )

    raise ValueError(
        f"city '{original_city}' not found in dictionary"
    )


def extract_customers(file_path):
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".json":

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            return data

    elif file_path.suffix.lower() == ".csv":

        with open(
            file_path,
            "r",
            encoding="utf-8",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            return list(reader)

    else:

        raise ValueError(
            f"Unsupported file type: {file_path.suffix}"
        )


def reject(row_number, reason, source, rejected):
    rejected.append(
        RejectedRow(
            row_number=row_number,
            reason=reason,
            source=dict(source)
        )
    )


def correction_to_dict(correction):
    return {
        "row_number": correction.row_number,
        "original_city": correction.original_city,
        "corrected_city": correction.corrected_city,
        "match_type": correction.match_type,
        "confidence": correction.confidence,
    }


def pending_match_to_dict(pending_match):
    return {
        "row_number": pending_match.row_number,
        "original_city": pending_match.original_city,
        "suggestions": pending_match.suggestions,
    }


def write_rejected_rows(rejected_rows, output_path=DEFAULT_REJECTS_FILE):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = sorted(
        {field for rejected in rejected_rows for field in rejected.source.keys()}
        | {"row_number", "reason"}
    )

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for rejected in rejected_rows:
            row = dict(rejected.source)
            row["row_number"] = rejected.row_number
            row["reason"] = rejected.reason
            writer.writerow(row)

    return output_path


def transform_customers(
    rows,
    city_dictionary_file=DEFAULT_CITY_DICTIONARY_FILE,
    city_decisions=None
):

    customers = []
    rejected = []
    city_corrections = []
    pending_city_matches = []
    city_dictionary = load_city_dictionary(str(city_dictionary_file))

    for row_number, row in enumerate(rows, start=2):

        try:
            corrected_city, city_correction, pending_city_match = correct_city(
                row["miejscowosck"],
                city_dictionary,
                row_number,
                city_decisions=city_decisions
            )

            if pending_city_match:
                pending_city_matches.append(pending_city_match)
                continue

            if city_correction:
                city_corrections.append(city_correction)

            customer = CustomerRecord(
                row_number=row_number,

                imie=normalize_text(row["imie"]),
                nazwisko=normalize_text(row["nazwisko"]),
                email=normalize_text(row["email"]),

                telefon=int(row["telefon"]),

                miejscowosck=corrected_city,
                ulica=normalize_text(row["ulica"]),
                kodpocztowyk=normalize_text(row["kodpocztowyk"]),
                krajk=normalize_text(row["krajk"]),
            )

            customers.append(customer)

        except Exception as error:
            reject(row_number, str(error), row, rejected)

    return customers, rejected, city_corrections, pending_city_matches


def load_customers(customers):

    session = SessionLocal()

    result = EtlResult(
        transformed=len(customers)
    )

    try:

        for customer in customers:

            stats = synchronize_customer(
                session,
                customer
            )

            result.inserted += stats["inserted"]
            result.updated += stats["updated"]

        session.commit()

        result.loaded = (
            result.inserted +
            result.updated
        )

        return result

    except Exception:

        session.rollback()
        raise

    finally:

        session.close()


def run_etl(
    file_path=DEFAULT_INPUT_FILE,
    dry_run=False,
    rejects_file=DEFAULT_REJECTS_FILE,
    city_dictionary_file=DEFAULT_CITY_DICTIONARY_FILE,
    city_decisions=None
):

    rows = extract_customers(file_path)

    (
        customers,
        rejected,
        city_corrections,
        pending_city_matches,
    ) = transform_customers(
        rows,
        city_dictionary_file=city_dictionary_file,
        city_decisions=city_decisions
    )

    result = EtlResult(
        extracted=len(rows),
        transformed=len(customers),
        skipped=len(rejected),
        city_corrections=len(city_corrections),
        city_correction_details=[
            correction_to_dict(correction)
            for correction in city_corrections
        ],
        pending_city_matches=len(pending_city_matches),
        pending_city_match_details=[
            pending_match_to_dict(pending_match)
            for pending_match in pending_city_matches
        ],
        needs_city_confirmation=bool(pending_city_matches),
    )

    if rejected:
        result.rejected_file = str(
            write_rejected_rows(rejected, rejects_file)
        )

    if result.needs_city_confirmation:
        return result

    if not dry_run:

        load_result = load_customers(
            customers
        )

        result.loaded = load_result.loaded
        result.inserted = load_result.inserted
        result.updated = load_result.updated

    return result
