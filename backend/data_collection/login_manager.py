from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from pathlib import Path
import os
import time

class LoginManager:
    """로그인 관리 클래스"""
    
    def __init__(self):
        self.active_sessions = {}  # 로그인된 세션 관리
        # Docker 컨테이너 내부에서 사용할 다운로드 경로
        self.download_dir = "/app/downloads"
        os.makedirs(self.download_dir, exist_ok=True)
    
    def login_account(self, account_data, keep_session=False):
        """계정 로그인"""
        company_name = account_data.get('company_name', 'Unknown')
        account_type = account_data.get('account_type', 'unknown')
        config = account_data.get('config', {})
        
        # Chrome 옵션 설정
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-features=TranslateUI')
            chrome_options.add_argument('--disable-ipc-flooding-protection')
            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
        except Exception as opt_error:
            print(f"❌ Chrome 옵션 설정 실패: {opt_error}")
            import traceback
            traceback.print_exc()
            return False, None
        
        try:
            from selenium.webdriver.chrome.service import Service
            service = Service(log_output="/tmp/chromedriver.log")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.maximize_window()
        except Exception as driver_error:
            print(f"❌ Chrome WebDriver 생성 실패: {driver_error}")
            import traceback
            traceback.print_exc()
            return False, None
        
        try:
            site_url = account_data.get('site_url')
            if not site_url:
                print(f"{company_name} 사이트 URL이 설정되지 않았습니다")
                print(f"계정 데이터 키: {list(account_data.keys())}")
                driver.quit()
                return False, None
                
            driver.get(site_url)
            wait = WebDriverWait(driver, 10)
            
            # ID 입력
            id_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['id_selector'])))
            id_element.send_keys(account_data['username'])
            
            # 비밀번호 입력
            pw_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['pw_selector'])))
            pw_element.send_keys(account_data['password'])
            
            # 체크박스 클릭
            checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['checkbox_selector'])))
            checkbox.click()
            
            # SMS 계정의 소프트폰 해제 (필요한 경우)
            if account_type == "sms" and config.get('need_softphone_off'):
                try:
                    softphone_checkbox = driver.find_element(By.CSS_SELECTOR, "#useCti")
                    is_checked = softphone_checkbox.is_selected()
                    
                    if is_checked:
                        # JavaScript로 체크박스 해제
                        driver.execute_script("arguments[0].click();", softphone_checkbox)
                        time.sleep(1)
                        print("소프트폰 해제 완료")
                    else:
                        print("소프트폰이 이미 해제되어 있습니다")
                except Exception as e:
                    print(f"소프트폰 해제 실패: {e}")
            
            # 로그인 버튼 클릭
            login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['login_btn'])))
            login_button.click()
            time.sleep(2)  # 로그인 처리 대기
            
            # 로그인 직후 알림창 처리
            try:
                alert_ok_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#ax5-dialog-29 > div.ax-dialog-body > div.ax-dialog-buttons > div > button"))
                )
                alert_ok_button.click()
                print("로그인 후 알림창 닫기 완료")
                time.sleep(1)
            except:
                print("로그인 후 알림창 없음")  # 알림창이 없는 경우 (정상적인 상황)
                pass
            
            if keep_session:
                print(f"{company_name} ({account_type.upper()}) 로그인 성공 (세션 유지)")
                self.active_sessions[f"{company_name}_{account_type}"] = {
                    'driver': driver,
                    'account_data': account_data
                }
                return True, driver
            else:
                print(f"{company_name} ({account_type.upper()}) 로그인 성공")
                driver.quit()
                return True, None
                
        except Exception as e:
            print(f"❌ {company_name} ({account_type.upper()}) 로그인 실패: {e}")
            import traceback
            traceback.print_exc()
            print(f"상세 에러 정보:")
            print(traceback.format_exc())
            try:
                driver.quit()
            except:
                pass
            return False, None
    
    def get_active_session(self, company_name, account_type):
        """활성 세션 조회"""
        session_key = f"{company_name}_{account_type}"
        return self.active_sessions.get(session_key)
    
    def close_session(self, company_name, account_type):
        """세션 종료"""
        session_key = f"{company_name}_{account_type}"
        if session_key in self.active_sessions:
            self.active_sessions[session_key]['driver'].quit()
            del self.active_sessions[session_key]
            print(f"{company_name} 세션 종료")
    
    def close_all_sessions(self):
        """모든 세션 종료"""
        for session_key in list(self.active_sessions.keys()):
            self.active_sessions[session_key]['driver'].quit()
            del self.active_sessions[session_key]
        print("모든 세션 종료")