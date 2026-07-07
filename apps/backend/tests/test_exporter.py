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
                    }
                ],
                "headers": ["BET surface area"],
            },
        )
    ]

    content = build_job_xlsx(job)

    assert content.startswith(b"PK")
    with ZipFile(BytesIO(content)) as archive:
        names = set(archive.namelist())
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names
        sheet = archive.read("xl/worksheets/sheet1.xml").decode()

    assert "paper.pdf" in sheet
    assert "PC-800" in sheet
    assert "BET surface area" in sheet
    assert "1850" in sheet
    assert export_filename(job) == f"deep-dig-{job_id}.xlsx"
