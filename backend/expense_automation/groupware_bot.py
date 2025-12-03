from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import re
from .config import ExpenseConfig

class GroupwareAutomation:
    """그룹웨어 자동화 클래스"""
    
    def __init__(self):
        self.config = ExpenseConfig()
        self.driver = None
        self.wait = None

    def setup_driver(self):
        """WebDriver 설정 (Docker 환경 대응, 크롤링 모듈과 동일)"""
        options = Options()
        # Docker 환경 필수 옵션 (크롤링 모듈과 동일)
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-ipc-flooding-protection')
        # 그룹웨어 접속을 위한 옵션
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        
        # 크롤링 모듈과 완전히 동일한 방식 사용
        try:
            from selenium.webdriver.chrome.service import Service
            # 크롤링 모듈(login_manager.py)과 동일: 경로 지정 없이 Service 사용
            service = Service(log_output="/tmp/chromedriver_expense.log")
            self.driver = webdriver.Chrome(service=service, options=options)
            print("✅ 브라우저 시작 완료 (Service 사용, 크롤링 모듈과 동일)")
        except Exception as service_error:
            print(f"⚠️ Service로 시작 실패: {service_error}")
            import traceback
            traceback.print_exc()
            # webdriver-manager로 재시도
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service as ServiceManager
                print("🔄 webdriver-manager로 ChromeDriver 설치 시도...")
                service = ServiceManager(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                print("✅ 브라우저 시작 완료 (webdriver-manager 사용)")
            except Exception as manager_error:
                print(f"⚠️ webdriver-manager 실패: {manager_error}")
                import traceback
                traceback.print_exc()
                # 마지막으로 Service 없이 직접 실행
                try:
                    self.driver = webdriver.Chrome(options=options)
                    print("✅ 브라우저 시작 완료 (Service 없이)")
                except Exception as direct_error:
                    print(f"❌ 브라우저 실행 실패: {direct_error}")
                    import traceback
                    traceback.print_exc()
                    raise Exception(f"브라우저 실행 실패: {direct_error}")
        
        try:
            self.driver.maximize_window()  # 크롤링 모듈과 동일
            self.wait = WebDriverWait(self.driver, 30)
            return True
        except Exception as e:
            print(f"⚠️ 창 최대화 또는 Wait 설정 실패: {e}")
            self.wait = WebDriverWait(self.driver, 30)
            return True

    def login_to_groupware(self, user_id, password):
        """그룹웨어 로그인"""
        from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
        
        try:
            print("로그인 시작...")
            self.driver.get(self.config.LOGIN_URL)
            time.sleep(3)
            
            # 아이디 입력
            id_input = self.wait.until(EC.presence_of_element_located((By.ID, "userId")))
            id_input.clear()
            id_input.send_keys(user_id)
            time.sleep(1)
            
            # 비밀번호 입력
            pw_input = self.driver.find_element(By.ID, "userPw")
            pw_input.clear()
            pw_input.send_keys(password)
            time.sleep(1)
            
            # 로그인 버튼 클릭
            pw_input.send_keys(Keys.ENTER)
            time.sleep(5)
            
            # 알림 처리 (로그인 실패 시)
            alert_detected = False
            alert_text = None
            
            try:
                # 알림이 있는지 확인
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                print(f"⚠️ 로그인 실패 알림: {alert_text}")
                alert.accept()
                alert_detected = True
            except NoAlertPresentException:
                # 알림이 없는 경우 - 정상 흐름
                pass
            except UnexpectedAlertPresentException as alert_ex:
                # UnexpectedAlertPresentException 처리 - 알림 텍스트 추출
                try:
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    print(f"⚠️ 알림 감지: {alert_text}")
                    alert.accept()
                    alert_detected = True
                except:
                    # 알림 텍스트를 예외 메시지에서 추출
                    error_str = str(alert_ex)
                    if "Alert Text:" in error_str:
                        alert_text = error_str.split("Alert Text:")[1].split("\\n")[0].strip()
                    alert_detected = True
            except Exception as alert_check:
                # "no such alert" 등의 기타 예외는 알림이 없는 것으로 간주
                if "no such alert" in str(alert_check).lower():
                    pass  # 알림 없음 - 정상 흐름
                else:
                    # 예상치 못한 예외는 로그만 남기고 계속 진행
                    print(f"⚠️ 알림 확인 중 예외 발생 (무시): {alert_check}")
            
            # 알림이 감지된 경우 즉시 실패 처리
            if alert_detected:
                # 알림 텍스트를 그대로 사용 (중복 방지)
                if alert_text:
                    raise ValueError(f"로그인 실패: {alert_text}")
                else:
                    raise ValueError("로그인 실패: 로그인 정보가 올바르지 않습니다.")
            
            # 로그인 성공 확인 - 알림이 없었고 URL이 메인 페이지인지 확인
            try:
                current_url = self.driver.current_url
                print(f"   현재 URL: {current_url}")
                
                # 로그인 성공 조건: userMain.do가 URL에 포함되어 있어야 함
                # (로그인 페이지와 메인 페이지가 같은 URL일 수 있으므로 단순히 userMain.do 포함 여부만 확인)
                if "userMain.do" not in current_url:
                    # 로그인 페이지로 리다이렉트되지 않은 경우 실패
                    raise ValueError("로그인 실패: 로그인 정보가 올바르지 않습니다.")
                
                # 로그인 성공으로 간주 (userMain.do가 포함되어 있으면 성공)
                    
            except ValueError:
                raise  # ValueError는 그대로 전달
            except UnexpectedAlertPresentException as url_alert_ex:
                # URL 확인 중 알림 발생
                try:
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    print(f"⚠️ URL 확인 중 알림: {alert_text}")
                    alert.accept()
                    raise ValueError(f"로그인 실패: {alert_text}")
                except ValueError:
                    raise  # ValueError는 그대로 전달
                except:
                    error_str = str(url_alert_ex)
                    if "Alert Text:" in error_str:
                        alert_text = error_str.split("Alert Text:")[1].split("\\n")[0].strip()
                        raise ValueError(f"로그인 실패: {alert_text}")
                    raise ValueError("로그인 실패: 로그인 정보가 올바르지 않습니다.")
            
            print("로그인 완료")
            return True
            
        except ValueError as e:
            # 로그인 실패 (정상적인 실패 케이스)
            raise e
        except Exception as e:
            # 그 외 예외는 포괄적 메시지로 변환
            raise Exception(f"로그인 실패: {e}")

    def navigate_to_expense_page(self):
        """지출결의서 페이지로 이동"""
        try:
            print("지출결의서 페이지로 이동...")
            self.driver.get(self.config.GROUPWARE_URL)
            time.sleep(5)
            print("페이지 이동 완료")
            return True
        except Exception as e:
            raise Exception(f"페이지 이동 실패: {e}")

    def setup_card_interface(self, start_date, end_date, category=None):
        """카드 사용내역 인터페이스 설정"""
        try:
            print("카드 사용내역 설정 시작...")
            
            # 1. 카드 사용내역 버튼 클릭
            print("  1) 카드 사용내역 버튼 클릭")
            card_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "btnExpendInterfaceCard")))
            card_btn.click()
            time.sleep(3)
            
            # 2. 카드 선택 팝업 처리
            print("  2) 카드 선택 팝업 처리")
            main_window = self.driver.current_window_handle
            
            # 선택 버튼 클릭하여 새창 팝업 열기
            select_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "btnExpendCardInfoHelpPop")))
            # JavaScript로 클릭 (더 안정적)
            self.driver.execute_script("arguments[0].click();", select_btn)
            print("    선택 버튼 클릭 완료 (JavaScript)")
            time.sleep(3)  # 팝업 열림 대기 시간 증가
            
            # 새창으로 전환 (올바른 팝업 찾기)
            if not self._switch_to_popup_window(main_window):
                raise Exception("새창으로 전환 실패")
            
            # 팝업 로드 대기 (실패 시 예외 발생)
            if not self._wait_for_card_popup():
                raise Exception("카드 팝업 로드 실패: 팝업이 제대로 로드되지 않았습니다.")
            
            # 카테고리에 따른 카드 선택
            if category == "해외결제 법인카드":
                if not self._select_overseas_card():
                    raise Exception("해외결제 법인카드 선택 실패")
            else:
                if not self._select_default_card():
                    raise Exception("기본 카드 선택 실패")
            
            # 확인 버튼 클릭 후 메인 윈도우로 복귀
            try:
                # 여러 방법으로 확인 버튼 찾기 시도
                confirm_btn = None
                confirm_selectors = [
                    (By.ID, "btnConfirm"),
                    (By.XPATH, "//button[contains(text(), '확인')]"),
                    (By.XPATH, "//input[@type='button' and contains(@value, '확인')]"),
                    (By.XPATH, "//button[contains(@class, 'btn') and contains(text(), '확인')]"),
                ]
                
                for selector_type, selector_value in confirm_selectors:
                    try:
                        confirm_btn = self.wait.until(EC.element_to_be_clickable((selector_type, selector_value)))
                        print(f"    확인 버튼 발견: {selector_type}, {selector_value}")
                        break
                    except:
                        continue
                
                if not confirm_btn:
                    # 현재 URL과 페이지 소스 일부 확인
                    current_url = self.driver.current_url
                    print(f"    현재 팝업 URL: {current_url}")
                    print(f"    ⚠️ 확인 버튼을 찾을 수 없습니다. 팝업이 제대로 로드되지 않았을 수 있습니다.")
                    raise Exception("확인 버튼을 찾을 수 없습니다. 팝업이 제대로 로드되지 않았을 수 있습니다.")
                
                # JavaScript로 클릭
                self.driver.execute_script("arguments[0].click();", confirm_btn)
                print(f"    확인 버튼 클릭 완료 (JavaScript)")
                time.sleep(2)  # 팝업 닫힘 대기
                
            except Exception as confirm_error:
                print(f"    확인 버튼 클릭 실패: {confirm_error}")
                raise Exception(f"확인 버튼 클릭 실패: {confirm_error}")
            
            # 메인 윈도우로 복귀
            self.driver.switch_to.window(main_window)
            time.sleep(1)
            
            # 3. 날짜 입력 및 검색
            print(f"  3) 날짜 입력 및 검색: {start_date} ~ {end_date}")
            self._input_dates(start_date, end_date)
            
            search_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "btnExpendCardListSearch")))
            search_btn.click()
            time.sleep(5)
            
            # 4. 최신순 정렬
            print("  4) 최신순 정렬")
            self._click_latest_sort_button()
            
            print("카드 사용내역 설정 완료")
            return True
            
        except Exception as e:
            error_msg = str(e) if str(e) else "알 수 없는 오류"
            raise Exception(f"카드 사용내역 설정 실패: {error_msg}")

    def _switch_to_popup_window(self, main_window):
        """새창(팝업 윈도우)으로 전환 - 올바른 카드 선택 팝업 찾기"""
        try:
            print("    새창 전환")
            
            # 새창이 열릴 때까지 대기 (최대 10초)
            for i in range(10):
                windows = self.driver.window_handles
                if len(windows) > 1:
                    # 모든 창을 확인하여 올바른 카드 선택 팝업 찾기
                    for window in windows:
                        if window != main_window:
                            self.driver.switch_to.window(window)
                            current_url = self.driver.current_url
                            print(f"    발견된 팝업 창 URL: {current_url}")
                            
                            # 공지사항 팝업인 경우 닫고 계속 찾기
                            if "gwpOpenNoticePopup" in current_url or "notice" in current_url.lower():
                                print(f"    공지사항 팝업 발견 - 닫기")
                                self.driver.close()
                                self.driver.switch_to.window(main_window)
                                time.sleep(1)
                                continue
                            
                            # 카드 선택 팝업인 경우
                            if "UserCardInfoHelpPop" in current_url or "UserCardUsageHistoryPop" in current_url:
                                print(f"    올바른 카드 선택 팝업 발견!")
                                return True
                    
                    # 올바른 팝업을 찾지 못한 경우 첫 번째 팝업 사용 (추가 대기)
                    if len(windows) > 1:
                        for window in windows:
                            if window != main_window:
                                self.driver.switch_to.window(window)
                                print(f"    임시로 첫 번째 팝업으로 전환 (추가 대기 중...)")
                                time.sleep(2)  # 추가 대기
                                current_url = self.driver.current_url
                                if "UserCardInfoHelpPop" in current_url or "UserCardUsageHistoryPop" in current_url:
                                    print(f"    올바른 팝업 확인!")
                                    return True
                                elif "gwpOpenNoticePopup" in current_url:
                                    # 여전히 공지사항이면 닫고 계속
                                    print(f"    여전히 공지사항 팝업 - 닫기")
                                    self.driver.close()
                                    self.driver.switch_to.window(main_window)
                                    break
                
                time.sleep(1)
            
            print("    새창 전환 실패 - 카드 선택 팝업을 찾을 수 없음")
            return False
            
        except Exception as e:
            print(f"    새창 전환 오류: {e}")
            import traceback
            print(traceback.format_exc())
            return False

    def _wait_for_card_popup(self):
        """카드 팝업 로드 완료 대기"""
        try:
            print("    카드 팝업 로드 대기")
            
            # 현재 URL 확인
            current_url = self.driver.current_url
            print(f"    현재 팝업 URL: {current_url}")
            
            # URL에서 카드 팝업이 포함되어 있는지 확인 (UserCardInfoHelpPop 또는 UserCardUsageHistoryPop)
            if "UserCardInfoHelpPop" not in current_url and "UserCardUsageHistoryPop" not in current_url:
                print(f"    ⚠️ 카드 선택 팝업 URL이 아님: {current_url}")
                return False
            
            # 페이지 로드 대기
            time.sleep(3)
            
            # 여러 방법으로 카드 테이블 찾기 시도
            table_found = False
            table_selectors = [
                "#tblUserCardInfo",
                "table[id='tblUserCardInfo']",
                "#tblUserCardInfo table",
                "table.grid-content",
            ]
            
            for selector in table_selectors:
                try:
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    print(f"    카드 테이블 요소 발견: {selector}")
                    table_found = True
                    break
                except:
                    continue
            
            if not table_found:
                print(f"    ⚠️ 카드 테이블 요소를 찾을 수 없음")
                # 페이지 제목 확인
                try:
                    page_title = self.driver.title
                    print(f"    페이지 제목: {page_title}")
                except:
                    pass
                # 페이지 소스 일부 확인 (body 태그 내부)
                try:
                    body_html = self.driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")[:1000]
                    print(f"    페이지 body 일부: {body_html[:500]}...")
                except:
                    pass
                return False
            
            time.sleep(2)  # 추가 대기 시간 (동적 로딩 고려)
            
            # 카드 행이 실제로 있는지 확인 (여러 셀렉터 시도)
            card_rows = []
            row_selectors = [
                "#tblUserCardInfo .grid-content tbody tr",
                "#tblUserCardInfo tbody tr",
                "#tblUserCardInfo tr",
                "table[id='tblUserCardInfo'] tbody tr",
            ]
            
            for selector in row_selectors:
                try:
                    card_rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if card_rows:
                        print(f"    카드 행 발견: {selector} - {len(card_rows)}개")
                        break
                except:
                    continue
            
            if not card_rows:
                print("    ⚠️ 카드 테이블은 로드되었지만 카드 행이 없음")
                return False
            
            # 카드 개수 확인
            try:
                total_count = self.driver.find_element(By.ID, "txtShowCount").text.strip()
                print(f"    팝업 로드 완료 - 총 {total_count}개 카드, {len(card_rows)}개 행 발견")
            except:
                print(f"    팝업 로드 완료 - {len(card_rows)}개 카드 행 발견")
            
            return True
            
        except Exception as e:
            print(f"    팝업 대기 실패: {e}")
            import traceback
            print(f"    상세 오류: {traceback.format_exc()}")
            return False

    def _select_overseas_card(self):
        """해외결제 법인카드 선택"""
        try:
            print("    해외결제 법인카드 선택")
            
            # 카드 테이블의 모든 행 찾기
            card_rows = self.driver.find_elements(By.CSS_SELECTOR, "#tblUserCardInfo .grid-content tbody tr")
            print(f"    발견된 카드 행 수: {len(card_rows)}")
            
            # "해외결제 법인카드" 또는 "AI솔루션"이 포함된 카드 찾기
            for i, row in enumerate(card_rows, 1):
                try:
                    # 카드명이 있는 td 찾기 (두 번째 컬럼)
                    card_name_cells = row.find_elements(By.CSS_SELECTOR, "td")
                    if len(card_name_cells) >= 2:
                        card_name = card_name_cells[1].text.strip()
                        print(f"    행 {i}: 카드명 = {card_name}")
                        
                        # 해외결제 법인카드인지 확인
                        if "해외결제 법인카드" in card_name or "AI솔루션" in card_name:
                            # 체크박스 찾기 (첫 번째 td의 input.PUDDCheckBox)
                            checkbox = row.find_element(By.CSS_SELECTOR, "td:first-child input.PUDDCheckBox")
                            self.driver.execute_script("arguments[0].click();", checkbox)
                            print(f"    해외결제 법인카드 선택 완료: {card_name}")
                            time.sleep(1)
                            return True
                except Exception as row_error:
                    print(f"    행 {i} 처리 중 오류: {row_error}")
                    continue
            
            # 해외결제 카드를 찾지 못한 경우 두 번째 카드 선택 (일반적으로 두 번째가 해외결제 카드)
            print("    해외결제 카드를 이름으로 찾지 못함 - 두 번째 카드 선택 시도")
            if len(card_rows) >= 2:
                checkbox = card_rows[1].find_element(By.CSS_SELECTOR, "td:first-child input.PUDDCheckBox")
                self.driver.execute_script("arguments[0].click();", checkbox)
                print("    두 번째 카드 선택 완료")
                time.sleep(1)
                return True
            
            print("    해외결제 카드 선택 실패 - 첫 번째 카드로 대체")
            return self._select_default_card()
            
        except Exception as e:
            print(f"    해외결제 카드 선택 실패: {e} - 첫 번째 카드로 대체")
            import traceback
            print(traceback.format_exc())
            return self._select_default_card()

    def _select_default_card(self):
        """기본 카드 선택 (첫 번째 카드)"""
        try:
            print("    첫 번째 카드 선택")
            
            # 카드 테이블의 첫 번째 행 찾기
            card_rows = self.driver.find_elements(By.CSS_SELECTOR, "#tblUserCardInfo .grid-content tbody tr")
            if not card_rows:
                print("    카드 행을 찾을 수 없음")
                return False
            
            # 첫 번째 행의 체크박스 선택
            checkbox = card_rows[0].find_element(By.CSS_SELECTOR, "td:first-child input.PUDDCheckBox")
            self.driver.execute_script("arguments[0].click();", checkbox)
            print("    첫 번째 카드 선택 완료")
            time.sleep(1)
            return True
            
        except Exception as e:
            print(f"    기본 카드 선택 실패: {e}")
            return False
        
    def _click_latest_sort_button(self):
        """최신순 정렬 버튼 클릭"""
        try:
            print("    최신순 정렬 적용 중...")
            
            latest_label = self.wait.until(EC.element_to_be_clickable((By.XPATH, self.config.CARD_ELEMENTS["latest_sort_xpath"])))
            latest_label.click()
            time.sleep(2)
            print("    최신순 정렬 완료")
            return True
            
        except Exception as e:
            print(f"    최신순 정렬 실패: {e} - 계속 진행")
            return False

    def _input_dates(self, start_date, end_date):
        """날짜 입력"""
        try:
            # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
            formatted_start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
            formatted_end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
            
            print(f"    시작날짜 입력: {formatted_start}")
            
            # 시작 날짜 입력
            start_input = self.wait.until(EC.presence_of_element_located((By.ID, "txtExpendCardFromDate")))
            self._clear_and_input(start_input, formatted_start)
            time.sleep(2)
            
            print(f"    종료날짜 입력: {formatted_end}")
            
            # 종료 날짜 입력
            end_input = self.driver.find_element(By.ID, "txtExpendCardToDate")
            self._clear_and_input(end_input, formatted_end)
            time.sleep(2)
            
            # 검증
            actual_start = start_input.get_attribute('value')
            actual_end = end_input.get_attribute('value')
            print(f"    입력 확인 - 시작: {actual_start}, 종료: {actual_end}")
            
            return True
            
        except Exception as e:
            # JavaScript 백업 방법
            print(f"    키보드 입력 실패, JavaScript로 재시도: {e}")
            return self._input_dates_with_javascript(formatted_start, formatted_end)

    def _clear_and_input(self, element, value):
        """요소 클리어 후 값 입력"""
        element.click()
        time.sleep(0.5)
        element.send_keys(Keys.CONTROL + "a")
        time.sleep(0.3)
        element.send_keys(Keys.DELETE)
        time.sleep(0.3)
        element.send_keys(value)
        time.sleep(0.5)
        element.send_keys(Keys.ENTER)
        time.sleep(1)

    def _input_dates_with_javascript(self, formatted_start, formatted_end):
        """JavaScript를 사용한 날짜 입력"""
        try:
            js_script = f"""
            // 시작 날짜 설정
            var startInput = document.getElementById('txtExpendCardFromDate');
            startInput.value = "{formatted_start}";
            startInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            // 종료 날짜 설정
            var endInput = document.getElementById('txtExpendCardToDate');
            endInput.value = "{formatted_end}";
            endInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            return [startInput.value, endInput.value];
            """
            
            result = self.driver.execute_script(js_script)
            print(f"    JavaScript 입력 결과: 시작={result[0]}, 종료={result[1]}")
            time.sleep(2)
            return True
            
        except Exception as e:
            raise Exception(f"JavaScript 날짜 입력 실패: {e}")

    def process_single_record(self, data_row, record_index, total_records):
        """단일 레코드 처리"""
        try:
            print(f"\n레코드 {record_index}/{total_records} 처리 시작")
            print(f"   처리할 금액: {data_row.get('amount', '')}")
            
            # 1. 금액 매칭하여 체크박스 클릭
            print("   1) 금액 매칭 및 체크박스 클릭")
            success = self._find_and_click_checkbox(data_row.get('amount', ''))
            
            if not success:
                print(f"   금액 매칭 실패: {data_row.get('amount', '')}")
                return False
            
            # 2. 폼 데이터 입력
            print("   2) 폼 데이터 입력")
            self._input_form_data(data_row)
            
            # 3. 저장
            print("   3) 저장")
            self._click_save(data_row)
            
            print(f"   레코드 {record_index} 완료")
            return True
            
        except Exception as e:
            print(f"   레코드 {record_index} 실패: {e}")
            return False

    def _find_and_click_checkbox(self, target_amount):
        """금액 매칭하여 체크박스 클릭"""
        try:
            clean_target = self._clean_amount(str(target_amount))
            print(f"      찾는 금액: {clean_target}")
            
            # 현재 페이지의 금액 셀들 찾기
            amount_cells = self.driver.find_elements(By.CSS_SELECTOR, "td.td_ri span.fwb")
            print(f"      총 {len(amount_cells)}개 금액 셀 발견")
            
            for i, cell in enumerate(amount_cells):
                cell_amount = self._clean_amount(cell.text)
                print(f"      웹 금액 {i+1}: {cell.text} -> {cell_amount}")
                print(f"      비교: '{cell_amount}' == '{clean_target}' -> {cell_amount == clean_target}")
                
                if cell_amount == clean_target:
                    print(f"      금액 매칭! 행 {i+1}")
                    print(f"      행 {i+1}을 처리합니다")
                    
                    # 체크박스 클릭 (JavaScript로 강제 클릭)
                    row_index = i + 1
                    
                    # 성공한 방법: label 클릭
                    checkbox_label_xpath = f"/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[2]/div/div[3]/div[2]/table/tbody/tr[{row_index}]/td[1]/span/label"
                    checkbox_label = self.wait.until(EC.presence_of_element_located((By.XPATH, checkbox_label_xpath)))
                    # 스크롤하여 요소를 뷰포트로 이동
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox_label)
                    time.sleep(0.5)
                    # JavaScript로 강제 클릭
                    self.driver.execute_script("arguments[0].click();", checkbox_label)
                    print(f"      체크박스 클릭 완료 (JavaScript)")
                    time.sleep(1)
                    return True
            
            print(f"      현재 페이지에서 매칭되는 금액을 찾지 못함")
            return False
            
        except Exception as e:
            print(f"      체크박스 클릭 실패: {e}")
            return False

    def _is_row_already_processed(self, row_index):
        """해당 행이 이미 처리되었는지 확인 (지출결의 정보 컬럼 확인)"""
        try:
            # 해당 행의 모든 td 확인하여 지출결의 정보 컬럼 찾기
            row_xpath = f"/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[2]/div/div[3]/div[2]/table/tbody/tr[{row_index + 1}]"
            
            try:
                row_element = self.driver.find_element(By.XPATH, row_xpath)
                
                # 모든 td 요소 확인
                all_tds = row_element.find_elements(By.CSS_SELECTOR, "td")
                
                # [DEBUG] 처리 여부 확인 로그 - 추후 삭제 가능
                print(f"        행 {row_index+1} 총 {len(all_tds)}개 컬럼 발견")
                
                # 지출결의 정보는 일반적으로 오른쪽 마지막 컬럼에 있음
                # 하지만 폼 영역의 데이터를 읽고 있으므로, 실제로는 다른 방법으로 확인 필요
                # 일단 마지막 td의 텍스트가 폼 입력값(표준적요, 증빙유형 등)과 다른지 확인
                
                # 마지막 td가 실제 지출결의 정보 컬럼인지 확인
                # 폼 영역의 데이터(표준적요, 증빙유형, 프로젝트, 적요)가 포함되어 있으면 폼 영역임
                last_td = all_tds[-1] if all_tds else None
                
                if not last_td:
                    print(f"        행 {row_index+1}은 아직 처리되지 않음 (td 없음)")
                    return False
                
                td_text = last_td.text.strip()
                
                # [DEBUG] 처리 여부 확인 로그 - 추후 삭제 가능
                print(f"        행 {row_index+1} 마지막 컬럼 내용: '{td_text[:100]}...' (전체 길이: {len(td_text)})")
                
                # 폼 영역의 데이터 패턴 확인 (표준적요, 증빙유형 등이 있으면 폼 영역의 데이터임)
                # 실제 반영 여부는 "지출결의 정보" 컬럼을 확인해야 하는데, 현재는 폼 영역을 읽고 있음
                # 폼 영역의 데이터가 있으면 이것은 실제 반영 정보가 아니므로 미처리로 처리
                if "표준적요 :" in td_text and "증빙유형 :" in td_text:
                    # 폼 영역의 데이터는 실제 반영 정보가 아님 - 미처리로 판단
                    print(f"        행 {row_index+1} - 폼 영역 데이터 감지 (실제 반영 정보 아님), 미처리로 처리")
                    return False
                
                # 실제 반영된 정보는 다른 형태일 수 있음
                # 일단 "-" 또는 매우 짧은 텍스트면 미처리
                if not td_text or td_text == "-" or len(td_text) < 5:
                    print(f"        행 {row_index+1}은 아직 처리되지 않음 (지출결의 정보 없음)")
                    return False
                
                # 폼 입력 패턴이 있으면 실제 반영 정보가 아닐 수 있음
                # 일단 항상 미처리로 판단하도록 변경 (실제 반영 여부를 정확히 확인할 수 없으므로)
                print(f"        행 {row_index+1} - 처리 여부 확인 불가, 일단 미처리로 간주")
                return False
                    
            except Exception as e:
                # [DEBUG] 처리 여부 확인 로그 - 추후 삭제 가능
                print(f"        ❓ 행 {row_index+1} 확인 실패: {e} - 미처리로 간주")
                return False
            
        except Exception as e:
            print(f"        ❓ 처리 여부 확인 실패: {e} - 미처리로 간주")
            return False

    def _clean_amount(self, amount_text):
        """금액 텍스트 정리"""
        try:
            if not amount_text:
                return "0"
            
            # 모든 특수문자, 공백, 쉼표 제거
            cleaned = str(amount_text).replace(',', '').replace(' ', '').replace('원', '').replace('₩', '')
            
            # 소숫점 처리
            if '.' in cleaned:
                cleaned = cleaned.split('.')[0]
            
            # 숫자가 아닌 문자 제거
            cleaned = re.sub(r'[^\d]', '', cleaned)
            
            # 빈 문자열이면 0
            if not cleaned:
                return "0"
                
            return str(int(cleaned))
        except:
            return "0"

    def _find_matching_data(self, web_amount, processed_data):
        """웹페이지 금액과 매칭되는 CSV 데이터 찾기"""
        try:
            web_amount_clean = int(self._clean_amount(web_amount))
            
            # 정확히 매칭되는 데이터 먼저 찾기
            for data in processed_data:
                if data.get('_used'):  # 이미 사용된 데이터는 건너뛰기
                    continue
                    
                csv_amount = int(self._clean_amount(data.get('amount', 0)))
                if csv_amount == web_amount_clean:
                    data['_used'] = True  # 사용됨 표시
                    return data
            
            # 정확한 매칭이 없으면 가장 가까운 금액 찾기 (차이가 100원 이내)
            closest_data = None
            min_diff = float('inf')
            
            for data in processed_data:
                if data.get('_used'):  # 이미 사용된 데이터는 건너뛰기
                    continue
                    
                csv_amount = int(self._clean_amount(data.get('amount', 0)))
                diff = abs(csv_amount - web_amount_clean)
                
                if diff < min_diff and diff <= 100:  # 100원 이내 차이만 허용
                    min_diff = diff
                    closest_data = data
            
            if closest_data:
                closest_data['_used'] = True  # 사용됨 표시
                return closest_data
                
            return None
            
        except Exception as e:
            print(f"      데이터 매칭 실패: {e}")
            return None

    def _input_form_data(self, data_row):
        """폼 데이터 입력"""
        try:
            # 표준 적요 입력
            if data_row.get('standard_summary'):
                print(f"      표준적요: {data_row['standard_summary']}")
                summary_input = self.driver.find_element(By.ID, "txtExpendCardDispSummary")
                summary_input.clear()
                summary_input.send_keys(data_row['standard_summary'])
                summary_input.send_keys(Keys.ENTER)
                time.sleep(1)
            
            # 증빙 유형 입력
            if data_row.get('evidence_type'):
                print(f"      증빙유형: {data_row['evidence_type']}")
                evidence_input = self.driver.find_element(By.ID, "txtExpendCardDispAuth")
                evidence_input.clear()
                evidence_input.send_keys(data_row['evidence_type'])
                evidence_input.send_keys(Keys.ENTER)
                time.sleep(1)
            
            # 적요 입력
            if data_row.get('note'):
                print(f"      적요: {data_row['note']}")
                note_input = self.driver.find_element(By.ID, "txtExpendCardDispNote")
                note_input.clear()
                note_input.send_keys(data_row['note'])
                note_input.send_keys(Keys.ENTER)
                time.sleep(1)
            
            # 프로젝트 입력
            if data_row.get('project'):
                print(f"      프로젝트: {data_row['project']}")
                project_input = self.driver.find_element(By.ID, "txtExpendCardDispProject")
                project_input.clear()
                project_input.send_keys(data_row['project'])
                project_input.send_keys(Keys.ENTER)
                time.sleep(1)
            
            return True
            
        except Exception as e:
            raise Exception(f"폼 데이터 입력 실패: {e}")

    def _input_default_form_data(self):
        """기본 폼 데이터 입력 (엑셀 데이터와 매칭하지 않고)"""
        try:
            # 표준 적요 입력 (기본값)
            print(f"      표준적요: 156 (기본값)")
            summary_input = self.driver.find_element(By.ID, "txtExpendCardDispSummary")
            summary_input.clear()
            summary_input.send_keys("156")
            summary_input.send_keys(Keys.ENTER)
            time.sleep(1)
            
            # 증빙 유형 입력 (기본값)
            print(f"      증빙유형: 003 (기본값)")
            evidence_input = self.driver.find_element(By.ID, "txtExpendCardDispAuth")
            evidence_input.clear()
            evidence_input.send_keys("003")
            evidence_input.send_keys(Keys.ENTER)
            time.sleep(1)
            
            # 적요 입력 (기본값)
            print(f"      적요: OpenAI_GPT API 토큰 비용 (기본값)")
            note_input = self.driver.find_element(By.ID, "txtExpendCardDispNote")
            note_input.clear()
            note_input.send_keys("OpenAI_GPT API 토큰 비용")
            note_input.send_keys(Keys.ENTER)
            time.sleep(1)
            
            # 프로젝트 입력 (기본값)
            print(f"      프로젝트: SAAS3002 (기본값)")
            project_input = self.driver.find_element(By.ID, "txtExpendCardDispProject")
            project_input.clear()
            project_input.send_keys("SAAS3002")
            project_input.send_keys(Keys.ENTER)
            time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"      기본 폼 데이터 입력 실패: {e}")
            return False

    def _click_save(self, data_row=None):
        """저장 버튼 클릭"""
        max_retry = 2
        
        for retry in range(max_retry):
            try:
                save_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "btnExpendCardInfoSave")))
                save_btn.click()
                
                # 저장 후 잠시 대기
                time.sleep(3)
                
                # Alert 확인
                try:
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    print(f"      Alert 발생: {alert_text}")
                    alert.accept()  # alert 확인 버튼 클릭
                    time.sleep(1)
                    
                    # Alert 내용에 따라 해당 필드 재입력
                    if "표준적요" in alert_text and data_row:
                        print(f"      표준적요 재입력 시도")
                        self._retry_input_field("standard_summary", data_row.get('standard_summary', ''))
                    elif "증빙유형" in alert_text and data_row:
                        print(f"      증빙유형 재입력 시도")
                        self._retry_input_field("evidence_type", data_row.get('evidence_type', ''))
                    elif "적요" in alert_text and data_row:
                        print(f"      적요 재입력 시도")
                        self._retry_input_field("note", data_row.get('note', ''))
                    elif "프로젝트" in alert_text and data_row:
                        print(f"      프로젝트 재입력 시도")
                        self._retry_input_field("project", data_row.get('project', ''))
                    
                    # 재입력 후 다시 저장 시도
                    continue
                    
                except Exception:
                    # alert가 없으면 저장 성공 (체크박스는 자동으로 해제됨)
                    print(f"      저장 완료")
                    return True
            
            except Exception as e:
                print(f"      저장 시도 {retry + 1} 실패: {e}")
                if retry == max_retry - 1:
                    raise Exception(f"저장 버튼 클릭 실패: {e}")
                time.sleep(2)
        
        return True

    def _retry_input_field(self, field_type, value):
        """특정 필드 재입력"""
        try:
            if not value:
                print(f"        {field_type} 값이 없어 재입력 불가")
                return
            
            field_mapping = {
                "standard_summary": "txtExpendCardDispSummary",
                "evidence_type": "txtExpendCardDispAuth", 
                "note": "txtExpendCardDispNote",
                "project": "txtExpendCardDispProject"
            }
            
            field_id = field_mapping.get(field_type)
            if not field_id:
                return
            
            print(f"        {field_type} 재입력: {value}")
            
            # 필드 클리어 후 재입력
            field_input = self.driver.find_element(By.ID, field_id)
            field_input.clear()
            time.sleep(0.5)
            field_input.send_keys(value)
            field_input.send_keys(Keys.ENTER)
            time.sleep(1)
            
            print(f"        {field_type} 재입력 완료")
            
        except Exception as e:
            print(f"        {field_type} 재입력 실패: {e}")
    
    def run_automation(self, processed_data, progress_callback=None, user_id="", password=""):
        """메인 자동화 실행 메서드"""
        try:
            print("자동화 프로세스 시작")
            
            # 1. 브라우저 설정
            if progress_callback:
                progress_callback("브라우저를 시작하는 중...")
            self.setup_driver()
            
            # 2. 로그인
            if progress_callback:
                progress_callback("그룹웨어에 로그인하는 중...")
            self.login_to_groupware(user_id, password)
            
            # 3. 데이터 정보 확인
            total_records = len(processed_data)
            if not processed_data:
                raise Exception("처리할 데이터가 없습니다.")
            
            start_date = processed_data[0].get('start_date', '')
            end_date = processed_data[0].get('end_date', '')
            
            print(f"총 레코드 수: {total_records}")
            print(f"처리 기간: {start_date} ~ {end_date}")
            
            # 4. 페이지 이동
            self.navigate_to_expense_page()
            
            # 5. 데이터 처리 루프
            processed_count = 0
            round_number = 1
            
            while processed_count < total_records:
                print(f"\n처리 라운드 {round_number} 시작 (진행률: {processed_count}/{total_records})")
                
                if progress_callback:
                    progress_callback(f"라운드 {round_number} 처리 중... ({processed_count}/{total_records})")
                
                # 카드 사용내역 설정 (카테고리 정보 전달)
                category = processed_data[0].get('category', '')
                self.setup_card_interface(start_date, end_date, category)
                
                # 현재 페이지에 있는 모든 금액을 자동으로 처리
                round_processed = 0
                
                # 현재 페이지의 모든 테이블 행 확인
                table_rows = self.driver.find_elements(By.CSS_SELECTOR, "#tblExpendCardList tbody tr")
                total_rows = len(table_rows)
                print(f"   현재 페이지에서 {total_rows}개 행 발견")
                
                # 저장된 항목의 인덱스를 추적하기 위한 리스트
                saved_row_indices = []
                
                # 각 행을 순차적으로 처리
                for i in range(total_rows):
                    try:
                        # 매번 새로 행들을 찾기 (Stale Element 방지)
                        current_table_rows = self.driver.find_elements(By.CSS_SELECTOR, "#tblExpendCardList tbody tr")
                        if i >= len(current_table_rows):
                            print(f"   행 {i+1}: 행이 더 이상 존재하지 않음")
                            break
                        
                        row = current_table_rows[i]
                        # 각 행에서 금액 컬럼(td.td_ri) 찾기
                        amount_td = row.find_element(By.CSS_SELECTOR, "td.td_ri")
                        
                        # td 안의 모든 span 확인
                        spans = amount_td.find_elements(By.TAG_NAME, "span")
                        
                        # [DEBUG] 디버깅을 위한 상세 로그 - 추후 삭제 가능
                        span_info = []
                        for idx, span in enumerate(spans):
                            span_class = span.get_attribute("class") or ""
                            span_text = span.text.strip()
                            span_info.append(f"span[{idx}]: class='{span_class}', text='{span_text}'")
                        
                        # 세 번째 span (최종금액, 부가세 제외) 사용
                        # CSV 데이터는 부가세 제외 금액이므로 매칭해야 함
                        amount_text = ""
                        if spans:
                            # 세 번째 span이 있으면 사용 (부가세 제외 최종금액)
                            if len(spans) >= 3:
                                amount_text = spans[2].text.strip()
                                print(f"      [DEBUG] 세 번째 span 사용 (부가세 제외 최종금액): {amount_text}")
                            # 두 개 이하인 경우 첫 번째 span.fwb 사용 (fallback)
                            else:
                                for span in spans:
                                    span_class = span.get_attribute("class") or ""
                                    if "fwb" in span_class:
                                        amount_text = span.text.strip()
                                        break
                                
                                if not amount_text and spans:
                                    amount_text = spans[0].text.strip()
                        
                        cell_amount = self._clean_amount(amount_text)
                        # [DEBUG] 금액 추출 로그 - 추후 삭제 가능
                        print(f"   행 {i+1} 금액: '{amount_text}' -> {cell_amount} (td 내 span 개수: {len(spans)})")
                        if len(span_info) > 0:
                            print(f"      [DEBUG] span 상세: {' | '.join(span_info[:3])}")  # 처음 3개만 출력
                        
                        # 이미 처리된 행인지 확인
                        # [DEBUG] 처리 여부 확인 - 추후 삭제 가능
                        if self._is_row_already_processed(i):
                            print(f"   행 {i+1}은 이미 처리됨 - 건너뛰기")
                            continue
                        
                        print(f"   행 {i+1}을 처리합니다")
                        
                        # 체크박스 클릭 (JavaScript로 강제 클릭)
                        row_index = i + 1
                        checkbox_label_xpath = f"/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[2]/div/div[3]/div[2]/table/tbody/tr[{row_index}]/td[1]/span/label"
                        try:
                            checkbox_label = self.wait.until(EC.presence_of_element_located((By.XPATH, checkbox_label_xpath)))
                            # 스크롤하여 요소를 뷰포트로 이동
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox_label)
                            time.sleep(0.5)
                            # JavaScript로 강제 클릭
                            self.driver.execute_script("arguments[0].click();", checkbox_label)
                            print(f"   체크박스 클릭 완료 (JavaScript)")
                            time.sleep(1)
                        except Exception as click_error:
                            print(f"   체크박스 클릭 시도 실패: {click_error}")
                            raise
                        
                        # 현재 행의 금액으로 CSV 데이터와 매칭
                        # [DEBUG] 매칭 시도 로그 - 추후 삭제 가능
                        print(f"   매칭 시도: 웹 금액={cell_amount}")
                        matching_data = self._find_matching_data(amount_text, processed_data)
                        
                        if matching_data:
                            print(f"   ✅ 매칭된 데이터 찾음: 금액={matching_data.get('amount')}, 적요={matching_data.get('note')}, 프로젝트={matching_data.get('project')}")
                            # 실제 CSV 데이터로 폼 입력
                            self._input_form_data(matching_data)
                        else:
                            print(f"   ⚠️ 매칭되는 데이터 없음 - 기본값 사용 (웹 금액: {cell_amount})")
                            # 매칭되는 데이터가 없으면 기본값 사용
                            self._input_default_form_data()
                        
                        # 저장 (저장 후 체크박스는 자동으로 해제됨)
                        self._click_save(matching_data if matching_data else None)
                        
                        # 저장 완료 후 DOM 업데이트 대기 (반영을 위해 충분한 대기 필요)
                        time.sleep(2)  # 저장 후 충분한 대기
                        
                        # [DEBUG] 저장 후 체크박스 상태 확인 - 추후 삭제 가능
                        try:
                            checkbox = self.driver.find_element(By.XPATH, f"/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[2]/div/div[3]/div[2]/table/tbody/tr[{row_index}]/td[1]/span/input")
                            is_checked = checkbox.is_selected()
                            print(f"      [DEBUG] 행 {i+1} 저장 후 체크박스 상태: {'체크됨' if is_checked else '체크 해제됨'}")
                        except Exception as check_err:
                            print(f"      [DEBUG] 행 {i+1} 저장 후 체크박스 상태 확인 실패: {check_err}")
                        
                        # [DEBUG] 행 처리 완료 로그 - 추후 삭제 가능
                        print(f"   행 {i+1} 처리 완료")
                        # 저장된 행 인덱스 추적
                        saved_row_indices.append(i + 1)
                        round_processed += 1
                        processed_count += 1
                        
                    except Exception as e:
                        print(f"   행 {i+1} 처리 중 오류: {e}")
                        continue
                
                print(f"라운드 {round_number} 완료: {round_processed}개 처리됨")
                
                # 처리된 데이터가 있으면 저장된 항목만 체크 후 반영
                if round_processed > 0:
                    has_next_page = self._check_has_next_page()
                    
                    print("저장된 항목만 체크 및 반영 시작...")
                    
                    # [DEBUG] 반영 전 체크박스 상태 확인 - 추후 삭제 가능
                    try:
                        all_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[name='inp_CardChk']")
                        checked_count_before = sum(1 for cb in all_checkboxes if cb.is_selected())
                        print(f"[DEBUG] 반영 전 체크된 항목 수: {checked_count_before}/{len(all_checkboxes)}")
                    except Exception as check_err:
                        print(f"[DEBUG] 체크박스 상태 확인 실패: {check_err}")
                    
                    # 저장된 항목만 개별 체크 (저장된 행 인덱스 목록 사용)
                    if self._check_saved_items_only(saved_row_indices):
                        
                        if self._click_apply_button():
                            print(f"{round_processed}개 데이터 반영 완료")
                            time.sleep(2)  # 반영 완료 후 짧은 대기
                            
                            # 다음 페이지 확인
                            if not has_next_page:
                                print("다음 페이지가 없어 작업을 종료합니다")
                                break
                            
                            if not has_next_page:
                                print("다음 페이지가 없어 작업을 종료합니다")
                                break
                            else:
                                # 다음 페이지로 이동
                                print("다음 페이지로 이동 중...")
                                try:
                                    next_page_btn = self.driver.find_element(By.XPATH, "//div[@id='tblExpendCardList_paginate']//a[@class='paginate_button next' and not(contains(@class, 'disabled'))]")
                                    self.driver.execute_script("arguments[0].click();", next_page_btn)
                                    print("다음 페이지로 이동 완료")
                                    time.sleep(3)  # 페이지 로드 대기
                                except Exception as next_page_error:
                                    print(f"다음 페이지 이동 실패: {next_page_error}")
                                    break
                        else:
                            print("반영 실패")
                            break
                    else:
                        print("전체 체크박스 클릭 실패")
                        break
                else:
                    print("현재 페이지에서 더 이상 처리할 데이터가 없어 작업을 종료합니다")
                    break
                    
                if processed_count >= total_records:
                    print("모든 데이터 처리 완료")
                    break
                
                round_number += 1
            
            print("모든 작업 완료!")
            # [DEBUG] 헤드리스 모드에서는 브라우저가 보이지 않으므로 메시지 제거 - 추후 삭제 가능
            if progress_callback:
                progress_callback("모든 작업이 완료되었습니다!")
            
        except Exception as e:
            print(f"자동화 실패: {e}")
            if progress_callback:
                progress_callback(f"작업 중 오류 발생: {str(e)}")
            # [DEBUG] 헤드리스 모드에서는 브라우저가 보이지 않으므로 메시지 제거 - 추후 삭제 가능
            raise e
        
    def _check_has_next_page(self):
        """다음 페이지가 있는지 확인"""
        try:
            print("페이지네이션 확인 중...")
            pagination_links = self.driver.find_elements(By.XPATH, "//div[@id='tblExpendCardList_paginate']//a")
            max_idx = max(int(link.get_attribute("data-dt-idx")) for link in pagination_links if link.get_attribute("data-dt-idx"))
            
            print(f"최대 data-dt-idx: {max_idx}")
            
            if max_idx <= 2:
                print("다음 페이지 없음 (1페이지만 존재)")
                return False
            else:
                print(f"다음 페이지 존재 (max_idx={max_idx})")
                return True
        except Exception as e:
            print(f"페이지네이션 확인 실패: {e}")
            return True
        
    def _click_apply_button(self):
        """반영 버튼 클릭"""
        try:
            print("반영 버튼 클릭...")
            
            apply_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, self.config.CARD_ELEMENTS["apply_btn"])))
            apply_btn.click()
            print("반영 버튼 클릭 완료")
            
            time.sleep(2)
            
            if self._wait_for_apply_completion():
                print("반영 완료")
                return True
            else:
                print("반영 대기 중 오류 발생")
                return False
            
        except Exception as e:
            print(f"반영 버튼 클릭 실패: {e}")
            return False    
    
    def _wait_for_apply_completion(self):
        """반영 진행률 팝업이 사라질 때까지 대기"""
        try:
            print("반영 진행률 팝업 대기 중...")
            
            time.sleep(3)
            
            popup_selectors = [
                (By.ID, "PLP_divMainProgPop"),
                (By.CSS_SELECTOR, "div[id='PLP_divMainProgPop']"),
                (By.XPATH, "//div[@id='PLP_divMainProgPop']")
            ]
            
            popup_appeared = False
            for selector_type, selector in popup_selectors:
                try:
                    popup = self.driver.find_element(selector_type, selector)
                    if popup.is_displayed():
                        popup_appeared = True
                        print("반영 진행률 팝업 감지됨")
                        break
                except:
                    continue
            
            if not popup_appeared:
                print("반영 팝업이 감지되지 않음 - 즉시 완료된 것으로 판단")
                time.sleep(5)
                return True
            
            max_wait_time = 120   
            wait_count = 0
            
            while wait_count < max_wait_time:
                try:
                    progress_element = self.driver.find_element(By.ID, "PLP_txtProgValue")
                    progress_text = progress_element.text.strip()
                    print(f"반영 진행률: {progress_text}")
                    
                    try:
                        total_count = self.driver.find_element(By.ID, "PLP_txtFullCnt").text.strip()
                        error_count = self.driver.find_element(By.ID, "PLP_txtErrorCnt").text.strip()
                        print(f"총 {total_count}건 (실패 {error_count}건)")
                    except:
                        pass
                    
                    popup_still_exists = False
                    for selector_type, selector in popup_selectors:
                        try:
                            popup = self.driver.find_element(selector_type, selector)
                            if popup.is_displayed():
                                popup_still_exists = True
                                break
                        except:
                            continue
                    
                    if not popup_still_exists:
                        print("반영 팝업이 사라짐 - 반영 완료!")
                        time.sleep(3)  # 반영 완료 후 추가 대기
                        return True
                    
                    time.sleep(2)
                    wait_count += 2
                    
                except Exception as e:
                    print(f"팝업 요소 접근 실패 (사라진 것으로 판단): {e}")
                    time.sleep(2)
                    return True
            
            print("반영 대기 시간 초과 (5분)")
            return False
            
        except Exception as e:
            print(f"반영 완료 대기 실패: {e}")
            return False

    def _check_saved_items_only(self, saved_row_indices):
        """저장된 항목만 체크"""
        try:
            print(f"저장된 항목 {len(saved_row_indices)}개 체크 시작...")
            
            checked_count = 0
            for row_index in saved_row_indices:
                try:
                    # 저장된 행의 체크박스만 클릭
                    checkbox_label_xpath = f"/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[2]/div/div[3]/div[2]/table/tbody/tr[{row_index}]/td[1]/span/label"
                    checkbox_label = self.wait.until(EC.presence_of_element_located((By.XPATH, checkbox_label_xpath)))
                    # 스크롤하여 요소를 뷰포트로 이동
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox_label)
                    time.sleep(0.3)
                    # JavaScript로 강제 클릭
                    self.driver.execute_script("arguments[0].click();", checkbox_label)
                    checked_count += 1
                except Exception as check_err:
                    print(f"   행 {row_index} 체크 실패: {check_err}")
            
            time.sleep(1)
            print(f"저장된 항목 {checked_count}개 체크 완료")
            
            # [DEBUG] 체크 후 상태 확인 - 추후 삭제 가능
            try:
                all_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[name='inp_CardChk']")
                checked_count_after = sum(1 for cb in all_checkboxes if cb.is_selected())
                print(f"[DEBUG] 저장된 항목 체크 후 체크된 항목 수: {checked_count_after}/{len(all_checkboxes)}")
            except Exception as check_err:
                print(f"[DEBUG] 체크박스 상태 확인 실패: {check_err}")
            
            return checked_count > 0
            
        except Exception as e:
            print(f"저장된 항목 체크 실패: {e}")
            return False

    def _click_select_all_checkbox(self):
        """전체 체크박스 클릭"""
        try:
            print("전체 체크박스 클릭...")
            
            # 성공한 셀렉터 사용
            select_all_btn = self.wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[2]/div/div[3]/div[1]/div/table/thead/tr/th[1]/input")))
            # 스크롤하여 요소를 뷰포트로 이동
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", select_all_btn)
            time.sleep(0.5)
            # JavaScript로 강제 클릭
            self.driver.execute_script("arguments[0].click();", select_all_btn)
            time.sleep(2)
            
            print("전체 체크박스 클릭 완료 (JavaScript)")
            return True
            
        except Exception as e:
            print(f"전체 체크박스 클릭 실패: {e}")
            return False

    def cleanup(self):
        """리소스 정리"""
        try:
            if self.driver:
                self.driver.quit()
                print("브라우저 종료 완료")
        except Exception as e:
            print(f"브라우저 종료 중 오류: {e}")
