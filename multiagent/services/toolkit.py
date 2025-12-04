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

    def summarize(self, content: str, instruction: str, max_retries: int = 3) -> str:
        """
        주어진 instruction/prompt와 원문을 이용해 간단히 요약합니다.
        
        Args:
            content: 원문
            instruction: 프롬프트/지시사항
            max_retries: 최대 재시도 횟수
        
        Returns:
            LLM 응답 텍스트
        """
        # instruction만 있고 content가 비어있는 경우 (prompt가 이미 완성된 경우)
        if instruction and not content:
            prompt = instruction
        elif not content and not instruction:
            return "본문과 지시사항이 모두 없어 요약할 수 없습니다."
        else:
            prompt = textwrap.dedent(
                f"""
                {instruction}

                원문:
                {content[:8000]}
                """
            ).strip()

        # 재시도 로직
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "당신은 주식 분석 전문가입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                    timeout=30,  # 30초 타임아웃
                )
                return response.choices[0].message.content if response.choices else ""
            
            except Exception as exc:
                print(f"⚠️  OpenAI API 호출 실패 (시도 {attempt+1}/{max_retries}): {exc}")
                if attempt == max_retries - 1:
                    return f"LLM 호출 실패: {str(exc)[:100]}"
                import time
                time.sleep(2 ** attempt)  # 지수 백오프 (2초, 4초, 8초)
        
        return "LLM 호출 실패"
