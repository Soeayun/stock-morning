"""
SEC EDGAR 크롤러 모듈
티커를 입력받아 SEC EDGAR에서 최신 공시 문서를 다운로드합니다.

표가 많은 공시자료의 경우 XML 형식을 권장합니다 (표 구조 보존에 최적).
XML 파일은 나중에 파싱하여 LLM에 적합한 형식(마크다운 테이블 등)으로 변환 가능합니다.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

import requests

from src.db import SECDatabase
from src.time_utils import get_korea_batch_yesterday, utc_to_korea_batch_date


class SECCrawler:
    """SEC EDGAR에서 기업 공시 자료를 크롤링하는 클래스"""
    
    BASE_URL = "https://www.sec.gov"
    USER_AGENT = "ehddus416@korea.ac.kr"  # SEC 요구사항: 본인 정보로 변경 필요
    
    def __init__(self, user_agent: Optional[str] = None):
        """
        Args:
            user_agent: SEC API 사용 시 필요한 User-Agent (본인/회사 정보)
        """
        self.user_agent = user_agent or self.USER_AGENT
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
    
    def get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """
        티커로부터 CIK 번호를 조회
        
        Args:
            ticker: 주식 티커 심볼 (예: "NVDA")
            
        Returns:
            CIK 번호 (문자열) 또는 None
        """
        try:
            url = f"{self.BASE_URL}/files/company_tickers.json"
            response = self.session.get(url) # HTTP GET 요청(지정된 URL로 GET 요청)
            response.raise_for_status() # error check
            
            companies = response.json() # json으로 parsing
            
            # 티커로 CIK 찾기 (대소문자 무시)
            ticker_upper = ticker.upper()
            for entry in companies.values():
                if entry.get("ticker", "").upper() == ticker_upper:
                    cik = str(entry["cik_str"]).zfill(10)  # CIK는 10자리로 패딩
                    print(f"티커 {ticker}의 CIK: {cik}")
                    return cik
            
            print(f"티커 {ticker}에 해당하는 CIK를 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            print(f"CIK 조회 중 오류 발생: {e}")
            return None
    
    def get_latest_filing(self, cik: str, only_today: bool = False) -> Optional[Dict]:
        """
        CIK로부터 최신 공시 정보를 조회합니다.
        
        Args:
            cik: CIK 번호
            only_today: True면 어제 날짜 기준 공시만 반환 (오전 6시 실행 시 어제 06:00~오늘 05:59 공시)
            
        Returns:
            공시 정보 딕셔너리 (4개 메타데이터 + acceptanceDateTime 포함) 또는 None
        """
        try:
            # SEC EDGAR submissions JSON API 사용
            cik_padded = cik.zfill(10)  # CIK는 10자리로 패딩
            submissions_json_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
            response = self.session.get(submissions_json_url)
            response.raise_for_status()
            
            data = response.json()
            
            # submissions.json 구조 확인
            # recent : 해당 CIK의 가장 최근 제출된 공시 목록을 의미 -> 40개 내외의 최신 공시가 포함됨
            if "filings" in data and "recent" in data["filings"]:
                recent = data["filings"]["recent"]
                
                if recent and len(recent["form"]) > 0:
                    # 한국 시간 기준 어제 날짜 (오전 6시에 실행 시 어제 06:00~오늘 05:59 공시 찾기) - 한 번만 계산
                    target_date = get_korea_batch_yesterday() if only_today else None
                    
                    # 당일 필터링이 필요한 경우
                    if only_today:
                        # acceptanceDateTime이 있는 공시 중 어제 날짜 기준 것만 찾기
                        # 예: 11/8 06:00 실행 → 11/7 날짜 공시 찾기 (11/7 06:00 ~ 11/8 05:59)
                        for idx in range(len(recent["form"])):
                            if recent.get("acceptanceDateTime") and len(recent["acceptanceDateTime"]) > idx:
                                acceptance_dt_str = recent["acceptanceDateTime"][idx]
                                if acceptance_dt_str:
                                    acceptance_date = utc_to_korea_batch_date(acceptance_dt_str)
                                    if acceptance_date == target_date:
                                        # 해당 날짜 공시 발견
                                        filed_date = recent["filingDate"][idx]
                                        reporting_for = (
                                            recent["reportDate"][idx]
                                            if recent.get("reportDate")
                                            and len(recent["reportDate"]) > idx
                                            else None
                                        )
                                        filing_info = {
                                            "form": recent["form"][idx],
                                            "filed": filed_date,
                                            "filed_date": filed_date,
                                            "reporting_for": reporting_for,
                                            "filing_entity": data.get("name", ""),
                                            "accession_number": recent["accessionNumber"][idx],
                                            "acceptance_datetime": acceptance_dt_str,
                                            "acceptance_date": acceptance_date,
                                            "cik": cik
                                        }
                                        
                                        print(f"해당 날짜 공시 발견:")
                                        print(f"  Form: {filing_info['form']}")
                                        print(f"  Filed: {filing_info['filed']}")
                                        print(f"  Acceptance Date (한국): {filing_info['acceptance_date']}")
                                        print(f"  Filing entity: {filing_info['filing_entity']}")
                                        
                                        return filing_info
                        
                        # 해당 날짜 공시 없음
                        print(f"어제 날짜({target_date}) 기준 공시가 없습니다. (오전 6시 실행 시 어제 06:00~오늘 05:59 공시)")
                        return None
                    
                    # 일단은 공시가 없더라도 최근 공시 정보를 추출할 수 있게 만듦
                    else:
                        # 가장 최근 공시 정보 추출
                        latest_idx = 0
                        
                        filed_date = recent["filingDate"][latest_idx]
                        reporting_for = (
                            recent["reportDate"][latest_idx]
                            if recent.get("reportDate") and len(recent["reportDate"]) > latest_idx
                            else None
                        )
                        filing_info = {
                            "form": recent["form"][latest_idx],
                            "filed": filed_date,
                            "filed_date": filed_date,
                            "reporting_for": reporting_for,
                            "filing_entity": data.get("name", ""),
                            "accession_number": recent["accessionNumber"][latest_idx],
                            "cik": cik
                        }
                        
                        # acceptanceDateTime 추가 (있는 경우)
                        if recent.get("acceptanceDateTime") and len(recent["acceptanceDateTime"]) > latest_idx:
                            acceptance_dt_str = recent["acceptanceDateTime"][latest_idx]
                            if acceptance_dt_str:
                                acceptance_date = utc_to_korea_batch_date(acceptance_dt_str)
                                filing_info["acceptance_datetime"] = acceptance_dt_str
                                filing_info["acceptance_date"] = acceptance_date
                        
                        print(f"최신 공시 발견:")
                        print(f"  Form: {filing_info['form']}")
                        print(f"  Filed: {filing_info['filed']}")
                        if "acceptance_date" in filing_info:
                            print(f"  Acceptance Date (한국): {filing_info['acceptance_date']}")
                        print(f"  Reporting for: {filing_info['reporting_for']}")
                        print(f"  Filing entity: {filing_info['filing_entity']}")
                        
                        return filing_info
            
            print("최신 공시를 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            print(f"최신 공시 조회 중 오류 발생: {e}")
            return None
    
    def download_filing_file(self, cik: str, accession_number: str, form: str, file_format: str = "xml") -> Optional[Path]:
        """
        공시 문서 파일을 다운로드합니다.
        
        표가 많은 공시자료의 경우 XML 형식이 표 구조를 가장 잘 보존합니다.
        - XML: 표 구조 완벽 보존, 파싱 후 LLM에 적합한 형식으로 변환 가능 (권장)
        - HTML: 표 구조 보존되지만 태그 노이즈 많음
        - TXT: 표 구조가 깨질 수 있음
        
        Args:
            cik: CIK 번호
            accession_number: 접수 번호 (예: "0000320193-24-000001")
            form: 공시 양식 (예: "10-K")
            file_format: 다운로드할 파일 형식 ("xml", "html", "txt")
            
        Returns:
            다운로드된 파일 경로 또는 None
        """
        try:
            # accession number에서 하이픈 제거
            accession_no_dash = accession_number.replace("-", "")
            
            # index.json에서 사용 가능한 파일 목록 확인
            index_url = f"{self.BASE_URL}/Archives/edgar/data/{cik}/{accession_no_dash}/index.json"
            response = self.session.get(index_url)
            response.raise_for_status()
            
            index_data = response.json()
            
            # 파일 형식별 우선순위 설정
            if file_format.lower() == "xml":
                # XML 우선: 표 구조를 가장 잘 보존
                file_priorities = [
                    f"{form}.xml",  # 순수 XML 파일 (가장 좋음)
                    f"{accession_no_dash}.txt",  # 전체 문서 (XML 인코딩된 텍스트)
                ]
                # index.json에서 XML 파일 찾기
                if "directory" in index_data:
                    for item in index_data["directory"]["item"]:
                        if item.get("name", "").endswith(".xml"):
                            file_priorities.insert(0, item["name"])
                            break
            elif file_format.lower() == "html":
                file_priorities = [
                    f"{form}.htm",
                    f"{form}.html",
                ]
                if "directory" in index_data:
                    for item in index_data["directory"]["item"]:
                        if item.get("name", "").endswith((".htm", ".html")):
                            file_priorities.insert(0, item["name"])
                            break
            else:  # txt
                file_priorities = [
                    f"{accession_no_dash}.txt",
                ]
            
            # 파일 다운로드 시도
            downloaded_file = None
            for filename in file_priorities:
                try:
                    file_url = f"{self.BASE_URL}/Archives/edgar/data/{cik}/{accession_no_dash}/{filename}"
                    response = self.session.get(file_url)
                    if response.status_code == 200:
                        # 파일 저장
                        download_dir = Path("downloads/sec_filings")
                        download_dir.mkdir(exist_ok=True)
                        
                        file_path = download_dir / f"{cik}_{accession_no_dash}_{filename}"
                        file_path.write_bytes(response.content)
                        
                        print(f"파일 다운로드 완료: {file_path} ({file_format.upper()} 형식)")
                        downloaded_file = file_path
                        break
                except Exception as e:
                    continue
            
            if not downloaded_file:
                print(f"{file_format.upper()} 파일을 다운로드할 수 없습니다.")
                return None
            
            return downloaded_file
            
        except Exception as e:
            print(f"파일 다운로드 중 오류 발생: {e}")
            return None
    
    def crawl_latest_filing(
        self,
        ticker: str,
        file_format: str = "xml",
        save_to_db: bool = True,
        db: Optional[SECDatabase] = None,
        only_today: bool = True
    ) -> Optional[Tuple[Dict, Path]]:
        """
        티커를 입력받아 최신 공시 문서를 크롤링하고 로컬 DB에 저장합니다.
        
        Args:
            ticker: 주식 티커 심볼
            file_format: 다운로드할 파일 형식 ("xml", "html", "txt") - 기본값: "xml"
            save_to_db: SQLite에 저장할지 여부 (기본값: True)
            only_today: True면 어제 날짜 기준 공시만 다운로드 (기본값: True)
            
        Returns:
            (공시 메타데이터, 로컬 파일 경로) 튜플 또는 None
        """
        # 1. 티커로 CIK 조회
        cik = self.get_cik_from_ticker(ticker)
        if not cik:
            return None
        
        # 2. 최신 공시 정보 조회 (only_today 옵션 적용)
        filing_info = self.get_latest_filing(cik, only_today=only_today)
        if not filing_info:
            return None
        
        # 3. 파일 다운로드 (임시)
        file_path = self.download_filing_file(
            cik=cik,
            accession_number=filing_info["accession_number"],
            form=filing_info["form"],
            file_format=file_format
        )
        
        if not file_path:
            return None
        
        # 4. 로컬 DB 저장
        saved_metadata = filing_info
        if save_to_db:
            try:
                metadata = {
                    'ticker': ticker.upper(),
                    'acceptance_date': filing_info.get('acceptance_date'),
                    'accession_number': filing_info.get('accession_number'),
                    'cik': cik,
                    'form': filing_info.get('form'),
                    'filed_date': filing_info.get('filed_date') or filing_info.get('filed'),
                    'reporting_for': filing_info.get('reporting_for'),
                    'file_format': file_format,
                    'filing_entity': filing_info.get('filing_entity', ''),
                }
                database = db or SECDatabase()
                database.save_filing(ticker, metadata, file_path)
            except Exception as e:
                print(f"❌ 로컬 DB 저장 실패: {e}")
        
        return (saved_metadata, file_path)


def main():
    """테스트: NVIDIA의 최신 문서 다운로드"""
    crawler = SECCrawler()
    
    # NVIDIA 티커로 테스트
    result = crawler.crawl_latest_filing("NVDA")
    
    if result:
        metadata, file_path = result
        print("\n=== 크롤링 완료 ===")
        print(f"메타데이터: {metadata}")
        print(f"파일 경로: {file_path}")
    else:
        print("크롤링 실패")


if __name__ == "__main__":
    main()
