from __future__ import annotations

from io import BytesIO
from re import sub
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from xml.sax.saxutils import escape

from app.models import Job, JobItem

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_EXCEL_ROWS = 1_048_576


class ExportTooLargeError(ValueError):
    pass


HEADERS = [
    "Job ID",
    "Workflow",
    "File Name",
    "File Hash",
    "Item Status",
    "Sample",
    "Record Type",
    "Measurement Index",
    "Property Group",
    "Property",
    "Value",
    "Unit",
    "Remark",
    "Source",
    "Method",
    "Error",
]


def build_job_xlsx(job: Job) -> bytes:
    result_type = _result_type(job)
    if result_type == "records":
        result_rows = _record_result_rows(job)
        summary_rows = _record_summary_rows(job)
    elif result_type == "entity_relation":
        result_rows = _entity_result_rows(job)
        summary_rows = _entity_summary_rows(job)
    else:
        result_rows = [HEADERS, *_result_rows(job)]
        summary_rows = _summary_rows(job)
    if len(result_rows) > MAX_EXCEL_ROWS or len(summary_rows) > MAX_EXCEL_ROWS:
        raise ExportTooLargeError(
            "Excel export exceeds the 1,048,576-row worksheet limit; "
            "reduce the batch size or extraction schema"
        )
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml())
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(result_rows))
        archive.writestr("xl/worksheets/sheet2.xml", _worksheet_xml(summary_rows))
    return buffer.getvalue()


def export_filename(job: Job) -> str:
    return f"deep-dig-{job.id}.xlsx"


def _result_rows(job: Job) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for item in sorted(job.items, key=lambda value: value.ordinal):
        try:
            parsed = _result_data(item.parsed_result or {})
            samples = parsed.get("samples") if isinstance(parsed, dict) else None
            if isinstance(samples, list) and samples:
                for sample in samples:
                    rows.extend(_sample_rows(job, item, sample))
                continue
            rows.append(
                _base_row(job, item)
                + ["", "", "", "", "", "", "", "", "", "", _item_error(item, parsed)]
            )
        except Exception as exc:
            rows.append(
                _base_row(job, item)
                + [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    f"EXPORT_ITEM_ERROR: {exc}",
                ]
            )
    return rows


def _sample_rows(job: Job, item: JobItem, sample: Any) -> list[list[Any]]:
    if not isinstance(sample, dict):
        return [
            _base_row(job, item) + ["", "", "", "", "", "", "", "", "", "", "Invalid sample result"]
        ]

    sample_name = sample.get("name", "")
    properties = sample.get("properties", {})
    measurements = sample.get("measurements", [])

    rows: list[list[Any]] = []
    if isinstance(properties, dict):
        for property_name, property_value in properties.items():
            rows.append(
                _property_row(
                    job,
                    item,
                    sample_name,
                    "sample",
                    "",
                    "sample_properties",
                    property_name,
                    property_value,
                )
            )
    if isinstance(measurements, list):
        for index, measurement in enumerate(measurements, start=1):
            if not isinstance(measurement, dict):
                continue
            for property_name, property_value in _dict_items(measurement.get("conditions", {})):
                rows.append(
                    _property_row(
                        job,
                        item,
                        sample_name,
                        "measurement",
                        index,
                        "conditions",
                        property_name,
                        property_value,
                        measurement,
                    )
                )
            for property_name, property_value in _dict_items(measurement.get("performance", {})):
                rows.append(
                    _property_row(
                        job,
                        item,
                        sample_name,
                        "measurement",
                        index,
                        "performance",
                        property_name,
                        property_value,
                        measurement,
                    )
                )
    if not rows:
        rows.append(
            _base_row(job, item)
            + [sample_name, "", "", "", "", "", "", "", "", "", "No properties parsed"]
        )
    return rows


def _dict_items(value: Any):
    if isinstance(value, dict):
        return value.items()
    return []


