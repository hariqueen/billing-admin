class ExpenseConfig:
    """지출결의서 자동화 설정 및 엘리먼트 정보"""
    
    # 그룹웨어 기본 설정
    GROUPWARE_URL = "https://gw.meta-m.co.kr/exp/ex/expend/master/ExUserMasterPop.do?formId=34&template_key=34&formSeq=34&processId=EXPENDU&form_id=34&form_tp=EXPENDU&doc_width=900&formTp=EXPENDU"
    LOGIN_URL = "https://gw.meta-m.co.kr/gw/userMain.do"
    LOGIN_TIMEOUT = 30
    PAGE_LOAD_TIMEOUT = 15
    SAVE_LIMIT = 100  # 저장 횟수 제한
    
    # 카드 사용내역 페이지 엘리먼트
    CARD_ELEMENTS = {
        # 카드 사용내역 버튼
        "card_history_btn": "//button[@id='btnExpendInterfaceCard']",
        "card_history_btn_xpath": "/html/body/div[4]/div[2]/div/div[2]/div[1]/div[2]/div/button[1]",
        
        # 선택 버튼
        "select_btn": "//button[@id='btnExpendCardInfoHelpPop']",
        "select_btn_xpath": "/html/body/div[4]/div[3]/div[3]/div[2]/div[1]/dl/dd[3]/div/button[1]",

        # 최신순 정렬 버튼
        "latest_sort_label": "//label[@for='cardSortingDesc']",
        "latest_sort_xpath": "/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[1]/div[1]/div/label[2]",
        "latest_sort_radio": "//input[@id='cardSortingDesc']",
                
        # 날짜 입력 필드
        "start_date_input": "//input[@id='txtExpendCardFromDate']",
        "start_date_xpath": "/html/body/div[4]/div[3]/div[3]/div[2]/div[1]/dl/dd[1]/span[1]/span/input",
        "end_date_input": "//input[@id='txtExpendCardToDate']",
        "end_date_xpath": "/html/body/div[4]/div[3]/div[3]/div[2]/div[1]/dl/dd[1]/span[2]/span/input",
        
        # 검색 버튼
        "search_btn": "//button[@id='btnExpendCardListSearch']",
        "search_btn_xpath": "/html/body/div[4]/div[3]/div[3]/div[2]/div[1]/dl/dd[3]/div/button[2]",
        
        # 데이터 입력 필드
        "standard_summary_input": "//input[@id='txtExpendCardDispSummary']",
        "standard_summary_xpath": "/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[2]/div[2]/table/tbody/tr[4]/td/div/input",
        
        "evidence_type_input": "//input[@id='txtExpendCardDispAuth']",
        "evidence_type_xpath": "/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[2]/div[2]/table/tbody/tr[5]/td/input",
        
        "note_input": "//input[@id='txtExpendCardDispNote']",
        "note_xpath": "/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[2]/div[2]/table/tbody/tr[8]/td/input",
        
        "project_input": "//input[@id='txtExpendCardDispProject']",
        "project_xpath": "/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[2]/div[2]/table/tbody/tr[9]/td/input",
        
        # 저장 버튼
        "save_btn": "//button[@id='btnExpendCardInfoSave']",
        "save_btn_xpath": "/html/body/div[4]/div[3]/div[3]/div[2]/div[1]/dl/dd[3]/div/button[2]",
        
        # 체크박스 (동적 생성되므로 기본 셀렉터)
        "checkbox_selector": "input[name='inp_CardChk']",
        "checkbox_xpath_base": "/html/body/div[4]/div[3]/div[3]/div[2]/table/tbody/tr/td[1]/div[2]/div/div[3]/div[2]/table/tbody/tr",
        
        # 반영 버튼
        "apply_btn": "//input[@id='btnExpendCardToExpend']",
        "apply_btn_xpath": "/html/body/div[4]/div[3]/div[3]/div[3]/div/input",
        
        # 금액 테이블 셀렉터
        "amount_table": "td.td_ri span.fwb"
    }
    
    # 데이터 컬럼 매핑 (CSV/Excel 컬럼명)
    COLUMN_MAPPING = {
        "매출금액": "amount",
        "표준적요": "standard_summary", 
        "증빙유형": "evidence_type",
        "적요": "note",
        "프로젝트": "project"
    }
