from __future__ import annotations

from typing import Any, Dict, List

from .base_agent import BaseAgent
from multiagent.services import AgentToolkit
from multiagent.prompts import SEC_SUMMARY_PROMPT


class SECAgent(BaseAgent):
    """최근 24시간 SEC 공시를 요약하는 에이전트"""

    def __init__(self, toolkit: AgentToolkit, name: str = "SEC Analyst"):
        super().__init__(name=name, role="sec")
        self.toolkit = toolkit

    def analyze(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        filings: List[Dict[str, Any]] = dataset.get("sec_filings", [])
        summaries = []
        for filing in filings[:5]:
            meta = filing.get("metadata", {})
            form = meta.get("form")
            filed_date = meta.get("filed_date") or meta.get("filed")
            text = filing.get("content") or ""
            summary_text = self.toolkit.summarize(text, SEC_SUMMARY_PROMPT)
            summaries.append(
                {
                    "form": form,
                    "filed_date": filed_date,
                    "summary": summary_text,
                }
            )

        return {
            "agent": self.name,
            "role": self.role,
            "summaries": summaries,
            "opinion": "SEC 공시 요약이 완료되었습니다. Debate 단계에서 뉴스 의견과 비교 예정.",
        }
