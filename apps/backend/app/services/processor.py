from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from app.schemas import ParsedResult, Property, Sample

Processor = Callable[[dict[str, Any]], ParsedResult]
PROCESSORS: dict[str, Processor] = {}


def register(name: str) -> Callable[[Processor], Processor]:
    def wrapper(func: Processor) -> Processor:
        PROCESSORS[name] = func
        return func
    return wrapper


def process_result(processor_name: str, raw: dict[str, Any]) -> ParsedResult:
    processor = PROCESSORS.get(processor_name, parse_generic)
    return processor(raw)


def _headers(samples: list[Sample]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for sample in samples:
        for key in sample.properties:
            if key not in seen:
                seen.add(key)
                ordered.append(key)
    return ordered


@register("generic")
def parse_generic(raw: dict[str, Any]) -> ParsedResult:
    if "samples" in raw:
        samples = [Sample.model_validate(sample) for sample in raw["samples"]]
        return ParsedResult(success=True, samples=samples, headers=_headers(samples))
    return ParsedResult(success=False, error="Unsupported raw result shape")


@register("code_friendly")
def parse_code_friendly(raw: dict[str, Any]) -> ParsedResult:
    text = str(raw.get("text") or raw.get("step1") or "")
    samples: list[Sample] = []
    current_name: str | None = None
    current_props: dict[str, Property] = {}
    header_pattern = re.compile(r"^\s*#\s*SAMPLE\s*:\s*(.+)$", re.IGNORECASE)
    prop_pattern = re.compile(r"^\s*-\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)(?:\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?))?\s*$")

    def flush() -> None:
        nonlocal current_name, current_props
        if current_name:
            samples.append(Sample(name=current_name, properties=current_props))
        current_name = None
        current_props = {}

    for line in text.splitlines():
        if match := header_pattern.match(line):
            flush()
            current_name = match.group(1).strip()
            continue
        match = prop_pattern.match(line)
        if match and current_name:
            name, value, unit, remark, source, method = [part.strip() if part else "" for part in match.groups()]
            if unit.upper() in {"N/A", "NONE", "NULL"}:
                unit = ""
            current_props[name] = Property(value=value, unit=unit, remark=remark, source=source, method=method)
    flush()
    return ParsedResult(success=bool(samples), samples=samples, headers=_headers(samples), error=None if samples else "No samples parsed")


@register("hierarchical_simple")
def parse_hierarchical_simple(raw: dict[str, Any]) -> ParsedResult:
    payload = raw.get("json") or raw.get("step2") or raw
    if isinstance(payload, str):
        payload = json.loads(payload)
    systems = payload.get("investigated_systems", [])
    samples: list[Sample] = []
    for system in systems:
        props: dict[str, Property] = {}
        for prop in system.get("properties", []):
            props[prop.get("name", "Unknown")] = Property(
                value=str(prop.get("value", "")),
                unit=str(prop.get("unit", "")),
                remark=str(prop.get("remark", "")),
                source=str(prop.get("source", "")),
                method=str(prop.get("method", "")),
            )
        samples.append(Sample(name=system.get("system_name", "Unknown"), properties=props))
    return ParsedResult(success=bool(samples), samples=samples, headers=_headers(samples))


@register("material_extraction")
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
            properties = sample_data.get("properties", {})
            if not isinstance(properties, dict):
                properties = {}
            props = {
                name: Property(
                    value=str(value.get("value", "")),
                    unit=str(value.get("unit", "")),
                    remark=str(value.get("remark", "")),
                    source=str(value.get("source", "")),
                    method=str(value.get("method", "")),
                )
                for name, value in properties.items()
                if isinstance(value, dict)
            }
            if props:
                samples.append(Sample(name=str(sample_name), properties=props))
        return ParsedResult(success=bool(samples), samples=samples, headers=_headers(samples), error=None if samples else "No samples parsed")

    sample_outputs = raw.get("extract_sample_data", [])
    samples: list[Sample] = []
    for item in sample_outputs:
        sample_name = item.get("sample_name", "Unknown")
        data = item.get("data", {})
        props = {
            name: Property(
                value=str(value.get("value", "")),
                unit=str(value.get("unit", "")),
                remark=str(value.get("remark", "")),
                source=str(value.get("source", "")),
                method=str(value.get("method", "")),
            )
            for name, value in data.items()
            if isinstance(value, dict)
        }
        samples.append(Sample(name=sample_name, properties=props))
    return ParsedResult(success=bool(samples), samples=samples, headers=_headers(samples))
