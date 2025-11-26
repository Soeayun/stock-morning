# 📈 Stock Morning

매 시점 실행 시 최근 24시간 동안의 주요 기업 SEC 공시와 관련 뉴스를 자동으로 수집하고, 로컬 데이터베이스에 저장한 뒤 Ticker별 Agent로 분석하는 시스템입니다. 모든 파이프라인은 로컬 SQLite DB를 사용하므로 AWS 계정 없이도 전체 흐름을 재현할 수 있습니다.

## 🎯 주요 기능

- **SEC EDGAR 크롤러**: 최근 24시간 동안 등록된 기업 공시 자료(10-K, 10-Q, 8-K 등) 자동 다운로드
- **뉴스 크롤러**: Google News RSS 기반 티커 관련 최신 뉴스 수집
- **로컬 데이터베이스 저장**: 공시·뉴스 원본/메타데이터를 `sec_filings.db`에 보관
- **분석 파이프라인**: 저장된 데이터를 Ticker별 Agent가 요약하고 JSON으로 기록
- **Ticker별 Agent**: 각 기업 데이터 요약 및 JSON 결과 저장

## 📦 설치 방법

```bash
git clone https://github.com/YOUR_USERNAME/stock-morning.git
cd stock-morning

# UV (권장)
uv sync

# 또는 pip
pip install -r requirements.txt
```

## ⚙️ 설정

`config/tickers.json`에서 수집할 티커와 기본 스케줄을 지정합니다.

```json
{
  "tickers": ["NVDA", "MSFT", "TSLA"],
  "schedule_time": "06:00",
  "timezone": "Asia/Seoul"
}
```

## 🚀 사용 방법

- **SEC + 뉴스 동시 수집 & Agent 실행**
  ```bash
  python main.py
  ```

## 🔄 실행 흐름 요약

1. `main.py` → `config/settings.py`에서 티커 목록을 불러옵니다.
2. `run_sec_crawler()`  
   - `src/sec_crawler.SECCrawler`: 각 티커의 최신 24시간 SEC 공시를 다운로드 후 `sec_filings.db` + `downloads/sec_filings/`에 저장  
   - `src/news_crawler.NewsCrawler`: Google News RSS에서 기사 최대 10건을 수집하고, URL 정규화 후 DB에 저장
3. `run_agents()`  
   - `src/database/data_fetcher.DataFetcher`: DB에서 “현재 시각 기준 직전 24시간”의 뉴스·공시를 조회  
   - `src/agents/base_agent.AgentManager`: 티커별 요약을 수행하고 `data/agent_results/`에 JSON으로 기록

## 📁 프로젝트 구조

```
stock-morning/
├── main.py                   # SEC+뉴스 수집 후 Agent 실행
├── config/
│   └── tickers.json          # 수집 대상 티커/시간
├── src/
│   ├── config/settings.py    # 로컬 설정 로더
│   ├── news_crawler.py       # 뉴스 크롤러 (Google News RSS)
│   ├── sec_crawler.py        # SEC EDGAR 크롤러 (로컬 DB 저장)
│   ├── database/data_fetcher.py # DB→Agent 데이터 수집
│   ├── agents/base_agent.py  # Ticker별 Agent 기본 클래스
│   ├── db.py                 # SQLite 관리 (공시 + 뉴스)
│   └── time_utils.py         # 24시간 윈도우 계산/변환
└── data/
    └── agent_results/        # Agent 결과 JSON
```

## 🗃️ 데이터 구조

- **SQLite (`sec_filings.db`)**
  - `filings`: SEC 공시 메타데이터 + 로컬 파일 경로
  - `news`: 뉴스 제목/본문 요약/URL/발행 시각
  - 추가로 Quartr 콜 저장소 등 확장 테이블 포함
- **로컬 파일**
  - `downloads/sec_filings/`: 다운로드한 SEC 원문(XML/HTML/TXT)

## 🔧 기술 스택

- Python 3.11+
- Requests (HTTP)
- SQLite (내장 DB)
- SEC EDGAR submissions API + Google News RSS

## 📝 TODO

- [x] 로컬 DB 기반 SEC + 뉴스 통합 수집
- [x] 6시~6시 배치 데이터 조회
- [x] Ticker별 Agent 결과 저장
- [ ] Agent 브리핑 생성 기능 (LangGraph)
- [ ] 고급 뉴스 분석/랭킹
- [ ] 웹 대시보드/알림 채널

## 📄 라이선스

MIT License
