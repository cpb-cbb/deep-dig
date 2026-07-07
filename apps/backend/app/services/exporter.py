from __future__ import annotations

from io import BytesIO
from re import sub
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from xml.sax.saxutils import escape

from app.models import Job, JobItem

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

HEADERS = [
    "Job ID",
    "Workflow",
    "File Name",
    "File Hash",
    "Item Status",
    "Sample",
    "Property",
    "Value",
    "Unit",
    "Remark",
    "Source",
    "Method",
    "Error",
]


def build_job_xlsx(job: Job) -> bytes:
    rows = [HEADERS, *_result_rows(job)]
    sheet_xml = _worksheet_xml(rows)
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml())
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def export_filename(job: Job) -> str:
    return f"deep-dig-{job.id}.xlsx"


def _result_rows(job: Job) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for item in sorted(job.items, key=lambda value: value.ordinal):
        parsed = item.parsed_result or {}
        samples = parsed.get("samples") if isinstance(parsed, dict) else None
        if isinstance(samples, list) and samples:
            for sample in samples:
                rows.extend(_sample_rows(job, item, sample))
            continue
        rows.append(_base_row(job, item) + ["", "", "", "", "", "", "", _item_error(item, parsed)])
    return rows


def _sample_rows(job: Job, item: JobItem, sample: Any) -> list[list[Any]]:
    if not isinstance(sample, dict):
        return [_base_row(job, item) + ["", "", "", "", "", "", "", "Invalid sample result"]]

    sample_name = sample.get("name", "")
    properties = sample.get("properties", {})
    if not isinstance(properties, dict) or not properties:
        return [
            _base_row(job, item) + [sample_name, "", "", "", "", "", "", "No properties parsed"]
        ]

    rows: list[list[Any]] = []
    for property_name, property_value in properties.items():
        if isinstance(property_value, dict):
            rows.append(
                _base_row(job, item)
                + [
                    sample_name,
                    property_name,
                    property_value.get("value", ""),
                    property_value.get("unit", ""),
                    property_value.get("remark", ""),
                    property_value.get("source", ""),
                    property_value.get("method", ""),
                    "",
                ]
            )
        else:
            rows.append(
                _base_row(job, item)
                + [sample_name, property_name, property_value, "", "", "", "", ""]
            )
    return rows


def _base_row(job: Job, item: JobItem) -> list[Any]:
    return [str(job.id), job.workflow_id, item.file_name, item.file_hash, item.status]


def _item_error(item: JobItem, parsed: Any) -> str:
    if item.error_message:
        return item.error_message
    if item.error_code:
        return item.error_code
    if isinstance(parsed, dict) and parsed.get("error"):
        return str(parsed["error"])
    return "No parsed result"


def _worksheet_xml(rows: list[list[Any]]) -> str:
    row_xml = "\n".join(_row_xml(index, row) for index, row in enumerate(rows, start=1))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <cols>{_columns_xml(len(HEADERS))}</cols>
  <sheetData>
{row_xml}
  </sheetData>
  <autoFilter ref="A1:{_column_name(len(HEADERS))}{max(len(rows), 1)}"/>
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
    text = sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    return text[:32767]


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _columns_xml(count: int) -> str:
    widths = [38, 24, 36, 18, 14, 24, 28, 18, 12, 32, 24, 24, 36]
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
  <sheets><sheet name="Results" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""


def _workbook_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
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
