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

# 크롤링 모듈들 import
from backend.data_collection.database import DatabaseManager
from backend.data_collection.login_manager import LoginManager
from backend.data_collection.data_manager import DataManager
from backend.data_collection.new_admin_manager import NewAdminManager

# 지출결의서 자동화 모듈들 import
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

# 크롤링 모듈 초기화
db_manager = DatabaseManager()
login_manager = LoginManager()
data_manager = DataManager(login_manager)
new_admin_manager = NewAdminManager(data_manager)
admin_storage = AdminStorage()
bill_processor = BillProcessor(admin_storage)
print("✅ 크롤링 시스템 초기화 완료")

# 작업 상태 저장
task_status = {}

print("🚀 청구자동화 API 서버 시작")
print("🔧 모드: 실제 크롤링")
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
print(f"📍 Frontend: http://{host}:3000")
print(f"📍 Backend API: http://{host}:5001")

@app.route('/api/companies', methods=['GET'])
def get_companies():
    """고객사 목록 조회"""
    try:
        return jsonify({
            "companies": AccountConfig.COMPANIES
        })
    except Exception as e:
        print(f"❌ 고객사 목록 조회 오류: {e}")
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
        
        print(f"🚀 데이터 수집 요청: {company_name}, {start_date} ~ {end_date}")
        
        if not all([company_name, start_date, end_date]):
            return jsonify({"error": "필수 파라미터 누락"}), 400
        
        # 작업 ID 생성
        task_id = str(uuid.uuid4())
        task_status[task_id] = {
            "status": "starting",
            "company": company_name,
            "files": [],
            "progress": 0,
            "log": [f"📋 {company_name} 데이터 수집 시작"],
            "crawling_mode": True
        }
        
        def run_real_crawling():
            try:
                task_status[task_id]["status"] = "running"
                task_status[task_id]["progress"] = 10
                task_status[task_id]["log"].append("🔧 시스템 초기화 중...")
                
                # 실제 크롤링 실행
                task_status[task_id]["log"].append("🌐 실제 크롤링 모드로 실행")
                
                # 날짜 설정 (제공되지 않은 경우 기본값 사용)
                if start_date and end_date:
                    DateConfig.set_dates(start_date, end_date)
                    task_status[task_id]["log"].append(f"📅 날짜 설정: {start_date} ~ {end_date}")
                else:
                    DateConfig.set_default_dates()
                    dates = DateConfig.get_dates()
                    task_status[task_id]["log"].append(f"📅 기본 날짜 설정: {dates['start_date']} ~ {dates['end_date']}")
                
                # 1단계: SMS 계정 로그인 및 데이터 수집
                task_status[task_id]["progress"] = 20
                task_status[task_id]["log"].append(f"🔐 {company_name} SMS 로그인 시작...")
                
                try:
                    # SMS 계정 정보 가져오기
                    sms_accounts = db_manager.get_accounts_by_type("sms")
                    target_account = None
                    for account in sms_accounts:
                        if account['company_name'] == company_name:
                            target_account = account
                            break
                    
                    if not target_account:
                        raise Exception(f"{company_name} SMS 계정 정보를 찾을 수 없습니다")
                    
                    # SMS 로그인
                    login_success, _ = login_manager.login_account(target_account, keep_session=True)
                    if not login_success:
                        raise Exception(f"{company_name} SMS 로그인 실패")
                        
                    task_status[task_id]["log"].append(f"✅ {company_name} SMS 로그인 성공")
                    
                    # SMS 데이터 수집
                    task_status[task_id]["progress"] = 40
                    task_status[task_id]["log"].append(f"📱 {company_name} SMS 데이터 수집 시작...")
                    
                    # 실제 SMS 크롤링 실행
                    sms_result = data_manager.download_sms_data(
                        company_name, 
                        DateConfig.get_sms_format()["start_date"], 
                        DateConfig.get_sms_format()["end_date"]
                    )
                    
                    if sms_result:
                        # SMS 수집 직후 다운로드된 파일 찾기
                        download_dir = str(Path.home() / "Downloads")
                        xlsx_files = [f for f in os.listdir(download_dir) if f.endswith('.xlsx')]
                        
                        # SMS 수집 직후이므로 가장 최근 파일이 SMS 파일
                        latest_file = max(xlsx_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                        
                        # SMS 수집 시간 기록 (CALL과 구분하기 위해)
                        task_status[task_id]["sms_collection_time"] = os.path.getctime(os.path.join(download_dir, latest_file))
                        
                        task_status[task_id]["files"].append(latest_file)
                        task_status[task_id]["log"].append(f"✅ SMS 파일 수집 완료: {latest_file}")
                    else:
                        task_status[task_id]["log"].append("⚠️ SMS 데이터 수집 실패 또는 데이터 없음")
                    
                    # 디싸이더스/애드프로젝트인 경우 CHAT 데이터도 수집
                    if company_name == "디싸이더스/애드프로젝트":
                        task_status[task_id]["log"].append("🗨️ CHAT 데이터 수집 시작...")
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
                                    task_status[task_id]["log"].append("✅ 알림창 처리 완료")
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
                                    task_status[task_id]["log"].append("✅ CHAT 데이터 수집 완료")
                                    # CHAT 파일도 수집된 파일 목록에 추가
                                    xlsx_files = [f for f in os.listdir(download_dir) if f.endswith('.xlsx')]
                                    latest_chat_file = max(xlsx_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                                    if latest_chat_file != latest_file:  # SMS 파일과 다른 경우만
                                        task_status[task_id]["files"].append(latest_chat_file)
                                        task_status[task_id]["log"].append(f"✅ CHAT 파일 수집 완료: {latest_chat_file}")
                                else:
                                    task_status[task_id]["log"].append("⚠️ CHAT 데이터 수집 실패 또는 데이터 없음")
                                    
                            else:
                                task_status[task_id]["log"].append("❌ SMS 세션을 찾을 수 없어 CHAT 수집 불가")
                                
                        except Exception as chat_error:
                            task_status[task_id]["log"].append(f"❌ CHAT 수집 중 오류: {str(chat_error)}")
                    
                    # SMS 세션 종료
                    login_manager.close_session(company_name, "sms")
                    task_status[task_id]["log"].append(f"🔒 {company_name} SMS 세션 종료")
                        
                except Exception as sms_error:
                    task_status[task_id]["log"].append(f"❌ SMS 수집 중 오류: {str(sms_error)}")
                    # SMS 실패해도 CALL은 시도
                
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
                            
                        task_status[task_id]["log"].append(f"✅ {company_name} CALL 로그인 성공")
                        task_status[task_id]["log"].append("📞 CALL 데이터 수집 시작...")
                        
                        call_result = data_manager.setup_call_data_collection(
                            company_name, 
                            start_date, 
                            end_date, 
                            download=True
                        )
                        
                        if call_result:
                            # CALL 수집 직후 다운로드된 파일 찾기
                            download_dir = str(Path.home() / "Downloads")
                            # .xlsx와 .xls 파일 모두 찾기
                            excel_files = [f for f in os.listdir(download_dir) if f.endswith(('.xlsx', '.xls'))]
                            
                            # SMS 파일 수집 시간 기록 (CALL과 구분하기 위해)
                            sms_collection_time = task_status[task_id].get("sms_collection_time")
                            
                            if sms_collection_time:
                                # SMS 수집 이후에 생성된 파일들만 필터링
                                call_files = []
                                for file in excel_files:
                                    file_path = os.path.join(download_dir, file)
                                    file_ctime = os.path.getctime(file_path)
                                    if file_ctime > sms_collection_time:
                                        call_files.append(file)
                                
                                if call_files:
                                    # 가장 최근 CALL 파일 선택
                                    latest_call_file = max(call_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                                    task_status[task_id]["files"].append(latest_call_file)
                                    task_status[task_id]["log"].append(f"✅ CALL 파일 수집 완료: {latest_call_file}")
                                else:
                                    task_status[task_id]["log"].append("⚠️ CALL 데이터 수집 실패: 새 파일이 생성되지 않음")
                            else:
                                # SMS 수집 시간이 없으면 기존 로직 사용
                                latest_call_file = max(excel_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                                task_status[task_id]["files"].append(latest_call_file)
                                task_status[task_id]["log"].append(f"✅ CALL 파일 수집 완료: {latest_call_file}")
                        else:
                            task_status[task_id]["log"].append("⚠️ CALL 데이터 수집 실패 또는 데이터 없음")
                        
                        # CALL 세션 종료
                        login_manager.close_session(company_name, "call")
                        task_status[task_id]["log"].append(f"🔒 {company_name} CALL 세션 종료")
                            
                    except Exception as call_error:
                        task_status[task_id]["log"].append(f"❌ CALL 수집 중 오류: {str(call_error)}")
                
                # 완료 처리
                if task_status[task_id]["files"]:
                    task_status[task_id]["status"] = "completed"
                    task_status[task_id]["progress"] = 100
                    task_status[task_id]["log"].append("🎉 데이터 수집 완료!")
                else:
                    task_status[task_id]["status"] = "completed"
                    task_status[task_id]["progress"] = 100
                    task_status[task_id]["log"].append("⚠️ 수집된 파일이 없습니다 (데이터 없음 또는 오류)")
                
                print(f"✅ {company_name} 크롤링 완료")
                
            except Exception as e:
                task_status[task_id]["status"] = "failed"
                task_status[task_id]["error"] = str(e)
                task_status[task_id]["log"].append(f"❌ 심각한 오류 발생: {str(e)}")
        
        # 백그라운드에서 실행
        thread = threading.Thread(target=run_real_crawling)
        thread.daemon = True
        thread.start()
        
        return jsonify({"task_id": task_id, "status": "started"})
        
    except Exception as e:
        print(f"❌ API 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/task-status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """작업 상태 조회"""
    if task_id not in task_status:
        return jsonify({"error": "작업을 찾을 수 없습니다"}), 404
    
    status = task_status[task_id]
    print(f"📊 Task {task_id[:8]}... 상태: {status['status']} ({status['progress']}%)")
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
                download_dir = str(Path.home() / "Downloads")
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
                    print(f"⚠️ 이미 존재하는 파일 건너뛰기: {filename}")
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
        download_dir = str(Path.home() / "Downloads")
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
    """파일 다운로드 (로컬 Downloads 폴더에서)"""
    try:
        from pathlib import Path
        
        # 로컬 Downloads 폴더에서 파일 찾기
        download_dir = str(Path.home() / "Downloads")
        file_path = os.path.join(download_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": f"파일을 찾을 수 없습니다: {filename}"}), 404
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/api/process-file', methods=['POST'])
def process_file():
    """파일 전처리"""
    try:
        data = request.get_json()
        company_name = data.get('company_name')
        collection_date = data.get('collection_date')  # YYYY-MM-DD 형식
        
        print(f"⚙️ 전처리 시작: {company_name}, {collection_date}")
        
        if not all([company_name, collection_date]):
            return jsonify({"error": "필수 파라미터 누락"}), 400
        
        # 회사별 전처리 실행
        if company_name == "앤하우스":
            preprocessor = AnhousPreprocessor()
            success = preprocessor.process_anhous_data(collection_date)
            
            if success:
                # 다운로드 폴더에서 생성된 파일명 찾기
                download_dir = str(Path.home() / "Downloads")
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
                download_dir = str(Path.home() / "Downloads")
                processed_files = []
                
                if os.path.exists(download_dir):
                    import time
                    current_time = time.time()
                    all_files = os.listdir(download_dir)
                    
                    # 코오롱 관련 3개 파일 찾기: 청구내역서, OpenAI 매칭결과, 코오롱FnC 상담솔루션 청구내역서
                    processed_files = []
                    
                    for filename in all_files:
                        if (("코오롱_청구내역서_" in filename and filename.endswith(".xlsx")) or
                            ("OpenAI매칭결과_" in filename and filename.endswith(".csv")) or
                            ("코오롱FnC" in filename and "상담솔루션 청구내역서" in filename and filename.endswith(".xlsx"))):
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
                download_dir = str(Path.home() / "Downloads")
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
            print(f"📊 W컨셉 라이선스 수량: {license_count}개")
            
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
        else:
            return jsonify({"error": f"{company_name}은 전처리를 지원하지 않습니다"}), 400
        
    except Exception as e:
        print(f"❌ 전처리 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload-bills', methods=['POST'])
def upload_bills():
    """HTML 고지서 일괄 업로드 및 처리"""
    try:
        if 'files[]' not in request.files:
            return jsonify({"error": "파일이 없습니다"}), 400
        
        files = request.files.getlist('files[]')
        html_files = [f for f in files if f.filename.endswith('.html')]
        
        if not html_files:
            return jsonify({"error": "HTML 파일이 없습니다"}), 400
        
        # HTML 파일 처리 및 통신비 정보 추출
        results = bill_processor.process_html_files(html_files)
        
        if results:
            return jsonify({
                "message": "고지서 처리 완료",
                "bill_amounts": results
            })
        else:
            return jsonify({"error": "고지서 처리 실패"}), 500
            
    except Exception as e:
        print(f"❌ 고지서 업로드 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/bill-amounts', methods=['GET'])
def get_bill_amounts():
    """각 고객사별 통신비 조회"""
    try:
        amounts = bill_processor.get_bill_amounts()
        return jsonify(amounts)
    except Exception as e:
        print(f"❌ 통신비 조회 오류: {e}")
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
    """저장된 청구서 결과 조회"""
    try:
        processed_files = admin_storage.get_processed_files()
        return jsonify({"processed_files": processed_files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Firebase에서 모든 계정 정보 조회"""
    try:
        accounts = db_manager.get_all_accounts()
        return jsonify({"accounts": accounts})
    except Exception as e:
        print(f"❌ 계정 정보 조회 오류: {e}")
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
        print(f"❌ 계정 정보 조회 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/accounts', methods=['POST'])
def create_account():
    """새 계정 생성"""
    try:
        data = request.get_json()
        account_id = db_manager.add_account(data)
        return jsonify({"message": "계정이 생성되었습니다", "account_id": account_id}), 201
    except Exception as e:
        print(f"❌ 계정 생성 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/accounts/<account_id>', methods=['PUT'])
def update_account(account_id):
    """계정 정보 수정"""
    try:
        data = request.get_json()
        db_manager.update_account(account_id, data)
        return jsonify({"message": "계정이 수정되었습니다"})
    except Exception as e:
        print(f"❌ 계정 수정 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/accounts/<account_id>', methods=['DELETE'])
def delete_account(account_id):
    """계정 삭제"""
    try:
        db_manager.delete_account(account_id)
        return jsonify({"message": "계정이 삭제되었습니다"})
    except Exception as e:
        print(f"❌ 계정 삭제 오류: {e}")
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
    try:
        # 파일 업로드 확인
        if 'file' not in request.files:
            return jsonify({"error": "파일이 업로드되지 않았습니다"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "파일이 선택되지 않았습니다"}), 400
        
        # 파라미터 받기
        category = request.form.get('category', '해외결제 법인카드')
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        user_id = request.form.get('user_id', '')
        password = request.form.get('password', '')
        
        # 필수 파라미터 검증
        if not all([start_date, end_date, user_id, password]):
            return jsonify({"error": "필수 파라미터가 누락되었습니다"}), 400
        
        # 날짜 형식 검증
        if len(start_date) != 8 or len(end_date) != 8:
            return jsonify({"error": "날짜 형식이 올바르지 않습니다 (YYYYMMDD)"}), 400
        
        # 임시 파일로 저장
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        file.save(file_path)
        
        try:
            # 데이터 처리
            print(f"📊 지출결의서 자동화 시작: {file.filename}")
            data_processor = ExpenseDataProcessor()
            
            # 파일 로드
            data = data_processor.load_file(file_path)
            print(f"✅ 파일 로드 완료: {len(data)}개 레코드")
            
            # 데이터 처리
            processed_data = data_processor.process_data(data, category, start_date, end_date)
            print(f"✅ 데이터 처리 완료: {len(processed_data)}개 레코드")
            
            if not processed_data:
                return jsonify({"error": "처리할 데이터가 없습니다"}), 400
            
            # 그룹웨어 자동화 실행
            automation = GroupwareAutomation()
            
            def progress_callback(message):
                print(f"📈 진행상황: {message}")
            
            automation.run_automation(
                processed_data=processed_data,
                progress_callback=progress_callback,
                user_id=user_id,
                password=password
            )
            
            print("🎉 지출결의서 자동화 완료!")
            
            return jsonify({
                "success": True,
                "message": "지출결의서 자동입력이 완료되었습니다",
                "processed_count": len(processed_data),
                "total_count": len(data)
            })
            
        except Exception as e:
            print(f"❌ 자동화 실행 오류: {e}")
            print(f"❌ 상세 오류: {traceback.format_exc()}")
            return jsonify({
                "success": False,
                "error": f"자동화 실행 중 오류가 발생했습니다: {str(e)}"
            }), 500
            
        finally:
            # 임시 파일 정리
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass
                
    except Exception as e:
        print(f"❌ API 오류: {e}")
        print(f"❌ 상세 오류: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)