def _property_row(
    job: Job,
    item: JobItem,
    sample_name: Any,
    record_type: str,
    measurement_index: Any,
    property_group: str,
    property_name: Any,
    property_value: Any,
    measurement: dict[str, Any] | None = None,
) -> list[Any]:
    if isinstance(property_value, dict):
        remark = property_value.get("remark", "") or (measurement or {}).get("remark", "")
        source = property_value.get("source", "") or (measurement or {}).get("source", "")
        return _base_row(job, item) + [
            sample_name,
            record_type,
            measurement_index,
            property_group,
            property_name,
            property_value.get("value", ""),
            property_value.get("unit", ""),
            remark,
            source,
            property_value.get("method", ""),
            "",
        ]
    return _base_row(job, item) + [
        sample_name,
        record_type,
        measurement_index,
        property_group,
        property_name,
        property_value,
        "",
        "",
        (measurement or {}).get("source", ""),
        "",
        "",
    ]


def _base_row(job: Job, item: JobItem) -> list[Any]:
    return [str(job.id), job.workflow_id, item.file_name, item.file_hash, item.status]


def _item_error(item: JobItem, parsed: Any) -> str:
    if item.error_message:
        return item.error_message
    if item.error_code:
        return item.error_code
    if isinstance(parsed, dict) and parsed.get("error"):
        return str(parsed["error"])
    if item.status == "cancelled":
        return "Task was cancelled"
    return "No parsed result"


def _summary_rows(job: Job) -> list[list[Any]]:
    properties = _requested_properties(job)
    rows = [["Sample", *properties]]
    for item in sorted(job.items, key=lambda value: value.ordinal):
        try:
            parsed = _result_data(item.parsed_result or {})
            samples = parsed.get("samples") if isinstance(parsed, dict) else None
            if not isinstance(samples, list):
                continue
            for sample in samples:
                if not isinstance(sample, dict):
                    continue
                rows.extend(_summary_sample_rows(sample, properties))
        except Exception:
            # The detailed Results sheet already records per-item export errors.
            # A malformed item must not prevent other summaries from exporting.
            continue
    return rows


def _requested_properties(job: Job) -> list[str]:
    config = job.config if isinstance(job.config, dict) else {}
    configured = config.get("properties")
    if isinstance(configured, list):
        return [str(value) for value in configured if str(value).strip()]

    seen: set[str] = set()
    properties: list[str] = []
    for item in sorted(job.items, key=lambda value: value.ordinal):
        parsed = _result_data(item.parsed_result or {})
        headers = parsed.get("headers") if isinstance(parsed, dict) else None
        if not isinstance(headers, list):
            continue
        for header in headers:
            name = str(header)
            if name and name not in seen:
                seen.add(name)
                properties.append(name)
    return properties


def _summary_sample_rows(sample: dict[str, Any], properties: list[str]) -> list[list[Any]]:
    sample_name = sample.get("name", "")
    sample_properties = sample.get("properties", {})
    if not isinstance(sample_properties, dict):
        sample_properties = {}
    measurements = sample.get("measurements", [])
    if not isinstance(measurements, list) or not measurements:
        return [
            [
                sample_name,
                *[
                    _summary_property_value(property_name, sample_properties)
                    for property_name in properties
                ],
            ]
        ]

    rows: list[list[Any]] = []
    for measurement in measurements:
        if not isinstance(measurement, dict):
            continue
        conditions = measurement.get("conditions", {})
        performance = measurement.get("performance", {})
        if not isinstance(conditions, dict):
            conditions = {}
        if not isinstance(performance, dict):
            performance = {}
        rows.append(
            [
                sample_name,
                *[
                    _summary_property_value(
                        property_name, sample_properties, conditions, performance
                    )
                    for property_name in properties
                ],
            ]
        )
    return rows or [
        [
            sample_name,
            *[
                _summary_property_value(property_name, sample_properties)
                for property_name in properties
            ],
        ]
    ]


