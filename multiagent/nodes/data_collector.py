"""
멀티 에이전트 그래프 첫 노드: 티커 데이터 준비
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from src.database.data_fetcher import DataFetcher
from aws_fetchers.yahoo_news_fetcher import YahooNewsFetcher
from multiagent.services import AgentToolkit
from multiagent.services.market_data import MarketDataFetcher
from multiagent.agents.fundamental_analyst import FundamentalAnalyst
from multiagent.agents.risk_manager import RiskManager
from multiagent.agents.growth_analyst import GrowthAnalyst
from multiagent.agents.sentiment_analyst import SentimentAnalyst


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

    # 1) AWS에서 뉴스 가져오기 (에러 핸들링)
    aws_news = []
    try:
        yahoo_fetcher = YahooNewsFetcher()
        aws_news = yahoo_fetcher.fetch(ticker_upper, limit=news_limit or 5)
    except Exception as exc:
        print(f"⚠️  [{ticker_upper}] AWS 뉴스 수집 실패: {exc}")
        aws_news = []

    # 2) 로컬 SEC 데이터 (최근 24시간)
    fetcher = DataFetcher()
    sec_data = fetcher.fetch_ticker_data(ticker_upper, include_file_content=True)

    # 3) 실시간 시장 데이터 (yfinance) - 에러 핸들링
    market_data = None
    market_data_text = ""
    try:
        market_fetcher = MarketDataFetcher()
        market_data = market_fetcher.fetch_market_data(ticker_upper)
        market_data_text = market_fetcher.format_market_data_for_prompt(market_data)
        
        if market_data and market_data.current_price:
            print(f"💰 [{ticker_upper}] 현재 주가: ${market_data.current_price:,.2f}")
    except Exception as exc:
        print(f"⚠️  [{ticker_upper}] 시장 데이터 수집 실패: {exc}")
        market_data = None
        market_data_text = "시장 데이터를 가져올 수 없습니다."

    dataset = {
        "ticker": ticker_upper,
        "period": sec_data.get("period"),
        "aws_news": aws_news,
        "sec_filings": sec_data.get("sec_filings"),
        "market_data": market_data,
        "market_data_text": market_data_text,
    }

    # 4명의 전문가 초기화
    toolkit = AgentToolkit()
    fundamental = FundamentalAnalyst(toolkit)
    risk = RiskManager(toolkit)
    growth = GrowthAnalyst(toolkit)
    sentiment = SentimentAnalyst(toolkit)

    # 각 전문가의 초기 분석 (Blind Assessment)
    initial_fundamental = fundamental.blind_assessment(dataset)
    initial_risk = risk.blind_assessment(dataset)
    initial_growth = growth.blind_assessment(dataset)
    initial_sentiment = sentiment.blind_assessment(dataset)

    return {
        "dataset": dataset,
        "initial_fundamental": initial_fundamental,
        "initial_risk": initial_risk,
        "initial_growth": initial_growth,
        "initial_sentiment": initial_sentiment,
    }
