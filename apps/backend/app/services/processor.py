from __future__ import annotations

import json
from typing import Any

from app.schemas import Measurement, ParsedResult, Property, Sample


def _headers(samples: list[Sample]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(key: str) -> None:
        if key not in seen:
            seen.add(key)
            ordered.append(key)

    for sample in samples:
        for key in sample.properties:
            add(key)
        for measurement in sample.measurements:
            for key in measurement.conditions:
                add(key)
            for key in measurement.performance:
                add(key)
    return ordered


def _properties_from_mapping(values: Any) -> dict[str, Property]:
    if not isinstance(values, dict):
        return {}
    return {
        name: Property(
            value=_clean_property_field(value.get("value", "")),
            unit=_clean_property_field(value.get("unit", "")),
            remark=_clean_property_field(value.get("remark", "")),
            source=_clean_property_field(value.get("source", "")),
            method=_clean_property_field(value.get("method", "")),
        )
        for name, value in values.items()
        if isinstance(value, dict)
    }


def _clean_property_field(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.upper() in {"", "N/A", "NA", "NONE", "NULL", "NOT REPORTED"}:
        return ""
    return text


def parse_material_extraction(raw: dict[str, Any]) -> ParsedResult:
    payload = raw.get("extract_property_table")
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, dict) and isinstance(payload.get("samples"), list):
        samples: list[Sample] = []
        for sample_data in payload["samples"]:
            if not isinstance(sample_data, dict):
                continue
            sample_name = sample_data.get("sample_name") or sample_data.get("name") or "Unknown"
            properties = sample_data.get("sample_properties", sample_data.get("properties", {}))
            props = _properties_from_mapping(properties)
            measurements: list[Measurement] = []
            measurement_data = sample_data.get("measurements", [])
            if isinstance(measurement_data, list):
                for item in measurement_data:
                    if not isinstance(item, dict):
                        continue
                    conditions = _properties_from_mapping(item.get("conditions", {}))
                    performance = _properties_from_mapping(item.get("performance", {}))
                    if conditions or performance:
                        measurements.append(
                            Measurement(
                                conditions=conditions,
                                performance=performance,
                                remark=str(item.get("remark", "")),
                                source=str(item.get("source", "")),
                            )
                        )
            if props or measurements:
                samples.append(
                    Sample(name=str(sample_name), properties=props, measurements=measurements)
                )
        return ParsedResult(
            success=bool(samples),
            samples=samples,
            headers=_headers(samples),
            error=None if samples else "No samples parsed",
        )

    return ParsedResult(success=False, error="Unsupported material extraction result shape")
