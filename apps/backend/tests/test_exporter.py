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
                                }
                            }
                        ],
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
