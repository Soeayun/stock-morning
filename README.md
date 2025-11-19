# 📈 Stock Morning

매일 아침 주요 기업의 SEC 공시와 컨퍼런스 콜 트랜스크립트를 자동으로 수집하는 크롤러입니다.

## 🎯 주요 기능

- **SEC EDGAR 크롤러**: 기업 공시 자료(10-K, 10-Q, 8-K 등) 자동 수집
- **Quartr 크롤러**: 컨퍼런스 콜 트랜스크립트 자동 수집
- **자동 스케줄링**: 매일 오전 6시(KST) 자동 실행
- **SQLite DB 저장**: 수집한 데이터를 로컬 DB에 체계적으로 저장
- **중복 방지**: 이미 수집한 데이터는 자동으로 필터링

## 📦 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/YOUR_USERNAME/stock-morning.git
cd stock-morning
```

### 2. 의존성 설치

**UV 사용 (권장):**
```bash
uv sync
```

**또는 pip 사용:**
```bash
pip install -r requirements.txt
```

### 3. 환경 설정

티커 설정 파일 확인 및 수정:
```bash
# config/tickers.json
{
  "tickers": ["CPNG", "ORCL", "COST", "GOOG"],
  "schedule_time": "06:00",
  "timezone": "Asia/Seoul"
}
```

### 4. API 키 설정 (Quartr 사용 시)

```bash
export QUARTR_API_KEY="your_api_key_here"
```

## 🚀 사용 방법

### 1. 수동 실행

**SEC 크롤러만 실행:**
```python
# main.py에서
run_sec()      # 주석 해제
# run_quartr() # 주석 처리
```

```bash
python main.py
```

**Quartr 크롤러만 실행:**
```python
# main.py에서
# run_sec()    # 주석 처리
run_quartr()   # 주석 해제
```

```bash
python main.py
```

### 2. 즉시 한 번 실행

```bash
python run_scheduler.py --once
```

### 3. 자동 스케줄러 실행 (매일 오전 6시)

```bash
python run_scheduler.py
```

## 📁 프로젝트 구조

```
stock-morning/
├── main.py                 # 메인 실행 스크립트
├── run_scheduler.py        # 스케줄러 실행 스크립트
├── config/
│   └── tickers.json        # 크롤링 대상 티커 설정
├── src/
│   ├── sec_crawler.py      # SEC EDGAR 크롤러
│   ├── quartr_crawler.py   # Quartr API 크롤러
│   ├── db.py               # 데이터베이스 관리
│   ├── scheduler.py        # 스케줄링 로직
│   └── time_utils.py       # 시간 유틸리티
├── downloads/              # 다운로드된 파일 저장 (gitignore)
├── sec_filings.db          # SEC 공시 DB (gitignore)
├── quartr_calls.db         # Quartr 컨퍼런스 콜 DB (gitignore)
└── crawler.log             # 크롤링 로그 (gitignore)
```

## 🗃️ 데이터베이스 구조

### SEC Filings
- 티커, CIK, 공시 번호, 공시 형식
- 제출 날짜, 수락 날짜
- 파일 경로 및 메타데이터

### Quartr Calls
- 티커, 이벤트 ID
- 컨퍼런스 콜 날짜 및 타입
- 트랜스크립트 텍스트 및 파일 경로

## 🔧 기술 스택

- **Python 3.11+**
- **SQLite3**: 로컬 데이터베이스
- **Requests**: HTTP 요청
- **APScheduler**: 작업 스케줄링
- **SEC EDGAR API**: 공시 자료 수집
- **Quartr API**: 컨퍼런스 콜 수집


## 📝 TODO

- [ ] 이메일/슬랙 알림 기능 추가
- [ ] 웹 대시보드 구현
- [ ] 더 많은 데이터 소스 통합
- [ ] 데이터 분석 및 시각화 기능

## 📄 라이선스

MIT License


