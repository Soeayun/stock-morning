#!/usr/bin/env python
"""
뉴스 본문 수집 스크립트

예시:
    python fetch_news_content.py             # 전체 뉴스 대상
    python fetch_news_content.py --hours 12  # 최근 12시간 뉴스만
    python fetch_news_content.py --limit 50  # 최대 50건만 처리
"""

import argparse
from datetime import datetime, timedelta, timezone

from src.news_content_fetcher import NewsContentFetcher


def parse_args():
    parser = argparse.ArgumentParser(description="뉴스 본문 수집기")
    parser.add_argument(
        "--hours",
        type=int,
        default=None,
        help="최근 N시간 동안의 뉴스만 대상으로 수집 (기본: 전체)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="최대 처리 뉴스 개수 (기본: 제한 없음)",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="특정 티커만 대상으로 실행 (기본: 전체)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    start_time = None
    end_time = None
    if args.hours:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=args.hours)

    fetcher = NewsContentFetcher()
    tickers = [args.ticker] if args.ticker else None

    fetcher.fetch_and_store(
        start_time=start_time,
        end_time=end_time,
        limit=args.limit,
        tickers=tickers,
    )


if __name__ == "__main__":
    main()
