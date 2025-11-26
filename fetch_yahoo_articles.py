#!/usr/bin/env python
"""
AWS DynamoDB/S3에서 특정 티커의 Yahoo Finance 뉴스를 JSON으로 저장

예시:
    python fetch_yahoo_articles.py --ticker GOOG --limit 5
"""

import argparse

from aws_fetchers.yahoo_news_fetcher import YahooNewsFetcher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Yahoo Finance news from AWS")
    parser.add_argument("--ticker", required=True, help="뉴스를 가져올 티커")
    parser.add_argument("--limit", type=int, default=5, help="최대 뉴스 개수 (기본 5)")
    parser.add_argument(
        "--output",
        type=str,
        default="aws_results",
        help="JSON 저장 폴더 (기본 aws_results)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    fetcher = YahooNewsFetcher(output_dir=args.output)
    fetcher.fetch(args.ticker, limit=args.limit)


if __name__ == "__main__":
    main()
