#!/usr/bin/env python
"""
스케줄러 실행 스크립트
매일 오전 6시에 자동으로 공시 자료를 크롤링합니다.

사용법:
    python run_scheduler.py          # 스케줄러 시작 (데몬 모드)
    python run_scheduler.py --once   # 즉시 한 번만 실행
"""

import argparse
from src.scheduler import crawl_all_tickers, setup_scheduler


def main():
    parser = argparse.ArgumentParser(description='SEC 공시 자료 자동 크롤링 스케줄러')
    parser.add_argument(
        '--once',
        action='store_true',
        help='즉시 한 번만 실행하고 종료 (스케줄러 모드 아님)'
    )
    
    args = parser.parse_args()
    
    if args.once:
        # 즉시 한 번만 실행
        print("즉시 크롤링 실행...")
        crawl_all_tickers()
    else:
        # 스케줄러 모드로 실행
        setup_scheduler()


if __name__ == "__main__":
    main()

