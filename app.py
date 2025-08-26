from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import threading
from datetime import datetime
import uuid
import traceback
from pathlib import Path

# 크롤링 모듈들 import
from backend.data_collection.database import DatabaseManager
from backend.data_collection.login_manager import LoginManager
from backend.data_collection.data_manager import DataManager
from backend.data_collection.new_admin_manager import NewAdminManager
from backend.data_collection.config import DateConfig, AccountConfig, ElementConfig
from backend.preprocessing.anhous_preprocessing import EnhancedAnhousePreprocessor
from backend.preprocessing.kolon_preprocessing import KolonPreprocessor

app = Flask(__name__)
CORS(app)

# 크롤링 모듈 초기화
db_manager = DatabaseManager()
login_manager = LoginManager()
data_manager = DataManager(login_manager)
new_admin_manager = NewAdminManager(data_manager)
print("✅ 크롤링 시스템 초기화 완료")

# 작업 상태 저장
task_status = {}

print("🚀 청구자동화 API 서버 시작")
print("🔧 모드: 실제 크롤링")
print("📍 Frontend: http://localhost:3000")
print("📍 Backend API: http://localhost:5001")

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
                
                # 날짜 설정
                DateConfig.set_dates(start_date, end_date)
                task_status[task_id]["log"].append(f"📅 날짜 설정: {start_date} ~ {end_date}")
                
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
                
                if not os.path.exists(source_path):
                    return jsonify({"error": f"파일을 찾을 수 없습니다: {collected_filename}"}), 404
                
                # 임시 폴더 생성 (전처리 후 자동 삭제)
                temp_dir = "temp_processing"
                os.makedirs(temp_dir, exist_ok=True)
                
                # 파일명 생성
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{company_name}_{file_label}_{timestamp}_{collected_filename}"
                filepath = os.path.join(temp_dir, filename)
                
                # 파일 복사
                import shutil
                shutil.copy2(source_path, filepath)
                
                print(f"📁 자동 업로드: {filename} (인덱스: {file_index}, 라벨: {file_label})")
                
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
        
        # 파일 저장 (파일 인덱스와 라벨 포함)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{company_name}_{file_label}_{timestamp}_{file.filename}"
        filepath = os.path.join(temp_dir, filename)
        file.save(filepath)
        
        print(f"📁 파일 업로드: {filename} (인덱스: {file_index}, 라벨: {file_label})")
        
        return jsonify({
            "filename": filename, 
            "file_index": int(file_index),
            "file_label": file_label,
            "message": "업로드 완료"
        })
        
    except Exception as e:
        print(f"❌ 업로드 오류: {e}")
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
        
        print(f"📁 자동 업로드 확인: {collected_filename}")
        
        return jsonify({
            "filename": collected_filename,
            "file_index": file_index,
            "file_label": file_label,
            "message": "파일 확인 완료"
        })
        
    except Exception as e:
        print(f"❌ 자동 업로드 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """파일 다운로드 (로컬 Downloads 폴더에서)"""
    try:
        from pathlib import Path
        
        # 로컬 Downloads 폴더에서 파일 찾기
        download_dir = str(Path.home() / "Downloads")
        file_path = os.path.join(download_dir, filename)
        
        print(f"🔍 파일 찾기: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
            return jsonify({"error": f"파일을 찾을 수 없습니다: {filename}"}), 404
        
        # 로컬 파일 직접 다운로드
        print(f"✅ 파일 발견: {file_path}")
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        print(f"❌ 다운로드 오류: {e}")
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
            preprocessor = EnhancedAnhousePreprocessor()
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
                    
                    # 가장 최근에 생성된 청구내역서와 OpenAI 매칭결과 파일만 찾기
                    processed_files = []
                    
                    for filename in all_files:
                        if (("코오롱_청구내역서_" in filename and filename.endswith(".xlsx")) or
                            ("OpenAI매칭결과_" in filename and filename.endswith(".csv"))):
                            file_path = os.path.join(download_dir, filename)
                            if os.path.exists(file_path) and (current_time - os.path.getctime(file_path)) < 300:
                                processed_files.append((filename, os.path.getctime(file_path)))
                    
                    # 가장 최근 파일들 선택
                    if processed_files:
                        latest_files = sorted(processed_files, key=lambda x: x[1], reverse=True)
                        return jsonify({
                            "message": "전처리 완료",
                            "company": company_name,
                            "processed_files": [f[0] for f in latest_files]
                        })
                
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)