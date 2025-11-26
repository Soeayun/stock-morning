"""
LangGraph 기반 멀티 에이전트 파이프라인
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, START, END

from multiagent.nodes.data_collector import prepare_ticker_dataset
from multiagent.services import AgentToolkit
from multiagent.prompts import DEBATE_CONCLUSION_PROMPT


class AgentState(TypedDict, total=False):
    ticker: str
    dataset: Dict[str, Any]
    agent_outputs: List[Dict[str, Any]]
    debate_transcript: str
    conclusion: str


def collect_data_node(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    dataset = prepare_ticker_dataset(ticker)
    return {
        "ticker": ticker,
        "dataset": dataset,
        "agent_outputs": dataset.get("agent_outputs", []),
    }


def debate_once_node(state: AgentState) -> AgentState:
    outputs = state.get("agent_outputs", [])
    transcript = _format_agent_outputs(outputs)
    toolkit = AgentToolkit()
    conclusion = toolkit.summarize(transcript, DEBATE_CONCLUSION_PROMPT)
    new_state = dict(state)
    new_state["debate_transcript"] = transcript
    new_state["conclusion"] = conclusion
    return new_state


def _format_agent_outputs(outputs: List[Dict[str, Any]]) -> str:
    lines = []
    for out in outputs:
        role = out.get("role")
        agent = out.get("agent")
        opinion = out.get("opinion") or ""
        lines.append(f"[{role}] {agent}: {opinion}")
        if "summaries" in out:
            for idx, summary in enumerate(out["summaries"], 1):
                headline = summary.get("title") or summary.get("form") or f"item {idx}"
                lines.append(f"  - {headline}: {summary.get('summary')}")
    return "\n".join(lines)


graph_builder = StateGraph(AgentState)
graph_builder.add_node("collect_data", collect_data_node)
graph_builder.add_node("debate_once", debate_once_node)

graph_builder.add_edge(START, "collect_data")
graph_builder.add_edge("collect_data", "debate_once")
graph_builder.add_edge("debate_once", END)

compiled_graph = graph_builder.compile()


def run_multiagent_pipeline(ticker: str) -> AgentState:
    """
    LangGraph 파이프라인을 실행하여 데이터 + 에이전트 초기 의견을 반환합니다.
    """
    initial_state: AgentState = {"ticker": ticker.upper()}
    return compiled_graph.invoke(initial_state)
