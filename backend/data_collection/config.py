from datetime import datetime, timedelta
from selenium.webdriver.common.keys import Keys

def get_previous_month_range():
    """현재 날짜 기준으로 한 달 전 1일부터 말일까지 날짜 계산"""
    today = datetime.now()
    current_year = today.year
    current_month = today.month
    
    # 한 달 전 계산
    if current_month == 1:
        prev_year = current_year - 1
        prev_month = 12
    else:
        prev_year = current_year
        prev_month = current_month - 1
    
    # 한 달 전 1일
    start_date = datetime(prev_year, prev_month, 1)
    # 한 달 전 말일
    end_date = datetime(prev_year, prev_month + 1, 1) - timedelta(days=1)
    
    return {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }

class ElementConfig:
    """요소 관련 설정"""
    
    # 공통 셀렉터
    LOADING_MASK = ".loading-mask, .loading-overlay"
    
    # 공통 JavaScript
    JS = {
        "click": "arguments[0].click();",
        "remove_mask": "document.querySelector('.ax-mask-body').remove();",
        "remove_brand": "document.querySelector('div[data-ax5autocomplete-remove=\"true\"]').click();"
    }
    
    # 공통 대기 시간 (초)
    WAIT = {
        "default": 10,
        "short": 3,
        "long": 30,
        "key_interval": 0.5,  
        "download_check": 1,  
        "brand_select": 0.5   
    }
    
    # 공통 셀렉터
    COMMON = {
        "loading_mask": ".ax-mask-body",
        "alert_ok_button": "button[data-dialog-btn='ok']",
        "download_button": "button.btn-default",
        "search_button": "button.btn-primary",
        "excel_download_button": "button[data-grid-control='excel-download']",
        "alert_dialog": "#ax5-dialog-29",
        "alert_message": "#ax5-dialog-29 .ax-dialog-msg",
        "alert_ok": "#ax5-dialog-29 button[data-dialog-btn='ok']",
        "brand_remove": "div[data-ax5autocomplete-remove='true']",
        "no_data_text": "검색된 데이터가 없습니다"
    }

    # 파일 관련 설정
    FILE = {
        "download_dir": "/Users/haribo/Downloads",  # 다운로드 폴더
        "excel_extensions": [".xlsx", ".xls"],      # 엑셀 파일 확장자
        "temp_extension": ".crdownload"             # 임시 파일 확장자
    }

    # iframe 관련 설정
    IFRAME = {
        "default_index": 1,  # 기본 iframe 인덱스 (0-based)
        "brand_popup_index": 1,  # 브랜드 팝업용 iframe 인덱스
        "data_index": 1  # 데이터 처리용 iframe 인덱스
    }

    # 브랜드 선택 관련 설정
    BRAND = {
        "key_sequence": {
            "select": [Keys.ARROW_DOWN, Keys.ENTER],  # 브랜드 선택용 키 시퀀스
            "remove": [Keys.ESCAPE]  # 브랜드 제거용 키 시퀀스
        },
        "messages": {
            "start": " {} 브랜드 처리 시작",
            "select": " {} 브랜드 선택 완료",
            "remove": " X버튼 클릭 완료",
            "complete": " {} 브랜드 처리 완료",
            "no_data": "마지막 브랜드 {}에서 데이터 없음 - 종료",
            "error": " {} 브랜드 처리 중 예외 발생: {}"
        }
    }

    # 상태 메시지
    MESSAGES = {
        "iframe": {
            "check": " iframe 확인 중...",
            "success": " iframe {}로 전환 완료",
            "error": " iframe이 부족함 (현재 {}개)"
        },
        "download": {
            "start": " 다운로드 시작",
            "waiting": " 다운로드 대기 중... ({}/{}초)",
            "complete": " 다운로드 완료: {}",
            "timeout": " 다운로드 대기 시간 초과"
        },
        "alert": {
            "no_data": "검색된 데이터가 없습니다. 다음 단계로 진행.",
            "close_success": " 데이터 없음 알림창 처리 완료 (방법: {})",
            "close_error": " 데이터 없음 알림창 처리 실패"
        }
    }

    # 채팅 관련 셀렉터 (brand_x_test.py, data_manager.py 호환)
    CHAT = {
        "id_input": "#userCd",
        "pw_input": "#userPs",
        "login_btn": "#formView01 > div.panel-body > div.panel-right > table > tbody > tr:nth-child(2) > td:nth-child(3) > button",
        "agree_checkbox": "#agreeCheck",
        "alert_ok_btn": "#ax5-dialog-29 > div.ax-dialog-body > div.ax-dialog-buttons > div > button",
        "menu_chat": "//span[@id='aside-menu-0_47_span'][contains(text(), '채팅관리')]",
        "menu_chat_list": "//span[@id='aside-menu-0_53_span'][contains(text(), '채팅진행건리스트')]",
        "team_tag_remove": "div[data-ax5autocomplete-remove='true']",
        "start_date_input": "#searchView01 > div > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div > input:nth-child(1)",
        "end_date_input": "#searchView01 > div > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div > input:nth-child(3)",
        "calendar_left_year": "div.ax-picker-content > div:nth-child(1) div.date-display span[data-calendar-display='year']",
        "calendar_left_month": "div.ax-picker-content > div:nth-child(1) div.date-display span[data-calendar-display='month']",
        "calendar_left_prev": "div.ax-picker-content > div:nth-child(1) a.date-move-left[data-calendar-move='left']",
        "calendar_left_next": "div.ax-picker-content > div:nth-child(1) a.date-move-right[data-calendar-move='right']",
        "calendar_left_day": "div.ax-picker-content > div:nth-child(1) a[data-calendar-item-date='{}']",
        "calendar_right_year": "div.ax-picker-content > div:nth-child(3) div.date-display span[data-calendar-display='year']",
        "calendar_right_month": "div.ax-picker-content > div:nth-child(3) div.date-display span[data-calendar-display='month']",
        "calendar_right_prev": "div.ax-picker-content > div:nth-child(3) a.date-move-left[data-calendar-move='left']",
        "calendar_right_next": "div.ax-picker-content > div:nth-child(3) a.date-move-right[data-calendar-move='right']",
        "calendar_right_day": "div.ax-picker-content > div:nth-child(3) a[data-calendar-item-date='{}']",
        "calendar_ok_btn": "div.ax-picker-buttons > button:nth-child(2)",
        "search_btn": "#titleBtn > button:nth-child(2)",
        "excel_btn": "#titleBtn > button:nth-child(1)",
        "x_btn": "div[data-ax5autocomplete-remove='true']",
        "iframe_index": 1,
    }

