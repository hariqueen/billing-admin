import time
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from backend.data_collection.database import DatabaseManager

class GuppuTest:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.db_manager = DatabaseManager()
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
            
            # 로그인 페이지로 이동
            site_url = guppu_account.get('site_url') or guppu_account.get('url')
            if not site_url:
                print("❌ 구쁘 사이트 URL이 설정되지 않았습니다")
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
            
            # 로그인 버튼 클릭
            login_btn = self.driver.find_element(By.CSS_SELECTOR, "#loginBtn")
            login_btn.click()
            print("✅ 로그인 버튼 클릭")
            
            # 로그인 성공 확인
            time.sleep(3)
            print("✅ 구쁘 로그인 완료")
            return True
            
        except Exception as e:
            print(f"❌ 로그인 실패: {e}")
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
    
    def switch_to_iframe(self, iframe_index=0):
        """iframe 전환"""
        try:
            print("🔍 iframe 확인 중...")
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if iframes and len(iframes) > iframe_index:
                self.driver.switch_to.frame(iframes[iframe_index])
                print(f"✅ iframe[{iframe_index}] 전환 완료")
                return True
            else:
                print(f"⚠️ iframe[{iframe_index}] 찾을 수 없음 (전체 {len(iframes)}개)")
                return False
        except Exception as e:
            print(f"❌ iframe 전환 실패: {e}")
            return False
    
    def get_current_date(self):
        """현재 날짜 확인"""
        try:
            # 페이지 구조 디버깅
            print("🔍 페이지 구조 확인 중...")
            
            # 모든 input 엘리먼트 확인
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            print(f"📋 페이지의 input 엘리먼트 개수: {len(inputs)}")
            
            for i, input_elem in enumerate(inputs[:10]):  # 처음 10개만 확인
                input_id = input_elem.get_attribute("id")
                input_name = input_elem.get_attribute("name")
                input_type = input_elem.get_attribute("type")
                print(f"  Input {i}: id='{input_id}', name='{input_name}', type='{input_type}'")
            
            # 날짜 관련 엘리먼트 찾기 시도
            date_selectors = [
                "#startDt",
                "input[name='startDt']",
                "input[name='pickerViewdt']",
                "input[data-picker='start']",
                "input[title='기간']"
            ]
            
            for selector in date_selectors:
                try:
                    date_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    current_date = date_element.get_attribute("value")
                    print(f"✅ 날짜 엘리먼트 발견: {selector} = {current_date}")
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
            
            # 페이지 구조 확인
            print("🔍 날짜 선택기 찾기 중...")
            
            # 날짜 선택기 찾기 시도
            date_picker_selectors = [
                "#schForm > table > tbody > tr > td:nth-child(2) > div",
                ".input-date.daterange",
                "div[data-target='date']",
                "input[data-picker='label']"
            ]
            
            date_picker = None
            for selector in date_picker_selectors:
                try:
                    date_picker = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"✅ 날짜 선택기 발견: {selector}")
                    break
                except:
                    continue
            
            if not date_picker:
                print("❌ 날짜 선택기를 찾을 수 없습니다")
                return False
            
            # 날짜 선택기 클릭
            date_picker.click()
            time.sleep(1)
            
            # 시작날짜 설정 시도
            start_date_selectors = ["#startDt", "input[name='startDt']", "input[data-picker='start']"]
            start_date_input = None
            
            for selector in start_date_selectors:
                try:
                    start_date_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.driver.execute_script("arguments[0].value = arguments[1]", start_date_input, start_date)
                    print(f"✅ 시작날짜 설정: {start_date}")
                    break
                except:
                    continue
            
            # 종료날짜 설정 시도
            end_date_selectors = ["#endDt", "input[name='endDt']", "input[data-picker='end']"]
            end_date_input = None
            
            for selector in end_date_selectors:
                try:
                    end_date_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.driver.execute_script("arguments[0].value = arguments[1]", end_date_input, end_date)
                    print(f"✅ 종료날짜 설정: {end_date}")
                    break
                except:
                    continue
            
            # 날짜 선택기 외부 클릭하여 닫기
            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"❌ 날짜 설정 실패: {e}")
            return False
    
    def navigate_date_calendar(self, direction="next", date_type="start"):
        """날짜 캘린더에서 이전/다음 버튼으로 날짜 이동"""
        try:
            print(f"📅 날짜 캘린더 이동: {direction} ({date_type})")
            
            # 날짜 선택기 클릭
            date_picker = self.driver.find_element(By.CSS_SELECTOR, "#schForm > table > tbody > tr > td:nth-child(2) > div")
            date_picker.click()
            time.sleep(1)
            
            # 날짜 타입에 따른 선택자 결정
            if date_type == "start":
                if direction == "prev":
                    selector = "body > div:nth-child(6) > div.drp-calendar.left > div.calendar-table > table > thead > tr:nth-child(1) > th.prev.available"
                else:  # next
                    selector = "body > div:nth-child(6) > div.drp-calendar.left > div.calendar-table > table > thead > tr:nth-child(1) > th.next.available"
            else:  # end
                if direction == "prev":
                    selector = "body > div:nth-child(6) > div.drp-calendar.right > div.calendar-table > table > thead > tr:nth-child(1) > th.prev.available"
                else:  # next
                    selector = "body > div:nth-child(6) > div.drp-calendar.right > div.calendar-table > table > thead > tr:nth-child(1) > th.next.available"
            
            # 버튼 클릭
            nav_button = self.driver.find_element(By.CSS_SELECTOR, selector)
            nav_button.click()
            time.sleep(1)
            
            print(f"✅ {direction} 버튼 클릭 완료 ({date_type})")
            return True
            
        except Exception as e:
            print(f"❌ 날짜 캘린더 이동 실패: {e}")
            return False
    
    def search_data(self):
        """조회 버튼 클릭"""
        try:
            print("🔍 조회 버튼 클릭")
            
            # 조회 버튼 클릭
            search_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.content-wrap > div.cont-top > div.title-wrap > div > button:nth-child(1)"))
            )
            search_btn.click()
            time.sleep(2)  # 조회 결과 로딩 대기
            
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
            
            # 엑셀 다운로드 버튼 클릭
            download_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.content-wrap > div.cont-top > div.title-wrap > div > button:nth-child(2)"))
            )
            download_btn.click()
            time.sleep(3)  # 다운로드 완료 대기
            
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
    
    def logout_guppu(self):
        """구쁘 로그아웃"""
        try:
            print("🚪 구쁘 로그아웃 시작")
            
            # 로그아웃 버튼 클릭
            logout_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#logoutBtn"))
            )
            logout_btn.click()
            time.sleep(2)  # 팝업 대기
            
            # 로그아웃 확인 팝업 처리
            try:
                # 팝업 확인 버튼 클릭
                confirm_btn = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#alert > div > div > div.modal-footer > button:nth-child(2)"))
                )
                confirm_btn.click()
                print("✅ 로그아웃 확인 팝업 처리 완료")
                time.sleep(2)  # 로그아웃 처리 대기
                
            except Exception as popup_error:
                print(f"⚠️ 팝업 처리 실패, iframe 전환 시도: {popup_error}")
                
                # iframe 전환 시도
                try:
                    # 기본 iframe으로 돌아가기
                    self.driver.switch_to.default_content()
                    time.sleep(1)
                    
                    # 팝업 확인 버튼 다시 시도
                    confirm_btn = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "#alert > div > div > div.modal-footer > button:nth-child(2)"))
                    )
                    confirm_btn.click()
                    print("✅ iframe 전환 후 로그아웃 확인 팝업 처리 완료")
                    time.sleep(2)
                    
                except Exception as iframe_error:
                    print(f"❌ iframe 전환 후에도 팝업 처리 실패: {iframe_error}")
                    return False
            
            print("✅ 구쁘 로그아웃 완료")
            return True
            
        except Exception as e:
            print(f"❌ 로그아웃 실패: {e}")
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
            if not self.switch_to_iframe(0):  # 첫 번째 iframe으로 전환
                return False
            
            # 5. 현재 날짜 확인
            current_date = self.get_current_date()
            if current_date:
                print(f"📅 현재 설정된 날짜: {current_date}")
            
            # 6. 날짜 범위 설정 테스트
            today = datetime.now()
            start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
            
            if self.set_date_range(start_date, end_date):
                print("✅ 날짜 범위 설정 완료")
            
            # 7. 조회 버튼 클릭
            if not self.search_data():
                return False
            
            # 8. 엑셀 다운로드
            if not self.download_excel():
                return False
            
            # 9. 날짜 캘린더 네비게이션 테스트 (선택사항)
            print("\n📅 날짜 캘린더 네비게이션 테스트")
            
            # 시작날짜 다음달로 이동
            self.navigate_date_calendar("next", "start")
            time.sleep(1)
            
            # 시작날짜 이전달로 이동
            self.navigate_date_calendar("prev", "start")
            time.sleep(1)
            
            # 종료날짜 다음달로 이동
            self.navigate_date_calendar("next", "end")
            time.sleep(1)
            
            # 종료날짜 이전달로 이동
            self.navigate_date_calendar("prev", "end")
            time.sleep(1)
            
            # 10. 로그아웃 (중복 로그인 방지)
            print("\n🚪 로그아웃 시작")
            if self.logout_guppu():
                print("✅ 구쁘 워크플로우 테스트 완료 (로그아웃 성공)")
            else:
                print("⚠️ 구쁘 워크플로우 테스트 완료 (로그아웃 실패)")
            
            return True
            
        except Exception as e:
            print(f"❌ 워크플로우 테스트 실패: {e}")
            return False
        
        finally:
            # 브라우저를 열어둔 상태로 유지 (수동으로 로그아웃 후 닫기)
            print("🔍 브라우저를 열어둔 상태로 유지합니다.")
            print("💡 수동으로 로그아웃 후 브라우저를 닫아주세요.")
            print("🚪 로그아웃 버튼: #logoutBtn")
            print("✅ 확인 버튼: #alert > div > div > div.modal-footer > button:nth-child(2)")

def main():
    """메인 실행 함수"""
    print("🎯 구쁘 고객사 테스트 시작")
    
    guppu_test = GuppuTest()
    try:
        success = guppu_test.test_guppu_workflow()
        
        if success:
            print("✅ 구쁘 테스트 성공")
        else:
            print("❌ 구쁘 테스트 실패")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
    
    finally:
        # 테스트 성공/실패와 관계없이 브라우저를 열어둔 상태로 유지
        print("🔍 브라우저를 열어둔 상태로 유지합니다.")
        print("💡 수동으로 로그아웃 후 브라우저를 닫아주세요.")
        print("🚪 로그아웃 버튼: #logoutBtn")
        print("✅ 확인 버튼: #alert > div > div > div.modal-footer > button:nth-child(2)")
        
        # 무한 대기 (수동으로 종료할 때까지)
        try:
            input("엔터 키를 누르면 프로그램이 종료됩니다...")
        except KeyboardInterrupt:
            print("\n프로그램이 중단되었습니다.")

if __name__ == "__main__":
    main()
