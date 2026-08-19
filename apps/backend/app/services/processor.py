from __future__ import annotations

import json
from typing import Any

from app.schemas import ExtractionResultEnvelope, Measurement, ParsedResult, Property, Sample


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


def parse_workflow_result(
    workflow: dict[str, Any], raw: dict[str, Any], config: dict[str, Any]
) -> ExtractionResultEnvelope:
    result_type = workflow.get("result_type")
    if result_type == "material_property_table":
        parsed = parse_material_extraction(raw)
        payload = parsed.model_dump(mode="json", exclude={"success", "error"})
        return _envelope(workflow, parsed.success, payload, error=parsed.error)
    if result_type == "records":
        return _parse_records(workflow, raw, config)
    if result_type == "entity_relation":
        return _parse_entity_relations(workflow, raw, config)
    return _envelope(
        workflow,
        False,
        {},
        error=f"Unsupported workflow result type: {result_type}",
        validation_errors=[f"Unknown result type {result_type!r}"],
    )


def _parse_records(
    workflow: dict[str, Any], raw: dict[str, Any], config: dict[str, Any]
) -> ExtractionResultEnvelope:
    payload = raw.get("extract_records")
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        return _envelope(
            workflow,
            False,
            {},
            error="Unsupported record extraction result shape",
            validation_errors=["extract_records.records must be an array"],
        )

    configured_fields = config.get("fields", [])
    allowed = {
        field.get("key"): field
        for field in configured_fields
        if isinstance(field, dict) and isinstance(field.get("key"), str)
    }
    records: list[dict[str, Any]] = []
    warnings = [str(value) for value in payload.get("warnings", []) if str(value).strip()]
    validation_errors: list[str] = []
    for index, record in enumerate(payload["records"]):
        if not isinstance(record, dict) or not isinstance(record.get("values"), dict):
            validation_errors.append(f"records[{index}].values must be an object")
            continue
        unknown = sorted(set(record["values"]) - set(allowed))
        if unknown:
            warnings.append(f"Record {index + 1} omitted unknown fields: {', '.join(unknown)}")
        values: dict[str, Any] = {}
        for key, value in record["values"].items():
            if key not in allowed or value in (None, ""):
                continue
            field_type = allowed[key].get("type", "text")
            normalized = _normalize_typed_value(value, field_type)
            if not _matches_field_type(normalized, field_type):
                validation_errors.append(
                    f"records[{index}].values.{key} does not match type {field_type}"
                )
                continue
            values[key] = normalized
        evidence = record.get("evidence", {})
        if not isinstance(evidence, dict):
            evidence = {}
        records.append({"values": values, "evidence": evidence})
    return _envelope(
        workflow,
        not validation_errors,
        {"fields": configured_fields, "records": records},
        warnings=warnings,
        validation_errors=validation_errors,
        error="Invalid record output" if validation_errors else None,
    )


def _parse_entity_relations(
    workflow: dict[str, Any], raw: dict[str, Any], config: dict[str, Any]
) -> ExtractionResultEnvelope:
    payload = raw.get("extract_entities")
    if not isinstance(payload, dict):
        return _envelope(
            workflow,
            False,
            {},
            error="Unsupported entity extraction result shape",
            validation_errors=["extract_entities must be an object"],
        )
    raw_entities = payload.get("entities")
    raw_relations = payload.get("relations")
    if not isinstance(raw_entities, list) or not isinstance(raw_relations, list):
        return _envelope(
            workflow,
            False,
            {},
            error="Unsupported entity extraction result shape",
            validation_errors=["entities and relations must be arrays"],
        )

    entity_types = set(config.get("entity_types", []))
    relation_types = set(config.get("relation_types", []))
    entities: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    warnings = [str(value) for value in payload.get("warnings", []) if str(value).strip()]
    for index, entity in enumerate(raw_entities):
        if not isinstance(entity, dict):
            warnings.append(f"Entity {index + 1} was not an object and was omitted")
            continue
        entity_id = str(entity.get("id", "")).strip()
        entity_type = str(entity.get("type", "")).strip()
        name = str(entity.get("name", "")).strip()
        if not entity_id or entity_id in seen_ids or entity_type not in entity_types or not name:
            warnings.append(
                f"Entity {index + 1} failed id, type, or name validation and was omitted"
            )
            continue
        seen_ids.add(entity_id)
        entities.append(
            {
                "id": entity_id,
                "type": entity_type,
                "name": name,
                "attributes": entity.get("attributes", {})
                if isinstance(entity.get("attributes"), dict)
                else {},
                "evidence": entity.get("evidence", {})
                if isinstance(entity.get("evidence"), dict)
                else {},
            }
        )

    relations: list[dict[str, Any]] = []
    for index, relation in enumerate(raw_relations):
        if not isinstance(relation, dict):
            warnings.append(f"Relation {index + 1} was not an object and was omitted")
            continue
        source = str(relation.get("source", "")).strip()
        target = str(relation.get("target", "")).strip()
        relation_type = str(relation.get("type", "")).strip()
        if source not in seen_ids or target not in seen_ids or relation_type not in relation_types:
            warnings.append(
                f"Relation {index + 1} failed endpoint or type validation and was omitted"
            )
            continue
        relations.append(
            {
                "source": source,
                "type": relation_type,
                "target": target,
                "attributes": relation.get("attributes", {})
                if isinstance(relation.get("attributes"), dict)
                else {},
                "evidence": relation.get("evidence", {})
                if isinstance(relation.get("evidence"), dict)
                else {},
            }
        )
    return _envelope(
        workflow,
        True,
        {"entities": entities, "relations": relations},
        warnings=warnings,
    )


def _normalize_typed_value(value: Any, field_type: str) -> Any:
    if field_type == "list":
        return value if isinstance(value, list) else [value]
    if field_type == "boolean" and isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    if field_type == "number" and isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value.strip()
    return value.strip() if isinstance(value, str) else value


def _matches_field_type(value: Any, field_type: str) -> bool:
    if field_type == "number":
        return not isinstance(value, bool) and isinstance(value, (int, float))
    if field_type == "boolean":
        return isinstance(value, bool)
    if field_type == "list":
        return isinstance(value, list)
    if field_type in {"text", "date"}:
        return isinstance(value, str)
    return False


def _envelope(
    workflow: dict[str, Any],
    success: bool,
    data: dict[str, Any],
    *,
    warnings: list[str] | None = None,
    validation_errors: list[str] | None = None,
    error: str | None = None,
) -> ExtractionResultEnvelope:
    errors = validation_errors or []
    return ExtractionResultEnvelope(
        success=success,
        workflow_id=str(workflow.get("id", "unknown")),
        workflow_version=str(workflow.get("version", "0.0.0")),
        result_type=str(workflow.get("result_type", "unknown")),
        data=data,
        warnings=warnings or [],
        validation={"valid": not errors, "errors": errors},
        error=error,
    )
