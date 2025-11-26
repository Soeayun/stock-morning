"""
데이터 조회 모듈
로컬 SQLite DB에서 6시~6시 기준 데이터를 가져옵니다.
"""

from pathlib import Path
from typing import Dict, List

from src.db import SECDatabase
from src.time_utils import get_korea_batch_window


class DataFetcher:
    """6시~6시 기준 데이터 조회 클래스"""
    
    def __init__(self):
        self.db = SECDatabase()
    
    def fetch_ticker_data(
        self,
        ticker: str,
        include_file_content: bool = True
    ) -> Dict:
        """
        특정 ticker의 6시~6시 기준 데이터 수집
        
        Args:
            ticker: 종목 코드
            include_file_content: SEC 파일 내용을 포함할지 여부
                                 (False면 메타데이터만)
        
        Returns:
            {
                'ticker': str,
                'period': {'start': datetime, 'end': datetime},
                'news': List[Dict],  # 로컬 뉴스 데이터
                'sec_filings': List[Dict]  # SEC 파일 (메타 + 내용)
            }
        """
        # 1. 시간 윈도우 계산 (어제 6시 ~ 오늘 6시)
        start, end = get_korea_batch_window()
        
        print(f"\n{'='*60}")
        print(f"[{ticker}] 데이터 조회 시작")
        print(f"기간: {start} ~ {end}")
        print(f"{'='*60}")
        
        # 2. 로컬 DB에서 뉴스 조회
        print(f"\n[{ticker}] 뉴스 조회 중...")
        news = self.db.get_news(
            ticker=ticker,
            start_time=start,
            end_time=end
        )
        print(f"✅ 뉴스 {len(news)}개 조회 완료")
        
        # 3. 로컬 DB에서 SEC 메타데이터 조회
        print(f"\n[{ticker}] SEC 메타데이터 조회 중...")
        sec_metadata = self.db.get_filings_between(
            ticker=ticker,
            start_time=start,
            end_time=end
        )
        print(f"✅ SEC 메타데이터 {len(sec_metadata)}개 조회 완료")
        
        # 4. 로컬 파일에서 SEC 내용 가져오기
        sec_filings = []
        if include_file_content and sec_metadata:
            print(f"\n[{ticker}] 로컬 파일에서 SEC 내용 가져오는 중...")
            for i, meta in enumerate(sec_metadata, 1):
                file_path_str = meta.get('file_path')
                if not file_path_str:
                    print(f"⚠️  {i}/{len(sec_metadata)}: 파일 경로 없음")
                    continue
                
                file_path = Path(file_path_str)
                if file_path.exists():
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    sec_filings.append({
                        'metadata': meta,
                        'content': content
                    })
                    print(f"✅ {i}/{len(sec_metadata)}: {meta.get('form', 'N/A')} 파일 읽기 완료")
                else:
                    print(f"❌ {i}/{len(sec_metadata)}: 파일 없음 - {file_path}")
        else:
            # 파일 내용 없이 메타데이터만
            sec_filings = [{'metadata': meta, 'content': None} for meta in sec_metadata]
        
        result = {
            'ticker': ticker,
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat()
            },
            'news': news,
            'sec_filings': sec_filings
        }
        
        print(f"\n{'='*60}")
        print(f"[{ticker}] 데이터 조회 완료")
        print(f"뉴스: {len(news)}개")
        print(f"SEC 공시: {len(sec_filings)}개")
        print(f"{'='*60}\n")
        
        return result
    
    def fetch_all_tickers(
        self,
        tickers: List[str],
        include_file_content: bool = True
    ) -> Dict[str, Dict]:
        """
        여러 ticker의 데이터를 한번에 조회
        
        Args:
            tickers: 종목 코드 리스트
            include_file_content: SEC 파일 내용 포함 여부
        
        Returns:
            {ticker: data} 딕셔너리
        """
        results = {}
        
        for ticker in tickers:
            try:
                data = self.fetch_ticker_data(ticker, include_file_content)
                results[ticker] = data
            except Exception as e:
                print(f"❌ [{ticker}] 데이터 조회 실패: {e}")
                results[ticker] = None
        
        return results
