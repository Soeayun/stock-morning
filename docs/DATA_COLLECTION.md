# 📊 Stock Morning 데이터 수집 상세 문서

> 작성일: 2024-12-27  
> 버전: 2.0

---

## 1. 개요

Stock Morning 시스템은 **3가지 데이터 소스**에서 주식 분석에 필요한 정보를 수집합니다:

| 데이터 소스 | 수집 방법 | 저장 위치 | 수집 내용 |
|------------|----------|----------|----------|
| **SEC EDGAR** | REST API | SQLite + 로컬 파일 | 10-K, 10-Q, 8-K, Form 4 등 공시 문서 |
| **Yahoo Finance 뉴스** | AWS (DynamoDB) | 메모리 (임시 파일) | 기업 관련 뉴스 기사 |
| **실시간 시장 데이터** | yfinance | 메모리 | 주가, P/E, 시가총액 등 30+ 지표 |

---

## 2. 실행 스크립트

### `run.py` - 통합 실행 스크립트 (권장)

```bash
# 전체 파이프라인 (크롤링 + 분석)
uv run run.py --ticker GOOG

# 크롤링 생략 (기존 데이터 사용)
uv run run.py --ticker GOOG --skip-crawl

# 결과 JSON 저장
uv run run.py --ticker GOOG --save
```

**실행 순서:**
```
run.py
├── run_crawling()                    # 1단계: SEC 크롤링
│   ├── SECCrawler.crawl_filings_in_window()
│   │   └── 최근 N일 공시 다운로드
│   ├── SECCrawler.crawl_latest_annual_quarterly()
│   │   └── 10-K, 10-Q 항상 포함 (기간 무관)
│   └── SQLite DB + 로컬 파일 저장
│
├── run_analysis()                    # 2단계: 4명 전문가 토론
│   └── run_multiagent_pipeline(ticker)
│       ├── collect_data_node         # 데이터 수집
│       ├── moderator_analysis_node   # 중재자 분석
│       ├── guided_debate_node (x3)   # 토론 라운드
│       └── conclusion_node           # 최종 결론
│
└── cleanup_temp_files()              # 3단계: 임시 파일 정리
    └── aws_results/{TICKER}_*.json 삭제
```

---

## 3. 데이터 소스별 상세 설명

### 3.1 SEC EDGAR 공시 수집

**파일:** `src/sec_crawler.py`

#### 수집 과정

```
1. 티커 → CIK 변환
   GET https://www.sec.gov/files/company_tickers.json
   예: GOOG → CIK 0001652044

2. 공시 목록 조회
   GET https://data.sec.gov/submissions/CIK{CIK}.json
   - 기본 윈도우: 10일 (SEC_CRAWLER_WINDOW_DAYS 환경변수)
   - 10-K, 10-Q는 기간 무관하게 최신 1건 항상 포함

3. 공시 파일 다운로드
   GET https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION}/{FILENAME}
   - 형식 우선순위: XML > HTML > TXT

4. 로컬 저장
   - 파일: downloads/sec_filings/{CIK}_{ACCESSION}_{FILENAME}
   - 메타데이터: sec_filings.db (SQLite)
```

#### 10-K/10-Q 항상 포함

```python
# src/sec_crawler.py
def crawl_latest_annual_quarterly(self, ticker: str):
    """최신 10-K와 10-Q를 기간 무관하게 크롤링"""
    # 최신 10-K 1건
    # 최신 10-Q 1건
```

이 기능으로 인해 분석 시 항상 연간/분기 보고서가 포함됩니다.

#### 저장되는 메타데이터 (SQLite)

```sql
CREATE TABLE filings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(10) NOT NULL,
    cik VARCHAR(10) NOT NULL,
    accession_number VARCHAR(50) UNIQUE,
    form VARCHAR(20) NOT NULL,          -- 10-K, 10-Q, 8-K, 4 등
    filed_date DATE NOT NULL,           -- 제출일 (LLM 인용에 사용)
    reporting_for DATE,                 -- 보고 기준일
    file_path VARCHAR(500),
    file_format VARCHAR(10),
    created_at TIMESTAMP
);
```

---

### 3.2 Yahoo Finance 뉴스 수집 (AWS)

**파일:** `aws_fetchers/yahoo_fetcher.py`, `aws_fetchers/news_saver.py`

#### AWS 리소스

