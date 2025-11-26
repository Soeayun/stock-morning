"""
간단한 뉴스 크롤러
Google News RSS를 활용해 특정 티커 관련 최신 뉴스를 수집합니다.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
import xml.etree.ElementTree as ET

import requests


class NewsCrawler:
    BASE_URL = "https://news.google.com/rss/search"
    USER_AGENT = "stock-morning/0.2 (+https://github.com)"
    TRACKING_PREFIXES = ("utm_",)
    TRACKING_KEYS = {
        "ocid",
        "cmpid",
        "fbclid",
        "gclid",
        "ref",
        "ref_src",
        "ref_url",
        "spref",
    }

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
        cleaned = raw_link.strip()
        if not cleaned:
            return cleaned

        if "news.google.com" in cleaned:
            parsed = urlparse(cleaned)
            query = parse_qs(parsed.query)
            redirected = query.get("url")
            if redirected:
                cleaned = redirected[0]

        return NewsCrawler._normalize_url(cleaned)

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url)
        if not parsed.scheme:
            return url

        query_dict = parse_qs(parsed.query, keep_blank_values=True)
        cleaned_query = {}
        for key, values in query_dict.items():
            key_lower = key.lower()
            if key_lower.startswith(NewsCrawler.TRACKING_PREFIXES) or key_lower in NewsCrawler.TRACKING_KEYS:
                continue
            cleaned_query[key] = values

        normalized_query = urlencode(cleaned_query, doseq=True)
        normalized = parsed._replace(query=normalized_query, fragment="")
        return urlunparse(normalized)

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
