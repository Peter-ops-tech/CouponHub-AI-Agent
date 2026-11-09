
import json
import unittest

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src import agent


class TestAgentFailureCases(unittest.TestCase):

    def test_invalid_tool_arguments(self):
        """案例一：AI 傳入錯誤的 category 型別。"""

        with TemporaryDirectory() as temp_dir:
            trace_path = Path(temp_dir) / "traces.jsonl"

            # 模擬 LLM 產生錯誤的工具參數
            fake_response = SimpleNamespace(
                tool_calls=[
                    {
                        "name": "search_offers",
                        "args": {
                            "merchant": "麥當勞",
                            "category": {}
                        },
                        "id": "test-call-001"
                    }
                ]
            )

            # 模擬資料庫查詢結果
            fake_offers = [
                {
                    "id": 1,
                    "merchant": "麥當勞",
                    "title": "[測試] 優惠活動",
                    "category": "美食",
                    "valid_from": "2026-11-01",
                    "valid_until": "2026-11-18",
                    "source_url": "https://example.com/test"
                }
            ]

            with (
                patch.object(agent, "TRACE_PATH", trace_path),
                patch("src.agent.ChatOllama") as mock_chat,
                patch(
                    "src.agent.search_offers",
                    return_value=fake_offers
                ) as mock_search,
            ):
                llm = mock_chat.return_value

                # AI 第一次回應：決定呼叫工具
                llm.bind_tools.return_value.invoke.return_value = (
                    fake_response
                )

                # AI 第二次回應：產生最終回答
                llm.invoke.return_value = SimpleNamespace(
                    content="已查到測試優惠。"
                )

                answer = agent.ask_agent(
                    "請查詢麥當勞優惠"
                )

                # 確認工具真正收到修正後的參數
                mock_search.assert_called_once_with(
                    merchant="麥當勞",
                    category=None
                )

            trace = json.loads(
                trace_path.read_text(encoding="utf-8")
            )

            self.assertEqual(
                trace["status"],
                "success"
            )

            self.assertEqual(
                trace["events"][1]["fixed_fields"],
                ["category"]
            )

            self.assertEqual(
                trace["events"][1]["validated_arguments"]["category"],
                ""
            )

            self.assertEqual(
                answer,
                "已查到測試優惠。"
            )

    def test_ollama_connection_failure(self):
        """案例二：Ollama 無法連線。"""

        with TemporaryDirectory() as temp_dir:
            trace_path = Path(temp_dir) / "traces.jsonl"

            with (
                patch.object(agent, "TRACE_PATH", trace_path),
                patch("src.agent.ChatOllama") as mock_chat,
            ):
                llm = mock_chat.return_value

                # 模擬 Ollama 連線失敗
                llm.bind_tools.return_value.invoke.side_effect = (
                    ConnectionError("無法連線至 Ollama")
                )

                answer = agent.ask_agent(
                    "請查詢麥當勞優惠"
                )

            trace = json.loads(
                trace_path.read_text(encoding="utf-8")
            )

            self.assertEqual(
                trace["status"],
                "agent_error"
            )

            self.assertIn(
                "Ollama",
                answer
            )

            self.assertTrue(
                any(
                    event["stage"] == "error"
                    for event in trace["events"]
                )
            )

    def test_no_tool_call(self):
        """額外案例：AI 沒有呼叫搜尋工具。"""

        with TemporaryDirectory() as temp_dir:
            trace_path = Path(temp_dir) / "traces.jsonl"

            with (
                patch.object(agent, "TRACE_PATH", trace_path),
                patch("src.agent.ChatOllama") as mock_chat,
            ):
                llm = mock_chat.return_value

                # 模擬 AI 完全沒有提出工具呼叫
                llm.bind_tools.return_value.invoke.return_value = (
                    SimpleNamespace(tool_calls=[])
                )

                answer = agent.ask_agent(
                    "請查詢優惠"
                )

            trace = json.loads(
                trace_path.read_text(encoding="utf-8")
            )

            self.assertEqual(
                trace["status"],
                "no_tool_call"
            )

            self.assertIn(
                "無法確認優惠資訊",
                answer
            )


if __name__ == "__main__":
    unittest.main()
