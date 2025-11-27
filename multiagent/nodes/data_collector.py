"""
멀티 에이전트 그래프 첫 노드: 티커 데이터 준비
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from src.database.data_fetcher import DataFetcher
from aws_fetchers.yahoo_news_fetcher import YahooNewsFetcher
from multiagent.services import AgentToolkit
from multiagent.agents.news_agent import NewsAgent
from multiagent.agents.sec_agent import SECAgent


def prepare_ticker_dataset(
    ticker: str,
    hours: int = 24,
    news_limit: Optional[int] = 5,
) -> Dict:
    """
    티커를 입력받아 AWS 뉴스(S3 + DynamoDB)와
    로컬 SEC 데이터(sec_filings.db)를 동시에 수집합니다.
    LangGraph 첫 노드에서 그대로 사용할 수 있는 유틸 함수입니다.
    """
    ticker_upper = ticker.upper()

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)

    # 1) AWS에서 뉴스 가져오기
    yahoo_fetcher = YahooNewsFetcher()
    aws_news = yahoo_fetcher.fetch(ticker_upper, limit=news_limit or 5)

    # 2) 로컬 SEC 데이터 (최근 24시간)
    fetcher = DataFetcher()
    sec_data = fetcher.fetch_ticker_data(ticker_upper, include_file_content=True)

    dataset = {
        "ticker": ticker_upper,
        "period": sec_data.get("period"),
        "aws_news": aws_news,
        "sec_filings": sec_data.get("sec_filings"),
    }

    toolkit = AgentToolkit()
    news_agent = NewsAgent(toolkit)
    sec_agent = SECAgent(toolkit)

    initial_news = news_agent.blind_assessment(dataset)
    initial_sec = sec_agent.blind_assessment(dataset)

    return {
        "dataset": dataset,
        "initial_news": initial_news,
        "initial_sec": initial_sec,
    }
