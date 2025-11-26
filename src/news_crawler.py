"""
간단한 뉴스 크롤러
Google News RSS를 활용해 특정 티커 관련 최신 뉴스를 수집합니다.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse
import xml.etree.ElementTree as ET

import requests


class NewsCrawler:
    BASE_URL = "https://news.google.com/rss/search"
    USER_AGENT = "stock-morning/0.2 (+https://github.com)"

    def __init__(self, user_agent: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": user_agent or self.USER_AGENT}
        )

    def fetch_news(self, ticker: str, limit: int = 10) -> List[Dict]:
        """
        Google News RSS에서 ticker 관련 뉴스 수집
        """
        params = {
            "q": f"{ticker} stock",
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        }
        try:
            resp = self.session.get(self.BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            print(f"❌ [{ticker}] 뉴스 요청 실패: {exc}")
            return []

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as exc:
            print(f"❌ [{ticker}] 뉴스 파싱 실패: {exc}")
            return []

        items = root.findall("./channel/item")
        articles: List[Dict] = []
        for item in items[:limit]:
            title = (item.findtext("title") or "").strip()
            link = self._extract_link(item.findtext("link") or "")
            summary = html.unescape((item.findtext("description") or "").strip())
            pub_raw = item.findtext("pubDate")
            published_at = self._parse_pub_date(pub_raw)
            source = (
                item.findtext("{http://www.w3.org/2005/Atom}source")
                or item.findtext("source")
                or ""
            ).strip()
            if not title or not link:
                continue
            articles.append(
                {
                    "ticker": ticker.upper(),
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "source": source,
                    "published_at": published_at,
                }
            )
        return articles

    @staticmethod
    def _extract_link(raw_link: str) -> str:
        if "news.google.com" not in raw_link:
            return raw_link.strip()
        parsed = urlparse(raw_link)
        query = parse_qs(parsed.query)
        redirected = query.get("url")
        if redirected:
            return redirected[0]
        return raw_link.strip()

    @staticmethod
    def _parse_pub_date(raw: Optional[str]) -> str:
        if not raw:
            return datetime.now(timezone.utc).isoformat()
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()
