from dataclasses import dataclass

import pytest

from app.services.extractor import _parse_json_output, run_workflow
from app.services.workflow_registry import get_workflow


def test_parse_json_output_accepts_plain_json():
    assert _parse_json_output('{"sampleNames":["PC-800"]}') == {"sampleNames": ["PC-800"]}


def test_parse_json_output_accepts_fenced_json():
    text = '```json\n{"sampleNames":["PC-800"]}\n```'

    assert _parse_json_output(text) == {"sampleNames": ["PC-800"]}


def test_parse_json_output_extracts_json_from_surrounding_text():
    text = 'Here is the JSON:\n{"sampleNames":["PC-800"]}\nDone.'

    assert _parse_json_output(text) == {"sampleNames": ["PC-800"]}


def test_parse_json_output_repairs_malformed_json():
    assert _parse_json_output('{"sampleNames":["PC-800",]}') == {"sampleNames": ["PC-800"]}


@pytest.mark.asyncio
async def test_run_workflow_does_not_repair_text_output(monkeypatch):
    @dataclass
    class Result:
        text: str

    async def fake_call(*args, **kwargs):
        return Result(text='{"sampleNames":["PC-800",]}')

    workflow = {
        "steps": [
            {
                "id": "step1",
                "output_format": "text",
                "system_prompt": "",
                "user_prompt_template": "{document_text}",
            }
        ],
    }
    monkeypatch.setattr("app.services.extractor.llm_gateway.call", fake_call)

    result = await run_workflow(workflow, "text", {})

    assert result["raw_results"]["step1"] == '{"sampleNames":["PC-800",]}'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("workflow_id", "config", "response"),
    [
        ("material_extraction", {"properties": ["Strength"]}, '{"samples": []}'),
        (
            "custom_record_extraction",
            {
                "fields": [
                    {
                        "key": "title",
                        "label": "Title",
                        "type": "text",
                        "description": "Document title",
                    }
                ]
            },
            '{"records": [], "warnings": []}',
        ),
        (
            "entity_relation_extraction",
            {"entity_types": ["Person"], "relation_types": []},
            '{"entities": [], "relations": [], "warnings": []}',
        ),
    ],
)
async def test_builtin_workflow_prompts_render_and_return_versioned_envelopes(
    monkeypatch, workflow_id, config, response
):
    @dataclass
    class Result:
        text: str

    async def fake_call(*args, **kwargs):
        return Result(text=response)

    monkeypatch.setattr("app.services.extractor.llm_gateway.call", fake_call)

    result = await run_workflow(get_workflow(workflow_id), "document", config)

    assert result["parsed_result"]["workflow_id"] == workflow_id
    assert result["parsed_result"]["schema_version"] == "1.0"