def _summary_property_value(property_name: str, *groups: dict[str, Any]) -> str:
    for group in groups:
        value = group.get(property_name)
        if isinstance(value, dict):
            raw_value = str(value.get("value", "")).strip()
            unit = str(value.get("unit", "")).strip()
            if raw_value and unit:
                return f"{raw_value} {unit}"
            return raw_value or unit
        if value not in (None, ""):
            return str(value)
    return ""


def _result_type(job: Job) -> str:
    snapshot = job.workflow_snapshot if isinstance(job.workflow_snapshot, dict) else {}
    configured = snapshot.get("result_type")
    if isinstance(configured, str):
        return configured
    for item in job.items:
        parsed = item.parsed_result if isinstance(item.parsed_result, dict) else {}
        if isinstance(parsed.get("result_type"), str):
            return parsed["result_type"]
    return "material_property_table"


def _result_data(parsed: Any) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {}
    data = parsed.get("data")
    return data if isinstance(data, dict) else parsed


def _record_result_rows(job: Job) -> list[list[Any]]:
    rows: list[list[Any]] = [
        [
            "Job ID",
            "Workflow",
            "File Name",
            "File Hash",
            "Item Status",
            "Record",
            "Field Key",
            "Field",
            "Value",
            "Evidence",
            "Location",
            "Error",
        ]
    ]
    labels = _record_field_labels(job)
    for item in sorted(job.items, key=lambda value: value.ordinal):
        parsed = _result_data(item.parsed_result or {})
        records = parsed.get("records")
        if not isinstance(records, list) or not records:
            rows.append(
                _base_row(job, item)
                + ["", "", "", "", "", "", _item_error(item, item.parsed_result)]
            )
            continue
        for record_index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                continue
            values = record.get("values", {})
            evidence = record.get("evidence", {})
            if not isinstance(values, dict):
                continue
            for key, value in values.items():
                source = evidence.get(key, {}) if isinstance(evidence, dict) else {}
                if not isinstance(source, dict):
                    source = {}
                rows.append(
                    _base_row(job, item)
                    + [
                        record_index,
                        key,
                        labels.get(key, key),
                        _display_value(value),
                        source.get("quote", ""),
                        source.get("location", ""),
                        "",
                    ]
                )
    return rows


def _record_summary_rows(job: Job) -> list[list[Any]]:
    labels = _record_field_labels(job)
    keys = list(labels)
    rows: list[list[Any]] = [["File Name", "Record", *[labels[key] for key in keys]]]
    for item in sorted(job.items, key=lambda value: value.ordinal):
        records = _result_data(item.parsed_result or {}).get("records", [])
        if not isinstance(records, list):
            continue
        for index, record in enumerate(records, start=1):
            values = record.get("values", {}) if isinstance(record, dict) else {}
            if not isinstance(values, dict):
                values = {}
            rows.append(
                [item.file_name, index, *[_display_value(values.get(key, "")) for key in keys]]
            )
    return rows


def _record_field_labels(job: Job) -> dict[str, str]:
    config = job.config if isinstance(job.config, dict) else {}
    fields = config.get("fields", [])
    return {
        str(field.get("key")): str(field.get("label") or field.get("key"))
        for field in fields
        if isinstance(field, dict) and field.get("key")
    }


