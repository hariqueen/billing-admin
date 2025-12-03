from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import threading
from datetime import datetime
import uuid
import traceback
from pathlib import Path
import json
import tempfile

from backend.data_collection.database import DatabaseManager
from backend.data_collection.login_manager import LoginManager
from backend.data_collection.data_manager import DataManager
from backend.data_collection.new_admin_manager import NewAdminManager

from backend.expense_automation.data_processor import ExpenseDataProcessor
from backend.expense_automation.groupware_bot import GroupwareAutomation
from backend.data_collection.config import DateConfig, AccountConfig, ElementConfig
from backend.preprocessing.anhous_preprocessing import AnhousPreprocessor
from backend.preprocessing.kolon_preprocessing import KolonPreprocessor
from backend.preprocessing.sk_preprocessing import SKPreprocessor
from backend.preprocessing.deciders_preprocessing import DecidersPreprocessor
from backend.preprocessing.bill_processor import BillProcessor
from backend.storage.admin_storage import AdminStorage

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 전역 예외 핸들러 추가
@app.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    import sys
    import traceback
    print("="*60)
    print("❌ Flask 500 에러 핸들러 호출")
    print(f"에러: {error}")
    print("스택 트레이스:")
    print(traceback.format_exc())
    print("="*60)
    sys.stdout.flush()
    return jsonify({
        "success": False,
        "error": f"내부 서버 오류: {str(error)}"
    }), 500

# 요청 전후 로깅 미들웨어 추가 (지출결의서 요청만)
# [DEBUG] 로그 중복 방지를 위해 before_request 로그 제거 - expense_automation 함수 내에서 이미 로그 출력
# @app.before_request
# def log_request_info():
#     """요청 전 로깅"""
#     pass

@app.after_request
def log_response_info(response):
    """응답 후 로깅"""
    if request.path == '/api/expense-automation':
        import sys
        print(f"📤 지출결의서 응답 전송: {response.status_code}")
        sys.stdout.flush()
    return response

# 크롤링 모듈 초기화
db_manager = DatabaseManager()
login_manager = LoginManager()
data_manager = DataManager(login_manager)
new_admin_manager = NewAdminManager(data_manager)
admin_storage = AdminStorage()
bill_processor = BillProcessor(admin_storage)
print("크롤링 시스템 초기화 완료")

# 작업 상태 저장
task_status = {}

print("청구자동화 API 서버 시작")
print("모드: 실제 크롤링")

# Xvfb는 headless Chrome 모드에서는 필요 없음
# Chrome이 --headless=new 모드로 실행되므로 가상 디스플레이 불필요

# 환경에 따라 호스트 자동 설정
import socket
def get_host_ip():
    try:
        # EC2에서는 실제 IP 반환
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return "13.125.245.229" if ip.startswith("172.31") else "localhost"
    except:
        return "localhost"

host = get_host_ip()
print(f"Frontend: http://{host}:3000")
print(f"Backend API: http://{host}:5001")

@app.route('/api/companies', methods=['GET'])
def get_companies():
    """고객사 목록 조회"""
    try:
        return jsonify({
            "companies": AccountConfig.COMPANIES
        })
    except Exception as e:
        print(f"고객사 목록 조회 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    return jsonify({
        "status": "healthy", 
        "message": "API 서버가 정상 작동중 (실제 크롤링 모드)",
        "crawling_available": True,
        "modules": {
            "database": 'db_manager' in globals(),
            "login_manager": 'login_manager' in globals(),
            "data_manager": 'data_manager' in globals()
        }
    })

