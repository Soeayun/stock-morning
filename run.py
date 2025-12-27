#!/usr/bin/env python
"""
통합 실행 스크립트: SEC 크롤링 + 4명 전문가 토론 파이프라인

사용법:
    python run.py --ticker GOOG                    # 크롤링 + 분석
    python run.py --ticker GOOG --skip-crawl       # 크롤링 생략, 분석만
    python run.py --ticker GOOG --crawl-only       # 크롤링만
    python run.py --ticker GOOG --save             # 결과 JSON 저장
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="SEC 크롤링 + 4명 전문가 토론 파이프라인"
    )
    parser.add_argument("--ticker", required=True, help="분석할 티커 (예: GOOG, AAPL)")
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="SEC 크롤링 생략 (이미 데이터가 있는 경우)",
    )
    parser.add_argument(
        "--crawl-only",
        action="store_true",
        help="SEC 크롤링만 실행 (분석 생략)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="결과를 JSON 파일로 저장",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/agent_results",
        help="결과 저장 디렉토리 (기본: data/agent_results)",
    )
    return parser.parse_args()


def run_crawling(ticker: str) -> dict:
    """SEC 크롤링 실행"""
    from src.sec_crawler import SECCrawler
    from src.db import SECDatabase
    
    print("\n" + "=" * 100)
    print("📥 SEC 크롤링 시작")
    print("=" * 100)
    
    sec_crawler = SECCrawler()
    db = SECDatabase()
    
    print(f"\n[{ticker}] SEC 공시 크롤링 중...")
    results = sec_crawler.crawl_filings_in_window(
        ticker,
        save_to_db=True,
        db=db,
        only_today=True,
        include_annual_quarterly=True,  # 10-K, 10-Q 항상 포함
    )
    
    stats = {"total": 0, "10-K": False, "10-Q": False}
    if results:
        for metadata, file_path in results:
            form = metadata.get('form')
            print(f"  ✅ {form}: {file_path}")
            stats["total"] += 1
            if form == "10-K":
                stats["10-K"] = True
            if form == "10-Q":
                stats["10-Q"] = True
    else:
        print(f"  ⚪ 새로운 공시 없음 (기존 데이터 사용)")
    
    print(f"\n📊 크롤링 결과: {stats['total']}건 (10-K: {'✅' if stats['10-K'] else '❌'}, 10-Q: {'✅' if stats['10-Q'] else '❌'})")
    print("=" * 100)
    
    return stats


def run_analysis(ticker: str, save: bool = False, output_dir: str = "data/agent_results") -> dict:
    """4명 전문가 토론 파이프라인 실행"""
    from multiagent.graph import run_multiagent_pipeline
    
    # LangSmith 추적 상태 확인
    langsmith_enabled = os.getenv("LANGCHAIN_TRACING_V2") == "true"
    langsmith_project = os.getenv("LANGCHAIN_PROJECT", "stock-morning")
    
    print("\n" + "=" * 100)
    print(f"🎯 4-EXPERT DEBATE PIPELINE START")
    print(f"📊 Ticker: {ticker}")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if langsmith_enabled:
        print(f"🔍 LangSmith Tracing: ✅ Enabled (Project: {langsmith_project})")
        print(f"   📎 https://smith.langchain.com/o/{os.getenv('LANGSMITH_ORG', 'default')}/projects/p/{langsmith_project}")
    else:
        print(f"🔍 LangSmith Tracing: ⚠️  Disabled")
    print("=" * 100)
    
    # 파이프라인 실행
    result = run_multiagent_pipeline(ticker)
    
    # JSON 저장
    if save:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_{timestamp}_debate.json"
        filepath = output_path / filename
        
        structured_conclusion = result.get("structured_conclusion")
        
        save_data = {
            "ticker": ticker,
            "timestamp": timestamp,
            "rounds": result.get("rounds", []),
            "conclusion": result.get("conclusion", ""),
            "readable_summary": result.get("readable_summary", ""),
            "debate_transcript": result.get("debate_transcript", ""),
        }
        
        if structured_conclusion:
            save_data["structured_conclusion"] = structured_conclusion.model_dump()
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장 완료: {filepath}")
    
    return result


def main():
    args = parse_args()
    ticker = args.ticker.upper()
    
    print("\n" + "=" * 100)
    print(f"🚀 STOCK MORNING - 통합 분석 파이프라인")
    print(f"📊 Ticker: {ticker}")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    
    # 1단계: SEC 크롤링
    if not args.skip_crawl:
        crawl_stats = run_crawling(ticker)
    else:
        print("\n⏭️  SEC 크롤링 생략 (--skip-crawl)")
    
    # 2단계: 전문가 토론 분석
    if not args.crawl_only:
        result = run_analysis(ticker, save=args.save, output_dir=args.output_dir)
        
        # 3단계: 임시 뉴스 파일 정리
        cleanup_temp_files(ticker)
    else:
        print("\n⏭️  분석 생략 (--crawl-only)")
        result = None
    
    # 완료
    print("\n" + "=" * 100)
    print("✨ PIPELINE COMPLETED")
    print(f"⏰ 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    
    return result


def cleanup_temp_files(ticker: str):
    """분석 완료 후 임시 뉴스 파일 정리"""
    import shutil
    
    aws_results_dir = Path("aws_results")
    if aws_results_dir.exists():
        # 해당 티커의 뉴스 파일만 삭제
        ticker_files = list(aws_results_dir.glob(f"{ticker}_*.json"))
        if ticker_files:
            for f in ticker_files:
                f.unlink()
            print(f"\n🧹 임시 파일 정리: {len(ticker_files)}개 뉴스 파일 삭제")


if __name__ == "__main__":
    main()
