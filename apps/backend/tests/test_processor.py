from app.services.processor import parse_material_extraction, parse_workflow_result
from app.services.workflow_registry import get_workflow


def test_material_extraction_parser_supports_property_table_output():
    raw = {
        "extract_property_table": {
            "samples": [
                {
                    "sample_name": "PC-800",
                    "properties": {
                        "BET surface area": {
                            "value": 1850,
                            "unit": "m2 g-1",
                            "remark": "KOH activated",
                            "source": "text",
                            "method": "Nitrogen adsorption",
                        }
                    },
                }
            ]
        }
    }

    parsed = parse_material_extraction(raw)

    assert parsed.success
    assert parsed.headers == ["BET surface area"]
    prop = parsed.samples[0].properties["BET surface area"]
    assert parsed.samples[0].name == "PC-800"
    assert prop.value == "1850"
    assert prop.unit == "m2 g-1"


def test_material_extraction_parser_supports_measurement_records():
    raw = {
        "extract_property_table": {
            "samples": [
                {
                    "sample_name": "PC-800",
                    "sample_properties": {
                        "BET surface area": {
                            "value": 1850,
                            "unit": "m2 g-1",
                            "remark": "KOH activated",
                            "source": "Table 1",
                            "method": "Nitrogen adsorption",
                        }
                    },
                    "measurements": [
                        {
                            "conditions": {
                                "current density": {
                                    "value": 0.5,
                                    "unit": "A g-1",
                                    "remark": "None",
                                    "source": "Figure 5a",
                                    "method": None,
                                }
                            },
                            "performance": {
                                "specific capacitance": {
                                    "value": 280,
                                    "unit": "F g-1",
                                    "remark": "three-electrode",
                                    "source": "Figure 5a",
                                    "method": "GCD",
                                }
                            },
                            "source": "Figure 5a",
                        }
                    ],
                }
            ]
        }
    }

    parsed = parse_material_extraction(raw)

    assert parsed.success
    assert parsed.headers == ["BET surface area", "current density", "specific capacitance"]
    sample = parsed.samples[0]
    assert sample.properties["BET surface area"].value == "1850"
    assert sample.measurements[0].conditions["current density"].value == "0.5"
    assert sample.measurements[0].conditions["current density"].remark == ""
    assert sample.measurements[0].conditions["current density"].method == ""
    assert sample.measurements[0].performance["specific capacitance"].value == "280"


def test_custom_record_parser_returns_common_envelope_and_omits_unknown_fields():
    workflow = get_workflow("custom_record_extraction")
    parsed = parse_workflow_result(
        workflow,
        {
            "extract_records": {
                "records": [
                    {
                        "values": {"party": "Acme", "unsupported": "ignore"},
                        "evidence": {"party": {"quote": "Acme agrees", "location": "Clause 1"}},
                    }
                ]
            }
        },
        {
            "fields": [
                {
                    "key": "party",
                    "label": "Party",
                    "type": "text",
                    "description": "Contracting party",
                }
            ]
        },
    )

    assert parsed.success
    assert parsed.result_type == "records"
    assert parsed.data["records"][0]["values"] == {"party": "Acme"}
    assert "unknown fields" in parsed.warnings[0]


def test_entity_parser_rejects_unconfigured_types_and_dangling_relations():
    workflow = get_workflow("entity_relation_extraction")
    parsed = parse_workflow_result(
        workflow,
        {
            "extract_entities": {
                "entities": [
                    {"id": "e1", "type": "Person", "name": "Alice"},
                    {"id": "e2", "type": "Unknown", "name": "Hidden"},
                ],
                "relations": [{"source": "e1", "type": "WORKS_FOR", "target": "e2"}],
            }
        },
        {"entity_types": ["Person"], "relation_types": ["WORKS_FOR"]},
    )

    assert parsed.success
    assert [entity["name"] for entity in parsed.data["entities"]] == ["Alice"]
    assert parsed.data["relations"] == []
    assert len(parsed.warnings) == 2
