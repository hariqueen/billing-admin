import os
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import time
from bs4 import BeautifulSoup
from ..data_collection.config import AccountConfig
from ..storage.admin_storage import AdminStorage

class BillProcessor:
    def __init__(self, admin_storage=None):
        self.temp_dir = "temp_processing"
        self.password = "1208192287"
        # 통합 저장소 사용 (외부에서 전달받거나 새로 생성)
        if admin_storage:
            self.storage = admin_storage
        else:
            self.storage = AdminStorage()
            # 기존 파일이 있다면 마이그레이션 실행 (새로 생성된 경우만)
            self.storage.migrate_from_separate_files()
        
        # 고객사별 정규식 매핑
        self.customer_mapping = {
            r'(\(주\)메타엠_구쁘)\s+고객님\s+([0-9,]+원)': '구쁘',
            r'(㈜메타엠\s+W컨셉)\s+고객님\s+([0-9,]+원)': 'W컨셉', 
            r'(메타엠_SAAS_디싸이더스)\s+고객님\s+([0-9,]+원)': '디싸이더스/애드프로젝트',
            r'(\(주\)메타엠_SAAS_9)\s+고객님\s+([0-9,]+원)': '매스프레소(콴다)',
            r'(\(주\)메타엠_앤하우스\(SAC2-S\))\s+고객님\s+([0-9,]+원)': '앤하우스',
            r'(\(주\)메타엠)\s+고객님\s+([0-9,]+원)': 'SK일렉링크',
        }

    def setup_driver(self):
        """Chrome 드라이버 설정"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        try:
            return webdriver.Chrome(options=chrome_options)
        except:
            return None

    def unlock_and_extract_html(self, file_path, driver):
        """HTML 파일의 비밀번호를 해제하고 텍스트를 추출"""
        try:
            file_url = f"file://{os.path.abspath(file_path)}"
            driver.get(file_url)
            time.sleep(1)
            
            # 비밀번호 필드 확인
            password_field = None
            try:
                password_field = WebDriverWait(driver, 2).until(
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

    def parse_billing_info(self, text_content):
        """텍스트에서 고객명과 금액을 추출"""
        customers = []
        amounts = []
        
        for pattern, mapped_name in self.customer_mapping.items():
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                customers.append(mapped_name)
                amounts.append(match[1].strip())
        
        return customers, amounts

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
                        customers, amounts = self.parse_billing_info(text_content)
                        
                        # 각 고객사별 금액 정보와 업데이트 날짜 저장
                        for customer, amount in zip(customers, amounts):
                            current_results[customer] = {
                                "amount": amount,
                                "update_date": update_date
                            }
                            
                        # 통합 저장소에 일괄 저장
                        self.storage.batch_update_bill_amounts(current_results)
                    
                    # 임시 파일 삭제
                    try:
                        os.remove(file_path)
                    except:
                        pass
                
                except:
                    pass
            
            return self.storage.get_bill_amounts()
                
        except:
            return None
            
        finally:
            try:
                driver.quit()
            except:
                pass

    def get_bill_amounts(self):
        """저장된 통신비 정보 조회"""
        return self.storage.get_bill_amounts()
