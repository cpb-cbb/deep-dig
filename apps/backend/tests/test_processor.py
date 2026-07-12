from app.services.processor import parse_material_extraction


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
