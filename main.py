"""
메인 실행 스크립트
SEC와 Quartr 크롤러를 선택적으로 실행할 수 있습니다.
"""

import json
from pathlib import Path

from src.sec_crawler import SECCrawler
from src.quartr_crawler import QuartrCrawler
from src.db import SECDatabase, QuartrDatabase


def load_tickers(config_path: str = "config/tickers.json") -> list[str]:
    """설정 파일에서 티커 리스트 로드"""
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"⚠️  설정 파일을 찾을 수 없습니다: {config_path}")
        return []
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return config.get("tickers", [])


def run_sec():
    """SEC 크롤러 실행"""
    print("=" * 60)
    print("SEC 크롤러 실행")
    print("=" * 60)
    
    tickers = load_tickers()
    if not tickers:
        print("⚠️  크롤링할 티커가 없습니다.")
        return
    
    crawler = SECCrawler()
    db = SECDatabase()
    
    success_count = 0
    
    for ticker in tickers:
        print(f"\n[{ticker}] 크롤링 시작...")
        result = crawler.crawl_latest_filing(ticker, save_to_db=True, db=db, only_today=True)
        
        if result:
            metadata, file_path = result
            print(f"✅ [{ticker}] 성공: {metadata.get('form')} - {file_path}")
            success_count += 1
        else:
            print(f"⚪ [{ticker}] 새로운 공시 없음")
    
    # DB 통계 출력
    stats = db.get_statistics()
    print("\n" + "=" * 60)
    print(f"SEC 크롤링 완료: {success_count}/{len(tickers)} 성공")
    print(f"전체 공시 수: {stats['total_filings']}")
    print(f"티커별: {stats['by_ticker']}")
    print("=" * 60)


def run_quartr():
    """Quartr 크롤러 실행"""
    print("=" * 60)
    print("Quartr 크롤러 실행")
    print("=" * 60)
    
    tickers = load_tickers()
    if not tickers:
        print("⚠️  크롤링할 티커가 없습니다.")
        return
    
    print(f"대상 티커: {', '.join(tickers)}\n")
    
    crawler = QuartrCrawler()
    results = crawler.run(tickers)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("Quartr 크롤링 결과")
    print("=" * 60)
    
    total_saved = 0
    for ticker, count in results.items():
        status = "✅" if count > 0 else "⚪"
        print(f"{status} {ticker}: {count}개 저장")
        total_saved += count
    
    print("=" * 60)
    print(f"총 {total_saved}개의 컨퍼런스 콜 저장 완료")
    print("=" * 60)


def main():
    """
    메인 실행 함수
    
    실행 방법:
    - SEC만 실행: run_sec()만 주석 해제
    - Quartr만 실행: run_quartr()만 주석 해제
    - 둘 다 실행: 둘 다 주석 해제
    """
    # run_sec()      # SEC 크롤러 실행
    run_quartr()   # Quartr 크롤러 실행


if __name__ == "__main__":
    main()
