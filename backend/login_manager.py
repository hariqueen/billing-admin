from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class LoginManager:
    """로그인 관리 클래스"""
    
    def __init__(self):
        self.active_sessions = {}  # 로그인된 세션 관리
    
    def login_account(self, account_data, keep_session=False):
        """계정 로그인"""
        company_name = account_data['company_name']
        account_type = account_data['account_type']
        config = account_data['config']
        
        print(f"{company_name} ({account_type.upper()}) 로그인 시작")
        
        driver = webdriver.Chrome()
        driver.maximize_window()
        
        try:
            # 사이트 접속
            driver.get(account_data['site_url'])
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
                softphone_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#useCti")))
                softphone_button.click()
                print("소프트폰 해제 완료")
            
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
            print(f"{company_name} ({account_type.upper()}) 로그인 실패: {e}")
            driver.quit()
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