import csv
import os
import tempfile
from datetime import datetime
from pathlib import Path


class FileManager:
    FIELDNAMES = [
        "time", "base", "county", "road", "place",
        "accident_info", "cause_code", "victim",
        "fatalities", "date", "latitude", "longitude",
    ]

    def __init__(self, file_path):
        """Store the path of the CSV data file."""
        self.file_path = Path(file_path)

    @staticmethod
    def _is_legacy_date(value):
        return any(
            datetime.strptime(value, date_format)
            for date_format in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y")
            if FileManager._matches_date(value, date_format)
        )

    @staticmethod
    def _matches_date(value, date_format):
        try:
            datetime.strptime(value, date_format)
        except (TypeError, ValueError):
            return False
        return True

    def load_incidents(self):
        """Read incident records, including legacy appended CSV sections."""
        if not self.file_path.exists():
            return []
        incidents = []
        canonical_fields = set(self.FIELDNAMES)
        required_fields = canonical_fields - {"latitude", "longitude"}
        with self.file_path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.reader(file)
            headers = next(reader, [])
            if not headers:
                return []
            for row in reader:
                if not row or not any(value.strip() for value in row):
                    continue
                row_headers = [value.strip() for value in row]
                if (
                    len(row_headers) == len(set(row_headers))
                    and required_fields.issubset(row_headers)
                    and set(row_headers).issubset(canonical_fields)
                ):
                    headers = row_headers
                    continue
                record = dict(zip(headers, row))
                incident = {
                    field: record.get(field, "")
                    for field in self.FIELDNAMES
                }
                if (
                    not incident["fatalities"].isdigit()
                    and incident["victim"].isdigit()
                    and self._is_legacy_date(incident["place"])
                    and not self._is_legacy_date(incident["date"])
                ):
                    incident["date"], incident["place"], incident["accident_info"] = (
                        incident["place"],
                        incident["accident_info"],
                        incident["date"],
                    )
                    incident["fatalities"], incident["victim"] = (
                        incident["victim"],
                        incident["fatalities"],
                    )
                incidents.append(incident)
        for incident in incidents:
            incident.setdefault("latitude", "")
            incident.setdefault("longitude", "")
        return incidents

    def save_incidents(self, incidents):
        """Replace the stored records with the provided collection."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                newline="",
                encoding="utf-8",
                dir=self.file_path.parent,
                prefix=f"{self.file_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = Path(file.name)
                writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                writer.writerows(incidents)
            os.replace(temporary_path, self.file_path)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    def deduplicate_incidents(self):
        """Remove exact duplicate records while preserving their first occurrence."""
        unique_incidents = []
        seen = set()
        incidents = self.load_incidents()
        for incident in incidents:
            key = tuple(incident.get(field, "") for field in self.FIELDNAMES)
            if key in seen:
                continue
            seen.add(key)
            unique_incidents.append(incident)
        removed = len(incidents) - len(unique_incidents)
        if removed:
            self.save_incidents(unique_incidents)
        return unique_incidents, removed

    def add_incident(
        self, time, date, county, road, base, place,
        accident_info, fatalities, victim, cause_code,
        latitude="", longitude="", reporter_id=None,
    ):
        """Add one incident record to the stored data."""
        incidents = self.load_incidents()
        if any(row["cause_code"] == str(cause_code) for row in incidents):
            return False

        incidents.append({
            "time": time,
            "date": date,
            "county": county,
            "road": road,
            "base": base,
            "place": place,
            "accident_info": accident_info,
            "fatalities": fatalities,
            "victim": victim,
            "cause_code": cause_code,
            "latitude": latitude,
            "longitude": longitude,
        })
        self.save_incidents(incidents)
        return True

    def file_exists(self):
        """Check whether the CSV file exists."""
        return self.file_path.is_file()
