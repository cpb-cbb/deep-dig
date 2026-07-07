# Titanium real material_extraction workflow check

Input: `tests/titanium_alloy_extraction_input.txt`
Result JSON: `tests/titanium_material_extraction_real_result.json`
Excel export: `tests/titanium_material_extraction_real_export.xlsx`

## Real call configuration
- provider: `openai_compatible`
- compat model: `deepseek-v4-flash`
- compat key set: `True`
- openrouter key set: `True`
- anthropic key set: `True`

## Parsed result summary
- success: `True`
- sample names: `['Ti64-STA', 'Ti64-ANN']`
- sample count: `2`
- measurement count: `6`
- headers count: `14`
- requested properties absent from parsed headers: `[]`
- expected snippets absent from exported sheets: `[]`
- none/null placeholder strings remaining in parsed result: `[]`

## Interpretation
The workflow was invoked through the real `llm_gateway.call` path, then parsed by the `material_extraction` processor and exported with `build_job_xlsx`.
The run produced two samples (`Ti64-STA`, `Ti64-ANN`) and six measurement records: four tensile records and two fatigue records.
The export contains both the detailed `Results` sheet and the simplified `Summary` sheet.
