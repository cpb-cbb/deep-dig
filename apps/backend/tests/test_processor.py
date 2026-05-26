from app.services.processor import process_result


def test_code_friendly_parser_supports_metadata_columns():
    raw = {"step1": "# SAMPLE: Alloy A\n- Yield Strength | 500 | MPa | aged 2h | Table 1 | tensile test"}
    parsed = process_result("code_friendly", raw)
    assert parsed.success
    prop = parsed.samples[0].properties["Yield Strength"]
    assert prop.value == "500"
    assert prop.unit == "MPa"
    assert prop.remark == "aged 2h"
    assert prop.source == "Table 1"
    assert prop.method == "tensile test"


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

    parsed = process_result("material_extraction", raw)

    assert parsed.success
    assert parsed.headers == ["BET surface area"]
    prop = parsed.samples[0].properties["BET surface area"]
    assert parsed.samples[0].name == "PC-800"
    assert prop.value == "1850"
    assert prop.unit == "m2 g-1"
