import os
import re
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import time
from bs4 import BeautifulSoup
import glob
from ..data_collection.config import AccountConfig
from ..storage.admin_storage import AdminStorage
from .wconcept_preprocessing import WconceptPreprocessor
from .mathpresso_preprocessing import MathpressoPreprocessor
from .guppu_preprocessing import GuppuPreprocessor

class BillProcessor:
    def __init__(self, admin_storage=None):
        self.temp_dir = "temp_processing"
        self.bill_images_dir = "bill_images"
        self.password = "1208192287"
        os.makedirs(self.bill_images_dir, exist_ok=True)
        # 통합 저장소 사용 (외부에서 전달받거나 새로 생성)
        if admin_storage:
            self.storage = admin_storage
        else:
            self.storage = AdminStorage()
            # 기존 파일이 있다면 마이그레이션 실행 (새로 생성된 경우만)
            self.storage.migrate_from_separate_files()
  
        # 고객사별 정규식 매핑 (기존 6개 고객사만)
        self.customer_mapping = {
            r'(\(주\)메타엠.*구쁘)\s+고객님\s+([0-9,]+원)': '구쁘',
            r'(㈜메타엠\s+W컨셉)\s+고객님\s+([0-9,]+원)': 'W컨셉', 
            r'(\(주\)메타엠.*디싸이더스)\s+고객님\s+([0-9,]+원)': '디싸이더스/애드프로젝트',
            r'(\(주\)메타엠.*하이픈스)\s+고객님\s+([0-9,]+원)': '매스프레소(콴다)',
            r'(\(주\)메타엠.*앤하우스)\s+고객님\s+([0-9,]+원)': '앤하우스',
            r'(\(주\)메타엠.*SK일렉링크)\s+고객님\s+([0-9,]+원)': 'SK일렉링크',
        }

    def setup_driver(self):
        """Chrome 드라이버 설정 (최대 속도 최적화)"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--page-load-strategy=none")  # eager에서 none으로 변경
        chrome_options.add_argument("--window-size=1280,720")
        
        # 메모리 사용량 최적화
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        
        try:
            return webdriver.Chrome(options=chrome_options)
        except:
            return None

    def unlock_and_extract_html(self, file_path, driver):
        """HTML 파일의 비밀번호를 해제하고 텍스트를 추출"""
        try:
            file_url = f"file://{os.path.abspath(file_path)}"
            driver.get(file_url)
            time.sleep(0.5)  # 1초에서 0.5초로 단축
            
            # 비밀번호 필드 확인
            password_field = None
            try:
                password_field = WebDriverWait(driver, 1).until(  # 2초에서 1초로 단축
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
                )
            except TimeoutException:
                pass
            
            if password_field:
                password_field.clear()
                password_field.send_keys(self.password)
                
                # 확인 버튼 클릭
                try:
                    button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                    button.click()
                except:
                    password_field.send_keys("\n")
                
                time.sleep(2)
            
            # 텍스트 추출
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text, password_field is not None
            
        except:
            return None, False

    def extract_customer_and_amount(self, text_content):
        """HTML에서 고객사명과 금액을 한 번에 추출 (최적화)"""
        # 고객사명 매핑
        customer_keywords = {
            "앤하우스": "앤하우스",
            "구쁘": "구쁘", 
            "W컨셉": "W컨셉",
            "디싸이더스": "디싸이더스/애드프로젝트",
            "SK일렉링크": "SK일렉링크",
            "하이픈스": "매스프레소(콴다)"
        }
        
        # 1. 고객사명 추출
        customer_patterns = [
            r'\(주\)메타엠[_\s]*([가-힣\w\s/()]+)\s+고객님',
            r'㈜메타엠[_\s]*([가-힣\w\s/()]+)\s+고객님'
        ]
        
        extracted_customer = None
        for pattern in customer_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE | re.DOTALL)
            if matches:
                raw_name = re.sub(r'\n.*', '', matches[0].strip()).strip()
                for keyword, mapped_name in customer_keywords.items():
                    if keyword in raw_name:
                        extracted_customer = mapped_name
                        break
                if extracted_customer:
                    break
        
        # 2. 금액 추출 (해당 고객사 패턴만 확인)
        customers = []
        amounts = []
        
        if extracted_customer:
            # 해당 고객사의 정규식 패턴만 확인
            for pattern, mapped_name in self.customer_mapping.items():
                if mapped_name == extracted_customer:
                    matches = re.findall(pattern, text_content, re.IGNORECASE | re.DOTALL)
                    if matches:
                        for match in matches:
                            customers.append(mapped_name)
                            if isinstance(match, tuple):
                                amounts.append(match[1].strip())
                            else:
                                amounts.append(match.strip())
                    break  # 매칭 성공하면 바로 종료
        
        return extracted_customer, customers, amounts

    def process_pdf_files(self, files):
        """PDF 파일들을 파일명 기반으로 고객사에 분배"""
        try:
            # PDF 파일 저장 디렉토리 생성
            pdf_dir = "bill_pdfs"
            os.makedirs(pdf_dir, exist_ok=True)
            
            # 고객사명 매핑 (파일명에서 직접 복사한 한글)
            customer_keywords = {
                "(하이픈스)": "매스프레소(콴다)",
                "(앤하우스)": "앤하우스", 
                "(디싸이더스)": "디싸이더스/애드프로젝트"
            }
            
            update_date = datetime.now().strftime("%m/%d")
            current_results = self.storage.get_bill_amounts().copy()
            processed_files = {}
            
            for file in files:
                filename = file.filename
                print(f"PDF 파일 처리: {filename}")
                
                # 파일명에서 고객사명 추출 (단순 문자열 검사)
                customer_found = None
                print(f"파일명 확인: '{filename}'")
                for keyword, mapped_name in customer_keywords.items():
                    print(f"키워드 확인: '{keyword}' in '{filename}' = {keyword in filename}")
                    if keyword in filename:
                        customer_found = mapped_name
                        print(f"매칭 성공: {filename} -> {mapped_name}")
                        break
                
                if customer_found:
                    # 파일 저장
                    file_path = os.path.join(pdf_dir, filename)
                    file.save(file_path)
                    
                    # 기존 PDF 파일 삭제 (같은 고객사)
                    for existing_file in os.listdir(pdf_dir):
                        if existing_file != filename:
                            for keyword, mapped_name in customer_keywords.items():
                                if keyword in existing_file and mapped_name == customer_found:
                                    old_file_path = os.path.join(pdf_dir, existing_file)
                                    try:
                                        os.remove(old_file_path)
                                        print(f"기존 PDF 파일 삭제: {existing_file}")
                                    except:
                                        pass
                    
                    # 결과 저장
                    if customer_found not in current_results:
                        current_results[customer_found] = {}
                    
                    current_results[customer_found].update({
                        "update_date": update_date,
                        "pdf_file": filename
                    })
                    
                    processed_files[customer_found] = filename
                    print(f"PDF 파일 분배 완료: {customer_found} -> {filename}")
                else:
                    print(f"매칭되지 않은 PDF 파일: {filename}")
            
            # 통합 저장소에 일괄 저장
            if processed_files:
                self.storage.batch_update_bill_amounts(current_results)
            
            return current_results
            
        except Exception as e:
            print(f"PDF 파일 처리 오류: {e}")
            return None

    def process_html_files(self, files):
        """HTML 파일들을 처리하고 통신비 정보 추출"""
        try:
            os.makedirs(self.temp_dir, exist_ok=True)
            
            driver = self.setup_driver()
            if not driver:
                return None
        
            update_date = datetime.now().strftime("%m/%d")  # 업데이트 날짜 (MM/DD)
            
            # 기존 데이터 유지하면서 업데이트
            current_results = self.storage.get_bill_amounts().copy()
            
            for file in files:
                try:
                    file_path = os.path.join(self.temp_dir, file.filename)
                    file.save(file_path)
                    
                    text_content, was_locked = self.unlock_and_extract_html(file_path, driver)
                    
                    if text_content:
                        # 최적화: 고객사명과 금액을 한 번에 추출
                        extracted_customer, customers, amounts = self.extract_customer_and_amount(text_content)
                        
                        # PDF 생성
                        pdf_path = None
                        if extracted_customer:
                            safe_customer_name = "디싸이더스" if extracted_customer == "디싸이더스/애드프로젝트" else extracted_customer
                            pdf_path = self.convert_html_to_pdf(file_path, safe_customer_name, driver)
                        
                        # 데이터 저장
                        for customer, amount in zip(customers, amounts):
                            current_results[customer] = {
                                "amount": amount,
                                "update_date": update_date,
                                "image_path": pdf_path
                            }
                    
                    # 임시 파일 삭제
                    try:
                        os.remove(file_path)
                    except:
                        pass
                
                except:
                    pass
            
            # 모든 파일 처리가 끝난 후 통합 저장소에 일괄 저장
            self.storage.batch_update_bill_amounts(current_results)
            
            return self.storage.get_bill_amounts()
                
        except:
            return None
            
        finally:
            try:
                driver.quit()
            except:
                pass

    def process_mixed_files(self, files):
        """HTML과 PDF 파일을 구분해서 처리"""
        try:
            html_files = [f for f in files if f.filename.endswith('.html')]
            pdf_files = [f for f in files if f.filename.endswith('.pdf')]
            
            results = {}
            
            # HTML 파일 처리 (기존 로직)
            if html_files:
                html_results = self.process_html_files(html_files)
                if html_results:
                    results.update(html_results)
            
            # PDF 파일 처리 (새로운 로직)
            if pdf_files:
                pdf_results = self.process_pdf_files(pdf_files)
                if pdf_results:
                    # 기존 결과와 병합
                    for customer, data in pdf_results.items():
                        if customer in results:
                            results[customer].update(data)
                        else:
                            results[customer] = data
            
            return results if results else None
            
        except Exception as e:
            print(f"파일 처리 오류: {e}")
            return None

    def get_bill_amounts(self):
        """저장된 통신비 정보 조회"""
        return self.storage.get_bill_amounts()

    def remove_existing_bill_image(self, customer_name):
        """기존 통신비 PDF 파일 삭제"""
        try:
            pattern = os.path.join(self.bill_images_dir, f"{customer_name}_*_통신비.*")
            existing_files = glob.glob(pattern)
            for file_path in existing_files:
                os.remove(file_path)
                print(f"기존 파일 삭제: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"기존 파일 삭제 실패: {e}")

    def convert_html_to_pdf(self, html_path, pdf_name, driver):
        """HTML 파일을 PDF로 변환하여 저장 (속도 최적화)"""
        try:
            # PDF 파일명 생성
            current_date = datetime.now().strftime("%Y%m%d")
            pdf_filename = f"{pdf_name}_{current_date}_통신비.pdf"
            pdf_path = os.path.join(self.bill_images_dir, pdf_filename)
            
            # 기존 파일이 있으면 삭제 후 새로 생성
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                print(f"기존 PDF 삭제 후 새로 생성: {pdf_filename}")
            
            # 기존 같은 고객사 파일들 삭제
            pattern = os.path.join(self.bill_images_dir, f"{pdf_name}_*_통신비.pdf")
            existing_files = glob.glob(pattern)
            for existing_file in existing_files:
                os.remove(existing_file)
            
            # Chrome PDF 생성 옵션 최적화
            print_options = {
                'landscape': False,
                'displayHeaderFooter': False,
                'printBackground': True,
                'preferCSSPageSize': True,
                'marginTop': 0,
                'marginBottom': 0,
                'marginLeft': 0,
                'marginRight': 0,
            }
            
            result = driver.execute_cdp_cmd('Page.printToPDF', print_options)
            
            with open(pdf_path, 'wb') as file:
                import base64
                file.write(base64.b64decode(result['data']))
            
            print(f"PDF 저장 완료: {pdf_filename}")
            return pdf_path
            
        except Exception as e:
            print(f"HTML PDF 변환 실패: {e}")
            return None

    def process_wconcept(self, collection_date, license_count=40):
        """W컨셉 전처리 처리"""
        try:
            preprocessor = WconceptPreprocessor()
            success = preprocessor.process_wconcept_data(collection_date, license_count)
            
            if success:
                # 성공 시 다운로드 폴더에서 생성된 파일 찾기 (W컨셉은 n-1월 파일명)
                download_dir = str(Path.home() / "Downloads")
                date_obj = datetime.strptime(collection_date, '%Y-%m-%d')
                
                # W컨셉은 n-1월로 파일명 생성
                if date_obj.month == 1:
                    prev_year = date_obj.year - 1
                    prev_month = 12
                else:
                    prev_year = date_obj.year
                    prev_month = date_obj.month - 1
                
                date_prefix = f"{str(prev_year)[2:]}{prev_month:02d}"
                expected_filename = f"{date_prefix}_W컨셉_청구내역서.xlsx"
                expected_path = os.path.join(download_dir, expected_filename)
                
                if os.path.exists(expected_path):
                    return [expected_filename]
                else:
                    print(f"생성된 파일을 찾을 수 없습니다: {expected_path}")
                    return []
            else:
                return []
                
        except Exception as e:
            print(f"W컨셉 전처리 실패: {e}")
            return []

    def process_mathpresso(self, collection_date):
        """매스프레소(콴다) 전처리 처리"""
        try:
            preprocessor = MathpressoPreprocessor()
            success = preprocessor.process_mathpresso_data(collection_date)
            
            if success:
                # 성공 시 다운로드 폴더에서 생성된 파일 찾기
                download_dir = str(Path.home() / "Downloads")
                date_obj = datetime.strptime(collection_date, '%Y-%m-%d')
                date_prefix = f"{str(date_obj.year)[2:]}{date_obj.month:02d}"
                expected_filename = f"{date_prefix}_매스프레소(콴다)_청구내역서.xlsx"
                expected_path = os.path.join(download_dir, expected_filename)
                
                if os.path.exists(expected_path):
                    return [expected_filename]
                else:
                    print(f"생성된 파일을 찾을 수 없습니다: {expected_path}")
                    return []
            else:
                return []
                
        except Exception as e:
            print(f"매스프레소(콴다) 전처리 실패: {e}")
            return []

    def process_guppu(self, collection_date):
        """구쁘 전처리 처리"""
        try:
            preprocessor = GuppuPreprocessor()
            success = preprocessor.process_guppu_data(collection_date)
            
            if success:
                # 성공 시 다운로드 폴더에서 생성된 파일 찾기
                download_dir = str(Path.home() / "Downloads")
                date_obj = datetime.strptime(collection_date, '%Y-%m-%d')
                date_prefix = f"{str(date_obj.year)[2:]}{date_obj.month:02d}"
                expected_filename = f"{date_prefix}_구쁘_상담솔루션 청구내역서.xlsx"
                expected_path = os.path.join(download_dir, expected_filename)
                
                if os.path.exists(expected_path):
                    return [expected_filename]
                else:
                    print(f"생성된 파일을 찾을 수 없습니다: {expected_path}")
                    return []
            else:
                return []
                
        except Exception as e:
            print(f"구쁘 전처리 실패: {e}")
            return []
