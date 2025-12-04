#!/usr/bin/env python
"""
4명 전문가 토론 파이프라인 실행 스크립트

예시:
    python run_multiagent.py --ticker GOOG
    python run_multiagent.py --ticker AAPL
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 환경변수 로드 (LangSmith 추적 설정 포함)
load_dotenv()

from multiagent.graph import run_multiagent_pipeline


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run 4-Expert Debate Pipeline for Stock Analysis"
    )
    parser.add_argument("--ticker", required=True, help="분석할 티커 (예: GOOG, AAPL)")
    parser.add_argument(
        "--save",
        action="store_true",
        help="결과를 JSON 파일로 저장할지 여부",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/agent_results",
        help="결과 저장 디렉토리 (기본: data/agent_results)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    ticker = args.ticker.upper()
    
    # LangSmith 추적 상태 확인
    langsmith_enabled = os.getenv("LANGCHAIN_TRACING_V2") == "true"
    langsmith_project = os.getenv("LANGCHAIN_PROJECT", "stock-morning-multiagent")
    
    print("\n" + "=" * 100)
    print(f"🎯 4-EXPERT DEBATE PIPELINE START")
    print(f"📊 Ticker: {ticker}")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if langsmith_enabled:
        print(f"🔍 LangSmith Tracing: ✅ Enabled (Project: {langsmith_project})")
        print(f"   📎 https://smith.langchain.com/o/{os.getenv('LANGSMITH_ORG', 'default')}/projects/p/{langsmith_project}")
    else:
        print(f"🔍 LangSmith Tracing: ⚠️  Disabled (환경변수 LANGCHAIN_TRACING_V2=true 설정 필요)")
    print("=" * 100)
    
    # 파이프라인 실행 (모든 출력은 graph.py에서 자동으로 처리됨)
    result = run_multiagent_pipeline(ticker)
    
    # JSON 저장 옵션
    if args.save:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_{timestamp}_debate.json"
        filepath = output_dir / filename
        
        # 저장할 데이터 정리
        structured_conclusion = result.get("structured_conclusion")
        readable_summary = result.get("readable_summary", "")
        
        save_data = {
            "ticker": ticker,
            "timestamp": timestamp,
            "rounds": result.get("rounds", []),
            "conclusion": result.get("conclusion", ""),  # LLM 원문 (상세)
            "readable_summary": readable_summary,  # 한눈에 보는 요약 (간결)
            "debate_transcript": result.get("debate_transcript", ""),
        }
        
        # 구조화된 결론 추가 (Pydantic 모델을 dict로 변환)
        if structured_conclusion:
            save_data["structured_conclusion"] = structured_conclusion.model_dump()
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 결과 저장 완료: {filepath}")
    
    print("\n" + "=" * 100)
    print("✨ PIPELINE COMPLETED")
    print("=" * 100)


if __name__ == "__main__":
    main()