class DateConfig:
    """날짜 설정"""
    
    _start_date = None
    _end_date = None
    
    @classmethod
    def set_dates(cls, start_date, end_date):
        """날짜 설정"""
        cls._start_date = start_date
        cls._end_date = end_date
    
    @classmethod
    def set_default_dates(cls):
        """기본 날짜 설정 (한 달 전 1일부터 말일까지)"""
        date_range = get_previous_month_range()
        cls._start_date = date_range["start_date"]
        cls._end_date = date_range["end_date"]
        print(f" 기본 날짜 설정: {cls._start_date} ~ {cls._end_date}")
    
    @classmethod
    def get_dates(cls):
        """현재 설정된 날짜 반환 (설정되지 않은 경우 기본값으로 설정)"""
        if cls._start_date is None or cls._end_date is None:
            cls.set_default_dates()
        return {
            "start_date": cls._start_date,
            "end_date": cls._end_date
        }
    
    @classmethod
    def get_sms_format(cls):
        """SMS용 날짜 포맷"""
        if not cls._start_date or not cls._end_date:
            raise ValueError("날짜가 설정되지 않았습니다")
        
        from datetime import datetime
        start = datetime.strptime(cls._start_date, "%Y-%m-%d")
        end = datetime.strptime(cls._end_date, "%Y-%m-%d")
        
        return {
            "start_date": start.strftime("%Y%m%d"),
            "end_date": end.strftime("%Y%m%d")
        }
    
    @classmethod
    def get_call_format(cls):
        """CALL용 날짜 포맷"""
        if not cls._start_date or not cls._end_date:
            raise ValueError("날짜가 설정되지 않았습니다")
        
        return {
            "start_date": cls._start_date,
            "end_date": cls._end_date
        }
    
    @classmethod
    def get_new_admin_month(cls):
        """새 어드민용 월 추출"""
        if not cls._start_date:
            raise ValueError("날짜가 설정되지 않았습니다")
        
        # "2025-05-01"에서 "2025-05" 추출
        month_key = cls._start_date[:7]  # YYYY-MM
        month_num = cls._start_date[5:7]  # MM (05)
        
        return {
            "month_key": month_key,     # "2025-05" (li[data-range-key="2025-05"] 클릭용)
            "month_num": month_num,     # "05" (5월)
            "month_name": f"{int(month_num)}월"  # "5월" (로그용)
        }

