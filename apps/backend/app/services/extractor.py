from __future__ import annotations

import json
from typing import Any

import json_repair

from app.services.llm_gateway import llm_gateway
from app.services.llm_config import ResolvedLLMConfig
from app.services.processor import parse_workflow_result


def _render(template: str, values: dict[str, Any]) -> str:
    return template.format(
        **{
            key: value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            for key, value in values.items()
        }
    )


def _parse_json_output(text: str) -> Any:
    return json_repair.loads(text)


async def run_workflow(
    workflow: dict[str, Any],
    document_text: str,
    params: dict[str, Any] | None = None,
    llm_config: ResolvedLLMConfig | None = None,
) -> dict[str, Any]:
    params = params or {}
    context: dict[str, Any] = {"document_text": document_text, **params}
    raw_results: dict[str, Any] = {}

    for step in workflow["steps"]:
        if step.get("iterate_over"):
            source = raw_results.get(step.get("depends_on", [None])[0], {})
            items = source.get(step["iterate_over"], []) if isinstance(source, dict) else []
            results = []
            for item in items:
                local_context = {**context, step.get("iterate_input_var", "item"): item}
                result = await llm_gateway.call(
                    step["system_prompt"],
                    _render(step["user_prompt_template"], local_context),
                    config=llm_config,
                )
                data = (
                    _parse_json_output(result.text)
                    if step.get("output_format") == "json"
                    else result.text
                )
                results.append({"sample_name": item, "data": data})
            raw_results[step["id"]] = results
            continue

        user_prompt = _render(step["user_prompt_template"], {**context, **raw_results})
        result = await llm_gateway.call(step["system_prompt"], user_prompt, config=llm_config)
        raw_results[step["id"]] = (
            _parse_json_output(result.text) if step.get("output_format") == "json" else result.text
        )

    parsed = parse_workflow_result(workflow, raw_results, params)
    return {"raw_results": raw_results, "parsed_result": parsed.model_dump(mode="json")}
