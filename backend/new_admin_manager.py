from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import ElementConfig, SiteConfig, DateConfig
import time
import os

class NewAdminManager:
    """새로운 어드민 시스템(볼드워크 등) 데이터 수집 관리 클래스"""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.common_config = SiteConfig.NEW_ADMIN_CONFIG
    
    def _click_element(self, driver, selector):
        """요소 클릭 (JavaScript)"""
        try:
            element = WebDriverWait(driver, ElementConfig.WAIT['default']).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            driver.execute_script(ElementConfig.JS['click'], element)
            self._wait_for_masks(driver)
        except Exception as e:
            print(f"요소 클릭 실패 ({selector}): {str(e)}")
            raise
    
    def _wait_for_masks(self, driver):
        """로딩 마스크 대기"""
        try:
            WebDriverWait(driver, ElementConfig.WAIT['default']).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, ElementConfig.LOADING_MASK))
            )
        except:
            pass  # 마스크가 없어도 계속 진행
    
    def _click_menus(self, driver, menu_config):
        """메뉴 클릭"""
        try:
            # 메인 메뉴
            main_menu = menu_config["main_menu"]
            self._click_element(driver, main_menu)
            print("메인 메뉴 클릭")
            
            # SMS 서비스 메뉴
            sms_service = menu_config["sms_service"]
            self._click_element(driver, sms_service)
            print("SMS 서비스 메뉴 클릭")
            
            # SMS 이력 메뉴
            sms_history = menu_config["sms_history"]
            self._click_element(driver, sms_history)
            print("SMS 이력 메뉴 클릭")
            
            return True
        except Exception as e:
            print(f"메뉴 클릭 실패: {str(e)}")
            return False
    
    def process_sms_data(self, driver, config):
        """SMS 데이터 처리"""
        try:
            # 1. 메뉴 클릭
            if not self._click_menus(driver, config["menu"]):
                return False
            
            # 2. iframe 전환
            iframe_index = config["iframe_index"]
            self._switch_to_iframe(driver, iframe_index)
            
            # 3. 날짜 설정
            month = DateConfig.get_new_admin_month()
            self._set_date(driver, month["month_key"])
            
            # 4. 브랜드 선택 (설정된 경우)
            if config.get("brand", {}).get("enabled"):
                self._select_brands(driver, config["brand"]["list"])
            
            # 5. 검색 실행
            search_button = config.get("search_button", "button.btn-primary")
            self._click_element(driver, search_button)
            
            # 6. 데이터 없음 체크
            if self._check_no_data(driver):
                print("데이터가 없습니다.")
                return False
            
            # 7. 다운로드 실행
            download_button = config.get("download_button", "button.btn-default")
            self._click_element(driver, download_button)
            
            print("데이터 다운로드 완료")
            return True
            
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            return False
    
    def _switch_to_iframe(self, driver, index):
        """iframe 전환"""
        try:
            WebDriverWait(driver, ElementConfig.WAIT['default']).until(
                EC.frame_to_be_available_and_switch_to_it(index)
            )
        except Exception as e:
            print(f"iframe 전환 실패: {str(e)}")
            raise
    
    def _set_date(self, driver, month):
        """날짜 설정"""
        try:
            # 날짜 선택자 목록에서 첫 번째로 발견되는 선택자 사용
            date_selectors = self.common_config["sms"]["date_selectors"]
            for selector in date_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    element.clear()
                    element.send_keys(month)
                    self._wait_for_masks(driver)
                    return
                except:
                    continue
            raise Exception("날짜 선택자를 찾을 수 없습니다.")
        except Exception as e:
            print(f"날짜 설정 실패: {str(e)}")
            raise
    
    def _select_brands(self, driver, brands):
        """브랜드 선택"""
        try:
            # 브랜드 선택 드롭다운 클릭
            brand_selector = self.common_config["sms"]["brand_selector"]
            self._click_element(driver, brand_selector)
            
            # 각 브랜드 선택
            for brand in brands:
                try:
                    xpath = f"//li[contains(text(), '{brand}')]"
                    element = WebDriverWait(driver, ElementConfig.WAIT['default']).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    driver.execute_script(ElementConfig.JS['click'], element)
                    self._wait_for_masks(driver)
                except:
                    print(f"브랜드 '{brand}' 선택 실패")
                    continue
        except Exception as e:
            print(f"브랜드 선택 실패: {str(e)}")
            raise
    
    def _check_no_data(self, driver):
        """데이터 없음 체크"""
        try:
            alert_selector = self.common_config["sms"]["no_data_alert"]
            no_data_text = self.common_config["sms"]["no_data_text"]
            
            alert = WebDriverWait(driver, ElementConfig.WAIT['short']).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, alert_selector))
            )
            return no_data_text in alert.text
        except:
            return False