class AccountConfig:
    """계정별 설정 관리 (중복 없이 단일화)"""
    # 고객사 목록
    COMPANIES = [
        # ICS 진입 고객사 (크롤링 가능)
        "앤하우스",
        "디싸이더스/애드프로젝트",
        "매스프레소(콴다)",
        "구쁘",
        # 수동 업로드 고객사
        "SK일렉링크",
        "코오롱Fnc",
        "W컨셉",
        "메디빌더"
    ]
    
    # SMS 계정 설정
    SMS_CONFIG = {
        "SK일렉링크": {
            "id_selector": "#userCd",
            "pw_selector": "#userPs",
            "login_btn": "#formView01 > div.panel-body > div.panel-right > table > tbody > tr:nth-child(2) > td:nth-child(3) > button",
            "need_softphone_off": False,
            "checkbox_selector": "#agreeCheck",
            "sms_service_selector": "#aside-menu-0_25_span",
            "sms_history_selector": "#aside-menu-0_27_span",
            "start_date_selector": "input[name='schSdate']",
            "end_date_selector": "input[name='schEdate']",
            "search_btn_text": "조회",
            "download_btn_selector": "#titleBtn > button:nth-child(1)"
        },
        "앤하우스": {
            "id_selector": "#userCd",
            "pw_selector": "#userPs",
            "login_btn": "#formView01 > div.panel-body > div.panel-right > table > tbody > tr:nth-child(2) > td:nth-child(3) > button",
            "need_softphone_off": False,
            "checkbox_selector": "#agreeCheck",
            "sms_service_selector": "#aside-menu-0_31_a",
            "sms_history_selector": "#aside-menu-0_33_span",
            "start_date_selector": "input[name='schSdate']",
            "end_date_selector": "input[name='schEdate']",
            "search_btn_text": "조회",
            "download_btn_selector": "#titleBtn > button:nth-child(1)"
        },
        "디싸이더스/애드프로젝트": {
            "id_selector": "#userCd",
            "pw_selector": "#userPs",
            "login_btn": "#formView01 > div.panel-body > div.panel-right > table > tbody > tr:nth-child(2) > td:nth-child(3) > button",
            "need_softphone_off": False,
            "checkbox_selector": "#agreeCheck",
            "sms_service_selector": "#aside-menu-0_16_span",
            "sms_history_selector": "#aside-menu-0_18_span",
            "start_date_selector": "input[name='schSdate']",
            "end_date_selector": "input[name='schEdate']",
            "search_btn_text": "조회",
            "download_btn_selector": "#titleBtn > button:nth-child(1)",
            "has_brands": True,
            "brands": ["엑스퍼", "스마트웰컴", "바이오숨", "스마트웰", "유리제로"],
            "brand_dropdown_selector": "input[data-ax5autocomplete-display='input']",
            "brand_remove_btn_selector": "#searchView > div > div:nth-child(2) > div:nth-child(2) > div > div > div > div > a > div > div:nth-child(1)",
            "sms_iframe_index": 1,
            "is_new_admin": True
        },
        "매스프레소(콴다)": {
            "id_selector": "#userCd",
            "pw_selector": "#userPs",
            "login_btn": "#formView01 > div.panel-body > div.panel-right > table > tbody > tr:nth-child(2) > td:nth-child(3) > button",
            "need_softphone_off": False,
            "checkbox_selector": "#agreeCheck",
            "sms_service_selector": "#aside-menu-0_19_span",
            "sms_history_selector": "#aside-menu-0_21_span",
            "start_date_selector": "input[name='schSdate']",
            "end_date_selector": "input[name='schEdate']",
            "search_btn_text": "조회",
            "download_btn_selector": "#titleBtn > button:nth-child(1)",
            "has_brands": True,
            "brands": ["콴다"],
            "brand_dropdown_selector": "input[data-ax5autocomplete-display='input']",
            "sms_iframe_index": 1
        },
        "구쁘": {
            "id_selector": "#projUserCd",
            "pw_selector": "#userPs",
            "login_btn": "#loginBtn",
            "need_softphone_off": True,
            "checkbox_selector": "#agreeCheck",
            "sms_service_selector": "#sidebar > div > div.top.tab-wrap > ul > li:nth-child(2) > a",
            "sms_menu_selector": "#menuNav > li:nth-child(5) > a",
            "sms_history_selector": "#menu_5603 > li:nth-child(2)",
            "start_date_selector": "#startDt",
            "end_date_selector": "#endDt",
            "display_date_selector": "#pickerViewdt",
            "search_btn_selector": "body > div.content-wrap > div.cont-top > div.title-wrap > div > button:nth-child(1)",
            "download_btn_selector": "body > div.content-wrap > div.cont-top > div.title-wrap > div > button:nth-child(2)",
            "sms_iframe_index": 2,
            "is_guppu": True
        }
    }
    # CALL 계정 설정
    CALL_CONFIG = {
        "앤하우스": {
            "id_selector": "#textfield-3551-inputEl",
            "pw_selector": "#textfield-3552-inputEl",
            "checkbox_selector": "#chkAgree-displayEl",
            "login_btn": "#login-btn-btnInnerEl",
            "company_text": "앤하우스",
            "outbound_selector": "#uxtagfield-2171-inputEl",
            "call_status_selector": "#uxtagfield-2172-inputEl",
            "start_date_selector": "#datefield-2168-inputEl",
            "end_date_selector": "#datefield-2170-inputEl",
            "search_btn_selector": "#button-2153",
            "download_btn_selector": "#button-2155",
            "no_data_alert_selector": "#ax5-dialog-29 .ax-dialog-msg",
            "no_data_text": "검색된 데이터가 없습니다"
        }
    }

class SiteConfig:
    NEW_ADMIN_CONFIG = {
        "menu": {
            "main_menu": "#sidebar > div > div.top.tab-wrap > ul > li:nth-child(2) > a",
            "sms_service": "#menuNav > li:nth-child(5) > a",
            "sms_history": "#menu_5423 > li:nth-child(2) > a"
        },
        "sms": {
            "iframe_index": 0,
            "date_selectors": ["#pickerViewdt", "#schForm > table > tbody > tr:nth-child(1) > td:nth-child(2) > div", "#startDt"],
            "brand_selector": "span.select2-selection",
            "search_button": "body > div.content-wrap > div.cont-top > div.title-wrap > div > button:nth-child(1)",
            "download_button": "body > div.content-wrap > div.cont-top > div.title-wrap > div > button:nth-child(2)",
            "no_data_alert": ".alert",
            "no_data_text": "데이터가 없습니다"
        }
    }