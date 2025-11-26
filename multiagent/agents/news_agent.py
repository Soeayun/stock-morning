from __future__ import annotations

from typing import Any, Dict, List

from .base_agent import BaseAgent
from multiagent.services import AgentToolkit
from multiagent.prompts import NEWS_SUMMARY_PROMPT


class NewsAgent(BaseAgent):
    """AWS에서 가져온 뉴스 본문을 요약하는 에이전트"""

    def __init__(self, toolkit: AgentToolkit, name: str = "News Analyst"):
        super().__init__(name=name, role="news")
        self.toolkit = toolkit

    def analyze(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        news_items: List[Dict[str, Any]] = dataset.get("aws_news", [])
        summaries = []

        for news in news_items[:5]:
            body = news.get("article_raw") or ""
            title = news.get("title") or news.get("pk")
            summary_text = self.toolkit.summarize(body, NEWS_SUMMARY_PROMPT)
            summaries.append(
                {
                    "title": title,
                    "published_at": news.get("published_at"),
                    "summary": summary_text,
                }
            )

        return {
            "agent": self.name,
            "role": self.role,
            "summaries": summaries,
            "opinion": "뉴스 요약이 완료되었습니다. Debate 단계에서 SEC 의견과 비교 예정.",
        }
