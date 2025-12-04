"""
LangGraph 기반 4명 전문가 토론 파이프라인
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, START, END

from multiagent.nodes.data_collector import prepare_ticker_dataset
from multiagent.services import AgentToolkit
from multiagent.services.consensus import ConsensusAnalyzer
from multiagent.services.conclusion_parser import ConclusionParser
from multiagent.agents.fundamental_analyst import FundamentalAnalyst
from multiagent.agents.risk_manager import RiskManager
from multiagent.agents.growth_analyst import GrowthAnalyst
from multiagent.agents.sentiment_analyst import SentimentAnalyst
from multiagent.prompts import DEBATE_CONCLUSION_PROMPT
from multiagent.schemas import InvestmentConclusion, ConsensusMetrics


class AgentState(TypedDict, total=False):
    ticker: str
    dataset: Dict[str, Any]
    agents: Dict[str, Any]  # 에이전트 재사용 (매번 생성 방지)
    rounds: List[Dict[str, str]]
    fundamental_statement: str
    risk_statement: str
    growth_statement: str
    sentiment_statement: str
    consensus_metrics: ConsensusMetrics
    should_continue: bool
    debate_transcript: str
    conclusion: str
    readable_summary: str
    structured_conclusion: InvestmentConclusion


def collect_data_node(state: AgentState) -> AgentState:
    """데이터 수집 + 4명의 전문가 초기 분석 (Blind Assessment)"""
    ticker = state["ticker"]
    info = prepare_ticker_dataset(ticker)
    dataset = info["dataset"]
    
    initial_round = {
        "round": 1,
        "fundamental": info["initial_fundamental"],
        "risk": info["initial_risk"],
        "growth": info["initial_growth"],
        "sentiment": info["initial_sentiment"],
    }
    
    print("=" * 100)
    print("🔍 ROUND 1: BLIND ANALYSIS - 각 전문가의 독립적 초기 분석")
    print("=" * 100)
    print("\n💼 Fundamental Analyst (Charlie Munger 스타일)")
    print(info["initial_fundamental"])
    print("\n" + "-" * 100)
    print("⚠️  Risk Manager (Ray Dalio 스타일)")
    print(info["initial_risk"])
    print("\n" + "-" * 100)
    print("🚀 Growth Catalyst Hunter (Cathie Wood 스타일)")
    print(info["initial_growth"])
    print("\n" + "-" * 100)
    print("📊 Market Sentiment Analyst (George Soros 스타일)")
    print(info["initial_sentiment"])
    
    # 초기 합의도 계산
    consensus_analyzer = ConsensusAnalyzer()
    initial_consensus = consensus_analyzer.calculate_consensus(
        info["initial_fundamental"],
        info["initial_risk"],
        info["initial_growth"],
        info["initial_sentiment"]
    )
    
    print(f"\n📊 초기 합의도: {initial_consensus.overall_consensus:.2f} (액션 합의: {initial_consensus.action_consensus:.2f})")
    
    # 에이전트 인스턴스 생성 (재사용)
    toolkit = AgentToolkit()
    agents = {
        "fundamental": FundamentalAnalyst(toolkit),
        "risk": RiskManager(toolkit),
        "growth": GrowthAnalyst(toolkit),
        "sentiment": SentimentAnalyst(toolkit),
    }
    
    return {
        "ticker": ticker,
        "dataset": dataset,
        "agents": agents,  # 에이전트 재사용
        "rounds": [initial_round],
        "fundamental_statement": info["initial_fundamental"],
        "risk_statement": info["initial_risk"],
        "growth_statement": info["initial_growth"],
        "sentiment_statement": info["initial_sentiment"],
        "consensus_metrics": initial_consensus,
        "should_continue": True,  # 첫 라운드는 항상 진행
    }


def _debate_round_node(round_number: int):
    """4명의 전문가가 서로의 의견을 듣고 반박/수정하는 토론 라운드 (최적화: 병렬 처리)"""
    def node(state: AgentState) -> AgentState:
        import concurrent.futures
        
        ticker = state.get("ticker", "")
        agents = state.get("agents", {})
        
        # 에이전트가 없으면 생성 (fallback)
        if not agents:
            toolkit = AgentToolkit()
            agents = {
                "fundamental": FundamentalAnalyst(toolkit),
                "risk": RiskManager(toolkit),
                "growth": GrowthAnalyst(toolkit),
                "sentiment": SentimentAnalyst(toolkit),
            }
        
        # 직전 라운드의 다른 분석가들 의견만 수집 (전체 히스토리가 아닌 직전 라운드만)
        prev_fundamental = state.get("fundamental_statement", "")
        prev_risk = state.get("risk_statement", "")
        prev_growth = state.get("growth_statement", "")
        prev_sentiment = state.get("sentiment_statement", "")
        
        # 이름표를 붙여서 누구의 의견인지 명확히 표시
        opponents_map = {
            "fundamental": [
                f"[Risk Manager] {prev_risk}",
                f"[Growth Hunter] {prev_growth}",
                f"[Sentiment Analyst] {prev_sentiment}"
            ],
            "risk": [
                f"[Fundamental Analyst] {prev_fundamental}",
                f"[Growth Hunter] {prev_growth}",
                f"[Sentiment Analyst] {prev_sentiment}"
            ],
            "growth": [
                f"[Fundamental Analyst] {prev_fundamental}",
                f"[Risk Manager] {prev_risk}",
                f"[Sentiment Analyst] {prev_sentiment}"
            ],
            "sentiment": [
                f"[Fundamental Analyst] {prev_fundamental}",
                f"[Risk Manager] {prev_risk}",
                f"[Growth Hunter] {prev_growth}"
            ],
        }
        
        # 병렬 처리: 4명의 분석가가 동시에 답변 생성 (시간 절약)
        def get_reply(agent_name: str):
            agent = agents[agent_name]
            opponents = opponents_map[agent_name]
            return agent.rebut(ticker, opponents)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                name: executor.submit(get_reply, name)
                for name in ["fundamental", "risk", "growth", "sentiment"]
            }
            
            results = {
                name: future.result()
                for name, future in futures.items()
            }
        
        fundamental_reply = results["fundamental"]
        risk_reply = results["risk"]
        growth_reply = results["growth"]
        sentiment_reply = results["sentiment"]
        
        print("\n" + "=" * 100)
        print(f"💬 ROUND {round_number}: DEBATE - 상호 반박 및 의견 조정")
        print("=" * 100)
        print("\n💼 Fundamental Analyst")
        print(fundamental_reply)
        print("\n" + "-" * 100)
        print("⚠️  Risk Manager")
        print(risk_reply)
        print("\n" + "-" * 100)
        print("🚀 Growth Catalyst Hunter")
        print(growth_reply)
        print("\n" + "-" * 100)
        print("📊 Market Sentiment Analyst")
        print(sentiment_reply)
        
        rounds = list(state.get("rounds", []))
        rounds.append({
            "round": round_number,
            "fundamental": fundamental_reply,
            "risk": risk_reply,
            "growth": growth_reply,
            "sentiment": sentiment_reply,
        })
        
        # 합의도 계산
        consensus_analyzer = ConsensusAnalyzer()
        current_consensus = consensus_analyzer.calculate_consensus(
            fundamental_reply,
            risk_reply,
            growth_reply,
            sentiment_reply
        )
        
        print(f"\n📊 Round {round_number} 합의도: {current_consensus.overall_consensus:.2f} "
              f"(액션: {current_consensus.action_consensus:.2f}, 분산: {current_consensus.score_variance:.2f})")
        
        # 동적 종료 조건 판단
        should_continue = True
        if current_consensus.overall_consensus >= 0.85:
            print(f"✅ 높은 합의도 달성 ({current_consensus.overall_consensus:.2f}) - 다음 라운드에서 종료 예정")
            should_continue = False
        elif round_number >= 3:  # 최대 3라운드
            print(f"⏱️  최대 라운드 도달 - 종료")
            should_continue = False
        
        new_state = dict(state)
        new_state["rounds"] = rounds
        new_state["fundamental_statement"] = fundamental_reply
        new_state["risk_statement"] = risk_reply
        new_state["growth_statement"] = growth_reply
        new_state["sentiment_statement"] = sentiment_reply
        new_state["consensus_metrics"] = current_consensus
        new_state["should_continue"] = should_continue
        return new_state
    
    return node


def conclusion_node(state: AgentState) -> AgentState:
    """4명의 토론 내용을 종합하여 최종 투자 결정"""
    rounds = state.get("rounds", [])
    transcript = _format_rounds(rounds)
    toolkit = AgentToolkit()
    ticker = state.get("ticker", "")
    
    full_prompt = DEBATE_CONCLUSION_PROMPT.format(transcript=transcript)
    conclusion_text = toolkit.summarize("", full_prompt)
    
    # JSON 파싱
    parser = ConclusionParser()
    consensus_metrics = state.get("consensus_metrics")
    confidence = consensus_metrics.overall_consensus if consensus_metrics else 0.5
    
    structured_conclusion = parser.parse(ticker, conclusion_text, confidence)
    
    # 읽기 쉬운 요약 생성
    readable_summary = _format_readable_conclusion(structured_conclusion)
    
    print("\n" + "=" * 100)
    print("📋 FINAL CONCLUSION - 포트폴리오 매니저의 통합 결론")
    print("=" * 100)
    print(conclusion_text)
    print("\n" + "=" * 100)
    print("📊 한눈에 보는 결론")
    print("=" * 100)
    print(readable_summary)
    print("=" * 100)
    
    new_state = dict(state)
    new_state["debate_transcript"] = transcript
    new_state["conclusion"] = conclusion_text
    new_state["structured_conclusion"] = structured_conclusion
    new_state["readable_summary"] = readable_summary
    return new_state


def _format_readable_conclusion(conclusion: InvestmentConclusion) -> str:
    """구조화된 결론을 읽기 쉬운 형태로 포맷"""
    lines = []
    
    # 헤더
    action_emoji = {
        "STRONG_BUY": "🟢",
        "BUY": "🔵", 
        "HOLD": "⚪",
        "SELL": "🟠",
        "STRONG_SELL": "🔴"
    }
    emoji = action_emoji.get(conclusion.action, "⚪")
    
    lines.append(f"\n{emoji} **최종 판단: {conclusion.action}**")
    lines.append(f"추천 포지션: {conclusion.position_size}% | 전문가 합의도: {conclusion.confidence:.0%}\n")
    
    # 핵심 요약
    lines.append("**📝 핵심 요약**")
    lines.append(conclusion.executive_summary)
    
    # 점수
    lines.append(f"\n**💯 종합 평가: {conclusion.scores.overall:.1f}/10**")
    lines.append(f"├─ 💼 Fundamental: {conclusion.scores.fundamental}/10 (재무/비즈니스)")
    lines.append(f"├─ ⚠️  Risk: {conclusion.scores.risk}/10 (위험도, 높을수록 위험)")
    lines.append(f"├─ 🚀 Growth: {conclusion.scores.growth}/10 (성장 가능성)")
    lines.append(f"└─ 📊 Sentiment: {conclusion.scores.sentiment}/10 (시장 심리)")
    
    # 실행 계획
    if conclusion.immediate_action:
        lines.append(f"\n**⚡ 즉시 행동 (1-5일)**")
        lines.append(f"• {conclusion.immediate_action}")
    
    if conclusion.short_term_strategy:
        lines.append(f"\n**📅 단기 전략 (1-3개월)**")
        lines.append(f"• {conclusion.short_term_strategy}")
    
    if conclusion.long_term_strategy:
        lines.append(f"\n**🎯 장기 전략 (6개월-1년)**")
        lines.append(f"• {conclusion.long_term_strategy}")
    
    # 트리거
    if conclusion.bullish_trigger:
        lines.append(f"\n**📈 상승 시그널**")
        lines.append(f"조건: {conclusion.bullish_trigger.condition}")
        lines.append(f"→ 액션: {conclusion.bullish_trigger.action}")
    
    if conclusion.bearish_trigger:
        lines.append(f"\n**📉 하락 시그널**")
        lines.append(f"조건: {conclusion.bearish_trigger.condition}")
        lines.append(f"→ 액션: {conclusion.bearish_trigger.action}")
    
    return "\n".join(lines)


def _format_rounds(rounds: List[Dict[str, str]]) -> str:
    """토론 기록을 텍스트로 포맷"""
    lines = []
    for entry in rounds:
        rid = entry.get("round")
        lines.append(f"\n{'='*80}")
        lines.append(f"Round {rid}")
        lines.append(f"{'='*80}")
        lines.append(f"\n[Fundamental Analyst]\n{entry.get('fundamental', '')}")
        lines.append(f"\n[Risk Manager]\n{entry.get('risk', '')}")
        lines.append(f"\n[Growth Catalyst Hunter]\n{entry.get('growth', '')}")
        lines.append(f"\n[Market Sentiment Analyst]\n{entry.get('sentiment', '')}")
    return "\n".join(lines)


# 동적 라운드 조정을 위한 조건부 함수
def should_continue_debate(state: AgentState) -> str:
    """합의도에 따라 토론 계속 여부 결정"""
    should_continue = state.get("should_continue", True)
    
    if should_continue:
        # 아직 라운드가 남았으면 다음 라운드로
        rounds = state.get("rounds", [])
        current_round = len(rounds)
        if current_round < 3:  # 최대 3라운드 (초기 + 2라운드 토론)
            return f"debate_round_{current_round}"
    
    # 종료 → conclusion으로
    return "conclusion"


# LangGraph 구성: 동적 라운드 조정
graph_builder = StateGraph(AgentState)
graph_builder.add_node("collect_data", collect_data_node)
graph_builder.add_node("debate_round_1", _debate_round_node(2))
graph_builder.add_node("debate_round_2", _debate_round_node(3))
graph_builder.add_node("conclusion", conclusion_node)

graph_builder.add_edge(START, "collect_data")

# collect_data → 항상 debate_round_1
graph_builder.add_edge("collect_data", "debate_round_1")

# debate_round_1 → 조건부 (합의도 높으면 conclusion, 아니면 debate_round_2)
graph_builder.add_conditional_edges(
    "debate_round_1",
    should_continue_debate,
    {
        "debate_round_2": "debate_round_2",
        "conclusion": "conclusion"
    }
)

# debate_round_2 → 항상 conclusion (최대 라운드)
graph_builder.add_edge("debate_round_2", "conclusion")
graph_builder.add_edge("conclusion", END)

compiled_graph = graph_builder.compile()


def run_multiagent_pipeline(ticker: str) -> AgentState:
    """
    4명의 전문가 토론 파이프라인 실행
    
    Args:
        ticker: 분석할 주식 티커
    
    Returns:
        최종 State (데이터, 토론 기록, 결론 포함)
    """
    initial_state: AgentState = {"ticker": ticker.upper()}
    return compiled_graph.invoke(initial_state)
