from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import os
from backend.data_collection.config import ElementConfig, DateConfig

class DataManager:
    """데이터 수집 설정 및 다운로드 관리 클래스"""
    
    def __init__(self, login_manager):
        self.login_manager = login_manager
    
    def setup_call_data_collection(self, company_name, start_date=None, end_date=None, download=False):
        """CALL 계정 데이터 수집 설정 및 다운로드 (빠른 재시도 로직 포함)"""
        session = self.login_manager.get_active_session(company_name, "call")
        if not session:
            print(f"{company_name} CALL 세션이 없습니다")
            return False
        
        driver = session['driver']
        config = session['account_data']['config']
        wait = WebDriverWait(driver, 10)
        
        print(f"{company_name} 데이터 수집 설정 시작")
        
        def retry_click(selector, selector_type="css", max_retries=3):
            """클릭 재시도 함수"""
            for attempt in range(max_retries):
                try:
                    # 로딩 마스크 대기
                    self._wait_for_masks(driver, timeout=2)
                    
                    if selector_type == "xpath":
                        element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    else:
                        element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    
                    # JavaScript로 클릭 시도
                    driver.execute_script("arguments[0].click();", element)
                    time.sleep(0.5)
                    return True
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    else:
                        raise e
        
        try:
            # 회사 선택
            company_text = config.get('company_text', company_name)
            retry_click(f"//span[contains(text(), '{company_text}')]", "xpath")
            time.sleep(1)
            
            # 콜데이터 선택
            retry_click("//span[contains(text(), '콜데이터')]", "xpath")
            time.sleep(1)
            
            # 아웃바운드 설정
            outbound_selector = config.get('outbound_selector', "#uxtagfield-2171-inputEl")
            retry_click(outbound_selector)
            time.sleep(0.3)
            
            # 아웃바운드 값 선택
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, outbound_selector)))
            element.send_keys(Keys.ARROW_DOWN, Keys.ENTER)
            
            # 호상태 설정
            call_status_selector = config.get('call_status_selector', "#uxtagfield-2172-inputEl")
            
            # 아웃바운드 드롭다운이 완전히 닫힐 때까지 대기
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(1.5)
            
            # 호상태 입력 필드가 나타날 때까지 대기 (ExtJS 위젯 구조 고려)
            call_status_element = None
            try:
                # 먼저 부모 컨테이너가 준비될 때까지 대기
                parent_selector = "#uxtagfield-2172-listWrapper"
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, parent_selector))
                )
                
                # 그 다음 실제 입력 필드 대기
                call_status_element = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, call_status_selector))
                )
            except Exception as e:
                print(f"⚠️ {company_name} - 호상태 입력 필드를 찾을 수 없음: {str(e)[:100]}")
                # 대체 셀렉터 시도
                alternative_selectors = [
                    "input[id='uxtagfield-2172-inputEl']",
                    "input.x-tagfield-input-field[id*='2172']",
                    "#uxtagfield-2172-inputEl",
                    "[id='uxtagfield-2172-inputEl']"
                ]
                for alt_selector in alternative_selectors:
                    try:
                        call_status_element = driver.find_element(By.CSS_SELECTOR, alt_selector)
                        call_status_selector = alt_selector
                        break
                    except:
                        continue
                
                if not call_status_element:
                    raise Exception(f"모든 셀렉터로 요소를 찾을 수 없음. 시도한 셀렉터: {call_status_selector}, {alternative_selectors}")
            
            # 클릭 가능할 때까지 추가 대기 (ExtJS 위젯은 부모 요소 클릭이 더 안정적)
            try:
                # ExtJS 위젯의 경우 부모 컨테이너를 클릭하는 것이 더 안정적
                parent_container = driver.find_element(By.CSS_SELECTOR, "#uxtagfield-2172-listWrapper")
                driver.execute_script("""
                    var container = arguments[0];
                    container.scrollIntoView({block: 'center', behavior: 'smooth'});
                    container.click();
                """, parent_container)
                time.sleep(0.5)
                
                # 입력 필드가 활성화될 때까지 대기
                call_status_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, call_status_selector))
                )
                # 입력 필드에 포커스
                driver.execute_script("arguments[0].focus();", call_status_element)
                time.sleep(0.3)
            except Exception as click_e:
                print(f"⚠️ {company_name} - 컨테이너 클릭 실패, 입력 필드 직접 클릭 시도: {str(click_e)[:100]}")
                # 직접 입력 필드 클릭
                driver.execute_script("""
                    var element = arguments[0];
                    element.scrollIntoView({block: 'center'});
                    element.focus();
                    element.click();
                """, call_status_element)
                time.sleep(0.5)
            
            # 호상태 값 선택
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, call_status_selector)))
            actions = ActionChains(driver)
            for _ in range(17):
                actions.send_keys(Keys.ARROW_DOWN).perform()
                time.sleep(0.05)
            actions.send_keys(Keys.ENTER).perform()
            time.sleep(0.5)
            
            # 날짜 설정 (헤드리스 최적화 - JavaScript 우선)
            if start_date and end_date:
                try:
                    start_selector = config['start_date_selector']
                    end_selector = config['end_date_selector']
                    driver.execute_script("""
                        var startSelector = arguments[0];
                        var endSelector = arguments[1];
                        var startDate = arguments[2];
                        var endDate = arguments[3];
                        var startInput = document.querySelector(startSelector);
                        var endInput = document.querySelector(endSelector);
                        if (startInput) {
                            startInput.value = startDate;
                            startInput.dispatchEvent(new Event('change', {bubbles: true}));
                        }
                        if (endInput) {
                            endInput.value = endDate;
                            endInput.dispatchEvent(new Event('change', {bubbles: true}));
                        }
                    """, start_selector, end_selector, start_date, end_date)
                    time.sleep(1)
                except Exception as js_error:
                    # JavaScript 실패 시 Selenium 방식으로 fallback
                    print(f"⚠️ {company_name} - JavaScript 날짜 설정 실패, Selenium 방식으로 재시도...")
                    try:
                        if start_date:
                            start_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['start_date_selector'])))
                            start_input.clear()
                            start_input.send_keys(start_date)
                        if end_date:
                            end_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['end_date_selector'])))
                            end_input.clear()
                            end_input.send_keys(end_date)
                    except Exception as date_error:
                        print(f"❌ {company_name} - 날짜 설정 실패: {str(date_error)[:100]}")
                        import traceback
                        traceback.print_exc()
            
            # 검색 실행 (JavaScript 방식으로 변경 - 헤드리스 최적화)
            try:
                search_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config['search_btn_selector'])))
                driver.execute_script("""
                    var btn = arguments[0];
                    btn.scrollIntoView({block: 'center'});
                    document.querySelectorAll('.loading-mask, .loading-overlay, .ax-mask-body').forEach(function(el) { el.style.display = 'none'; });
                    btn.click();
                """, search_btn)
                time.sleep(3)
            except Exception as search_error:
                print(f"❌ {company_name} - 조회 버튼 클릭 실패: {str(search_error)[:100]}")
                # 대체 셀렉터 시도
                try:
                    search_btn = driver.find_element(By.CSS_SELECTOR, "#button-2153, button[id*='2153'], [id='button-2153']")
                    driver.execute_script("arguments[0].click();", search_btn)
                    time.sleep(3)
                except:
                    raise
            
            # 다운로드 시도 (JavaScript 방식으로 변경)
            if download:
                try:
                    download_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config['download_btn_selector'])))
                    driver.execute_script("""
                        var btn = arguments[0];
                        btn.scrollIntoView({block: 'center'});
                        document.querySelectorAll('.loading-mask, .loading-overlay, .ax-mask-body').forEach(function(el) { el.style.display = 'none'; });
                        btn.click();
                    """, download_btn)
                    time.sleep(1)
                except Exception as download_error:
                    print(f"❌ {company_name} - 다운로드 버튼 클릭 실패: {str(download_error)[:100]}")
                    # 대체 셀렉터 시도
                    try:
                        download_btn = driver.find_element(By.CSS_SELECTOR, "#button-2155, button[id*='2155'], [id='button-2155']")
                        driver.execute_script("arguments[0].click();", download_btn)
                        time.sleep(1)
                    except:
                        raise
                
                # 데이터 없음 체크
                try:
                    alert = wait.until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, config['no_data_alert_selector']))
                    )
                    if config['no_data_text'] in alert.text:
                        print("검색된 데이터가 없습니다. 다음 단계로 진행.")
                        return True
                except Exception:
                    pass
                
                # 데이터가 있는 경우 다운로드 진행
                print(" 다운로드 시작")
                time.sleep(3)
                
                # 다운로드 완료 후 파일 확인 (Docker 환경 대응)
                try:
                    download_dir = "/app/downloads"
                    os.makedirs(download_dir, exist_ok=True)
                    excel_files = [f for f in os.listdir(download_dir) if f.endswith(('.xlsx', '.xls'))] if os.path.exists(download_dir) else []
                    if excel_files:
                        latest_file = max(excel_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                        print(f"다운로드 완료: {latest_file}")
                except Exception as e:
                    print(f"파일 확인 중 오류: {e}")
            
            print(f"{company_name} 데이터 수집 완료")
            return True
            
        except Exception as e:
            print(f"❌ {company_name} 데이터 수집 실패: {e}")
            import traceback
            print(f"❌ {company_name} 데이터 수집 실패 - 상세 오류:")
            traceback.print_exc()
            return False
    
    def _handle_alert(self, driver, check_iframe=False):
        """알림창 처리 (브랜드 선택 팝업 포함)"""
        try:
            if check_iframe:
                # iframe 2에서 알림창 확인
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                if len(iframes) > 1:
                    driver.switch_to.frame(iframes[1])
                    try:
                        alert = driver.find_element(By.CSS_SELECTOR, "button[data-dialog-btn='ok']")
                        alert.click()
                        driver.switch_to.default_content()
                        return True
                    except:
                        driver.switch_to.default_content()
                        return False
            else:
                # 일반 알림창 처리
                alert = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-dialog-btn='ok']"))
                )
                alert.click()
                print("알림창 처리 완료")
                return True
        except:
            return False

    def _wait_for_masks(self, driver, timeout=None):
        """로딩 마스크 대기"""
        if timeout is None:
            timeout = ElementConfig.WAIT['default']
            
        masks = driver.find_elements(By.CSS_SELECTOR, ElementConfig.COMMON['loading_mask'])
        if masks:
            for mask in masks:
                if mask.is_displayed():
                    WebDriverWait(driver, timeout).until(
                        EC.invisibility_of_element(mask)
                    )
    
    def _click_element(self, driver, element, js_click=True):
        """엘리먼트 클릭 (JavaScript 또는 일반)"""
        try:
            if js_click:
                driver.execute_script(ElementConfig.JS['click'], element)
            else:
                element.click()
            return True
        except Exception as e:
            print(f"클릭 실패: {e}")
            return False
    
    def _switch_to_iframe(self, driver, iframe_index):
        """iframe 전환"""
        print("iframe 확인 중...")
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes and len(iframes) > iframe_index:
            driver.switch_to.frame(iframes[iframe_index])
            print(f"iframe[{iframe_index}] 전환 완료")
            return True
        else:
            print(f"iframe[{iframe_index}] 찾을 수 없음 (전체 {len(iframes)}개)")
            return False
    
    def _handle_download(self, driver, button_selector, brand=None):
        """다운로드 처리"""
        brand_text = f" ({brand})" if brand else ""
        
        # 마스크 대기
        self._wait_for_masks(driver)
        
        # 다운로드 버튼 찾기 및 클릭
        download_btn = driver.find_element(By.CSS_SELECTOR, button_selector)
        print(f"🔍 다운로드 버튼 상태: displayed={download_btn.is_displayed()}, enabled={download_btn.is_enabled()}")
        
        if self._click_element(driver, download_btn):
            print(f"JavaScript로 다운로드 버튼 클릭 성공{brand_text}")
            print(f"엑셀 다운로드 시작{brand_text}")
            return True
        return False
    
    def _try_click_no_data_alert(self, driver, wait):
        """데이터 없음 알림창 확인 버튼 클릭"""
        try:
            ok_button = driver.find_element(By.CSS_SELECTOR, "#ax5-dialog-29 button[data-dialog-btn='ok']")
            ok_button.click()
            return True
        except Exception:
            return False

    def _handle_no_data_alert(self, driver, wait):
        """데이터 없음 알림창 처리"""
        try:
            alert = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "#ax5-dialog-29 .ax-dialog-msg"))
            )
            if "검색된 데이터가 없습니다" in alert.text:
                print("검색된 데이터가 없습니다. 다음 단계로 진행.")
                return True
        except Exception:
            pass
        return False

    def _process_sms_data(self, driver, config, start_date=None, end_date=None, brand=None, is_last_brand=False):
        """SMS 데이터 처리 (검색 및 다운로드) - 간소화 버전"""
        wait = WebDriverWait(driver, 15)
        
        # 날짜 입력 (헤드리스 최적화 - JavaScript 우선)
        if start_date and end_date:
            try:
                start_selector = config['start_date_selector']
                end_selector = config['end_date_selector']
                driver.execute_script("""
                    var startSelector = arguments[0];
                    var endSelector = arguments[1];
                    var startDate = arguments[2];
                    var endDate = arguments[3];
                    var startInput = document.querySelector(startSelector);
                    var endInput = document.querySelector(endSelector);
                    if (startInput) {
                        startInput.value = startDate;
                        startInput.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                    if (endInput) {
                        endInput.value = endDate;
                        endInput.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                """, start_selector, end_selector, start_date, end_date)
                time.sleep(1)
            except Exception as js_error:
                # JavaScript 실패 시 Selenium 방식으로 fallback
                try:
                    start_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config['start_date_selector'])))
                    start_input.clear()
                    start_input.send_keys(start_date)
                    time.sleep(0.5)
                    
                    end_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config['end_date_selector'])))
                    end_input.clear()
                    end_input.send_keys(end_date)
                    time.sleep(0.5)
                except Exception as date_error:
                    print(f"❌ 날짜 설정 실패: {str(date_error)[:100]}")
        
        # 조회 버튼 클릭
        search_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-page-btn="search"], button[btnid="B0002"]')))
        driver.execute_script("""
            var btn = arguments[0];
            btn.scrollIntoView({block: 'center'});
            document.querySelectorAll('.loading-mask, .loading-overlay, .ax-mask-body').forEach(function(el) { el.style.display = 'none'; });
            btn.click();
        """, search_btn)
        time.sleep(3)
        
        # 데이터 없음 알림 처리
        try:
            alert = WebDriverWait(driver, 2).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "#ax5-dialog-29 .ax-dialog-msg"))
            )
            if "검색된 데이터가 없습니다" in alert.text:
                print("⚠️ 검색된 데이터가 없습니다")
                if not is_last_brand:
                    driver.find_element(By.CSS_SELECTOR, "#ax5-dialog-29 button[data-dialog-btn='ok']").click()
                return False
        except:
            pass  # 알림창이 없으면 계속 진행
        
        # 엑셀 다운로드
        download_dir = "/app/downloads"
        os.makedirs(download_dir, exist_ok=True)
        before_files = set(os.listdir(download_dir)) if os.path.exists(download_dir) else set()
        
        download_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-page-btn="excel"], button[btnid="B0004"], #titleBtn > button:nth-child(1)')))
        driver.execute_script("""
            var btn = arguments[0];
            btn.scrollIntoView({block: 'center'});
            document.querySelectorAll('.loading-mask, .loading-overlay, .ax-mask-body').forEach(function(el) { el.style.display = 'none'; });
            btn.click();
        """, download_btn)
        time.sleep(5)
        
        # 다운로드 완료 후 파일 확인
        try:
            time.sleep(5)
            after_files = set(os.listdir(download_dir)) if os.path.exists(download_dir) else set()
            new_files = after_files - before_files
            new_excel_files = [f for f in new_files if f.endswith(('.xlsx', '.xls'))]
            
            if new_excel_files:
                return True
            
            # 기존 Excel 파일이 최근에 수정되었는지 확인
            all_excel_files = [f for f in after_files if f.endswith(('.xlsx', '.xls'))]
            if all_excel_files:
                current_time = time.time()
                for excel_file in all_excel_files:
                    file_path = os.path.join(download_dir, excel_file)
                    if os.path.exists(file_path) and current_time - os.path.getmtime(file_path) < 10:
                        return True
            
            return False
        except Exception as e:
            print(f"⚠️ 파일 확인 중 오류: {e}")
            return False

    def process_chat_no_brand(self, driver, config, start_date, end_date):
        wait = WebDriverWait(driver, 10)
        try:
            # 채팅관리 메뉴 클릭
            chat_menu = wait.until(EC.element_to_be_clickable((By.XPATH, ElementConfig.CHAT["menu_chat"])))
            chat_menu.click()
            time.sleep(1)
            # 채팅진행건리스트 클릭
            chat_list = wait.until(EC.element_to_be_clickable((By.XPATH, ElementConfig.CHAT["menu_chat_list"])))
            chat_list.click()
            time.sleep(1)
            # iframe 전환
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > 1:
                driver.switch_to.frame(iframes[1])
                time.sleep(2)
                # 팀 태그 제거
                try:
                    team_tag = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ElementConfig.CHAT["team_tag_remove"])))
                    team_tag.click()
                except Exception:
                    pass
                time.sleep(1)
                
                # 날짜 입력
                if start_date and end_date:
                    try:
                        start_selector = ElementConfig.CHAT["start_date_input"]
                        end_selector = ElementConfig.CHAT["end_date_input"]
                        start_date_formatted = start_date.replace("-", "")
                        end_date_formatted = end_date.replace("-", "")
                        driver.execute_script(f"""
                            var startInput = document.querySelector('{start_selector}');
                            var endInput = document.querySelector('{end_selector}');
                            if (startInput) {{
                                startInput.value = '{start_date_formatted}';
                                startInput.dispatchEvent(new Event('change', {{bubbles: true}}));
                            }}
                            if (endInput) {{
                                endInput.value = '{end_date_formatted}';
                                endInput.dispatchEvent(new Event('change', {{bubbles: true}}));
                            }}
                        """)
                        time.sleep(1)
                    except Exception as date_error:
                        print(f"❌ 날짜 설정 실패: {date_error}")
                
                # 조회 버튼 클릭
                try:
                    search_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ElementConfig.CHAT["search_btn"])))
                    driver.execute_script("""
                        var btn = arguments[0];
                        btn.scrollIntoView({block: 'center'});
                        document.querySelectorAll('.loading-mask, .loading-overlay, .ax-mask-body').forEach(function(el) { el.style.display = 'none'; });
                        btn.click();
                    """, search_btn)
                    time.sleep(3)
                except Exception as e:
                    print(f"❌ 조회 버튼 클릭 실패: {e}")
                time.sleep(2)
                
                # 알림창 처리
                def handle_alert(driver):
                    try:
                        alert_button = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, ElementConfig.CHAT["alert_ok_btn"]))
                        )
                        alert_button.click()
                        return True
                    except Exception:
                        return False
                
                if not handle_alert(driver):
                    # 다운로드 버튼 클릭
                    try:
                        excel_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ElementConfig.CHAT["excel_btn"])))
                        driver.execute_script("""
                            var btn = arguments[0];
                            btn.scrollIntoView({block: 'center'});
                            document.querySelectorAll('.loading-mask, .loading-overlay, .ax-mask-body').forEach(function(el) { el.style.display = 'none'; });
                            btn.click();
                        """, excel_btn)
                        time.sleep(5)
                    except Exception as e:
                        print(f"❌ 엑셀 다운로드 버튼 클릭 실패: {e}")
        except Exception as e:
            print(f"채팅 메뉴 이동 실패: {e}")
        return True

    def download_sms_data(self, company_name, start_date=None, end_date=None):
        """SMS 데이터 다운로드"""
        session = self.login_manager.get_active_session(company_name, "sms")
        if not session:
            print(f"❌ {company_name} SMS 세션이 없습니다")
            return False
        
        driver = session['driver']
        config = session['account_data']['config']
        wait = WebDriverWait(driver, ElementConfig.WAIT['default'])
        
        # SMS 기능이 없는 회사 체크
        if 'sms_service_selector' not in config:
            print(f"{company_name}는 SMS 기능이 없습니다")
            return False
        
        def click_menu_chain():
            """메뉴 클릭 체인"""
            try:
                # 구쁘 전용 처리
                if config.get('is_guppu'):
                    # 메뉴 버튼 클릭
                    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['sms_service_selector']))).click()
                    time.sleep(1)
                    
                    # SMS 버튼 클릭
                    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['sms_menu_selector']))).click()
                    time.sleep(1)
                    
                    # 문자발송이력 버튼 클릭
                    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['sms_history_selector']))).click()
                    time.sleep(2)
                    return True
                
                # 기존 로직 (다른 회사들)
                # 메뉴 클릭 (볼드워크 등 새 어드민)
                if config.get('need_menu_click'):
                    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['menu_selector']))).click()
                    time.sleep(ElementConfig.WAIT['short'])
                
                # 문자서비스 클릭
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['sms_service_selector']))).click()
                time.sleep(ElementConfig.WAIT['short'])
                
                # 문자발송이력 클릭
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config['sms_history_selector']))).click()
                time.sleep(ElementConfig.WAIT['short'])
                return True
            except Exception as e:
                print(f"메뉴 클릭 실패: {e}")
                return False
        
        # 최초 메뉴 클릭
        if not click_menu_chain():
            return False
        
        # 브랜드 선택이 필요한 회사들 처리
        if config.get('has_brands'):
            # 브랜드 선택 팝업 닫기
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > ElementConfig.IFRAME['brand_popup_index']:
                driver.switch_to.frame(iframes[ElementConfig.IFRAME['brand_popup_index']])
                try:
                    driver.find_element(By.CSS_SELECTOR, ElementConfig.COMMON['alert_ok']).click()
                    pass
                except Exception as e:
                    pass
                driver.switch_to.default_content()

            # 각 브랜드별로 처리
            for brand_index, brand in enumerate(config['brands']):
                is_last_brand = brand_index == len(config['brands']) - 1
                print(ElementConfig.BRAND['messages']['start'].format(brand))
                try:
                    # iframe 전환
                    print(ElementConfig.MESSAGES['iframe']['check'])
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    if len(iframes) <= ElementConfig.IFRAME['data_index']:
                        print(ElementConfig.MESSAGES['iframe']['error'].format(len(iframes)))
                        raise RuntimeError("iframe 없음")
                    
                    driver.switch_to.frame(iframes[ElementConfig.IFRAME['data_index']])
                    print(ElementConfig.MESSAGES['iframe']['success'].format(ElementConfig.IFRAME['data_index'] + 1))
                    
                    # 브랜드 선택 (이미 선택되어 있는지 먼저 확인)
                    brand_already_selected = False
                    
                    # 1단계: 브랜드가 이미 선택되어 있는지 확인 (더 안전한 방법)
                    try:
                        # select 요소에서 선택된 옵션 확인 (여러 방법 시도)
                        select_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='mallId']")))
                        
                        # 방법 1: selected 속성 확인 (다양한 형식 시도)
                        selected_option = None
                        try:
                            selected_option = select_element.find_element(By.CSS_SELECTOR, "option[selected]")
                        except:
                            try:
                                selected_option = select_element.find_element(By.CSS_SELECTOR, "option[selected='true']")
                            except:
                                try:
                                    selected_option = select_element.find_element(By.CSS_SELECTOR, "option[selected='selected']")
                                except:
                                    pass
                        
                        if selected_option:
                            selected_value = selected_option.get_attribute("value")
                            selected_text = selected_option.text.strip()
                            
                            # 브랜드가 이미 선택되어 있으면 건너뛰기
                            if selected_text == brand or selected_value == "qanda":
                                brand_already_selected = True
                            else:
                                brand_already_selected = False
                        else:
                            # selected 속성이 없으면 첫 번째 옵션이나 value로 확인
                            try:
                                all_options = select_element.find_elements(By.TAG_NAME, "option")
                                if all_options:
                                    first_option_value = all_options[0].get_attribute("value")
                                    if first_option_value == "qanda":
                                        brand_already_selected = True
                                    else:
                                        brand_already_selected = False
                                else:
                                    brand_already_selected = False
                            except:
                                brand_already_selected = False
                    except Exception as check_error:
                        brand_already_selected = False
                    
                    # 브랜드가 이미 선택되어 있지 않으면 선택 진행
                    if not brand_already_selected:
                        try:
                            brand_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config['brand_dropdown_selector'])))
                            
                            # autocomplete 위젯을 위한 브랜드 선택 (순수 Selenium 메서드만 사용)
                            # 1단계: input 클릭하여 autocomplete 열기 (Selenium 네이티브)
                            brand_input.click()
                            time.sleep(1)
                            
                            # 2단계: 브랜드 이름 입력
                            brand_input.clear()
                            brand_input.send_keys(brand)
                            time.sleep(2)  # autocomplete 드롭다운 표시 대기 시간 증가
                            
                            # 3단계: autocomplete 항목 선택 시도 (정확한 선택자 사용)
                            try:
                                # autocomplete 드롭다운 표시 대기
                                time.sleep(1)
                                
                                # 다양한 선택자 시도 (제공된 HTML 구조 기반 - 사용자가 제공한 구조)
                                selectors = [
                                    "div.ax-autocomplete-option-item[data-option-value='qanda']",  # 가장 정확한 선택자 (제공된 HTML 기반)
                                    "div.ax-autocomplete-option-item-holder[title='콴다']",  # holder 클릭 (사용자 제안)
                                    "div.ax-autocomplete-option-item[data-option-index='0']",  # index로 찾기
                                    "//div[@class='ax-autocomplete-option-item' and @data-option-value='qanda']",  # XPath 버전
                                    "//div[contains(@class, 'ax-autocomplete-option-item') and @data-option-value='qanda']",
                                    "//span[@class='ax-autocomplete-option-item-label' and text()='콴다']"  # label 클릭
                                ]
                                
                                autocomplete_item = None
                                for selector in selectors:
                                    try:
                                        if selector.startswith("//"):
                                            autocomplete_item = WebDriverWait(driver, 2).until(
                                                EC.element_to_be_clickable((By.XPATH, selector))
                                            )
                                        else:
                                            autocomplete_item = WebDriverWait(driver, 2).until(
                                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                            )
                                        break
                                    except:
                                        continue
                                
                                if autocomplete_item:
                                    autocomplete_item.click()
                                    time.sleep(1)
                                else:
                                    brand_input.send_keys(Keys.ENTER)
                                    time.sleep(1)
                            except Exception as ac_error:
                                brand_input.send_keys(Keys.ENTER)
                                time.sleep(1)
                        except Exception as e:
                            print(f"❌ 브랜드 선택 중 오류: {str(e)[:200]}")
                            import traceback
                            traceback.print_exc()
                            # 브랜드 선택 실패해도 계속 진행 (데이터가 없을 수 있음)
                            print(f"⚠️ 브랜드 선택 실패했지만 계속 진행: {brand}")
                    
                    # SMS 데이터 처리
                    result = self._process_sms_data(driver, config, start_date, end_date, brand, is_last_brand)
                    
                    # 마지막 브랜드이고 데이터가 없으면 종료
                    if is_last_brand and not result:
                        print(ElementConfig.BRAND['messages']['no_data'].format(brand))
                        driver.switch_to.default_content()
                        return True
                    
                    # 다음 브랜드를 위해 X버튼 클릭 (마지막 브랜드가 아니고, 브랜드를 선택한 경우에만)
                    if not is_last_brand and not brand_already_selected:
                        try:
                            # JavaScript 대신 Selenium으로 직접 클릭
                            remove_btn = driver.find_element(By.CSS_SELECTOR, "div[data-ax5autocomplete-remove='true']")
                            remove_btn.click()
                            print(ElementConfig.BRAND['messages']['remove'])
                            time.sleep(ElementConfig.WAIT['short'])
                        except Exception as remove_error:
                            print(f"⚠️ 브랜드 제거 버튼 클릭 실패 (무시): {str(remove_error)[:100]}")
                    
                    driver.switch_to.default_content()
                    print(ElementConfig.BRAND['messages']['complete'].format(brand))
                    
                except Exception as e:
                    print(ElementConfig.BRAND['messages']['error'].format(brand, e))
                    driver.switch_to.default_content()
                    if not is_last_brand:
                        click_menu_chain()
                        continue
                    else:
                        print(ElementConfig.BRAND['messages']['no_data'].format(brand))
                        return True
                
                time.sleep(ElementConfig.WAIT['short'])
        
        else:
            # 구쁘 전용 처리
            if config.get('is_guppu'):
                return self._process_guppu_sms_data(driver, config, start_date, end_date)
            
            # 기존 로직 (다른 회사들 - 앤하우스 포함)
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > ElementConfig.IFRAME['data_index']:
                driver.switch_to.frame(iframes[ElementConfig.IFRAME['data_index']])
                time.sleep(ElementConfig.WAIT['short'])
                
                # SMS 데이터 처리
                result = self._process_sms_data(driver, config, start_date, end_date)
                driver.switch_to.default_content()
                
                if not result:
                    print(f"⚠️ {company_name} - SMS 파일 다운로드 실패")
                    return False
            else:
                print(ElementConfig.MESSAGES['iframe']['error'].format(len(iframes)))
                return False
        
        print(f"{company_name} SMS 데이터 수집 완료")
        return True
    
    def _process_guppu_sms_data(self, driver, config, start_date=None, end_date=None):
        """구쁘 전용 SMS 데이터 처리 (간소화된 버전)"""
        try:
            wait = WebDriverWait(driver, 15)
            
            # iframe 전환 (간단하게)
            print("SMS iframe 찾기...")
            driver.switch_to.default_content()
            time.sleep(2)
            
            # iframe을 src로 찾기
            iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[src*="smsHistory"], iframe#frm-5605')))
            driver.switch_to.frame(iframe)
            time.sleep(2)
            
            # 날짜 설정
            if start_date and end_date:
                driver.execute_script(f"""
                    var startInput = document.querySelector('{config['start_date_selector']}');
                    var endInput = document.querySelector('{config['end_date_selector']}');
                    var displayInput = document.querySelector('{config['display_date_selector']}');
                    if (startInput) startInput.value = '{start_date}';
                    if (endInput) endInput.value = '{end_date}';
                    if (displayInput) displayInput.value = '{start_date} ~ {end_date}';
                """)
                time.sleep(1)
            
            # 조회 버튼 클릭
            search_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config['search_btn_selector'])))
            driver.execute_script("""
                var btn = arguments[0];
                btn.scrollIntoView({block: 'center'});
                document.querySelectorAll('.loading-mask, .loading-overlay, .ax-mask-body').forEach(function(el) { el.style.display = 'none'; });
                btn.click();
            """, search_btn)
            time.sleep(3)
            
            download_dir = "/app/downloads"
            os.makedirs(download_dir, exist_ok=True)
            before_files = set(os.listdir(download_dir)) if os.path.exists(download_dir) else set()
            
            # 다운로드 버튼 클릭
            download_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config['download_btn_selector'])))
            driver.execute_script("""
                var btn = arguments[0];
                btn.scrollIntoView({block: 'center'});
                document.querySelectorAll('.loading-mask, .loading-overlay, .ax-mask-body').forEach(function(el) { el.style.display = 'none'; });
                btn.click();
            """, download_btn)
            time.sleep(5)
            
            after_files = set(os.listdir(download_dir))
            new_files = after_files - before_files
            
            if new_files:
                print(f"엑셀 다운로드 완료: {list(new_files)}")
                return True
            else:
                print("다운로드된 파일을 찾을 수 없습니다")
                return False
                
        except Exception as e:
            print(f"구쁘 SMS 데이터 처리 실패: {e}")
            return False
        finally:
            driver.switch_to.default_content()