| 서비스 | 리소스명 | 용도 |
|--------|---------|------|
| **DynamoDB** | `kubig-YahoofinanceNews` | 뉴스 메타데이터 + 본문 |

#### 수집 과정

```
1. DynamoDB Query
   - FilterExpression: tickers.contains(ticker)
   - 최신순 정렬, 상위 10건

2. 로컬 임시 저장
   - 경로: aws_results/{TICKER}_{TIMESTAMP}_{INDEX}.json
   - 파이프라인 완료 후 자동 삭제

3. 뉴스 상세 조회 (토론 중)
   - get_news_detail 도구로 상세 내용 조회
   - 메모리 캐시 (news_cache) 사용
```

#### 반환 데이터 구조

```python
{
    "pk": "article-unique-id",
    "ticker": "GOOG",
    "published_at": "2025-12-23T10:30:00Z",
    "title": "Google started the year behind in the AI race...",
    "article_raw": "원문 내용..."
}
```

---

### 3.3 실시간 시장 데이터 (yfinance)

**파일:** `multiagent/services/market_data.py`

#### 수집 항목 (30+ 지표)

**주가 정보:**
| 지표 | 설명 | 예시 |
|------|------|------|
| `current_price` | 현재 주가 | $314.96 |
| `market_cap` | 시가총액 | $2.1T |
| `fifty_two_week_high` | 52주 최고가 | $328.50 |
| `fifty_two_week_low` | 52주 최저가 | $244.58 |
| `volume` | 거래량 | 25,000,000 |

**밸류에이션 지표:**
| 지표 | 설명 | 예시 |
|------|------|------|
| `pe_ratio` | P/E Ratio (TTM) | 31.06 |
| `forward_pe` | Forward P/E | 28.11 |
| `price_to_book` | P/B Ratio | 6.8 |

**수익성 지표:**
| 지표 | 설명 | 예시 |
|------|------|------|
| `operating_margin` | 영업이익률 | 30.5% |
| `profit_margin` | 순이익률 | 32.2% |
| `roe` | 자기자본이익률 | 28% |

**재무 건전성:**
| 지표 | 설명 | 예시 |
|------|------|------|
| `debt_to_equity` | 부채비율 | 11.42 |
| `free_cash_flow` | 잉여현금흐름 | $48B |

---

## 4. 데이터 통합 및 Agent 전달

**파일:** `multiagent/nodes/data_collector.py`

### `prepare_ticker_dataset()` 함수

```python
def prepare_ticker_dataset(ticker: str, hours: int = 24, news_limit: int = 10):
    """
    3가지 데이터 소스를 통합하여 Agent에게 전달할 데이터셋 생성
    """
    
    # 1. AWS 뉴스 수집
    yahoo_fetcher = YahooNewsFetcher()
    aws_news = yahoo_fetcher.fetch(ticker, limit=news_limit)
    
    # 2. 로컬 SEC 데이터 조회 (10-K, 10-Q 항상 포함)
    fetcher = DataFetcher()
    sec_data = fetcher.fetch_ticker_data(ticker)
    # → has_10k, has_10q 플래그 확인
    
    # 3. 실시간 시장 데이터
    market_fetcher = MarketDataFetcher()
    market_data = market_fetcher.fetch_market_data(ticker)
    
    return {
        "ticker": ticker,
        "aws_news": aws_news,
        "sec_filings": sec_data["filings"],
        "market_data": market_data,
        "has_10k": sec_data.get("has_10k", False),
        "has_10q": sec_data.get("has_10q", False),
    }
```

---

## 5. 4명 전문가 토론 시스템

### 전문가 페르소나

| 전문가 | 스타일 | 분석 초점 |
|--------|-------|----------|
| 💼 **Fundamental Analyst** | Charlie Munger | 재무제표, 비즈니스 모델, 경쟁우위 |
| ⚠️ **Risk Manager** | Ray Dalio | 리스크 요인, 최악의 시나리오 |
| 🚀 **Growth Analyst** | Cathie Wood | 혁신, 성장 촉매, AI 전환 |
| 📊 **Sentiment Analyst** | George Soros | 시장 심리, 뉴스 톤, 과열 여부 |

### 토론 흐름

