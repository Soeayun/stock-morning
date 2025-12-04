"""
메인 실행 스크립트
SEC 크롤러와 Agent 시스템을 관리합니다.
"""

from typing import Iterable, List, Optional

from src.sec_crawler import SECCrawler
from src.database.data_fetcher import DataFetcher
from src.agents.base_agent import AgentManager
from src.config.settings import get_settings
from src.db import SECDatabase


def _resolved_tickers(tickers: Optional[Iterable[str]]) -> List[str]:
    if tickers:
        return [t.upper() for t in tickers]
    settings = get_settings()
    return [t.upper() for t in settings.tickers]


def run_sec_crawler(tickers: Optional[Iterable[str]] = None, only_today: bool = True):
    """
    SEC 크롤러 실행 (로컬 DB 저장)
    """
    resolved = _resolved_tickers(tickers)
    if not resolved:
        print("⚠️  크롤링할 티커가 없습니다.")
        return

    print("\n" + "=" * 60)
    print("SEC 크롤러 실행")
    print("=" * 60)

    sec_crawler = SECCrawler()
    db = SECDatabase()

    for ticker in resolved:
        print(f"\n[{ticker}] SEC 크롤링 시작...")
        results = sec_crawler.crawl_filings_in_window(
            ticker,
            save_to_db=True,
            db=db,
            only_today=only_today,
        )
        if results:
            for metadata, file_path in results:
                print(f"✅ [{ticker}] SEC 성공: {metadata.get('form')} - {file_path}")
        else:
            print(f"⚪ [{ticker}] 새로운 공시 없음")

    print("\n" + "=" * 60)
    print("SEC 크롤러 실행 완료")
    print("=" * 60)


def run_agents(tickers: Optional[Iterable[str]] = None):
    """Agent 시스템 실행 (6시~6시 데이터 조회 및 처리)"""
    resolved = _resolved_tickers(tickers)
    if not resolved:
        print("⚠️  Agent를 실행할 티커가 없습니다.")
        return

    print("\n" + "=" * 60)
    print("Agent 시스템 실행")
    print("=" * 60)

    fetcher = DataFetcher()
    print("\n데이터 조회 시작...")
    data_dict = fetcher.fetch_all_tickers(resolved, include_file_content=True)

    print("\nAgent 처리 시작...")
    agent_manager = AgentManager(resolved)
    results = agent_manager.process_all(data_dict)

    print("\n결과 저장 중...")
    for ticker, result in results.items():
        if result.get('status') == 'processed':
            agent = agent_manager.agents[ticker]
            agent.save_result(result)

    print("\n" + "=" * 60)
    print("Agent 시스템 실행 완료")
    print("=" * 60)


def main():
    """
    메인 실행 함수: SEC/뉴스 수집 후 Agent 실행
    """
    run_sec_crawler()
    run_agents()


if __name__ == "__main__":
    main()
