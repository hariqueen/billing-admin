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
        """WebDriver 설정"""
        try:
            options = Options()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 30)
            print("브라우저 시작 완료")
            return True
        except Exception as e:
            raise Exception(f"브라우저 실행 실패: {e}")

    def login_to_groupware(self, user_id, password):
        """그룹웨어 로그인"""
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
            
            # 로그인 성공 확인
            current_url = self.driver.current_url
            if "userMain.do" not in current_url:
                raise Exception("로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.")
            
            print("로그인 완료")
            return True
            
        except Exception as e:
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
            select_btn.click()
            time.sleep(2)
            
            # 새창으로 전환
            if not self._switch_to_popup_window(main_window):
                raise Exception("새창으로 전환 실패")
            
            # 팝업 로드 대기
            self._wait_for_card_popup()
            
            # 카테고리에 따른 카드 선택
            if category == "해외결제 법인카드":
                self._select_overseas_card()
            else:
                self._select_default_card()
            
            # 확인 버튼 클릭 후 메인 윈도우로 복귀
            confirm_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "btnConfirm")))
            confirm_btn.click()
            time.sleep(1)
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
            raise Exception(f"카드 사용내역 설정 실패: {e}")

    def _switch_to_popup_window(self, main_window):
        """새창(팝업 윈도우)으로 전환"""
        try:
            print("    새창 전환")
            
            # 새창이 열릴 때까지 대기 (최대 5초)
            for i in range(5):
                windows = self.driver.window_handles
                if len(windows) > 1:
                    # 메인 윈도우가 아닌 새창으로 전환
                    for window in windows:
                        if window != main_window:
                            self.driver.switch_to.window(window)
                            print("    새창 전환 완료")
                            return True
                time.sleep(1)
            
            print("    새창 전환 실패")
            return False
            
        except Exception as e:
            print(f"    새창 전환 오류: {e}")
            return False

    def _wait_for_card_popup(self):
        """카드 팝업 로드 완료 대기"""
        try:
            print("    카드 팝업 로드 대기")
            
            # 카드 테이블 로드 확인
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#tblUserCardInfo")))
            
            # 카드 개수 확인
            try:
                total_count = self.driver.find_element(By.ID, "txtShowCount").text.strip()
                print(f"    팝업 로드 완료 - 총 {total_count}개 카드")
            except:
                print("    팝업 로드 완료")
            
            return True
            
        except Exception as e:
            print(f"    팝업 대기 실패: {e}")
            return False

    def _select_overseas_card(self):
        """해외결제 법인카드 선택"""
        try:
            print("    해외결제 법인카드 선택")
            
            # 성공한 셀렉터 사용
            selector = "#tblUserCardInfo .grid-content tbody tr:nth-child(2) td:nth-child(1) input.PUDDCheckBox"
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            self.driver.execute_script("arguments[0].click();", element)
            print("    해외결제 카드 선택 완료")
            time.sleep(1)
            return True
            
        except Exception as e:
            print(f"    해외결제 카드 선택 실패: {e} - 첫 번째 카드로 대체")
            return self._select_default_card()

    def _select_default_card(self):
        """기본 카드 선택 (첫 번째 카드)"""
        try:
            print("    첫 번째 카드 선택")
            
            # 첫 번째 카드 셀렉터 (해외결제 카드와 동일한 패턴)
            selector = "#tblUserCardInfo .grid-content tbody tr:first-child td:first-child input.PUDDCheckBox"
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            self.driver.execute_script("arguments[0].click();", element)
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
                    
                    # 체크박스 클릭
                    row_index = i + 1
                    
                    # 성공한 방법: label 클릭
                    checkbox_label_xpath = f"/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[2]/div/div[3]/div[2]/table/tbody/tr[{row_index}]/td[1]/span/label"
                    checkbox_label = self.wait.until(EC.element_to_be_clickable((By.XPATH, checkbox_label_xpath)))
                    checkbox_label.click()
                    print(f"      체크박스 클릭 완료")
                    time.sleep(1)
                    return True
            
            print(f"      현재 페이지에서 매칭되는 금액을 찾지 못함")
            return False
            
        except Exception as e:
            print(f"      체크박스 클릭 실패: {e}")
            return False

    def _is_row_already_processed(self, row_index):
        """해당 행이 이미 처리되었는지 확인"""
        try:
            # 해당 행의 마지막 td (4번째 컬럼) 확인
            row_xpath = f"/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[2]/div/div[3]/div[2]/table/tbody/tr[{row_index + 1}]"
            
            try:
                row_element = self.driver.find_element(By.XPATH, row_xpath)
                # 마지막 td 찾기 (4번째 컬럼)
                last_td = row_element.find_element(By.CSS_SELECTOR, "td:last-child")
                
                # td 내부의 모든 span 태그 확인
                spans = last_td.find_elements(By.TAG_NAME, "span")
                
                # span이 없거나 모든 span이 비어있으면 미처리
                if not spans:
                    print(f"        행 {row_index+1}은 아직 처리되지 않음 (span 없음)")
                    return False
                
                # span들에 의미있는 데이터가 있는지 확인
                has_data = False
                span_contents = []
                
                for span in spans:
                    span_text = span.text.strip()
                    span_id = span.get_attribute("id")
                    
                    # span에 텍스트나 id가 있으면 데이터가 있는 것
                    if span_text or span_id:
                        has_data = True
                        span_contents.append(f"'{span_text}'" if span_text else f"id='{span_id}'")
                
                if has_data:
                    print(f"        행 {row_index+1}은 이미 처리됨 (span 데이터: {', '.join(span_contents)})")
                    return True
                else:
                    print(f"        행 {row_index+1}은 아직 처리되지 않음 (span들이 모두 비어있음)")
                    return False
                    
            except Exception as e:
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
                    # alert가 없으면 저장 성공
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
                
                # 현재 페이지의 금액 셀 개수 확인
                amount_cells = self.driver.find_elements(By.CSS_SELECTOR, "td.td_ri span.fwb")
                total_cells = len(amount_cells)
                print(f"   현재 페이지에서 {total_cells}개 금액 셀 발견")
                
                # 각 행을 순차적으로 처리 (DOM 변경을 고려하여 매번 다시 찾기)
                for i in range(total_cells):
                    try:
                        # 매번 새로 금액 셀들을 찾기 (Stale Element 방지)
                        current_amount_cells = self.driver.find_elements(By.CSS_SELECTOR, "td.td_ri span.fwb")
                        if i >= len(current_amount_cells):
                            print(f"   행 {i+1}: 금액 셀이 더 이상 존재하지 않음")
                            break
                        
                        cell = current_amount_cells[i]
                        cell_amount = self._clean_amount(cell.text)
                        print(f"   웹 금액 {i+1}: {cell.text} -> {cell_amount}")
                        
                        # 이미 처리된 행인지 확인
                        if self._is_row_already_processed(i):
                            print(f"   행 {i+1}은 이미 처리됨 - 건너뛰기")
                            continue
                        
                        print(f"   행 {i+1}을 처리합니다")
                        
                        # 체크박스 클릭
                        row_index = i + 1
                        checkbox_label_xpath = f"/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[2]/div/div[3]/div[2]/table/tbody/tr[{row_index}]/td[1]/span/label"
                        checkbox_label = self.wait.until(EC.element_to_be_clickable((By.XPATH, checkbox_label_xpath)))
                        checkbox_label.click()
                        print(f"   체크박스 클릭 완료")
                        time.sleep(1)
                        
                        # 현재 행의 금액 추출하여 CSV 데이터와 매칭
                        current_amount_text = current_amount_cells[i].text
                        matching_data = self._find_matching_data(current_amount_text, processed_data)
                        
                        if matching_data:
                            print(f"   매칭된 데이터 찾음: 금액={matching_data.get('amount')}, 적요={matching_data.get('note')}, 프로젝트={matching_data.get('project')}")
                            # 실제 CSV 데이터로 폼 입력
                            self._input_form_data(matching_data)
                        else:
                            print(f"   매칭되는 데이터 없음 - 기본값 사용")
                            # 매칭되는 데이터가 없으면 기본값 사용
                            self._input_default_form_data()
                        
                        # 저장
                        self._click_save(matching_data if matching_data else None)
                        print(f"   행 {i+1} 처리 완료")
                        round_processed += 1
                        
                    except Exception as e:
                        print(f"   행 {i+1} 처리 중 오류: {e}")
                        continue
                
                print(f"라운드 {round_number} 완료: {round_processed}개 처리됨")
                
                # 처리된 데이터가 있으면 전체 체크박스 클릭 후 반영
                if round_processed > 0:
                    has_next_page = self._check_has_next_page()
                    
                    print("전체 체크박스 클릭 및 반영 시작...")
                    
                    if self._click_select_all_checkbox():
                        if self._click_apply_button():
                            print(f"{round_processed}개 데이터 반영 완료")
                            time.sleep(2)
                            
                            if not has_next_page:
                                print("다음 페이지가 없어 작업을 종료합니다")
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
            print("브라우저가 열린 상태로 유지됩니다. 확인 후 수동으로 닫아주세요.")
            if progress_callback:
                progress_callback("모든 작업이 완료되었습니다! (브라우저는 열린 상태로 유지됩니다)")
            
        except Exception as e:
            print(f"자동화 실패: {e}")
            if progress_callback:
                progress_callback(f"작업 중 오류 발생: {str(e)}")
            print("오류가 발생했지만 브라우저는 열린 상태로 유지됩니다.")
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
                        time.sleep(2)
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

    def _click_select_all_checkbox(self):
        """전체 체크박스 클릭"""
        try:
            print("전체 체크박스 클릭...")
            
            # 성공한 셀렉터 사용
            select_all_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[2]/div/div[3]/div[1]/div/table/thead/tr/th[1]/input")))
            select_all_btn.click()
            time.sleep(2)
            
            print("전체 체크박스 클릭 완료")
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