```
Round 1: Blind Analysis
├── 4명 전문가 독립 분석 (병렬)
└── 중재자: 합의점/쟁점 정리

Round 2-3: Guided Debate
├── 중재자 가이드 기반 데이터 중심 토론
├── Sentiment Analyst: get_news_detail 도구 사용 가능
└── 중재자: 추가 토론 필요 여부 판단

Final: Conclusion
└── 팟캐스트 대본 + 구조화된 분석 + JSON
```

---

## 6. 최종 출력 형식

### 팟캐스트 대본 (줄글)

```
오늘 분석한 구글(Alphabet Inc.)에 대해 최종 결론을 말씀드리겠습니다.
최근 제출된 10-Q(2025-10-30)에 따르면 영업이익률이 30%를 유지하고 있고
약 480억 달러의 현금흐름을 기록했습니다. 또한 12월 23일 보도된 뉴스에서는
AI 경쟁력이 크게 회복되었다는 내용이 있었습니다...
```

**특징:**
- 전문가 역할명 없음 (Fundamental, Risk 등)
- 뉴스/공시 날짜 정확히 인용
- 바로 발표/영상에 사용 가능

### JSON 출력

```json
{
  "action": "BUY/HOLD/SELL",
  "position_size": 5,
  "debate_summary": "...",
  "buy_reasons": ["근거1 (출처, 날짜)", ...],
  "risk_factors": ["리스크1", ...],
  "immediate_action": "이번 주 $310-320 구간에서 5% 매수",
  "short_term_strategy": "3개월 내 Cloud YoY >25% 시 3% 추가",
  "long_term_strategy": "목표가 $380, 총 포지션 10%"
}
```

---

## 7. 환경 설정

### 필수 환경변수 (.env)

```bash
# OpenAI API (필수) - GPT-5.1 사용
OPENAI_API_KEY=sk-...

# AWS (뉴스 수집용)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-northeast-2

# LangSmith (선택, 디버깅용)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=stock-morning
LANGCHAIN_API_KEY=...

# SEC 크롤러 설정 (선택)
SEC_CRAWLER_WINDOW_DAYS=10  # 기본값: 10일 (10-K/10-Q는 무관)
```

---

## 8. 파일 구조

```
stock-morning/
├── run.py                            # 📌 메인 실행 스크립트
│
├── multiagent/                       # 4명 전문가 토론 시스템
│   ├── graph.py                      # LangGraph 파이프라인
│   ├── agents/
│   │   ├── fundamental_analyst.py
│   │   ├── risk_manager.py
│   │   ├── growth_analyst.py
│   │   ├── sentiment_analyst.py
│   │   └── moderator.py
│   ├── services/
│   │   ├── toolkit.py                # GPT-5.1 API (chat_json 포함)
│   │   ├── market_data.py
│   │   └── conclusion_parser.py
│   ├── prompts.py
│   └── schemas.py
│
├── src/                              # 데이터 수집
│   ├── sec_crawler.py                # SEC 크롤러 (10-K/10-Q 항상 포함)
│   ├── db.py                         # SQLite (get_latest_annual_quarterly)
│   ├── database/data_fetcher.py
│   └── config/settings.py
│
├── aws_fetchers/                     # AWS 뉴스 수집
│   ├── yahoo_fetcher.py
│   └── news_saver.py
│
├── config/tickers.json               # 티커 설정
├── downloads/sec_filings/            # SEC 원문 파일
└── sec_filings.db                    # SQLite DB
```

---

## 9. 실행 예시

```bash
# 전체 파이프라인
uv run run.py --ticker GOOG
```

**출력:**
```
====================================================================================================
🚀 STOCK MORNING - 통합 분석 파이프라인
📊 Ticker: GOOG
====================================================================================================

📥 SEC 크롤링: 16건 (10-K: ✅, 10-Q: ✅)
✅ 뉴스 수집: 10건
💰 현재 주가: $314.96

🎯 4-EXPERT DEBATE PIPELINE
├── Round 1: Blind Analysis
├── Round 2: Guided Debate
├── Round 3: Guided Debate
└── Final: 결론 도출

📋 FINAL CONCLUSION
────────────────────────────────────────
오늘 분석한 구글(Alphabet Inc.)에 대해 최종 결론을 말씀드리겠습니다...
────────────────────────────────────────

⚪ 최종 판단: HOLD (5%)
🧹 임시 파일 정리: 10개 삭제

✨ PIPELINE COMPLETED (약 2분)
```
