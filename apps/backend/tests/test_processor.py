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
