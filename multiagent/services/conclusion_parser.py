"""
LLM 최종 결론 텍스트를 JSON으로 파싱
"""

from __future__ import annotations

import re
import json
from typing import Optional
from multiagent.schemas import InvestmentConclusion, Scores, KeyTrigger


class ConclusionParser:
    """LLM이 생성한 텍스트를 InvestmentConclusion 객체로 파싱"""
    
    def parse(self, ticker: str, raw_text: str, confidence: float) -> InvestmentConclusion:
        """
        최종 결론 텍스트를 구조화된 객체로 파싱
        
        Args:
            ticker: 티커 심볼
            raw_text: LLM이 생성한 원문
            confidence: 전문가 합의도 (0-1)
        
        Returns:
            InvestmentConclusion 객체
        """
        try:
            # 1. 점수 추출
            scores = self._extract_scores(raw_text)
            
            # 2. 액션 추출
            action = self._extract_action(raw_text)
            
            # 3. 포지션 크기 추출
            position_size = self._extract_position_size(raw_text)
            
            # 4. Executive Summary 추출
            executive_summary = self._extract_executive_summary(raw_text)
            
            # 5. 주요 토론 쟁점 추출
            key_debates = self._extract_key_debates(raw_text)
            
            # 6. 실행 계획 추출
            immediate, short_term, long_term = self._extract_strategies(raw_text)
            
            # 7. 트리거 추출
            bullish, bearish = self._extract_triggers(raw_text)
            
            # 8. 재검토 항목 추출
            review_items = self._extract_review_items(raw_text)
            
            return InvestmentConclusion(
                ticker=ticker,
                scores=scores,
                action=action,
                position_size=position_size,
                confidence=confidence,
                executive_summary=executive_summary,
                key_debates=key_debates,
                immediate_action=immediate,
                short_term_strategy=short_term,
                long_term_strategy=long_term,
                bullish_trigger=bullish,
                bearish_trigger=bearish,
                next_review_items=review_items,
                raw_conclusion=raw_text
            )
        
        except Exception as exc:
            print(f"⚠️  결론 파싱 중 오류, 기본값 사용: {exc}")
            # 파싱 실패 시 안전한 기본값
            return InvestmentConclusion(
                ticker=ticker,
                scores=Scores(fundamental=5, risk=5, growth=5, sentiment=5, overall=5.0),
                action="HOLD",
                position_size=5,
                confidence=confidence,
                executive_summary="파싱 실패",
                raw_conclusion=raw_text
            )
    
    def _extract_scores(self, text: str) -> Scores:
        """점수 추출 (Fundamental, Risk, Growth, Sentiment)"""
        patterns = {
            "fundamental": r'Fundamental Score[:\s]*(\d+)',
            "risk": r'Risk Score[:\s]*(\d+)',
            "growth": r'Growth Score[:\s]*(\d+)',
            "sentiment": r'Sentiment Score[:\s]*(\d+)',
        }
        
        scores_dict = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores_dict[key] = int(match.group(1))
            else:
                scores_dict[key] = 5  # 기본값
        
        # 종합 점수 추출 또는 계산
        overall_match = re.search(r'종합 점수[:\s]*(\d+(?:\.\d+)?)', text)
        if overall_match:
            overall = float(overall_match.group(1))
        else:
            # 가중평균: Fundamental 30%, Risk -20%, Growth 30%, Sentiment 20%
            overall = (scores_dict["fundamental"] * 0.3 + 
                      (10 - scores_dict["risk"]) * 0.2 +  # Risk는 역방향
                      scores_dict["growth"] * 0.3 + 
                      scores_dict["sentiment"] * 0.2)
        
        return Scores(**scores_dict, overall=overall)
    
    def _extract_action(self, text: str) -> str:
        """액션 추출 (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)"""
        action_map = {
            "STRONG BUY": "STRONG_BUY",
            "STRONG_BUY": "STRONG_BUY",
            "🟢 STRONG BUY": "STRONG_BUY",
            "BUY": "BUY",
            "🔵 BUY": "BUY",
            "HOLD": "HOLD",
            "⚪ HOLD": "HOLD",
            "SELL": "SELL",
            "🟠 SELL": "SELL",
            "STRONG SELL": "STRONG_SELL",
            "STRONG_SELL": "STRONG_SELL",
            "🔴 STRONG SELL": "STRONG_SELL",
        }
        
        for pattern, action in action_map.items():
            if pattern in text.upper():
                return action
        
        return "HOLD"  # 기본값
    
    def _extract_position_size(self, text: str) -> int:
        """포지션 크기 추출 (0-20%)"""
        match = re.search(r'포트폴리오의?\s*(\d+)\s*%', text)
        if match:
            return min(int(match.group(1)), 20)
        
        match = re.search(r'(\d+)%\s*비중', text)
        if match:
            return min(int(match.group(1)), 20)
        
        return 10  # 기본값
    
    def _extract_executive_summary(self, text: str) -> str:
        """Executive Summary 추출"""
        match = re.search(r'##\s*📊\s*Executive Summary\s*\n(.+?)(?=\n##|\Z)', text, re.DOTALL)
        if match:
            return match.group(1).strip()[:500]  # 최대 500자
        
        # 첫 2-3문장 추출
        sentences = re.split(r'[.!?]\s+', text[:1000])
        return '. '.join(sentences[:3]) + '.'
    
    def _extract_key_debates(self, text: str) -> list:
        """주요 토론 쟁점 추출"""
        debates = []
        
        # "쟁점 1:", "쟁점 2:" 패턴 찾기
        debate_pattern = r'\*\*쟁점\s*\d+\*\*[:\s]*(.+?)(?=\*\*쟁점|\n##|\Z)'
        matches = re.findall(debate_pattern, text, re.DOTALL)
        
        for match in matches[:3]:  # 최대 3개
            debate_text = match.strip()[:300]  # 최대 300자
            debates.append(debate_text)
        
        return debates
    
    def _extract_strategies(self, text: str) -> tuple:
        """실행 계획 추출 (즉시/단기/장기)"""
        immediate = None
        short_term = None
        long_term = None
        
        # 즉시 행동
        match = re.search(r'###\s*즉시 행동.*?\n-\s*(.+?)(?=\n###|\n##|\Z)', text, re.DOTALL)
        if match:
            immediate = match.group(1).strip()[:200]
        
        # 단기 전략
        match = re.search(r'###\s*단기 전략.*?\n-\s*(.+?)(?=\n###|\n##|\Z)', text, re.DOTALL)
        if match:
            short_term = match.group(1).strip()[:200]
        
        # 장기 전략
        match = re.search(r'###\s*장기 전략.*?\n-\s*(.+?)(?=\n###|\n##|\Z)', text, re.DOTALL)
        if match:
            long_term = match.group(1).strip()[:200]
        
        return immediate, short_term, long_term
    
    def _extract_triggers(self, text: str) -> tuple:
        """트리거 추출 (상승/하락 시나리오)"""
        bullish = None
        bearish = None
        
        # 상승 시나리오
        bull_match = re.search(
            r'###\s*상승 시나리오.*?조건[:\s]*(.+?)액션[:\s]*(.+?)(?=\n###|\n##|\Z)',
            text,
            re.DOTALL
        )
        if bull_match:
            bullish = KeyTrigger(
                condition=bull_match.group(1).strip()[:200],
                action=bull_match.group(2).strip()[:200]
            )
        
        # 하락 시나리오
        bear_match = re.search(
            r'###\s*하락 시나리오.*?조건[:\s]*(.+?)액션[:\s]*(.+?)(?=\n###|\n##|\Z)',
            text,
            re.DOTALL
        )
        if bear_match:
            bearish = KeyTrigger(
                condition=bear_match.group(1).strip()[:200],
                action=bear_match.group(2).strip()[:200]
            )
        
        return bullish, bearish
    
    def _extract_review_items(self, text: str) -> list:
        """재검토 항목 추출"""
        items = []
        
        # "1. ...", "2. ...", "3. ..." 패턴
        pattern = r'##\s*🔮.*?재검토 항목.*?\n(.+?)(?=\n---|\n##|\Z)'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            content = match.group(1)
            item_pattern = r'\d+\.\s*(.+)'
            for m in re.finditer(item_pattern, content):
                items.append(m.group(1).strip()[:200])
        
        return items[:3]  # 최대 3개

