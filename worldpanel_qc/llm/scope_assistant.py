from __future__ import annotations

import json


def fallback_scope_questions(file_overview: dict, review_goal: str = "") -> list[dict]:
    files = file_overview.get("files", [])
    types = {item.get("file_type") for item in files}
    questions = []
    if {"pptx", "ppt", "pdf"} & types and {"xlsx", "xls"} & types:
        questions.append(
            {
                "id": "cross_check",
                "question": "这些 PPT/PDF 和 Excel 是否属于同一套交付文件，需要做 PPT-Excel 交叉检查吗？",
            }
        )
    questions.append(
        {
            "id": "scope_range",
            "question": "本次是全量检查，还是只检查指定页码、sheet 或部分指标？",
        }
    )
    if review_goal:
        questions.append(
            {
                "id": "focus_metrics",
                "question": "是否有特别关注的指标，例如价格、share、penetration、volume、spend 或标注问题？",
            }
        )
    return questions[:3]


def parse_scope_questions_response(text: str) -> list[dict]:
    content = text.strip()
    if not content:
        return []
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return [{"id": "ai_scope_question", "question": line.strip("- 0123456789.、")} for line in content.splitlines() if line.strip()][:3]

    if isinstance(data, dict):
        data = data.get("questions", [])
    if not isinstance(data, list):
        return []

    questions = []
    for index, item in enumerate(data):
        if isinstance(item, str):
            question = item.strip()
            question_id = f"ai_scope_{index + 1}"
        elif isinstance(item, dict):
            question = str(item.get("question", "")).strip()
            question_id = str(item.get("id") or f"ai_scope_{index + 1}").strip()
        else:
            continue
        if question:
            questions.append({"id": question_id, "question": question})
    return questions[:3]


def ai_scope_questions(client, file_overview: dict, review_goal: str = "") -> list[dict]:
    prompt = {
        "role": "user",
        "content": (
            "你是 Worldpanel Data QC Assistant 的检查范围助手。"
            "请基于上传文件和用户目标，最多提出 3 个必须在开始检查前确认的问题，"
            "用于明确本次是全量检查、指定页码/sheet/指标检查、是否需要 PPT-Excel 交叉检查。"
            "只返回 JSON，格式为 {\"questions\":[{\"id\":\"...\",\"question\":\"...\"}]}。\n\n"
            f"上传文件：{json.dumps(file_overview, ensure_ascii=False)}\n"
            f"用户目标：{review_goal or '未填写'}"
        ),
    }
    response = client._chat([prompt])
    questions = parse_scope_questions_response(response)
    return questions or fallback_scope_questions(file_overview, review_goal)
