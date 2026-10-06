"""Read source CSVs without changing their contents."""

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .contracts import Sample

COLUMNS = ("timestamp", "car_velocity", "car_trip", "car_voltage", "car_current",
           "power", "gps_1", "gps_2", "timestamp_original", "retroceso_detectado", "segmento")
NUMERIC = dict(zip(COLUMNS[1:8], ("speed_kmh", "trip_km", "voltage_v", "current_a",
                                "power_w", "latitude", "longitude")))
LOCAL_TIME = timezone(timedelta(hours=-5))


def read_records(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        if set(COLUMNS) - set(columns):
            raise ValueError(f"Missing required columns: {sorted(set(COLUMNS) - set(columns))}")
        return columns, list(reader)


def load_csv(path: Path) -> list[Sample]:
    _, records = read_records(path)
    samples = []
    for row_number, row in enumerate(records, 2):
        try:
            timestamp = datetime.fromisoformat(row["timestamp"])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=LOCAL_TIME)
            else:
                timestamp = timestamp.astimezone(LOCAL_TIME)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid timestamp at CSV row {row_number}") from exc
        values = {}
        for column, field in NUMERIC.items():
            try:
                values[field] = float(row[column])
            except (TypeError, ValueError):
                values[field] = float("nan")
        samples.append(Sample(row_number, timestamp, **values,
                              timestamp_original=row["timestamp_original"],
                              retroceso_detectado=row["retroceso_detectado"],
                              segmento=row["segmento"]))
    return samples
