"""
스케줄러 모듈
매일 오전 6시에 지정된 티커들의 공시 자료를 자동으로 크롤링합니다.
"""

import json
import logging
from pathlib import Path
from typing import List
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from src.sec_crawler import SECCrawler
from src.db import SECDatabase

# 로깅 설정 => 정보, 경고, 에러등을 기록
logging.basicConfig(
    level=logging.INFO, # INFO 이상 level log만 기록 (DEBUG < INFO < WARNING< ERROR< CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', # 메세지 출력형식
    handlers=[
        logging.FileHandler('crawler.log'), # 파일 기록
        logging.StreamHandler() # terminal 기록
    ]
)
logger = logging.getLogger(__name__) # logger 객체 생성


def load_tickers(config_path: str = "config/tickers.json") -> List[str]:
    """
    설정 파일에서 티커 리스트를 로드합니다.
    
    Args:
        config_path: 설정 파일 경로
        
    Returns:
        티커 리스트
    """
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
            return []
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        tickers = config.get("tickers", []) # 딕셔너리 config애서 tickers key 값 가져오고, 키가 없으면 빈 list를 반환
        logger.info(f"티커 리스트 로드 완료: {tickers}")
        return tickers
    except Exception as e:
        logger.error(f"설정 파일 로드 중 오류 발생: {e}")
        return []


def crawl_all_tickers():
    """
    설정된 모든 티커에 대해 공시 자료를 크롤링합니다.
    """
    logger.info("=" * 50)
    logger.info("크롤링 작업 시작")
    logger.info("=" * 50)
    
    # 티커 리스트 로드
    tickers = load_tickers()
    if not tickers:
        logger.warning("크롤링할 티커가 없습니다.")
        return
    
    # 크롤러 및 DB 초기화
    crawler = SECCrawler()
    db = SECDatabase()
    
    success_count = 0
    fail_count = 0
    
    # 각 티커에 대해 크롤링 실행
    for ticker in tickers:
        try:
            logger.info(f"\n[{ticker}] 크롤링 시작...")
            result = crawler.crawl_latest_filing(
                ticker=ticker,
                save_to_db=True,
                db=db,
                only_today=True  # 어제 날짜 기준 공시만
            )
            
            if result:
                metadata, file_path = result
                logger.info(f"[{ticker}] 크롤링 성공: {metadata.get('form')} - {file_path}")
                success_count += 1
            else:
                logger.info(f"[{ticker}] 크롤링할 공시가 없거나 이미 저장된 공시입니다.")
                
        except Exception as e:
            logger.error(f"[{ticker}] 크롤링 중 오류 발생: {e}", exc_info=True)
            fail_count += 1
    
    # 결과 요약
    logger.info("\n" + "=" * 50)
    logger.info("크롤링 작업 완료")
    logger.info(f"성공: {success_count}, 실패: {fail_count}, 전체: {len(tickers)}")
    logger.info("=" * 50)
    
    # DB 통계 출력
    stats = db.get_statistics()
    logger.info(f"\nDB 통계:")
    logger.info(f"  전체 공시 수: {stats['total_filings']}")
    logger.info(f"  티커별: {stats['by_ticker']}")
    logger.info(f"  형식별: {stats['by_form']}")


def setup_scheduler():
    """
    스케줄러를 설정하고 실행합니다.
    매일 오전 6시(한국 시간)에 크롤링 작업을 실행합니다.
    """
    # BlockingScheduler: APSscheduler의 스케줄러로, main thread를 차단()하면서 예약 작업을 실행
    # 프로그램이 scheduler만 기다리는 상태로 머묾 (예약한 작업 외의 코드는 못돌림) => 다른 process가 사용을 못함
    # 예약된 시간외에는 아무일도 안하고 대기 -> 웹서버, 사용자 입력등과 병행 불가 (웹서버 등의 기능을 동시에 구현할 경우 문제가 생길 수 있음) => 확장성, 상호작용이 필요한 ㅜㄱ조에 제한적
    scheduler = BlockingScheduler(timezone='Asia/Seoul') # 아시아/서울 시간대에 맞춘 스케줄러 생성
    
    # 매일 오전 6시에 실행 (한국 시간 기준)
    # add_job: 예약 작업을 추가
    scheduler.add_job(
        crawl_all_tickers, # 해당 ticker에 있는 모든 기업들을 crawling
        trigger=CronTrigger(hour=6, minute=0, timezone='Asia/Seoul'), # 해당 시간에 실행
        id='daily_crawl',
        name='매일 오전 6시 공시 크롤링',
        replace_existing=True
    )
    
    logger.info("스케줄러 설정 완료")
    logger.info("매일 오전 6시(한국 시간)에 크롤링이 실행됩니다.")
    logger.info("스케줄러를 시작합니다...")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("스케줄러를 종료합니다.")
        scheduler.shutdown()


if __name__ == "__main__":
    # 즉시 한 번 실행 (테스트용)
    # crawl_all_tickers()
    
    # 스케줄러 시작
    setup_scheduler()

