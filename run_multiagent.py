#!/usr/bin/env python
"""
멀티 에이전트 파이프라인 실행 스크립트
예시:
    python run_multiagent.py --ticker GOOG
"""

import argparse
from pprint import pprint

from multiagent.graph import run_multiagent_pipeline


def parse_args():
    parser = argparse.ArgumentParser(description="Run LangGraph multi-agent pipeline")
    parser.add_argument("--ticker", required=True, help="분석할 티커")
    return parser.parse_args()


def main():
    args = parse_args()
    print(f"=== Multi-Agent Pipeline Start (ticker={args.ticker.upper()}) ===")

    result = run_multiagent_pipeline(args.ticker)

    rounds = result.get("rounds", [])
    for entry in rounds:
        rid = entry.get("round")
        header = "Blind Analysis" if rid == 1 else f"Debate Round {rid}"
        print("\n" + "=" * 80)
        print(f"--- {header} ---")
        print("=" * 80)
        print("[News Agent]")
        print(entry.get("news"))
        print("\n[SEC Agent]")
        print(entry.get("sec"))

    print("\n" + "=" * 80)
    print("--- Debate Transcript ---")
    print("=" * 80)
    print(result.get("debate_transcript"))

    print("\n" + "=" * 80)
    print("=== Final Conclusion ===")
    print("=" * 80)
    print(result.get("conclusion"))


if __name__ == "__main__":
    main()
