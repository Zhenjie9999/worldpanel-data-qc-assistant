import unittest

from worldpanel_qc.llm.scope_assistant import ai_scope_questions, fallback_scope_questions, parse_scope_questions_response


class FakeScopeClient:
    def __init__(self, response):
        self.response = response

    def _chat(self, messages):
        self.messages = messages
        return self.response


class ScopeAssistantTests(unittest.TestCase):
    def test_fallback_questions_are_limited_and_actionable(self):
        questions = fallback_scope_questions(
            {"files": [{"file_name": "deck.pptx", "file_type": "pptx"}, {"file_name": "source.xlsx", "file_type": "xlsx"}]},
            "检查价格页",
        )

        self.assertLessEqual(len(questions), 3)
        self.assertTrue(any("PPT" in item["question"] and "Excel" in item["question"] for item in questions))
        self.assertTrue(all(item["id"] for item in questions))

    def test_parse_json_questions_from_model(self):
        questions = parse_scope_questions_response(
            '{"questions":[{"id":"pages","question":"请确认页码范围？"},{"id":"metrics","question":"重点指标是什么？"}]}'
        )

        self.assertEqual(["pages", "metrics"], [item["id"] for item in questions])
        self.assertIn("页码", questions[0]["question"])

    def test_ai_questions_fall_back_when_model_response_is_empty(self):
        questions = ai_scope_questions(FakeScopeClient(""), {"files": [{"file_name": "deck.pptx", "file_type": "pptx"}]}, "")

        self.assertTrue(questions)
        self.assertEqual("scope_range", questions[0]["id"])


if __name__ == "__main__":
    unittest.main()
