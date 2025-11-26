from __future__ import annotations

import textwrap
from typing import Optional

from openai import OpenAI


class AgentToolkit:
    """
    멀티에이전트에서 공용으로 사용하는 LLM 툴 모음.
    - summarize: 문자열과 프롬프트를 입력받아 요약
    추후 감성 분석, 리포트 생성 등 함수도 이 클래스에 확장 가능.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI()
        self.model = model

    def summarize(self, content: str, instruction: str) -> str:
        """
        주어진 instruction/prompt와 원문을 이용해 간단히 요약합니다.
        """
        if not content:
            return "본문이 없어 요약할 수 없습니다."

        prompt = textwrap.dedent(
            f"""
            {instruction}

            원문:
            {content[:8000]}
            """
        ).strip()

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        return response.output[0].content[0].text if response.output else ""
