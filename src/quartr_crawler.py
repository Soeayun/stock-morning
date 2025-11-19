"""
Quartr earnings call 크롤러
Quartr API에서 이벤트/트랜스크립트를 수집해 데이터베이스와 파일로 저장합니다.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests

from src.db import QuartrDatabase
from src.time_utils import get_korea_batch_window, parse_iso_datetime


class QuartrAPIError(RuntimeError):
    """Quartr API 호출 실패"""


class QuartrCrawler:
    """
    Quartr API를 사용해 earnings call 이벤트와 트랜스크립트를 가져와 저장합니다.

    실제 엔드포인트 구조는 Quartr API 버전에 따라 달라질 수 있으므로 필요 시 BASE_URL/경로를 조정하세요.
    """

    BASE_URL = "https://api.quartr.com/public/v0"
    EVENTS_PATH = "/companies/{ticker}/events"
    TRANSCRIPT_PATH = "/events/{event_id}/transcripts"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        db_path: str = "quartr_calls.db",
        download_dir: str = "downloads/quartr",
        timezone_name: str = "Asia/Seoul",
        timeout: int = 30,
    ):
        self.api_key = api_key or os.getenv("QUARTR_API_KEY")
        self.db = QuartrDatabase(db_path=db_path)
        self.download_dir = Path(download_dir)
        self.timezone = ZoneInfo(timezone_name)
        self.timeout = timeout
        self.session = self._build_session()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update( # header에 추가
            {
                "Accept": "application/json", # json 형식을 원함
                "User-Agent": "stock-morning/1.0 (Quartr crawler)",
            }
        )
        if self.api_key:
            session.headers["x-api-key"] = self.api_key
        return session

    # request가 제대로 받았는지 & JSON 형식인지 확인
    def _request(self, method: str, url: str, **kwargs) -> Dict:
        resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        if resp.status_code >= 400:
            raise QuartrAPIError(f"{method} {url} 실패: {resp.status_code} {resp.text[:200]}")
        try:
            return resp.json()
        except ValueError:
            raise QuartrAPIError(f"{method} {url} 응답이 JSON이 아닙니다.")


    # 특정 tikcer를 마지막으로 언제 crawling을 진행했는지 확인하는 함수
    def _load_since(self, ticker: str) -> datetime:
        state = self.db.get_fetch_state(ticker)
        if state and state.get("last_call_datetime"):
            try:
                return datetime.fromisoformat(state["last_call_datetime"])
            except ValueError:
                self.logger.warning("잘못된 last_call_datetime 포맷, 기본 윈도우 사용: %s", state["last_call_datetime"])
        start, _ = get_korea_batch_window()
        return start


    # Auantr API에서 날짜 이후의 event만 list로 반환 -> 
    def _fetch_events(self, ticker: str, since: datetime) -> List[Dict]:
        url = f"{self.BASE_URL}{self.EVENTS_PATH.format(ticker=ticker)}"
        params = { # API 호출에 사용할 parameter dictionary
            "types": "earnings_call,conference_call",
            "from": since.isoformat(),
            "order": "asc",
        }
        payload = self._request("GET", url, params=params) # 해당 parameter로 GET 요청을 하여 JSON 응답을 받음
        # isinstance(obj, type)는 객체가 특정 타입이나 그 하위 클래스의 인스턴스인지 확인하는 함수
        events = payload.get("events") if isinstance(payload, dict) else payload # 응답이 dictionary면 events key값을, 아닐 경우 전체 payload를 event로 사용
        if not isinstance(events, list): # events가 list가 아니라면 오류
            raise QuartrAPIError("이벤트 응답 형식을 알 수 없습니다.")
        return events # 개별 earing call 정보를 의미 -> 여래개 event(conference call)이 list로 반환

    # ticker 별로 다운로드 directory를 생성하고 해당 path를 반환
    def _ensure_ticker_dir(self, ticker: str) -> Path:
        path = self.download_dir / ticker.upper() # 폴더 경로
        path.mkdir(parents=True, exist_ok=True)  # 상위 폴더까지 모두 생성 & 이미 폴더가 있어도 error 없이 넘어가게 만듦
        return path


    # 주어진 evet에서 transcript 파일을 API에서 다운로드 -> local file로 저장 & text와 file 경로를 반환
    def _download_transcript(self, ticker: str, event: Dict) -> Tuple[Optional[str], Optional[Path]]:
        transcript_url = (
            event.get("transcript_url")
            or event.get("transcriptUrl")
            or event.get("transcriptDownloadUrl")
        )
        
        # event dictorinary에서 transcrpit URL 찾거나 생성 (_fetch_event에서는 dictiorary list를 return -> URL, 날짜등 들어있음) 
        event_id = event.get("event_id") or event.get("id")
        if not transcript_url and event_id: # event는 등록됐지만 transcrpit가 아직 없을 수 있음
            transcript_url = f"{self.BASE_URL}{self.TRANSCRIPT_PATH.format(event_id=event_id)}"
        if not transcript_url:
            self.logger.info("트랜스크립트 URL 없음: %s", event)
            return None, None

        # transcript을 다운로드
        resp = self.session.get(transcript_url, timeout=self.timeout)
        if resp.status_code >= 400:
            self.logger.error("트랜스크립트 다운로드 실패(%s): %s", resp.status_code, transcript_url)
            return None, None

        ticker_dir = self._ensure_ticker_dir(ticker) # ticker별로 다운로드 path 생성
        filename = f"{event_id or int(datetime.utcnow().timestamp())}.json" # event id가 없으면 UTC timestamp를 파일명으로 함
        file_path = ticker_dir / filename # file_path는 Path 객체 (ticer_dir과 filename 모두 Path 모듈을 사용)
        file_path.write_bytes(resp.content) # 해당 파일에 binary 형태로 데이터 저장 -> write_bytes 호출하여 파일 생성한 뒤 저장
        # resp.content: local 파일을 그대로 저장하는 원본

        transcript_text: Optional[str] = None
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                payload = json.loads(resp.text)
                transcript_text = payload.get("transcript") or payload.get("text")
                if not transcript_text and isinstance(payload, dict):
                    parts = payload.get("segments") or []
                    if isinstance(parts, list):
                        transcript_text = "\n".join(
                            segment.get("text", "") for segment in parts if isinstance(segment, dict)
                        )
            except ValueError:
                transcript_text = resp.text
        else:
            transcript_text = resp.text

        return transcript_text, file_path


    def _event_to_call_info(self, event: Dict) -> Optional[Dict]:
        event_id = event.get("event_id") or event.get("id")
        call_datetime = (
            parse_iso_datetime(event.get("call_datetime"))
            or parse_iso_datetime(event.get("start_time"))
            or parse_iso_datetime(event.get("startTime"))
            or parse_iso_datetime(event.get("datetime"))
        )
        if not event_id or not call_datetime:
            self.logger.warning("event_id 또는 call_datetime이 없어 스킵합니다: %s", event)
            return None

        return {
            "event_id": str(event_id),
            "call_datetime": call_datetime,
            "call_type": event.get("type") or event.get("event_type"),
            "timezone": event.get("timezone") or event.get("timeZone"),
            "source_url": event.get("source_url") or event.get("sourceUrl"),
            "language": event.get("language") or "en",
            "transcript_hash": event.get("transcript_hash"),
            "cursor": event.get("cursor"),
        }


    def process_ticker(self, ticker: str) -> int:
        since = self._load_since(ticker)
        try:
            events = self._fetch_events(ticker, since)
        except QuartrAPIError as exc:
            self.logger.error("[%-5s] 이벤트 조회 실패: %s", ticker, exc)
            return 0

        saved_count = 0
        latest_call_time: Optional[datetime] = None

        for raw_event in events:
            call_info = self._event_to_call_info(raw_event)
            if not call_info:
                continue

            if call_info["call_datetime"] <= since:
                continue

            transcript_text, transcript_path = self._download_transcript(ticker, raw_event)

            record_id = self.db.save_earning_call(
                ticker=ticker,
                call_info=call_info,
                transcript_text=transcript_text,
                transcript_path=transcript_path,
            )

            if record_id:
                saved_count += 1
                latest_call_time = call_info["call_datetime"]
                self.db.update_fetch_state(
                    ticker,
                    last_call_datetime=latest_call_time,
                    last_cursor=call_info.get("cursor"),
                )

        if saved_count:
            self.db.mark_successful_run(ticker)
        return saved_count


    def run(self, tickers: List[str]) -> Dict[str, int]:
        results: Dict[str, int] = {}
        for ticker in tickers:
            try:
                count = self.process_ticker(ticker)
            except Exception as exc:  # noqa: BLE001 - 배치 안정성용
                self.logger.exception("[%-5s] 처리 중 예기치 못한 오류: %s", ticker, exc)
                count = 0
            results[ticker.upper()] = count
        return results
