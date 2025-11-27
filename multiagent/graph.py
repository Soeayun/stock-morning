"""
LangGraph 기반 멀티 에이전트 파이프라인
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, START, END

from multiagent.nodes.data_collector import prepare_ticker_dataset
from multiagent.services import AgentToolkit
from multiagent.agents.news_agent import NewsAgent
from multiagent.agents.sec_agent import SECAgent
from multiagent.prompts import DEBATE_CONCLUSION_PROMPT


class AgentState(TypedDict, total=False):
    ticker: str
    dataset: Dict[str, Any]
    rounds: List[Dict[str, str]]
    news_statement: str
    sec_statement: str
    debate_transcript: str
    conclusion: str


def collect_data_node(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    info = prepare_ticker_dataset(ticker)
    dataset = info["dataset"]
    initial_round = {
        "round": 1,
        "news": info["initial_news"],
        "sec": info["initial_sec"],
    }
    print("=" * 80)
    print("[Blind Analysis] News Agent")
    print(info["initial_news"])
    print("-" * 80)
    print("[Blind Analysis] SEC Agent")
    print(info["initial_sec"])
    return {
        "ticker": ticker,
        "dataset": dataset,
        "rounds": [initial_round],
        "news_statement": info["initial_news"],
        "sec_statement": info["initial_sec"],
    }


def _debate_round_node(round_number: int):
    def node(state: AgentState) -> AgentState:
        dataset = state["dataset"]
        toolkit = AgentToolkit()
        news_agent = NewsAgent(toolkit)
        sec_agent = SECAgent(toolkit)

        prev_sec = state.get("sec_statement", "")
        prev_news = state.get("news_statement", "")

        news_reply = news_agent.rebut(dataset, prev_sec)
        sec_reply = sec_agent.rebut(dataset, prev_news)

        print("=" * 80)
        print(f"[Round {round_number}] News Agent")
        print(news_reply)
        print("-" * 80)
        print(f"[Round {round_number}] SEC Agent")
        print(sec_reply)

        rounds = list(state.get("rounds", []))
        rounds.append({"round": round_number, "news": news_reply, "sec": sec_reply})

        new_state = dict(state)
        new_state["rounds"] = rounds
        new_state["news_statement"] = news_reply
        new_state["sec_statement"] = sec_reply
        return new_state

    return node


def conclusion_node(state: AgentState) -> AgentState:
    rounds = state.get("rounds", [])
    transcript = _format_rounds(rounds)
    toolkit = AgentToolkit()
    conclusion = toolkit.summarize(transcript, DEBATE_CONCLUSION_PROMPT)
    new_state = dict(state)
    new_state["debate_transcript"] = transcript
    new_state["conclusion"] = conclusion
    return new_state


def _format_rounds(rounds: List[Dict[str, str]]) -> str:
    lines = []
    for entry in rounds:
        rid = entry.get("round")
        lines.append(f"[Round {rid}] News: {entry.get('news')}")
        lines.append(f"[Round {rid}] SEC: {entry.get('sec')}")
    return "\n".join(lines)


graph_builder = StateGraph(AgentState)
graph_builder.add_node("collect_data", collect_data_node)
graph_builder.add_node("debate_round_1", _debate_round_node(2))
graph_builder.add_node("debate_round_2", _debate_round_node(3))
graph_builder.add_node("conclusion", conclusion_node)

graph_builder.add_edge(START, "collect_data")
graph_builder.add_edge("collect_data", "debate_round_1")
graph_builder.add_edge("debate_round_1", "debate_round_2")
graph_builder.add_edge("debate_round_2", "conclusion")
graph_builder.add_edge("conclusion", END)

compiled_graph = graph_builder.compile()


def run_multiagent_pipeline(ticker: str) -> AgentState:
    """
    LangGraph 파이프라인을 실행하여 데이터 + 에이전트 초기 의견을 반환합니다.
    """
    initial_state: AgentState = {"ticker": ticker.upper()}
    return compiled_graph.invoke(initial_state)
