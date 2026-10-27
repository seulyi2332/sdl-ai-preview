"""Shared OpenAI Responses API JSON wrapper for strategy and diary modules."""
import json
import re


def _response_text(response):
    result = getattr(response, "output_text", None)
    if isinstance(result, str) and result.strip():
        return result
    parts = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) == "message":
            for c in getattr(item, "content", []) or []:
                if getattr(c, "type", None) == "output_text":
                    parts.append(getattr(c, "text", "") or "")
    return "".join(parts)


def complete_json(client, model, system, payload):
    user_prompt = (
        json.dumps(payload, ensure_ascii=False) +
        "\n\n결과는 다른 설명 없이 유효한 json 객체 하나로 작성하세요."
    )
    response = client.responses.create(
        model=model,
        instructions=system,
        input=[{"role": "user", "content": user_prompt}],
        text={"format": {"type": "json_object"}},
        max_output_tokens=6000,
        store=False,
    )
    answer = _response_text(response).strip()
    if not answer:
        status = getattr(response, "status", "") or ""
        detail = getattr(getattr(response, "incomplete_details", None), "reason", "") or ""
        raise ValueError(f"OpenAI 응답이 비어 있습니다. status={status}, reason={detail}")
    if answer.startswith(chr(96)*3):
        answer = re.sub(r"^\x60{3}(?:json)?\s*|\s*\x60{3}$", "", answer).strip()
    data = json.loads(answer)
    if not isinstance(data, dict):
        raise ValueError("AI 응답은 JSON 객체여야 합니다.")
    return data


def safe_error_message(exc):
    """Show API error metadata, never keys or student prompts."""
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    code = ""
    param = ""
    if isinstance(body, dict):
        info = body.get("error", body)
        if isinstance(info, dict):
            code = str(info.get("code") or "")
            param = str(info.get("param") or "")
    parts = [name]
    if status:
        parts.append("HTTP " + str(status))
    if code and re.fullmatch(r"[\w.-]{1,70}", code):
        parts.append("code=" + code)
    if param and re.fullmatch(r"[\w.-]{1,70}", param):
        parts.append("param=" + param)
    return " · ".join(parts)
