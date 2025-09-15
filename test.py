import time
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from backend.data_collection.database import DatabaseManager
from backend.data_collection.config import DateConfig

class GuppuTest:
    def __init__(self, start_date=None, end_date=None):
        self.driver = None
        self.wait = None
        self.db_manager = DatabaseManager()
        
        # 날짜 설정 (제공되지 않으면 기본값 사용)
        if start_date and end_date:
            DateConfig.set_dates(start_date, end_date)
            print(f"📅 사용자 지정 날짜 설정: {start_date} ~ {end_date}")
        else:
            # 기본값: 6월 전체
            DateConfig.set_dates("2025-06-01", "2025-06-30")
            print("📅 기본 날짜 설정: 2025-06-01 ~ 2025-06-30")
        
        self.setup_driver()
        
    def setup_driver(self):
        """Chrome 드라이버 설정"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 다운로드 경로 설정
        download_dir = os.path.expanduser("~/Downloads")
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 10)
        
        # 브라우저 위치 설정
        self.driver.set_window_position(100, 100)
        
    def login_guppu(self, username, password):
        """구쁘 로그인"""
        try:
            print("🚀 구쁘 로그인 시작")
            
            # Firebase에서 구쁘 계정 정보 가져오기
            accounts = self.db_manager.get_all_accounts()
            guppu_account = None
            
            for account in accounts:
                if account.get('company_name') == '구쁘':
                    guppu_account = account
                    break
            
            if not guppu_account:
                print("❌ Firebase에서 구쁘 계정 정보를 찾을 수 없습니다")
                return False
            
            # 로그인 페이지로 이동 (site_url 또는 url 키 확인)
            site_url = guppu_account.get('site_url') or guppu_account.get('url')
            if not site_url:
                print("❌ 구쁘 사이트 URL이 설정되지 않았습니다")
                print(f"계정 데이터: {guppu_account}")
                return False
                
            self.driver.get(site_url)
            time.sleep(2)
            
            # 아이디 입력
            username_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#projUserCd"))
            )
            username_input.clear()
            username_input.send_keys(username)
            print("✅ 아이디 입력 완료")
            
            # 비밀번호 입력
            password_input = self.driver.find_element(By.CSS_SELECTOR, "#userPs")
            password_input.clear()
            password_input.send_keys(password)
            print("✅ 비밀번호 입력 완료")
            
            # 비밀서약 준수 체크박스 클릭
            agree_checkbox = self.driver.find_element(By.CSS_SELECTOR, "#agreeCheck")
            if not agree_checkbox.is_selected():
                agree_checkbox.click()
            print("✅ 비밀서약 준수 체크 완료")
            
            # 소프트폰 사용 체크박스 해제 (로그인 전에 해제해야 함)
            self.uncheck_softphone_usage()
            
            # 로그인 버튼 클릭
            login_btn = self.driver.find_element(By.CSS_SELECTOR, "#loginBtn")
            login_btn.click()
            print("로그인 버튼 클릭")
            
            # 로그인 성공 확인
            time.sleep(3)
            print("구쁘 로그인 완료")
            
            return True
            
        except Exception as e:
            print(f"❌ 로그인 실패: {e}")
            return False
    
    def uncheck_softphone_usage(self):
        """소프트폰 사용 체크박스 해제 (중복 로그인 방지 해제)"""
        try:
            print("🔍 소프트폰 사용 체크박스 확인 중...")
            
            # 소프트폰 사용 체크박스 찾기
            softphone_checkbox = self.driver.find_element(By.CSS_SELECTOR, "#useCti")
            
            # 현재 체크 상태 확인
            is_checked = softphone_checkbox.is_selected()
            print(f"📋 소프트폰 사용 체크박스 현재 상태: {'체크됨' if is_checked else '체크 안됨'}")
            
            if is_checked:
                print("🔄 소프트폰 사용 체크박스 해제 시도 중...")
                
                # 방법 1: JavaScript로 직접 클릭
                try:
                    self.driver.execute_script("arguments[0].click();", softphone_checkbox)
                    time.sleep(1)
                    print("✅ JavaScript로 소프트폰 사용 체크박스 해제 완료")
                except Exception as js_error:
                    print(f"⚠️ JavaScript 클릭 실패: {js_error}")
                    
                    # 방법 2: JavaScript로 직접 체크 해제
                    try:
                        self.driver.execute_script("arguments[0].checked = false;", softphone_checkbox)
                        # change 이벤트 트리거
                        self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", softphone_checkbox)
                        time.sleep(1)
                        print("✅ JavaScript로 소프트폰 사용 체크박스 직접 해제 완료")
                    except Exception as direct_error:
                        print(f"⚠️ JavaScript 직접 해제 실패: {direct_error}")
                        
                        # 방법 3: ActionChains 사용
                        try:
                            actions = ActionChains(self.driver)
                            actions.move_to_element(softphone_checkbox).click().perform()
                            time.sleep(1)
                            print("✅ ActionChains로 소프트폰 사용 체크박스 해제 완료")
                        except Exception as action_error:
                            print(f"⚠️ ActionChains 클릭 실패: {action_error}")
                            return False
                
                # 해제 후 상태 확인
                try:
                    final_state = softphone_checkbox.is_selected()
                    if not final_state:
                        print("✅ 소프트폰 사용 체크박스 해제 확인됨 (중복 로그인 방지 해제)")
                    else:
                        print("⚠️ 소프트폰 사용 체크박스가 여전히 체크되어 있습니다")
                except Exception as check_error:
                    print(f"⚠️ 최종 상태 확인 실패: {check_error}")
                    
            else:
                print("ℹ️ 소프트폰 사용 체크박스가 이미 해제되어 있습니다")
            
            return True
            
        except Exception as e:
            print(f"⚠️ 소프트폰 사용 체크박스 처리 실패: {e}")
            return False
    
    def navigate_to_sms_history(self):
        """SMS 문자발송이력 페이지로 이동"""
        try:
            print("🔍 SMS 문자발송이력 페이지로 이동")
            
            # 메뉴 버튼 클릭
            menu_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#sidebar > div > div.top.tab-wrap > ul > li:nth-child(2) > a"))
            )
            menu_btn.click()
            time.sleep(1)
            print("✅ 메뉴 버튼 클릭")
            
            # SMS 버튼 클릭
            sms_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#menuNav > li:nth-child(5) > a"))
            )
            sms_btn.click()
            time.sleep(1)
            print("✅ SMS 버튼 클릭")
            
            # 문자발송이력 버튼 클릭
            sms_history_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#menu_5603 > li:nth-child(2)"))
            )
            sms_history_btn.click()
            time.sleep(2)
            print("✅ 문자발송이력 버튼 클릭")
            
            return True
            
        except Exception as e:
            print(f"❌ SMS 페이지 이동 실패: {e}")
            return False
    
    def switch_to_iframe(self, target_src_keyword="smsHistory"):
        """SMS 문자발송이력 iframe으로 전환"""
        try:
            print("🔍 SMS iframe 찾기...")
            
            # 먼저 기본 프레임으로 전환
            self.driver.switch_to.default_content()
            time.sleep(1)
            
            # 모든 iframe 찾기
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            
            # smsHistory 키워드로 직접 찾기
            for i, iframe in enumerate(iframes):
                iframe_src = iframe.get_attribute("src")
                if iframe_src and target_src_keyword in iframe_src:
                    self.driver.switch_to.frame(iframe)
                    print(f"✅ SMS iframe[{i}] 전환 완료")
                    return True
            
            print("❌ SMS iframe을 찾을 수 없습니다")
            return False
            
        except Exception as e:
            print(f"❌ iframe 전환 실패: {e}")
            return False
    
    def get_current_date(self):
        """현재 날짜 확인"""
        try:
            
            # 날짜 관련 엘리먼트 찾기 시도
            date_selectors = [
                "#pickerViewdt",  # 표시용 날짜 input
                "#startDt",      # 시작날짜 hidden input
                "#endDt",        # 종료날짜 hidden input
                "input[name='startDt']",
                "input[data-picker='label']",
                "input[title='기간']"
            ]
            
            for selector in date_selectors:
                try:
                    date_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    current_date = date_element.get_attribute("value")
                    print(f" 날짜 엘리먼트 발견: {selector} = {current_date}")
                    return current_date
                except:
                    continue
            
            print("❌ 날짜 관련 엘리먼트를 찾을 수 없습니다")
            return None
            
        except Exception as e:
            print(f"❌ 현재 날짜 확인 실패: {e}")
            return None
    
    def set_date_range(self, start_date, end_date):
        """날짜 범위 설정"""
        try:
            print(f"📅 날짜 범위 설정: {start_date} ~ {end_date}")
            
            # 날짜 선택기 찾기 (성공한 방식만 사용)
            print("🔍 날짜 선택기 찾기...")
            try:
                date_picker = self.driver.find_element(By.CSS_SELECTOR, "#pickerViewdt")
                print("✅ 날짜 선택기 발견")
            except:
                print("❌ 날짜 선택기를 찾을 수 없습니다")
                return False
            
            # 날짜 선택기 클릭
            print("🖱️ 날짜 선택기 클릭...")
            date_picker.click()
            time.sleep(3)  # 캘린더 팝업 대기
            
            # 날짜 설정 (성공한 방법: hidden input 직접 설정)
            print(f"📅 {start_date} ~ {end_date} 기간으로 날짜 설정...")
            
            # hidden input 필드에 직접 값 설정
            start_date_input = self.driver.find_element(By.CSS_SELECTOR, "#startDt")
            self.driver.execute_script("arguments[0].value = arguments[1]", start_date_input, start_date)
            
            end_date_input = self.driver.find_element(By.CSS_SELECTOR, "#endDt")
            self.driver.execute_script("arguments[0].value = arguments[1]", end_date_input, end_date)
            
            # 표시용 필드도 업데이트
            display_input = self.driver.find_element(By.CSS_SELECTOR, "#pickerViewdt")
            display_value = f"{start_date} ~ {end_date}"
            self.driver.execute_script("arguments[0].value = arguments[1]", display_input, display_value)
            
            print(f"✅ 날짜 설정 완료: {display_value}")
            
            # 달력 닫기 (성공한 방법: 외부 클릭)
            print("🔄 달력 닫기...")
            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(2)
            
            # 설정된 값 확인
            try:
                final_start = self.driver.find_element(By.CSS_SELECTOR, "#startDt").get_attribute("value")
                final_end = self.driver.find_element(By.CSS_SELECTOR, "#endDt").get_attribute("value")
                print(f"📅 최종 설정된 날짜: {final_start} ~ {final_end}")
            except Exception as e:
                print(f"⚠️ 최종 날짜 확인 실패: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ 날짜 설정 실패: {e}")
            return False
    
    def search_data(self):
        """조회 버튼 클릭"""
        try:
            print("🔍 조회 버튼 클릭...")
            
            search_btn = self.driver.find_element(By.CSS_SELECTOR, "body > div.content-wrap > div.cont-top > div.title-wrap > div > button:nth-child(1)")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", search_btn)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", search_btn)
            
            time.sleep(3)  # 조회 결과 로딩 대기
            print("✅ 조회 완료")
            return True
            
        except Exception as e:
            print(f"❌ 조회 실패: {e}")
            return False
    
    def download_excel(self):
        """엑셀 다운로드 버튼 클릭"""
        try:
            print("📥 엑셀 다운로드 시작")
            
            # 다운로드 전 파일 개수 확인
            download_dir = os.path.expanduser("~/Downloads")
            before_files = set(os.listdir(download_dir))
            
            # 엑셀 다운로드 버튼 클릭 (성공한 방식만 사용)
            print("🔍 엑셀 다운로드 버튼 클릭...")
            
            download_btn = self.driver.find_element(By.CSS_SELECTOR, "body > div.content-wrap > div.cont-top > div.title-wrap > div > button:nth-child(2)")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", download_btn)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", download_btn)
            
            time.sleep(5)  # 다운로드 완료 대기 (더 길게)
            
            # 다운로드 후 파일 개수 확인
            after_files = set(os.listdir(download_dir))
            new_files = after_files - before_files
            
            if new_files:
                print(f"✅ 엑셀 다운로드 완료: {list(new_files)}")
                return True
            else:
                print("⚠️ 다운로드된 파일을 찾을 수 없습니다")
                return False
            
        except Exception as e:
            print(f"❌ 엑셀 다운로드 실패: {e}")
            return False
    
    def test_guppu_workflow(self):
        """구쁘 워크플로우 테스트"""
        try:
            print("🚀 구쁘 워크플로우 테스트 시작")
            
            # 1. Firebase에서 구쁘 계정 정보 가져오기
            accounts = self.db_manager.get_all_accounts()
            guppu_account = None
            
            for account in accounts:
                if account.get('company_name') == '구쁘':
                    guppu_account = account
                    break
            
            if not guppu_account:
                print("❌ Firebase에서 구쁘 계정 정보를 찾을 수 없습니다")
                return False
            
            # 2. 로그인
            username = guppu_account.get('username')
            password = guppu_account.get('password')
            
            if not username or not password:
                print("❌ 구쁘 계정의 사용자명 또는 비밀번호가 설정되지 않았습니다")
                return False
            
            if not self.login_guppu(username, password):
                return False
            
            # 3. SMS 문자발송이력 페이지로 이동
            if not self.navigate_to_sms_history():
                return False
            
            # 4. iframe 전환
            if not self.switch_to_iframe("smsHistory"):
                return False
            
            # 5. 현재 날짜 확인
            current_date = self.get_current_date()
            if current_date:
                print(f"📅 현재 설정된 날짜: {current_date}")
            
            # 6. 날짜 범위 설정 (DateConfig에서 가져오기)
            dates = DateConfig.get_dates()
            start_date = dates["start_date"]
            end_date = dates["end_date"]
            
            self.set_date_range(start_date, end_date)
            
            # 7. 조회 버튼 클릭
            if not self.search_data():
                return False
            
            # 8. 엑셀 다운로드
            if not self.download_excel():
                return False
            
            print("\n✅ SMS 문자발송이력 자동화 완료!")
            return True
            
        except Exception as e:
            print(f"❌ 워크플로우 테스트 실패: {e}")
            return False
        
        finally:
            # 작업 완료 후 브라우저 닫기
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                print("\n✅ 브라우저가 자동으로 닫혔습니다.")

def main(start_date=None, end_date=None):
    """메인 실행 함수"""
    print("🎯 구쁘 고객사 테스트 시작")
    
    # 날짜 파라미터와 함께 GuppuTest 초기화
    guppu_test = GuppuTest(start_date, end_date)
    try:
        success = guppu_test.test_guppu_workflow()
        
        if success:
            print("✅ 구쁘 테스트 성공")
            
            # 간소화된 워크플로우 완료
            print("\n" + "="*50)
            print("✅ SMS 문자발송이력 자동화 완료!")
            print("="*50)
            print("📋 완료된 작업:")
            print("  1. 구쁘 로그인")
            print("  2. SMS 문자발송이력 페이지 이동")
            dates = DateConfig.get_dates()
            print(f"  3. {dates['start_date']} ~ {dates['end_date']} 기간 설정")
            print("  4. 데이터 조회")
            print("  5. 엑셀 파일 다운로드")
            print("="*50)
        else:
            print("❌ 구쁘 테스트 실패")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
    
    finally:
        # 작업 완료 후 브라우저 자동 닫기
        if hasattr(guppu_test, 'driver') and guppu_test.driver:
            guppu_test.driver.quit()
            print("\n✅ 프로그램이 완료되어 브라우저가 자동으로 닫혔습니다.")

def run_guppu_collection(start_date=None, end_date=None):
    """app.py에서 호출할 수 있는 구쁘 데이터 수집 함수"""
    try:
        print(f"🎯 구쁘 데이터 수집 시작: {start_date} ~ {end_date}")
        
        guppu_test = GuppuTest(start_date, end_date)
        success = guppu_test.test_guppu_workflow()
        
        if success:
            print("✅ 구쁘 데이터 수집 성공")
            return True
        else:
            print("❌ 구쁘 데이터 수집 실패")
            return False
            
    except Exception as e:
        print(f"❌ 구쁘 데이터 수집 중 오류: {e}")
        return False

if __name__ == "__main__":
    # 테스트용 날짜 설정 (6월 전체)
    # main("2025-06-01", "2025-06-30")  # 특정 날짜로 테스트
    main()  # 기본 날짜(6월)로 테스트
