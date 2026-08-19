from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

from app.models import Job, JobItem
from app.services.exporter import build_job_xlsx, export_filename


def test_build_job_xlsx_flattens_parsed_results():
    job_id = uuid4()
    job = Job(
        id=job_id,
        workflow_id="material_extraction",
        status="completed",
        total_items=1,
        completed_items=1,
        failed_items=0,
        config={
            "properties": [
                "BET surface area",
                "current density",
                "specific capacitance",
            ]
        },
    )
    job.items = [
        JobItem(
            id=uuid4(),
            job_id=job_id,
            ordinal=0,
            file_name="paper.pdf",
            file_hash="abc123456789",
            text_length=1200,
            status="done",
            parsed_result={
                "success": True,
                "result_type": "material_property_table",
                "data": {
                    "samples": [
                        {
                            "name": "PC-800",
                            "properties": {
                                "BET surface area": {
                                    "value": "1850",
                                    "unit": "m2 g-1",
                                    "remark": "KOH activated",
                                    "source": "Table 1",
                                    "method": "N2 adsorption",
                                }
                            },
                            "measurements": [
                                {
                                    "conditions": {
                                        "current density": {
                                            "value": "0.5",
                                            "unit": "A g-1",
                                            "remark": "",
                                            "source": "Figure 5a",
                                            "method": "GCD",
                                        }
                                    },
                                    "performance": {
                                        "specific capacitance": {
                                            "value": "280",
                                            "unit": "F g-1",
                                            "remark": "three-electrode",
                                            "source": "Figure 5a",
                                            "method": "GCD",
                                        }
                                    },
                                },
                            ],
                        }
                    ],
                    "headers": ["BET surface area"],
                },
            },
        )
    ]

    content = build_job_xlsx(job)

    assert content.startswith(b"PK")
    with ZipFile(BytesIO(content)) as archive:
        names = set(archive.namelist())
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names
        assert "xl/worksheets/sheet2.xml" in names
        sheet = archive.read("xl/worksheets/sheet1.xml").decode()
        summary = archive.read("xl/worksheets/sheet2.xml").decode()

    assert "paper.pdf" in sheet
    assert "PC-800" in sheet
    assert "BET surface area" in sheet
    assert "1850" in sheet
    assert "Measurement Index" in sheet
    assert "current density" in sheet
    assert "specific capacitance" in sheet
    assert "280" in sheet
    assert "Sample" in summary
    assert "BET surface area" in summary
    assert "current density" in summary
    assert "specific capacitance" in summary
    assert "1850 m2 g-1" in summary
    assert "0.5 A g-1" in summary
    assert "280 F g-1" in summary
    assert export_filename(job) == f"deep-dig-{job_id}.xlsx"


def test_build_job_xlsx_keeps_failed_items_as_error_rows():
    job_id = uuid4()
    job = Job(
        id=job_id,
        workflow_id="material_extraction",
        status="completed",
        total_items=2,
        completed_items=1,
        failed_items=1,
        config={"properties": ["BET surface area"]},
    )
    job.items = [
        JobItem(
            id=uuid4(),
            job_id=job_id,
            ordinal=0,
            file_name="good.pdf",
            file_hash="good12345678",
            text_length=100,
            status="done",
            parsed_result={
                "success": True,
                "samples": [{"name": "Sample A", "properties": {}, "measurements": []}],
            },
        ),
        JobItem(
            id=uuid4(),
            job_id=job_id,
            ordinal=1,
            file_name="bad.pdf",
            file_hash="bad123456789",
            text_length=100,
            status="failed",
            error_code="RESULT_FORMAT_ERROR",
            error_message="Invalid model output\x00",
        ),
    ]

    content = build_job_xlsx(job)

    with ZipFile(BytesIO(content)) as archive:
        sheet = archive.read("xl/worksheets/sheet1.xml").decode()
    assert "good.pdf" in sheet
    assert "bad.pdf" in sheet
    assert "Invalid model output" in sheet
    assert "\x00" not in sheet


def test_build_job_xlsx_exports_custom_records_with_evidence():
    job_id = uuid4()
    job = Job(
        id=job_id,
        workflow_id="custom_record_extraction",
        workflow_version="1.0.0",
        workflow_snapshot={"result_type": "records"},
        status="completed",
        total_items=1,
        completed_items=1,
        failed_items=0,
        config={
            "fields": [
                {
                    "key": "effective_date",
                    "label": "Effective date",
                    "type": "date",
                    "description": "Agreement start date",
                }
            ]
        },
    )
    job.items = [
        JobItem(
            id=uuid4(),
            job_id=job_id,
            ordinal=0,
            file_name="contract.pdf",
            file_hash="contract1234",
            text_length=100,
            status="done",
            parsed_result={
                "success": True,
                "result_type": "records",
                "data": {
                    "records": [
                        {
                            "values": {"effective_date": "2026-01-01"},
                            "evidence": {
                                "effective_date": {
                                    "quote": "effective on January 1, 2026",
                                    "location": "Clause 2",
                                }
                            },
                        }
                    ]
                },
            },
        )
    ]

    with ZipFile(BytesIO(build_job_xlsx(job))) as archive:
        results = archive.read("xl/worksheets/sheet1.xml").decode()
        summary = archive.read("xl/worksheets/sheet2.xml").decode()

    assert "Effective date" in results
    assert "effective on January 1, 2026" in results
    assert "Clause 2" in results
    assert "2026-01-01" in summary


def test_build_job_xlsx_exports_entities_and_relations():
    job_id = uuid4()
    job = Job(
        id=job_id,
        workflow_id="entity_relation_extraction",
        workflow_version="1.0.0",
        workflow_snapshot={"result_type": "entity_relation"},
        status="completed",
        total_items=1,
        completed_items=1,
        failed_items=0,
        config={"entity_types": ["Person", "Company"], "relation_types": ["WORKS_FOR"]},
    )
    job.items = [
        JobItem(
            id=uuid4(),
            job_id=job_id,
            ordinal=0,
            file_name="profile.pdf",
            file_hash="profile12345",
            text_length=100,
            status="done",
            parsed_result={
                "success": True,
                "result_type": "entity_relation",
                "data": {
                    "entities": [
                        {"id": "e1", "type": "Person", "name": "Alice"},
                        {"id": "e2", "type": "Company", "name": "Acme"},
                    ],
                    "relations": [{"source": "e1", "type": "WORKS_FOR", "target": "e2"}],
                },
            },
        )
    ]

    with ZipFile(BytesIO(build_job_xlsx(job))) as archive:
        results = archive.read("xl/worksheets/sheet1.xml").decode()
        summary = archive.read("xl/worksheets/sheet2.xml").decode()

    assert "Alice" in results
    assert "WORKS_FOR" in results
    assert "Acme" in results
    assert "Relationships" in summary