@app.route('/api/collect-data', methods=['POST'])
def collect_data():
    """실제 데이터 수집"""
    try:
        data = request.get_json()
        company_name = data.get('company_name')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        print(f"데이터 수집 요청: {company_name}, {start_date} ~ {end_date}")
        
        if not all([company_name, start_date, end_date]):
            return jsonify({"error": "필수 파라미터 누락"}), 400
        
        # 작업 ID 생성
        task_id = str(uuid.uuid4())
        task_status[task_id] = {
            "status": "starting",
            "company": company_name,
            "files": [],
            "progress": 0,
            "log": [f" {company_name} 데이터 수집 시작"],
            "crawling_mode": True
        }
        
        def run_real_crawling():
            try:
                print(f"\n{'='*60}")
                print(f"🚀 run_real_crawling 함수 시작 - 회사: {company_name}")
                print(f"{'='*60}\n")
                import sys
                sys.stdout.flush()
                
                task_status[task_id]["status"] = "running"
                task_status[task_id]["progress"] = 10
                task_status[task_id]["log"].append("🔧 시스템 초기화 중...")
                
                # 실제 크롤링 실행
                task_status[task_id]["log"].append("🌐 실제 크롤링 모드로 실행")
                
                # 날짜 설정 (제공되지 않은 경우 기본값 사용)
                if start_date and end_date:
                    DateConfig.set_dates(start_date, end_date)
                    task_status[task_id]["log"].append(f"날짜 설정: {start_date} ~ {end_date}")
                else:
                    DateConfig.set_default_dates()
                    dates = DateConfig.get_dates()
                    task_status[task_id]["log"].append(f"기본 날짜 설정: {dates['start_date']} ~ {dates['end_date']}")
                
                # 1단계: SMS 계정 로그인 및 데이터 수집
                task_status[task_id]["progress"] = 20
                task_status[task_id]["log"].append(f"{company_name} SMS 로그인 시작...")
                
                try:
                    # SMS 계정 정보 가져오기
                    sms_accounts = db_manager.get_accounts_by_type("sms")
                    target_account = None
                    for account in sms_accounts:
                        if account['company_name'] == company_name:
                            target_account = account
                            break
                    
                    if not target_account:
                        error_msg = f"{company_name} SMS 계정 정보를 찾을 수 없습니다"
                        print(f"❌ {error_msg}")
                        raise Exception(error_msg)
                    
                    # SMS 로그인
                    task_status[task_id]["log"].append(f"{company_name} SMS 로그인 시도 중...")
                    try:
                        login_success, login_driver = login_manager.login_account(target_account, keep_session=True)
                        task_status[task_id]["log"].append(f"로그인 결과: {login_success}")
                        
                        if not login_success:
                            error_msg = f"{company_name} SMS 로그인 실패"
                            print(f"❌ {error_msg}")
                            task_status[task_id]["log"].append(f"❌ {error_msg}")
                            raise Exception(error_msg)
                            
                        task_status[task_id]["log"].append(f"✅ {company_name} SMS 로그인 성공")
                    except Exception as login_err:
                        print(f"❌ 로그인 예외 발생: {login_err}")
                        import traceback
                        print(traceback.format_exc())
                        task_status[task_id]["log"].append(f"❌ 로그인 예외: {str(login_err)}")
                        raise
                    
                    # SMS 데이터 수집
                    task_status[task_id]["progress"] = 40
                    task_status[task_id]["log"].append(f"{company_name} SMS 데이터 수집 시작...")
                    
                    # 실제 SMS 크롤링 실행
                    sms_result = False
                    sms_collection_start_time = None
                    try:
                        import time
                        sms_collection_start_time = time.time()
                        sms_result = data_manager.download_sms_data(
                            company_name, 
                            DateConfig.get_sms_format()["start_date"], 
                            DateConfig.get_sms_format()["end_date"]
                        )
                        task_status[task_id]["log"].append(f"SMS 크롤링 결과: {sms_result}")
                    except Exception as crawl_error:
                        print(f"❌ SMS 크롤링 중 예외 발생: {crawl_error}")
                        import traceback
                        print(traceback.format_exc())
                        task_status[task_id]["log"].append(f"❌ SMS 크롤링 중 예외: {str(crawl_error)}")
                        sms_result = False
                    
                    # SMS 수집 직후 다운로드된 파일 찾기
                    download_dir = "/app/downloads"
                    os.makedirs(download_dir, exist_ok=True)
                    
                    if sms_collection_start_time and sms_result:
                        # SMS 수집 시작 이후 생성된 파일만 필터링
                        all_excel_files = [f for f in os.listdir(download_dir) if f.endswith(('.xlsx', '.xls'))] if os.path.exists(download_dir) else []
                        sms_candidate_files = []
                        for filename in all_excel_files:
                            file_path = os.path.join(download_dir, filename)
                            if os.path.getctime(file_path) >= sms_collection_start_time:
                                sms_candidate_files.append((filename, os.path.getctime(file_path)))
                        
                        if sms_candidate_files:
                            # 앤하우스의 경우 발송이력 파일 우선 찾기
                            if company_name == "앤하우스":
                                sms_files = [f for f, t in sms_candidate_files if '발송이력' in f]
                                if sms_files:
                                    latest_file = max(sms_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                                else:
                                    latest_file = max([f for f, t in sms_candidate_files], key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                            elif company_name == "디싸이더스/애드프로젝트":
                                # 발송이력 파일들 모두 수집
                                recent_sms_files = [(f, t) for f, t in sms_candidate_files if '발송이력' in f]
                                recent_sms_files.sort(key=lambda x: x[1])
                                for filename, ctime in recent_sms_files:
                                    task_status[task_id]["files"].append(filename)
                                    task_status[task_id]["log"].append(f"✅ SMS 파일 수집 완료: {filename}")
                                if recent_sms_files:
                                    task_status[task_id]["sms_collection_time"] = recent_sms_files[-1][1]
                                latest_file = None
                            else:
                                latest_file = max([f for f, t in sms_candidate_files], key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                            
                            if latest_file:
                                task_status[task_id]["sms_collection_time"] = os.path.getctime(os.path.join(download_dir, latest_file))
                                task_status[task_id]["files"].append(latest_file)
                                task_status[task_id]["log"].append(f"✅ SMS 파일 수집 완료: {latest_file}")
                    
                    if not sms_result:
                        task_status[task_id]["log"].append("⚠️ SMS 데이터 수집 실패")
                    
                    # 디싸이더스/애드프로젝트인 경우 CHAT 데이터도 수집
                    if company_name == "디싸이더스/애드프로젝트":
                        task_status[task_id]["log"].append("CHAT 데이터 수집 시작...")
                        try:
                            # 세션 재사용을 위해 세션 종료하지 않고 계속 사용
                            session = login_manager.get_active_session(company_name, "sms")
                            if session:
                                driver = session['driver']
                                
                                # 페이지 새로고침 및 알림창 처리
                                driver.switch_to.default_content()
                                driver.refresh()
                                import time
                                time.sleep(2)
                                
                                try:
                                    from selenium.webdriver.support.ui import WebDriverWait
                                    from selenium.webdriver.support import expected_conditions as EC
                                    from selenium.webdriver.common.by import By
                                    
                                    alert_button = WebDriverWait(driver, 3).until(
                                        EC.element_to_be_clickable((By.CSS_SELECTOR, ElementConfig.CHAT["alert_ok_btn"]))
                                    )
                                    alert_button.click()
                                    time.sleep(1)
                                    task_status[task_id]["log"].append("알림창 처리 완료")
                                except Exception:
                                    pass
                                
                                # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
                                sms_dates = DateConfig.get_sms_format()
                                sms_start = sms_dates["start_date"]  # YYYYMMDD 형식
                                sms_end = sms_dates["end_date"]      # YYYYMMDD 형식
                                
                                chat_start = f"{sms_start[:4]}-{sms_start[4:6]}-{sms_start[6:]}"
                                chat_end = f"{sms_end[:4]}-{sms_end[4:6]}-{sms_end[6:]}"
                                
                                task_status[task_id]["log"].append(f"📅 CHAT 날짜 변환: {sms_start} -> {chat_start}, {sms_end} -> {chat_end}")
                                
                                # CHAT 데이터 수집 실행
                                chat_result = data_manager.process_chat_no_brand(driver, target_account.get('config', {}), chat_start, chat_end)
                                
                                if chat_result:
                                    task_status[task_id]["log"].append("CHAT 데이터 수집 완료")
                                    # CHAT 파일도 수집된 파일 목록에 추가
                                    xlsx_files = [f for f in os.listdir(download_dir) if f.endswith('.xlsx')]
                                    # SMS 수집 이후 생성된 파일 찾기 (CHAT 파일)
                                    chat_files = [f for f in xlsx_files if os.path.getctime(os.path.join(download_dir, f)) > task_status[task_id].get("sms_collection_time", 0)]
                                    if chat_files:
                                        latest_chat_file = max(chat_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                                        task_status[task_id]["files"].append(latest_chat_file)
                                        task_status[task_id]["log"].append(f"CHAT 파일 수집 완료: {latest_chat_file}")
                                    else:
                                        task_status[task_id]["log"].append(" CHAT 파일을 찾을 수 없음")
                                else:
                                    task_status[task_id]["log"].append(" CHAT 데이터 수집 실패 또는 데이터 없음")
                                    
                            else:
                                task_status[task_id]["log"].append(" SMS 세션을 찾을 수 없어 CHAT 수집 불가")
                                
                        except Exception as chat_error:
                            task_status[task_id]["log"].append(f" CHAT 수집 중 오류: {str(chat_error)}")
                    
                    # SMS 세션 종료
                    login_manager.close_session(company_name, "sms")
                    task_status[task_id]["log"].append(f" {company_name} SMS 세션 종료")
                        
                except Exception as sms_error:
                    error_detail = str(sms_error)
                    import traceback
                    error_traceback = traceback.format_exc()
                    print(f"❌ {company_name} SMS 수집 중 오류 발생:")
                    print(f"   오류 메시지: {error_detail}")
                    print(f"   상세 스택 트레이스:")
                    print(error_traceback)
                    task_status[task_id]["log"].append(f"❌ {company_name} SMS 수집 중 오류: {error_detail}")
                
                # 2단계: 앤하우스인 경우 CALL 데이터도 수집
                if company_name == "앤하우스":
                    task_status[task_id]["progress"] = 60
                    task_status[task_id]["log"].append("🔐 앤하우스 CALL 로그인 시작...")
                    
                    try:
                        # CALL 계정 정보 가져오기
                        call_accounts = db_manager.get_accounts_by_type("call")
                        call_account = None
                        for account in call_accounts:
                            if account['company_name'] == company_name:
                                call_account = account
                                break
                        
                        if not call_account:
                            raise Exception(f"{company_name} CALL 계정 정보를 찾을 수 없습니다")
                        
                        # CALL 로그인
                        call_login_success, _ = login_manager.login_account(call_account, keep_session=True)
                        if not call_login_success:
                            raise Exception(f"{company_name} CALL 로그인 실패")
                            
                        task_status[task_id]["log"].append(f" {company_name} CALL 로그인 성공")
                        task_status[task_id]["log"].append(" CALL 데이터 수집 시작...")
                        
                        call_result = data_manager.setup_call_data_collection(
                            company_name, 
                            start_date, 
                            end_date, 
                            download=True
                        )
                        
                        if call_result:
                            # CALL 수집 직후 다운로드된 파일 찾기
                            download_dir = "/app/downloads"
                            os.makedirs(download_dir, exist_ok=True)
                            # .xlsx와 .xls 파일 모두 찾기
                            excel_files = [f for f in os.listdir(download_dir) if f.endswith(('.xlsx', '.xls'))] if os.path.exists(download_dir) else []
                            
                            # SMS 파일 수집 시간 기록 (CALL과 구분하기 위해)
                            sms_collection_time = task_status[task_id].get("sms_collection_time")
                            
                            if sms_collection_time:
                                # SMS 수집 이후에 생성된 파일들만 필터링
                                call_files = []
                                for file in excel_files:
                                    file_path = os.path.join(download_dir, file)
                                    file_ctime = os.path.getctime(file_path)
                                    # 시간 필터링 + 파일명 기반 필터링 (통화내역 포함 확인)
                                    if file_ctime > sms_collection_time and '통화내역' in file:
                                        call_files.append(file)
                                
                                if call_files:
                                    # 가장 최근 CALL 파일 선택
                                    latest_call_file = max(call_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                                    task_status[task_id]["files"].append(latest_call_file)
                                    task_status[task_id]["log"].append(f" CALL 파일 수집 완료: {latest_call_file}")
                                else:
                                    # 통화내역 키워드 없이 시간 기반으로 재시도
                                    call_files_time_based = [f for f in excel_files if os.path.getctime(os.path.join(download_dir, f)) > sms_collection_time]
                                    if call_files_time_based:
                                        latest_call_file = max(call_files_time_based, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                                        task_status[task_id]["files"].append(latest_call_file)
                                        task_status[task_id]["log"].append(f" CALL 파일 수집 완료 (시간 기반): {latest_call_file}")
                                    else:
                                        task_status[task_id]["log"].append(" CALL 데이터 수집 실패: 새 파일이 생성되지 않음")
                            else:
                                # SMS 수집 시간이 없으면 파일명으로 CALL 파일 찾기
                                call_files_by_name = [f for f in excel_files if '통화내역' in f]
                                if call_files_by_name:
                                    latest_call_file = max(call_files_by_name, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                                    task_status[task_id]["files"].append(latest_call_file)
                                    task_status[task_id]["log"].append(f" CALL 파일 수집 완료: {latest_call_file}")
                                else:
                                    # 통화내역 키워드가 없으면 가장 최근 파일 (하위 호환성)
                                    if excel_files:
                                        latest_call_file = max(excel_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                                        task_status[task_id]["files"].append(latest_call_file)
                                        task_status[task_id]["log"].append(f" CALL 파일 수집 완료 (가장 최근 파일): {latest_call_file}")
                                    else:
                                        task_status[task_id]["log"].append(" CALL 데이터 수집 실패: 파일이 없음")
                        else:
                            task_status[task_id]["log"].append(" CALL 데이터 수집 실패 또는 데이터 없음")
                        
                        # CALL 세션 종료
                        login_manager.close_session(company_name, "call")
                        task_status[task_id]["log"].append(f" {company_name} CALL 세션 종료")
                            
                    except Exception as call_error:
                        task_status[task_id]["log"].append(f" CALL 수집 중 오류: {str(call_error)}")
                
                # 완료 처리
                if task_status[task_id]["files"]:
                    task_status[task_id]["status"] = "completed"
                    task_status[task_id]["progress"] = 100
                    task_status[task_id]["log"].append("✅ 데이터 수집 완료!")
                    print(f"✅ {company_name} 크롤링 완료 - 파일: {len(task_status[task_id]['files'])}개")
                else:
                    task_status[task_id]["status"] = "completed"
                    task_status[task_id]["progress"] = 100
                    task_status[task_id]["log"].append("⚠️ 수집된 파일이 없습니다 (데이터 없음 또는 오류)")
                    print(f"⚠️ {company_name} 크롤링 완료 - 하지만 파일이 없음 (오류 가능성)")
                
            except Exception as e:
                task_status[task_id]["status"] = "failed"
                task_status[task_id]["error"] = str(e)
                task_status[task_id]["log"].append(f"심각한 오류 발생: {str(e)}")
        
        # 백그라운드에서 실행
        thread = threading.Thread(target=run_real_crawling)
        thread.daemon = True
        thread.start()
        
        return jsonify({"task_id": task_id, "status": "started"})
        
    except Exception as e:
        print(f" API 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/task-status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """작업 상태 조회"""
    if task_id not in task_status:
        return jsonify({"error": "작업을 찾을 수 없습니다"}), 404
    
    status = task_status[task_id]
    print(f"Task {task_id[:8]}... 상태: {status['status']} ({status['progress']}%)")
    return jsonify(status)

@app.route('/api/upload-file', methods=['POST'])
def upload_file():
    """파일 업로드 (다중 파일 지원)"""
    try:
        company_name = request.form.get('company_name')
        file_index = request.form.get('file_index', '0')
        file_label = request.form.get('file_label', '')
        
        # 자동업로드 모드 (파일이 없는 경우)
        if 'file' not in request.files:
            collected_filename = request.form.get('collected_filename')
            if collected_filename:
                # 다운로드 폴더에서 파일 찾기
                download_dir = "/app/downloads"
                os.makedirs(download_dir, exist_ok=True)
                source_path = os.path.join(download_dir, collected_filename)
                
                # 파일 존재 여부와 접근 가능성 확인
                if not os.path.exists(source_path):
                    return jsonify({"error": f"파일을 찾을 수 없습니다: {collected_filename}"}), 404
                
                if not os.path.isfile(source_path):
                    return jsonify({"error": f"유효하지 않은 파일입니다: {collected_filename}"}), 400
                
                if not os.access(source_path, os.R_OK):
                    return jsonify({"error": f"파일 읽기 권한이 없습니다: {collected_filename}"}), 403
                
                # 임시 폴더 생성 (전처리 후 자동 삭제)
                temp_dir = "temp_processing"
                os.makedirs(temp_dir, exist_ok=True)
                
                # 파일명 생성 (슬래시 제거)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_company_name = company_name.replace('/', '')  # 슬래시 제거해서 이어붙이기
                filename = f"{safe_company_name}_{file_label}_{timestamp}_{collected_filename}"
                filepath = os.path.join(temp_dir, filename)
                
                # 중복 처리 방지: 이미 같은 파일이 있으면 건너뛰기
                if os.path.exists(filepath):
                    print(f"이미 존재하는 파일 건너뛰기: {filename}")
                    return jsonify({
                        "filename": filename, 
                        "file_index": int(file_index),
                        "file_label": file_label,
                        "message": "이미 업로드된 파일입니다"
                    })
                
                # 파일 복사
                import shutil
                try:
                    shutil.copy2(source_path, filepath)
                except FileNotFoundError:
                    return jsonify({"error": f"원본 파일을 찾을 수 없습니다: {collected_filename}"}), 404
                except Exception as e:
                    return jsonify({"error": f"파일 복사 중 오류: {str(e)}"}), 500
                
                return jsonify({
                    "filename": filename, 
                    "file_index": int(file_index),
                    "file_label": file_label,
                    "message": "자동 업로드 완료"
                })
            else:
                return jsonify({"error": "파일이 없습니다"}), 400
        
        # 일반 업로드 모드
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "파일명이 없습니다"}), 400
        
        # 임시 폴더 생성 (전처리 후 자동 삭제)
        temp_dir = "temp_processing"
        os.makedirs(temp_dir, exist_ok=True)
        
        # 파일 저장 (파일 인덱스와 라벨 포함, 슬래시 제거)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_company_name = company_name.replace('/', '')  # 슬래시 제거해서 이어붙이기
        filename = f"{safe_company_name}_{file_label}_{timestamp}_{file.filename}"
        filepath = os.path.join(temp_dir, filename)
        file.save(filepath)
        

        
        return jsonify({
            "filename": filename, 
            "file_index": int(file_index),
            "file_label": file_label,
            "message": "업로드 완료"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auto-upload', methods=['POST'])
def auto_upload():
    """자동 업로드"""
    try:
        data = request.get_json()
        company_name = data.get('company_name')
        collected_filename = data.get('collected_filename')
        file_index = data.get('file_index', 0)
        file_label = data.get('file_label', '')
        
        if not all([company_name, collected_filename, file_label]):
            return jsonify({"error": "필수 파라미터 누락"}), 400
        
        # 다운로드 폴더에서 파일 확인
        download_dir = "/app/downloads"
        os.makedirs(download_dir, exist_ok=True)
        source_path = os.path.join(download_dir, collected_filename)
        
        if not os.path.exists(source_path):
            return jsonify({"error": f"파일을 찾을 수 없습니다: {collected_filename}"}), 404
        
        return jsonify({
            "filename": collected_filename,
            "file_index": file_index,
            "file_label": file_label,
            "message": "파일 확인 완료"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """파일 다운로드 (다양한 디렉토리에서 검색)"""
    try:
        from urllib.parse import unquote
        
        # URL 디코딩 (공백 등이 %20으로 인코딩되어 있을 수 있음)
        decoded_filename = unquote(filename)
        
        # 검색할 디렉토리 목록
        search_dirs = [
            "/app/downloads",  # 크롤링으로 다운로드된 파일
            "temp_processing",  # 전처리된 파일
        ]
        
        # 각 디렉토리에서 파일 찾기
        for search_dir in search_dirs:
            os.makedirs(search_dir, exist_ok=True)
            file_path = os.path.join(search_dir, decoded_filename)
            
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True, download_name=decoded_filename)
        
        # 파일을 찾지 못한 경우 더 유연하게 검색 (부분 일치)
        print(f"❌ 파일을 찾을 수 없습니다: {decoded_filename}")
        print(f"   검색한 디렉토리: {search_dirs}")
        
        # 부분 일치로 파일 검색
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                files = os.listdir(search_dir)
                print(f"   {search_dir}에 있는 파일 수: {len(files)}")
                
                # 파일명에서 핵심 부분 추출 (날짜_회사명_...)
                decoded_base = decoded_filename.replace(" 청구내역서.xlsx", "").replace(".xlsx", "")
                for f in files:
                    file_base = f.replace(" 청구내역서.xlsx", "").replace(".xlsx", "")
                    # 핵심 부분이 일치하면 찾은 것으로 간주
                    if decoded_base in file_base or file_base in decoded_base:
                        file_path = os.path.join(search_dir, f)
                        if os.path.exists(file_path):
                            print(f"   ✅ 부분 일치 파일 발견: {f}")
                            return send_file(file_path, as_attachment=True, download_name=decoded_filename)
        
        return jsonify({"error": f"파일을 찾을 수 없습니다: {decoded_filename}"}), 404
        
    except Exception as e:
        print(f"❌ 다운로드 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/bill-image/<filename>', methods=['GET'])
def get_bill_image(filename):
    """통신비 PDF 파일 서빙"""
    try:
        bill_images_dir = "bill_images"
        file_path = os.path.join(bill_images_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": f"파일을 찾을 수 없습니다: {filename}"}), 404
        
        return send_file(file_path, mimetype='application/pdf')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bill-pdf/<filename>', methods=['GET'])
def get_bill_pdf(filename):
    """고지서 PDF 파일 서빙"""
    try:
        pdf_files_dir = "bill_pdfs"
        file_path = os.path.join(pdf_files_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": f"파일을 찾을 수 없습니다: {filename}"}), 404
        
        return send_file(file_path, mimetype='application/pdf')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/api/process-file', methods=['POST'])
def process_file():
    """파일 전처리"""
    try:
        data = request.get_json()
        company_name = data.get('company_name')
        collection_date = data.get('collection_date')  # YYYY-MM-DD 형식
        
        print(f"전처리 시작: {company_name}, {collection_date}")
        
        if not all([company_name, collection_date]):
            return jsonify({"error": "필수 파라미터 누락"}), 400
        
        # 회사별 전처리 실행
        if company_name == "앤하우스":
            preprocessor = AnhousPreprocessor()
            success = preprocessor.process_anhous_data(collection_date)
            
            if success:
                # 다운로드 폴더에서 생성된 파일명 찾기
                download_dir = "/app/downloads"
                os.makedirs(download_dir, exist_ok=True)
                processed_files = []
                
                if os.path.exists(download_dir):
                    import time
                    current_time = time.time()
                    all_files = os.listdir(download_dir)
                    
                    for filename in all_files:
                        # 앤하우스 수수료 청구내역서 파일 찾기
                        if "앤하우스 수수료 청구내역서_" in filename and filename.endswith(".xlsx"):
                            file_path = os.path.join(download_dir, filename)
                            # 최근 5분 이내에 생성된 파일만 포함
                            if os.path.exists(file_path) and (current_time - os.path.getctime(file_path)) < 300:
                                processed_files.append(filename)
                
                # 결과 저장
                save_processed_files(company_name, processed_files)
                
                return jsonify({
                    "message": "전처리 완료",
                    "company": company_name,
                    "processed_files": processed_files
                })
            else:
                return jsonify({"error": "전처리 실패"}), 500
                
        elif company_name == "코오롱Fnc":
            preprocessor = KolonPreprocessor()
            success = preprocessor.process_kolon_data(collection_date)
            
            if success:
                # 다운로드 폴더에서 생성된 파일명 찾기
                download_dir = "/app/downloads"
                os.makedirs(download_dir, exist_ok=True)
                processed_files = []
                
                if os.path.exists(download_dir):
                    import time
                    current_time = time.time()
                    all_files = os.listdir(download_dir)
                    
                    # 코오롱 관련 3개 파일 찾기: 청구내역서, OpenAI 매칭결과, 코오롱FnC 상담솔루션 청구내역서
                    processed_files = []
                    
                    for filename in all_files:
                        if (("코오롱_청구내역서_" in filename and filename.endswith(".xlsx")) or
                            ("OpenAI_정확매칭결과_" in filename and filename.endswith(".csv")) or
                            ("코오롱FnC_상담솔루션 청구내역서" in filename and filename.endswith(".xlsx"))):
                            file_path = os.path.join(download_dir, filename)
                            if os.path.exists(file_path) and (current_time - os.path.getctime(file_path)) < 300:
                                processed_files.append((filename, os.path.getctime(file_path)))
                    
                    # 가장 최근 파일들 선택
                    if processed_files:
                        latest_files = sorted(processed_files, key=lambda x: x[1], reverse=True)
                        processed_file_names = [f[0] for f in latest_files]
                        
                        # 결과 저장
                        save_processed_files(company_name, processed_file_names)
                        
                        return jsonify({
                            "message": "전처리 완료",
                            "company": company_name,
                            "processed_files": processed_file_names
                        })
                
                return jsonify({
                    "message": "전처리 완료",
                    "company": company_name,
                    "processed_files": processed_files
                })
            else:
                return jsonify({"error": "전처리 실패"}), 500
        
        elif company_name == "SK일렉링크":
            preprocessor = SKPreprocessor()
            success = preprocessor.process_sk_data(collection_date)
            
            if success:
                # 다운로드 폴더에서 생성된 파일명 찾기
                download_dir = "/app/downloads"
                os.makedirs(download_dir, exist_ok=True)
                processed_files = []
                
                if os.path.exists(download_dir):
                    import time
                    current_time = time.time()
                    all_files = os.listdir(download_dir)
                    
                    for filename in all_files:
                        # SK일렉링크 청구내역서 파일 찾기
                        if ("SK일렉링크" in filename and "청구내역서" in filename and filename.endswith(".xlsx")):
                            file_path = os.path.join(download_dir, filename)
                            # 최근 5분 이내에 생성된 파일만 포함
                            if os.path.exists(file_path) and (current_time - os.path.getctime(file_path)) < 300:
                                processed_files.append(filename)
                
                # 결과 저장
                save_processed_files(company_name, processed_files)
                
                return jsonify({
                    "message": "전처리 완료",
                    "company": company_name,
                    "processed_files": processed_files
                })
            else:
                return jsonify({"error": "전처리 실패"}), 500

        elif company_name == "W컨셉":
            # W컨셉은 라이선스 수량이 필요
            license_count = data.get('license_count', 40)
            print(f"W컨셉 라이선스 수량: {license_count}개")
            
            processed_files = bill_processor.process_wconcept(collection_date, license_count)
            
            if processed_files:
                # 결과 저장
                save_processed_files(company_name, processed_files)
                
                return jsonify({
                    "message": "전처리 완료",
                    "company": company_name,
                    "processed_files": processed_files
                })
            else:
                return jsonify({"error": "전처리 실패"}), 500

        elif company_name == "매스프레소(콴다)":
            processed_files = bill_processor.process_mathpresso(collection_date)
            
            if processed_files:
                # 결과 저장
                save_processed_files(company_name, processed_files)
                
                return jsonify({
                    "message": "전처리 완료",
                    "company": company_name,
                    "processed_files": processed_files
                })
            else:
                return jsonify({"error": "전처리 실패"}), 500

        elif company_name == "디싸이더스/애드프로젝트":
            # 디싸이더스/애드프로젝트 전용 전처리
            preprocessor = DecidersPreprocessor()
            processed_files = preprocessor.process_deciders_data(collection_date)
            
            if processed_files:
                # 결과 저장
                save_processed_files(company_name, processed_files)
                
                return jsonify({
                    "message": "전처리 완료",
                    "company": company_name,
                    "processed_files": processed_files
                })
            else:
                return jsonify({"error": "전처리 실패"}), 500

        elif company_name == "구쁘":
            processed_files = bill_processor.process_guppu(collection_date)
            
            if processed_files:
                # 결과 저장
                save_processed_files(company_name, processed_files)
                
                return jsonify({
                    "message": "전처리 완료",
                    "company": company_name,
                    "processed_files": processed_files
                })
            else:
                return jsonify({"error": "전처리 실패"}), 500
        else:
            return jsonify({"error": f"{company_name}은 전처리를 지원하지 않습니다"}), 400
        
    except Exception as e:
        print(f" 전처리 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload-bills', methods=['POST'])
def upload_bills():
    """고지서 일괄 업로드 및 처리 (HTML/PDF 통합)"""
    try:
        if 'files[]' not in request.files:
            return jsonify({"error": "파일이 없습니다"}), 400
        
        files = request.files.getlist('files[]')
        valid_files = [f for f in files if f.filename.endswith(('.html', '.pdf'))]
        
        if not valid_files:
            return jsonify({"error": "HTML 또는 PDF 파일이 없습니다"}), 400
        
        # HTML과 PDF 파일 통합 처리
        results = bill_processor.process_mixed_files(valid_files)
        
        if results:
            return jsonify({
                "message": "고지서 처리 완료",
                "bill_amounts": results
            })
        else:
            return jsonify({"error": "고지서 처리 실패"}), 500
            
    except Exception as e:
        print(f"고지서 업로드 오류: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/bill-amounts', methods=['GET'])
def get_bill_amounts():
    """각 고객사별 통신비 조회"""
    try:
        amounts = bill_processor.get_bill_amounts()
        return jsonify(amounts)
    except Exception as e:
        print(f"통신비 조회 오류: {e}")
        return jsonify({"error": str(e)}), 500

# 청구서 결과 영속성 관리 (통합 저장소 사용)
def save_processed_files(company_name, processed_files):
    """청구서 결과 저장"""
    admin_storage.save_processed_files(company_name, processed_files)

def clear_processed_files(company_name):
    """특정 회사의 청구서 결과 초기화"""
    admin_storage.clear_processed_files(company_name)

@app.route('/api/get-processed-files', methods=['GET'])
def get_processed_files():
    """저장된 청구서 결과 및 파일 목록 조회"""
    try:
        processed_files = admin_storage.get_processed_files()
        uploaded_files = admin_storage.get_uploaded_files()
        collected_files = admin_storage.get_collected_files()
        return jsonify({
            "processed_files": processed_files,
            "uploaded_files": uploaded_files,
            "collected_files": collected_files
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/save-uploaded-files', methods=['POST'])
def save_uploaded_files():
    """업로드된 파일 목록 저장"""
    try:
        data = request.get_json()
        company_name = data.get('company_name')
        uploaded_files = data.get('uploaded_files', [])
        admin_storage.save_uploaded_files(company_name, uploaded_files)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/save-collected-files', methods=['POST'])
def save_collected_files():
    """수집된 파일 목록 저장"""
    try:
        data = request.get_json()
        company_name = data.get('company_name')
        collected_files = data.get('collected_files', [])
        admin_storage.save_collected_files(company_name, collected_files)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Firebase에서 모든 계정 정보 조회"""
    try:
        accounts = db_manager.get_all_accounts()
        return jsonify({"accounts": accounts})
    except Exception as e:
        print(f"계정 정보 조회 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/accounts/<account_id>', methods=['GET'])
def get_account(account_id):
    """특정 계정 정보 조회"""
    try:
        account = db_manager.get_account_by_id(account_id)
        if account:
            return jsonify(account)
        else:
            return jsonify({"error": "계정을 찾을 수 없습니다"}), 404
    except Exception as e:
        print(f"계정 정보 조회 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/accounts', methods=['POST'])
def create_account():
    """새 계정 생성"""
    try:
        data = request.get_json()
        account_id = db_manager.add_account(data)
        return jsonify({"message": "계정이 생성되었습니다", "account_id": account_id}), 201
    except Exception as e:
        print(f"계정 생성 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/accounts/<account_id>', methods=['PUT'])
def update_account(account_id):
    """계정 정보 수정"""
    try:
        data = request.get_json()
        db_manager.update_account(account_id, data)
        return jsonify({"message": "계정이 수정되었습니다"})
    except Exception as e:
        print(f"계정 수정 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/accounts/<account_id>', methods=['DELETE'])
def delete_account(account_id):
    """계정 삭제"""
    try:
        db_manager.delete_account(account_id)
        return jsonify({"message": "계정이 삭제되었습니다"})
    except Exception as e:
        print(f"계정 삭제 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clear-processed-files', methods=['POST'])
def clear_company_processed_files():
    """특정 회사의 청구서 결과 초기화"""
    try:
        data = request.get_json()
        company_name = data.get('company_name')
        
        if not company_name:
            return jsonify({"error": "회사명이 필요합니다"}), 400
        
        admin_storage.clear_processed_files(company_name)
        return jsonify({"message": f"{company_name} 청구서 결과 초기화 완료"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/expense-automation', methods=['POST'])
def expense_automation():
    """지출결의서 자동화 실행"""
    import sys
    try:
        print("="*60)
        print("✅✅✅ 지출결의서 자동화 API 엔드포인트 진입 ✅✅✅")
        print(f"   요청 메서드: {request.method}")
        print(f"   Content-Type: {request.content_type}")
        print(f"   파일 키: {list(request.files.keys())}")
        print(f"   Form 키: {list(request.form.keys())}")
        print("="*60)
        sys.stdout.flush()
        
        # 파일 업로드 확인
        if 'file' not in request.files:
            print("❌ 오류: 파일이 업로드되지 않았습니다")
            return jsonify({"error": "파일이 업로드되지 않았습니다"}), 400
        
        file = request.files['file']
        if file.filename == '':
            print("❌ 오류: 파일명이 비어있습니다")
            return jsonify({"error": "파일이 선택되지 않았습니다"}), 400
        
        # 파라미터 받기
        category = request.form.get('category', '해외결제 법인카드')
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        user_id = request.form.get('user_id', '')
        password = request.form.get('password', '')
        
        # 디버깅을 위한 파라미터 로그
        print(f"📋 받은 파라미터:")
        print(f"   category: '{category}'")
        print(f"   start_date: '{start_date}'")
        print(f"   end_date: '{end_date}'")
        print(f"   user_id: '{user_id}'")
        print(f"   password: '***' (길이: {len(password)})")
        print(f"   file: '{file.filename}'")
        import sys
        sys.stdout.flush()
        
        # 필수 파라미터 검증
        if not all([start_date, end_date, user_id, password]):
            missing_params = []
            if not start_date: missing_params.append('start_date')
            if not end_date: missing_params.append('end_date')
            if not user_id: missing_params.append('user_id')
            if not password: missing_params.append('password')
            print(f"❌ 누락된 파라미터: {missing_params}")
            sys.stdout.flush()
            return jsonify({"error": f"필수 파라미터가 누락되었습니다: {', '.join(missing_params)}"}), 400
        
        # 날짜 형식 검증
        if len(start_date) != 8 or len(end_date) != 8:
            print(f"❌ 날짜 형식 오류: start_date={start_date}, end_date={end_date}")
            sys.stdout.flush()
            return jsonify({"error": "날짜 형식이 올바르지 않습니다 (YYYYMMDD)"}), 400
        
        # 임시 파일로 저장
        print(f"📁 임시 파일 저장 시작...")
        sys.stdout.flush()
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        try:
            file.save(file_path)
            print(f"✅ 임시 파일 저장 완료: {file_path}")
            print(f"   파일 크기: {os.path.getsize(file_path)} bytes")
            sys.stdout.flush()
        except Exception as save_error:
            print(f"❌ 파일 저장 실패: {save_error}")
            import traceback
            print(traceback.format_exc())
            sys.stdout.flush()
            return jsonify({"error": f"파일 저장 실패: {str(save_error)}"}), 500
        
        try:
            # 데이터 처리
            print(f"\n🔧 지출결의서 자동화 시작: {file.filename}")
            sys.stdout.flush()
            
            print(f"📊 1단계: ExpenseDataProcessor 초기화...")
            sys.stdout.flush()
            data_processor = ExpenseDataProcessor()
            
            # 파일 로드
            print(f"📥 2단계: 파일 로드 시작...")
            sys.stdout.flush()
            try:
                data = data_processor.load_file(file_path)
                print(f"✅ 파일 로드 완료: {len(data)}개 레코드")
                print(f"   컬럼: {list(data.columns)}")
                sys.stdout.flush()
            except Exception as load_error:
                print(f"❌ 파일 로드 실패: {load_error}")
                import traceback
                print(traceback.format_exc())
                sys.stdout.flush()
                return jsonify({
                    "success": False,
                    "error": f"파일 로드 실패: {str(load_error)}"
                }), 500
            
            # 데이터 처리
            print(f"🔄 3단계: 데이터 처리 시작...")
            sys.stdout.flush()
            try:
                processed_data = data_processor.process_data(data, category, start_date, end_date)
                print(f"✅ 데이터 처리 완료: {len(processed_data)}개 레코드")
                sys.stdout.flush()
            except Exception as process_error:
                print(f"❌ 데이터 처리 실패: {process_error}")
                import traceback
                print(traceback.format_exc())
                sys.stdout.flush()
                return jsonify({
                    "success": False,
                    "error": f"데이터 처리 실패: {str(process_error)}"
                }), 500
            
            if not processed_data:
                print(f"⚠️ 처리할 데이터가 없습니다")
                sys.stdout.flush()
                return jsonify({"error": "처리할 데이터가 없습니다"}), 400
            
            # 그룹웨어 자동화 실행
            print(f"🤖 4단계: 그룹웨어 자동화 시작...")
            sys.stdout.flush()
            try:
                automation = GroupwareAutomation()
                
                def progress_callback(message):
                    print(f"   진행상황: {message}")
                    sys.stdout.flush()
                
                automation.run_automation(
                    processed_data=processed_data,
                    progress_callback=progress_callback,
                    user_id=user_id,
                    password=password
                )
                
                print(f"✅ 지출결의서 자동화 완료!")
                sys.stdout.flush()
                
                return jsonify({
                    "success": True,
                    "message": "지출결의서 자동입력이 완료되었습니다",
                    "processed_count": len(processed_data),
                    "total_count": len(data)
                })
            except ValueError as login_error:
                # 로그인 실패 (정상적인 실패 케이스) - 200으로 반환
                error_msg = str(login_error)
                if "로그인 실패:" in error_msg:
                    error_msg = error_msg.replace("로그인 실패: ", "")
                print(f"⚠️ 로그인 실패: {error_msg}")
                sys.stdout.flush()
                return jsonify({
                    "success": False,
                    "error": error_msg
                }), 200
            except Exception as automation_error:
                print(f"❌ 그룹웨어 자동화 실패: {automation_error}")
                import traceback
                print(traceback.format_exc())
                sys.stdout.flush()
                return jsonify({
                    "success": False,
                    "error": f"그룹웨어 자동화 실패: {str(automation_error)}"
                }), 500
            
        except Exception as e:
            print(f"❌ 자동화 실행 중 예외 발생: {e}")
            import traceback
            print(traceback.format_exc())
            sys.stdout.flush()
            return jsonify({
                "success": False,
                "error": f"자동화 실행 중 오류가 발생했습니다: {str(e)}"
            }), 500
            
        finally:
            # 임시 파일 정리
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🗑️ 임시 파일 삭제: {file_path}")
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                    print(f"🗑️ 임시 디렉토리 삭제: {temp_dir}")
            except Exception as cleanup_error:
                print(f"⚠️ 임시 파일 정리 실패: {cleanup_error}")
                
    except Exception as e:
        print(f"❌ API 오류 (최상위 예외): {e}")
        import traceback
        error_traceback = traceback.format_exc()
        print(error_traceback)
        sys.stdout.flush()
        return jsonify({
            "success": False,
            "error": f"API 오류: {str(e)}",
            "traceback": error_traceback[:500] if len(error_traceback) > 500 else error_traceback
        }), 500

@app.route('/api/reset', methods=['POST'])
def reset_data():
    """초기화: temp_processing, bill_images 디렉토리 비우기 및 admin_storage.json 초기화"""
    try:
        # 디렉토리 비우기 헬퍼 함수
        def clear_directory(dir_path):
            """디렉토리 내 모든 파일 삭제"""
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        print(f"파일 삭제 실패: {file_path}, 오류: {e}")
        
        # 1. 디렉토리들 비우기
        clear_directory("temp_processing")
        clear_directory("bill_images")
        
        # 2. admin_storage.json 초기화
        admin_storage.clear_all()
        
        return jsonify({
            "success": True,
            "message": "초기화가 완료되었습니다."
        })
    except Exception as e:
        print(f"초기화 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "초기화 중 오류가 발생했습니다."
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)