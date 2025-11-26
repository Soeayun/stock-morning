"""
뉴스 본문 수집 모듈
DB에 저장된 뉴스 URL을 기반으로 실제 본문 텍스트를 다운로드하여 저장합니다.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from src.db import SECDatabase


class NewsContentFetcher:
    """뉴스 URL에서 본문을 추출하여 DB에 저장하는 유틸"""

    DEFAULT_HEADERS = {
        "User-Agent": "stock-morning-content-fetcher/0.1 (+https://github.com/)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, timeout: int = 20):
        self.db = SECDatabase()
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self.timeout = timeout

    def fetch_and_store(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        tickers: Optional[List[str]] = None,
    ) -> int:
        """
        뉴스 본문이 비어 있는 항목에 대해 기사 텍스트를 수집하여 저장합니다.

        Args:
            start_time, end_time: 특정 기간으로 제한하고 싶을 때 사용 (기본값: 전체)
            limit: 최대 처리 개수 (None이면 전부)

        Returns:
            실제로 본문을 저장한 레코드 수
        """
        rows = self.db.get_news_without_content(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            tickers=tickers,
        )
        if not rows:
            print("본문이 비어있는 뉴스가 없습니다.")
            return 0

        success = 0
        for row in rows:
            url = row.get("url")
            if not url:
                continue
            try:
                content = self._download_article(url)
                if content:
                    updated = self.db.update_news_content(row["id"], content)
                    if updated:
                        success += 1
                        print(f"✅ 본문 저장 완료 (id={row['id']}, ticker={row['ticker']})")
                else:
                    print(f"⚠️  본문 추출 실패: {url}")
            except Exception as exc:
                print(f"❌ 뉴스 본문 수집 중 오류 발생 ({url}): {exc}")

        print(f"뉴스 본문 수집 완료: {success}/{len(rows)} 건 저장")
        return success

    def _download_article(self, url: str) -> Optional[str]:
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        final_domain = urlparse(resp.url).netloc

        # Google News 중간 페이지 처리
        if "news.google.com" in final_domain:
            redirected = self._extract_redirect_from_google(soup, base_url=resp.url)
            if redirected:
                resp = self.session.get(redirected, timeout=self.timeout)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                final_domain = urlparse(resp.url).netloc

        # 도메인별 특화 추출
        specialized = self._extract_by_domain(final_domain, soup)
        if specialized:
            return specialized

        # article 태그 우선
        article = soup.find("article")
        if article:
            text = self._clean_text(article.get_text(separator="\n"))
            if text:
                return text

        # 주요 콘텐츠 후보
        candidates: List[str] = []
        for selector in ["main", "div#main", "div.article-body", "div.post-content", "section.article"]:
            node = soup.select_one(selector)
            if node:
                candidates.append(node.get_text(separator="\n"))

        if not candidates:
            candidates.append(soup.get_text(separator="\n"))

        for text in candidates:
            cleaned = self._clean_text(text)
            if cleaned:
                return cleaned
        return None

    @staticmethod
    def _clean_text(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        stripped = "\n".join(
            line.strip()
            for line in raw.splitlines()
            if line.strip()
        )
        return stripped or None

    @staticmethod
    def _extract_by_domain(domain: str, soup: BeautifulSoup) -> Optional[str]:
        domain = domain.lower()

        if "investing.com" in domain:
            container = soup.select_one("div.article_WYSIWYG__O0uhw, div.article_articlePage__UMz3q, div.articlePage")
            if not container:
                container = soup.select_one("div#article")
            if container:
                text = container.get_text(separator="\n")
                return NewsContentFetcher._clean_text(text)

        return None

    @staticmethod
    def _extract_redirect_from_google(soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Google News RSS 중간 페이지에서 실제 기사 링크를 추출합니다.
        """
        # meta refresh
        meta = soup.find("meta", attrs={"http-equiv": "refresh"})
        if meta and meta.get("content"):
            parts = meta["content"].split("url=")
            if len(parts) == 2:
                return urljoin(base_url, parts[1].strip())

        # 주요 버튼/링크
        anchor = soup.find("a", attrs={"href": True, "data-ved": True})
        if anchor:
            return urljoin(base_url, anchor["href"])

        return None
