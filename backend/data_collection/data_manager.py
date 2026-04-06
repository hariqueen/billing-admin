from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

        def _safe_text(css_selector):
            try:
                return driver.find_element(By.CSS_SELECTOR, css_selector).text.strip()
            except Exception:
                return ""

        def _safe_attr(css_selector, attr_name):
            try:
                return driver.find_element(By.CSS_SELECTOR, css_selector).get_attribute(attr_name) or ""
            except Exception:
                return ""

        def _debug_active_element(stage):
            try:
                active_id = driver.execute_script("return (document.activeElement && document.activeElement.id) || '';")
                active_name = driver.execute_script("return (document.activeElement && document.activeElement.name) || '';")
                print(f"[CALL-DEBUG] {stage} | activeElement: id='{active_id}', name='{active_name}'")
            except Exception as debug_error:
                print(f"[CALL-DEBUG] {stage} | activeElement 확인 실패: {str(debug_error)[:120]}")

        def _debug_tagfield(stage, selected_text_selector, hidden_input_selector):
            selected_text = _safe_text(selected_text_selector)
            hidden_value = _safe_attr(hidden_input_selector, "value")
            print(f"[CALL-DEBUG] {stage} | selectedText='{selected_text}' | hiddenValue='{hidden_value}'")

        def _select_tagfield_option(trigger_selector, hidden_input_selector, target_labels, field_name, max_retries=3):
            """TagField 드롭다운에서 텍스트 항목을 직접 클릭해 선택한다."""
            if isinstance(target_labels, str):
                target_labels = [target_labels]

            for attempt in range(max_retries):
                try:
                    # 트리거(화살표) 우선 클릭, 실패 시 입력 필드 클릭
                    try:
                        trigger = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, trigger_selector)))
                        driver.execute_script("arguments[0].click();", trigger)
                    except Exception:
                        input_selector = trigger_selector.replace("-trigger-picker", "-inputEl")
                        input_el = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, input_selector)))
                        driver.execute_script("arguments[0].click();", input_el)

                    time.sleep(0.3)

                    # 드롭다운 옵션 텍스트 클릭 (ExtJS boundlist/일반 항목 모두 대응)
                    option_clicked = False
                    for label in target_labels:
                        option_xpath = (
                            f"//*[contains(@class,'x-boundlist-item') and normalize-space(.)='{label}']"
                            f" | //*[contains(@class,'x-boundlist-item') and contains(normalize-space(.), '{label}')]"
                            f" | //div[contains(@class,'x-boundlist-item') and normalize-space(.)='{label}']"
                            f" | //li[contains(@class,'x-boundlist-item') and normalize-space(.)='{label}']"
                        )
                        options = driver.find_elements(By.XPATH, option_xpath)
                        for opt in options:
                            if opt.is_displayed():
                                driver.execute_script("arguments[0].click();", opt)
                                option_clicked = True
                                break
                        if option_clicked:
                            break

                    time.sleep(0.4)
                    selected_value = _safe_attr(hidden_input_selector, "value")
                    if option_clicked and selected_value:
                        print(f"[CALL-DEBUG] {field_name} 선택 성공 | value='{selected_value}'")
                        return True

                    print(
                        f"[CALL-DEBUG] {field_name} 선택 재시도({attempt + 1}/{max_retries}) | "
                        f"option_clicked={option_clicked}, value='{selected_value}'"
                    )
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(0.2)
                except Exception as select_error:
                    print(
                        f"[CALL-DEBUG] {field_name} 선택 중 예외({attempt + 1}/{max_retries}): "
                        f"{str(select_error)[:120]}"
                    )
                    time.sleep(0.3)

            raise Exception(f"{field_name} 선택 실패: target_labels={target_labels}")
        
        try:
            # 콜데이터 선택 (회사 선택 단계 제거됨)
            retry_click("//span[contains(text(), '콜데이터')]", "xpath")
            time.sleep(1)
            _debug_active_element("콜데이터 클릭 후")
            
            # 아웃바운드 설정
            outbound_selector = config.get('outbound_selector', "#uxtagfield-2171-inputEl")
            retry_click(outbound_selector)
            time.sleep(0.3)
            
            # 아웃바운드 값 선택 (텍스트 직접 클릭)
            call_type_labels = config.get('call_type_labels', ['아웃바운드', 'Outbound'])
            _select_tagfield_option(
                "#uxtagfield-2171-trigger-picker",
                "#uxtagfield-2171-hiddenDataEl input[name='call_type']",
                call_type_labels,
                "호타입"
            )
            time.sleep(0.4)
            _debug_tagfield(
                "호타입 선택 후",
                "#uxtagfield-2171-selectedText",
                "#uxtagfield-2171-hiddenDataEl input[name='call_type']"
            )
            _debug_active_element("호타입 선택 후")
            
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
            
            # 호상태 값 선택 (텍스트 직접 클릭)
            call_status_labels = config.get('call_status_labels', ['통화성공', 'Connect'])
            _select_tagfield_option(
                "#uxtagfield-2172-trigger-picker",
                "#uxtagfield-2172-hiddenDataEl input[name='state']",
                call_status_labels,
                "호상태"
            )
            time.sleep(0.5)
            _debug_tagfield(
                "호상태 선택 후",
                "#uxtagfield-2172-selectedText",
                "#uxtagfield-2172-hiddenDataEl input[name='state']"
            )
            _debug_active_element("호상태 선택 후")
            
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
                    start_value = driver.execute_script(
                        "var el = document.querySelector(arguments[0]); return el ? el.value : '';",
                        start_selector
                    )
                    end_value = driver.execute_script(
                        "var el = document.querySelector(arguments[0]); return el ? el.value : '';",
                        end_selector
                    )
                    print(
                        f"[CALL-DEBUG] 날짜 설정 후 | start='{start_value}', end='{end_value}', "
                        f"requested_start='{start_date}', requested_end='{end_date}'"
                    )
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
                        start_value = _safe_attr(config['start_date_selector'], "value")
                        end_value = _safe_attr(config['end_date_selector'], "value")
                        print(
                            f"[CALL-DEBUG] 날짜(Fallback) 설정 후 | start='{start_value}', end='{end_value}', "
                            f"requested_start='{start_date}', requested_end='{end_date}'"
                        )
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
                download_dir = "/app/downloads"
                os.makedirs(download_dir, exist_ok=True)
                before_files = set(os.listdir(download_dir)) if os.path.exists(download_dir) else set()
                print(f"[CALL-DEBUG] 다운로드 전 파일 수: {len(before_files)}")
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
                    print(f"[CALL-DEBUG] 데이터없음 알림 감지: '{alert.text.strip()}'")
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
                    after_files = set(os.listdir(download_dir)) if os.path.exists(download_dir) else set()
                    new_files = sorted(list(after_files - before_files))
                    excel_files = [f for f in after_files if f.endswith(('.xlsx', '.xls'))] if os.path.exists(download_dir) else []
                    print(f"[CALL-DEBUG] 다운로드 후 파일 수: {len(after_files)} | 신규 파일: {new_files}")
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

    def _snapshot_download_dir(self, download_dir):
        """다운로드 폴더 파일명 집합과 mtime 스냅샷(덮어쓰기 감지용)."""
        names = set()
        mtimes = {}
        if not os.path.exists(download_dir):
            return names, mtimes
        for n in os.listdir(download_dir):
            p = os.path.join(download_dir, n)
            if os.path.isfile(p):
                names.add(n)
                try:
                    mtimes[n] = os.path.getmtime(p)
                except OSError:
                    pass
        return names, mtimes

    def _wait_for_excel_in_download_dir(self, download_dir, before_names, before_mtimes, max_wait_sec=90):
        """
        엑셀 다운로드 완료까지 대기.
        - 신규 파일명
        - 동일 파일명 덮어쓰기(mtime 갱신)
        - Chrome .crdownload 진행 중이면 소멸까지 대기
        """
        interval = 2
        elapsed = 0
        while elapsed < max_wait_sec:
            time.sleep(interval)
            elapsed += interval
            if not os.path.exists(download_dir):
                continue
            listing = os.listdir(download_dir)
            if any(x.endswith(".crdownload") for x in listing):
                print(f"SMS 다운로드 대기 (.crdownload, {elapsed}/{max_wait_sec}초)")
                continue
            for n in listing:
                low = n.lower()
                if not (low.endswith(".xlsx") or low.endswith(".xls")):
                    continue
                p = os.path.join(download_dir, n)
                if not os.path.isfile(p):
                    continue
                try:
                    m = os.path.getmtime(p)
                except OSError:
                    continue
                if n not in before_names:
                    print(f"SMS 엑셀 다운로드 감지(신규): {n}")
                    return True
                old = before_mtimes.get(n)
                if old is not None and m > old + 1.0:
                    print(f"SMS 엑셀 다운로드 감지(갱신): {n}")
                    return True
        print(f"⚠️ SMS 다운로드 폴더에서 엑셀 확인 시간 초과 ({max_wait_sec}초)")
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
        
        # 조회 버튼 클릭 (마스크를 억지로 숨기지 않음 → 조회 후 그리드/로딩이 정상 동작)
        search_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-page-btn="search"], button[btnid="B0002"]')))
        driver.execute_script("""
            var btn = arguments[0];
            btn.scrollIntoView({block: 'center'});
            btn.click();
        """, search_btn)
        time.sleep(1)
        try:
            self._wait_for_masks(driver, timeout=45)
        except Exception:
            pass
        time.sleep(1)
        
        # 데이터 없음 알림 (늦게 뜨는 경우 대비해 최대 12초까지 폴링; 데이터가 있으면 다이얼로그 없이 곧바로 통과)
        no_data_deadline = time.time() + 12
        while time.time() < no_data_deadline:
            try:
                msg_el = driver.find_element(By.CSS_SELECTOR, "#ax5-dialog-29 .ax-dialog-msg")
                if not msg_el.is_displayed():
                    time.sleep(0.35)
                    continue
                text = (msg_el.text or "").strip()
                if "검색된 데이터가 없습니다" in text:
                    print("⚠️ 검색된 데이터가 없습니다")
                    try:
                        driver.find_element(By.CSS_SELECTOR, "#ax5-dialog-29 button[data-dialog-btn='ok']").click()
                    except Exception:
                        pass
                    return False
                try:
                    driver.find_element(By.CSS_SELECTOR, "#ax5-dialog-29 button[data-dialog-btn='ok']").click()
                    time.sleep(0.4)
                except Exception:
                    pass
                break
            except Exception:
                time.sleep(0.35)
        time.sleep(0.3)
        
        # 엑셀 다운로드
        download_dir = "/app/downloads"
        os.makedirs(download_dir, exist_ok=True)
        before_names, before_mtimes = self._snapshot_download_dir(download_dir)
        
        download_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-page-btn="excel"], button[btnid="B0004"], #titleBtn > button:nth-child(1)')))
        driver.execute_script("""
            var btn = arguments[0];
            btn.scrollIntoView({block: 'center'});
            document.querySelectorAll('.loading-mask, .loading-overlay, .ax-mask-body').forEach(function(el) { el.style.display = 'none'; });
            btn.click();
        """, download_btn)
        try:
            self._wait_for_masks(driver, timeout=20)
        except Exception:
            pass
        
        ok = self._wait_for_excel_in_download_dir(
            download_dir, before_names, before_mtimes, max_wait_sec=90
        )
        if not ok:
            print("⚠️ SMS 엑셀 다운로드 검증 실패 또는 타임아웃")
        return ok

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

        debug_prefix = f"[SMS-DEBUG][{company_name}]"

        def debug_snapshot(stage):
            """현재 페이지/프레임/팝업 상태 스냅샷"""
            try:
                current_url = driver.current_url
            except Exception as e:
                current_url = f"조회실패: {e}"

            try:
                page_title = driver.title
            except Exception as e:
                page_title = f"조회실패: {e}"

            try:
                iframe_count = len(driver.find_elements(By.TAG_NAME, "iframe"))
            except Exception as e:
                iframe_count = f"조회실패: {e}"

            try:
                ready_state = driver.execute_script("return document.readyState")
            except Exception as e:
                ready_state = f"조회실패: {e}"

            alert_text = None
            try:
                alert = driver.switch_to.alert
                alert_text = alert.text
            except Exception:
                pass

            print(f"{debug_prefix} {stage}")
            print(f"{debug_prefix} URL={current_url}")
            print(f"{debug_prefix} TITLE={page_title}")
            print(f"{debug_prefix} READY_STATE={ready_state}, IFRAMES={iframe_count}")
            if alert_text:
                print(f"{debug_prefix} JS Alert 감지: {alert_text}")

            try:
                menu_nodes = driver.find_elements(By.CSS_SELECTOR, "span[id^='aside-menu-']")
                menu_texts = [node.text.strip() for node in menu_nodes if node.text and node.text.strip()]
                if menu_texts:
                    print(f"{debug_prefix} 메뉴 텍스트 샘플(최대10): {', '.join(menu_texts[:10])}")
            except Exception:
                pass

        def click_with_debug(by, selector, step_name, timeout=ElementConfig.WAIT['default']):
            """selector 클릭 + 실패 시 상세 디버깅"""
            try:
                print(f"{debug_prefix} {step_name} 시도: by={by}, selector={selector}")
                element = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((by, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.3)
                element.click()
                print(f"{debug_prefix} {step_name} 성공")
                return True
            except Exception as e:
                print(f"{debug_prefix} {step_name} 실패: {e}")
                debug_snapshot(f"{step_name} 실패 직후 스냅샷")
                return False
        
        def click_menu_chain():
            """메뉴 클릭 체인"""
            try:
                debug_snapshot("메뉴 클릭 체인 시작")

                # 구쁘 전용 처리
                if config.get('is_guppu'):
                    # 메뉴 버튼 클릭
                    if not click_with_debug(By.CSS_SELECTOR, config['sms_service_selector'], "구쁘 메뉴 버튼 클릭"):
                        return False
                    time.sleep(1)
                    
                    # SMS 버튼 클릭
                    if not click_with_debug(By.CSS_SELECTOR, config['sms_menu_selector'], "구쁘 SMS 버튼 클릭"):
                        return False
                    time.sleep(1)
                    
                    # 문자발송이력 버튼 클릭
                    if not click_with_debug(By.CSS_SELECTOR, config['sms_history_selector'], "구쁘 문자발송이력 클릭"):
                        return False
                    time.sleep(2)
                    debug_snapshot("구쁘 메뉴 클릭 체인 완료")
                    return True
                
                # 기존 로직 (다른 회사들)
                # 메뉴 클릭 (볼드워크 등 새 어드민)
                if config.get('need_menu_click'):
                    if not click_with_debug(By.CSS_SELECTOR, config['menu_selector'], "공통 상위 메뉴 클릭"):
                        return False
                    time.sleep(ElementConfig.WAIT['short'])
                
                # 문자서비스 클릭
                if not click_with_debug(By.CSS_SELECTOR, config['sms_service_selector'], "문자서비스 클릭"):
                    return False
                time.sleep(ElementConfig.WAIT['short'])
                
                # 문자발송이력 클릭
                if not click_with_debug(By.CSS_SELECTOR, config['sms_history_selector'], "문자발송이력 클릭"):
                    return False
                time.sleep(ElementConfig.WAIT['short'])
                debug_snapshot("메뉴 클릭 체인 완료")
                return True
            except Exception as e:
                print(f"메뉴 클릭 실패: {e}")
                debug_snapshot("메뉴 클릭 체인 예외")
                return False
        
        # 최초 메뉴 클릭
        if not click_menu_chain():
            return False
        
        # 브랜드 선택이 필요한 회사들 처리
        if config.get('has_brands'):
            # 브랜드 선택 팝업 닫기
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"{debug_prefix} 브랜드 팝업 전 iframe 개수: {len(iframes)}")
            if len(iframes) > ElementConfig.IFRAME['brand_popup_index']:
                driver.switch_to.frame(iframes[ElementConfig.IFRAME['brand_popup_index']])
                try:
                    driver.find_element(By.CSS_SELECTOR, ElementConfig.COMMON['alert_ok']).click()
                    print(f"{debug_prefix} 브랜드 팝업 확인 버튼 클릭 성공")
                except Exception as e:
                    print(f"{debug_prefix} 브랜드 팝업 확인 버튼 없음/실패: {str(e)[:150]}")
                driver.switch_to.default_content()
            else:
                print(
                    f"{debug_prefix} 브랜드 팝업 iframe 인덱스 부족: "
                    f"need>{ElementConfig.IFRAME['brand_popup_index']}, has={len(iframes)}"
                )

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
                                    print(f"{debug_prefix} 브랜드 자동완성 선택자 매칭: {selector}")
                                    autocomplete_item.click()
                                    time.sleep(1)
                                else:
                                    print(f"{debug_prefix} 브랜드 자동완성 항목 없음, ENTER로 대체")
                                    brand_input.send_keys(Keys.ENTER)
                                    time.sleep(1)
                            except Exception as ac_error:
                                print(f"{debug_prefix} 브랜드 자동완성 클릭 실패, ENTER 대체: {str(ac_error)[:150]}")
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
                try:
                    guppu_result = self._process_guppu_sms_data(driver, config, start_date, end_date)
                    if not guppu_result:
                        raise RuntimeError("GUPPU_DOWNLOAD_FAIL: 구쁘 SMS 다운로드 실패")
                    return True
                except Exception as guppu_error:
                    print(f"{debug_prefix} 구쁘 전용 처리 실패: {guppu_error}")
                    raise
            
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
        debug_prefix = "[SMS-DEBUG][구쁘]"
        try:
            wait = WebDriverWait(driver, 15)
            print(f"{debug_prefix} 구쁘 SMS 처리 시작")
            
            # iframe 전환 (간단하게)
            print(f"{debug_prefix} SMS iframe 찾기 시작")
            driver.switch_to.default_content()
            time.sleep(2)
            
            # iframe을 src로 찾기
            iframe_selector = 'iframe[src*="smsHistory"], iframe#frm-5605'
            iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, iframe_selector)))
            driver.switch_to.frame(iframe)
            print(f"{debug_prefix} iframe 전환 성공: selector={iframe_selector}")
            time.sleep(2)
            
            # 날짜 설정
            if start_date and end_date:
                print(f"{debug_prefix} 날짜 설정 시작: {start_date} ~ {end_date}")
                driver.execute_script(f"""
                    var startInput = document.querySelector('{config['start_date_selector']}');
                    var endInput = document.querySelector('{config['end_date_selector']}');
                    var displayInput = document.querySelector('{config['display_date_selector']}');
                    if (startInput) startInput.value = '{start_date}';
                    if (endInput) endInput.value = '{end_date}';
                    if (displayInput) displayInput.value = '{start_date} ~ {end_date}';
                """)
                print(f"{debug_prefix} 날짜 설정 완료")
                time.sleep(1)
            
            # 조회 버튼 클릭
            print(f"{debug_prefix} 조회 버튼 클릭 시도: {config['search_btn_selector']}")
            search_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config['search_btn_selector'])))
            driver.execute_script("""
                var btn = arguments[0];
                btn.scrollIntoView({block: 'center'});
                document.querySelectorAll('.loading-mask, .loading-overlay, .ax-mask-body').forEach(function(el) { el.style.display = 'none'; });
                btn.click();
            """, search_btn)
            print(f"{debug_prefix} 조회 버튼 클릭 성공")
            time.sleep(3)
            
            download_dir = "/app/downloads"
            os.makedirs(download_dir, exist_ok=True)
            before_files = set(os.listdir(download_dir)) if os.path.exists(download_dir) else set()
            print(f"{debug_prefix} 다운로드 전 파일 수: {len(before_files)}")
            try:
                self.login_manager._apply_chrome_download_path_cdp(driver)
            except Exception as cdp_e:
                print(f"{debug_prefix} CDP 다운로드 경로 재적용(무시 가능): {cdp_e}")

            # 다운로드 버튼 클릭
            print(f"{debug_prefix} 다운로드 버튼 클릭 시도: {config['download_btn_selector']}")
            download_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config['download_btn_selector'])))
            driver.execute_script("""
                var btn = arguments[0];
                btn.scrollIntoView({block: 'center'});
                document.querySelectorAll('.loading-mask, .loading-overlay, .ax-mask-body').forEach(function(el) { el.style.display = 'none'; });
                btn.click();
            """, download_btn)
            print(f"{debug_prefix} 다운로드 버튼 클릭 성공")
            # 폴더가 비어 있으면 .crdownload 도 없어 이전 로직이 즉시 종료됨 → 최대 90초까지 폴링.
            # Chrome은 동일 파일명 덮어쓰기 시 신규 파일명이 없을 수 있음 → mtime 도 함께 판정.
            deadline = time.time() + 90
            saw_download_activity = False
            while time.time() < deadline:
                try:
                    names = os.listdir(download_dir)
                except OSError:
                    time.sleep(0.3)
                    continue
                if any(n.endswith(".crdownload") for n in names):
                    saw_download_activity = True
                    time.sleep(0.35)
                    continue
                after_set = set(names)
                if after_set - before_files:
                    saw_download_activity = True
                    break
                now = time.time()
                for fname in names:
                    if not fname.endswith((".xlsx", ".xls")):
                        continue
                    fp = os.path.join(download_dir, fname)
                    try:
                        if now - os.path.getmtime(fp) < 90:
                            saw_download_activity = True
                            break
                    except OSError:
                        pass
                if saw_download_activity:
                    break
                time.sleep(0.45)
            else:
                print(f"{debug_prefix} 경고: 다운로드 대기 90초 초과")

            after_files = set(os.listdir(download_dir))
            new_files = after_files - before_files
            new_excel = [f for f in new_files if f.endswith((".xlsx", ".xls"))]
            if new_excel:
                print(f"{debug_prefix} 엑셀 다운로드 완료(신규 파일): {new_excel}")
                return True

            all_excel = [f for f in after_files if f.endswith((".xlsx", ".xls"))]
            now = time.time()
            for fname in all_excel:
                fp = os.path.join(download_dir, fname)
                try:
                    if now - os.path.getmtime(fp) < 45:
                        print(f"{debug_prefix} 엑셀 다운로드 완료(동일 이름 덮어쓰기, 최근 수정): {fname}")
                        return True
                except OSError:
                    continue

            print(
                f"{debug_prefix} 다운로드 폴더 상태: "
                f"{sorted(after_files)[:20]}{'...' if len(after_files) > 20 else ''}"
            )
            raise RuntimeError("GUPPU_DOWNLOAD_FAIL: 다운로드된 파일을 찾을 수 없습니다")
                
        except Exception as e:
            print(f"{debug_prefix} 구쁘 SMS 데이터 처리 실패: {e}")
            raise
        finally:
            driver.switch_to.default_content()