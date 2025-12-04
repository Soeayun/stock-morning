# 📈 Stock Morning

매 시점 실행 시 최근 24시간 동안의 주요 기업 SEC 공시와 관련 뉴스를 자동으로 수집하고, 로컬 데이터베이스에 저장한 뒤 Ticker별 Agent로 분석하는 시스템입니다. 모든 파이프라인은 로컬 SQLite DB를 사용하므로 AWS 계정 없이도 전체 흐름을 재현할 수 있습니다.

## 🎯 주요 기능

- **SEC EDGAR 크롤러**: 최근 24시간 동안 등록된 기업 공시 자료(10-K, 10-Q, 8-K 등) 자동 다운로드
- **AWS 뉴스 수집**: Yahoo Finance 뉴스를 AWS DynamoDB/S3에서 수집
- **로컬 데이터베이스 저장**: 공시·뉴스 원본/메타데이터를 `sec_filings.db`에 보관
- **4명 전문가 토론 시스템**: 서로 다른 관점을 가진 4명의 AI 전문가가 같은 데이터를 분석하고 토론
  - 💼 **Fundamental Analyst** (Charlie Munger 스타일): 재무제표와 비즈니스 모델 평가
  - ⚠️ **Risk Manager** (Ray Dalio 스타일): 리스크 요인과 최악의 시나리오 분석
  - 🚀 **Growth Catalyst Hunter** (Cathie Wood 스타일): 혁신과 성장 촉매 발굴
  - 📊 **Market Sentiment Analyst** (George Soros 스타일): 시장 심리와 단기 트렌드 예측
- **LangGraph 기반 토론 파이프라인**: 3라운드 토론 후 포트폴리오 매니저가 최종 결론 도출

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
ㅇ
```json
{
  "tickers": ["NVDA", "MSFT", "TSLA"],
  "schedule_time": "06:00",
  "timezone": "Asia/Seoul"
}
```

## 🚀 사용 방법

### 1. 데이터 수집 (SEC 공시)
```bash
python main.py
```

### 2. 4명 전문가 토론 파이프라인 실행
```bash
# 기본 실행 (콘솔 출력만)
python run_multiagent.py --ticker GOOG

# JSON 파일로 저장
python run_multiagent.py --ticker AAPL --save
```

**토론 흐름:**
1. **Blind Analysis**: 각 전문가가 독립적으로 데이터 분석
2. **Debate Round 1-2**: 서로의 의견을 듣고 반박/수정
3. **Final Conclusion**: 포트폴리오 매니저가 종합 결론 도출 (BUY/SELL/HOLD 액션 포함)

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
- [x] 4명 전문가 토론 파이프라인 (LangGraph)
- [x] 페르소나 기반 프롬프트 엔지니어링 (Charlie Munger, Ray Dalio, Cathie Wood, George Soros 스타일)
- [x] **최종 결론 JSON 구조화** (scores, action, position_size, confidence)
- [x] **yfinance 통합** (실시간 주가, P/E, ROE, 부채비율 등 30+ 지표)
- [x] **합의도 계산 & 동적 라운드 조정** (합의도 85% 이상 시 조기 종료)
- [x] **에러 핸들링** (AWS/OpenAI 실패 시 재시도, fallback)
- [ ] 최종 결론 기반 자동 거래 시그널 생성
- [ ] 웹 대시보드/알림 채널

## 📄 라이선스

MIT License
