"""
Base Agent
각 Ticker별 Agent의 기본 클래스입니다.
(나중에 브리핑 생성 기능을 추가할 예정)
"""

from typing import Dict, List, Any
import json
from pathlib import Path
from datetime import datetime


class TickerAgent:
    """Ticker별 Agent 기본 클래스"""
    
    def __init__(self, ticker: str):
        """
        Args:
            ticker: 종목 코드
        """
        self.ticker = ticker.upper()
    
    def process_data(self, data: Dict) -> Dict:
        """
        데이터 처리 (현재는 분석만, 나중에 브리핑 생성)
        
        Args:
            data: {
                'ticker': str,
                'period': {'start': str, 'end': str},
                'news': List[Dict],
                'sec_filings': List[Dict]
            }
        
        Returns:
            처리 결과
        """
        print(f"\n{'='*60}")
        print(f"[{self.ticker}] Agent 데이터 처리 시작")
        print(f"{'='*60}")
        
        # 데이터 요약
        news_count = len(data.get('news', []))
        sec_count = len(data.get('sec_filings', []))
        
        print(f"\n📊 데이터 요약:")
        print(f"  - 뉴스: {news_count}개")
        print(f"  - SEC 공시: {sec_count}개")
        print(f"  - 기간: {data['period']['start']} ~ {data['period']['end']}")
        
        # 뉴스 분석
        if news_count > 0:
            print(f"\n📰 뉴스 분석:")
            for i, news_item in enumerate(data['news'][:3], 1):  # 최대 3개만 출력
                print(f"  {i}. {news_item.get('title', 'N/A')[:80]}...")
        
        # SEC 공시 분석
        if sec_count > 0:
            print(f"\n📄 SEC 공시 분석:")
            for i, filing in enumerate(data['sec_filings'][:3], 1):
                meta = filing.get('metadata', {})
                print(f"  {i}. {meta.get('form', 'N/A')} - {meta.get('filed_date', 'N/A')}")
        
        result = {
            'ticker': self.ticker,
            'processed_at': datetime.utcnow().isoformat(),
            'data_summary': {
                'news_count': news_count,
                'sec_filing_count': sec_count,
                'period': data['period']
            },
            'status': 'processed'
        }
        
        print(f"\n{'='*60}")
        print(f"[{self.ticker}] Agent 처리 완료")
        print(f"{'='*60}\n")
        
        return result
    
    def save_result(self, result: Dict, output_dir: str = "data/agent_results"):
        """
        처리 결과 저장 (JSON 파일)
        
        Args:
            result: 처리 결과
            output_dir: 저장 디렉토리
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{self.ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = output_path / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ 결과 저장 완료: {file_path}")
        
        return file_path


class AgentManager:
    """여러 Ticker Agent를 관리하는 클래스"""
    
    def __init__(self, tickers: List[str]):
        """
        Args:
            tickers: 종목 코드 리스트
        """
        self.agents = {ticker.upper(): TickerAgent(ticker) for ticker in tickers}
    
    def process_all(self, data_dict: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        모든 Agent 데이터 처리
        
        Args:
            data_dict: {ticker: data} 딕셔너리
        
        Returns:
            {ticker: result} 딕셔너리
        """
        results = {}
        
        for ticker, agent in self.agents.items():
            if ticker in data_dict and data_dict[ticker]:
                try:
                    result = agent.process_data(data_dict[ticker])
                    results[ticker] = result
                except Exception as e:
                    print(f"❌ [{ticker}] Agent 처리 실패: {e}")
                    results[ticker] = {'status': 'failed', 'error': str(e)}
            else:
                print(f"⚠️  [{ticker}] 데이터 없음")
                results[ticker] = {'status': 'no_data'}
        
        return results