def _entity_result_rows(job: Job) -> list[list[Any]]:
    rows: list[list[Any]] = [
        [
            "Job ID",
            "Workflow",
            "File Name",
            "File Hash",
            "Item Status",
            "Record Type",
            "ID / Source",
            "Type",
            "Name / Target",
            "Attributes",
            "Evidence",
            "Location",
            "Error",
        ]
    ]
    for item in sorted(job.items, key=lambda value: value.ordinal):
        data = _result_data(item.parsed_result or {})
        entities = data.get("entities", [])
        relations = data.get("relations", [])
        wrote = False
        if isinstance(entities, list):
            for entity in entities:
                if not isinstance(entity, dict):
                    continue
                evidence = entity.get("evidence", {})
                evidence = evidence if isinstance(evidence, dict) else {}
                rows.append(
                    _base_row(job, item)
                    + [
                        "entity",
                        entity.get("id", ""),
                        entity.get("type", ""),
                        entity.get("name", ""),
                        _display_value(entity.get("attributes", {})),
                        evidence.get("quote", ""),
                        evidence.get("location", ""),
                        "",
                    ]
                )
                wrote = True
        if isinstance(relations, list):
            for relation in relations:
                if not isinstance(relation, dict):
                    continue
                evidence = relation.get("evidence", {})
                evidence = evidence if isinstance(evidence, dict) else {}
                rows.append(
                    _base_row(job, item)
                    + [
                        "relation",
                        relation.get("source", ""),
                        relation.get("type", ""),
                        relation.get("target", ""),
                        _display_value(relation.get("attributes", {})),
                        evidence.get("quote", ""),
                        evidence.get("location", ""),
                        "",
                    ]
                )
                wrote = True
        if not wrote:
            rows.append(
                _base_row(job, item)
                + ["", "", "", "", "", "", "", _item_error(item, item.parsed_result)]
            )
    return rows


def _entity_summary_rows(job: Job) -> list[list[Any]]:
    rows: list[list[Any]] = [["File Name", "Entities", "Relationships", "Warnings"]]
    for item in sorted(job.items, key=lambda value: value.ordinal):
        parsed = item.parsed_result if isinstance(item.parsed_result, dict) else {}
        data = _result_data(parsed)
        entities = data.get("entities", [])
        relations = data.get("relations", [])
        warnings = parsed.get("warnings", [])
        rows.append(
            [
                item.file_name,
                len(entities) if isinstance(entities, list) else 0,
                len(relations) if isinstance(relations, list) else 0,
                "; ".join(str(value) for value in warnings) if isinstance(warnings, list) else "",
            ]
        )
    return rows


def _display_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        import json

        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return "" if value is None else str(value)


def _worksheet_xml(rows: list[list[Any]]) -> str:
    row_xml = "\n".join(_row_xml(index, row) for index, row in enumerate(rows, start=1))
    column_count = max((len(row) for row in rows), default=1)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <cols>{_columns_xml(column_count)}</cols>
  <sheetData>
{row_xml}
  </sheetData>
  <autoFilter ref="A1:{_column_name(column_count)}{max(len(rows), 1)}"/>
</worksheet>"""


def _row_xml(row_index: int, values: list[Any]) -> str:
    cells = "".join(
        _cell_xml(row_index, col_index, value) for col_index, value in enumerate(values, start=1)
    )
    return f'    <row r="{row_index}">{cells}</row>'


def _cell_xml(row_index: int, col_index: int, value: Any) -> str:
    cell_ref = f"{_column_name(col_index)}{row_index}"
    text = _clean_cell_value(value)
    style = ' s="1"' if row_index == 1 else ""
    return f'<c r="{cell_ref}" t="inlineStr"{style}><is><t>{escape(text)}</t></is></c>'


def _clean_cell_value(value: Any) -> str:
    text = "" if value is None else str(value)
    text = sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\uD800-\uDFFF\uFFFE\uFFFF]", "", text)
    return text[:32767]


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _columns_xml(count: int) -> str:
    widths = [38, 24, 36, 18, 14, 24, 16, 18, 18, 28, 18, 12, 32, 24, 24, 36]
    columns = []
    for index in range(1, count + 1):
        width = widths[index - 1] if index <= len(widths) else 18
        columns.append(f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>')
    return "".join(columns)


def _content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""


def _root_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def _workbook_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Results" sheetId="1" r:id="rId1"/>
    <sheet name="Summary" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>"""


def _workbook_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def _styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""
