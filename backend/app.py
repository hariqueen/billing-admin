from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import threading
from datetime import datetime
import uuid
import traceback
from pathlib import Path

# 실제 크롤링 모듈들 import
try:
    from database import DatabaseManager
    from login_manager import LoginManager
    from data_manager import DataManager
    from new_admin_manager import NewAdminManager
    from config import DateConfig, AccountConfig
    print("✅ 모든 크롤링 모듈 로드 성공")
    CRAWLING_AVAILABLE = True
except ImportError as e:
    print(f"❌ 크롤링 모듈 로드 실패: {e}")
    print("⚠️ 시뮬레이션 모드로 실행됩니다")
    CRAWLING_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# 전역 객체들
if CRAWLING_AVAILABLE:
    try:
        db_manager = DatabaseManager()
        login_manager = LoginManager()
        data_manager = DataManager(login_manager)
        new_admin_manager = NewAdminManager(data_manager)
        print("✅ 크롤링 시스템 초기화 완료")
    except Exception as e:
        print(f"❌ 크롤링 시스템 초기화 실패: {e}")
        CRAWLING_AVAILABLE = False

# 작업 상태 저장
task_status = {}

print("🚀 청구자동화 API 서버 시작")
print(f"🔧 모드: {'실제 크롤링' if CRAWLING_AVAILABLE else '시뮬레이션'}")
print("📍 Frontend: http://localhost:3000")
print("📍 Backend API: http://localhost:5001")

@app.route('/api/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    return jsonify({
        "status": "healthy", 
        "message": f"API 서버가 정상 작동중 ({'실제 크롤링' if CRAWLING_AVAILABLE else '시뮬레이션'} 모드)",
        "crawling_available": CRAWLING_AVAILABLE,
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
            "crawling_mode": CRAWLING_AVAILABLE
        }
        
        def run_real_crawling():
            try:
                task_status[task_id]["status"] = "running"
                task_status[task_id]["progress"] = 10
                task_status[task_id]["log"].append("🔧 시스템 초기화 중...")
                
                if CRAWLING_AVAILABLE:
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
                            download_dir = str(Path.home() / "Downloads")
                            xlsx_files = [f for f in os.listdir(download_dir) if f.endswith('.xlsx')]
                            latest_file = max(xlsx_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                            
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
                                        from config import ElementConfig
                                        
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
                                print(f"CHAT 크롤링 오류: {chat_error}")
                                import traceback
                                traceback.print_exc()
                        
                        # SMS 세션 종료
                        login_manager.close_session(company_name, "sms")
                        task_status[task_id]["log"].append(f"🔒 {company_name} SMS 세션 종료")
                            
                    except Exception as sms_error:
                        task_status[task_id]["log"].append(f"❌ SMS 수집 중 오류: {str(sms_error)}")
                        print(f"SMS 크롤링 오류: {sms_error}")
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
                                # 실제 다운로드된 CALL 파일 찾기
                                download_dir = str(Path.home() / "Downloads")
                                xlsx_files = [f for f in os.listdir(download_dir) if f.endswith('.xlsx')]
                                latest_call_file = max(xlsx_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                                
                                task_status[task_id]["files"].append(latest_call_file)
                                task_status[task_id]["log"].append(f"✅ CALL 파일 수집 완료: {latest_call_file}")
                            else:
                                task_status[task_id]["log"].append("⚠️ CALL 데이터 수집 실패 또는 데이터 없음")
                            
                            # CALL 세션 종료
                            login_manager.close_session(company_name, "call")
                            task_status[task_id]["log"].append(f"🔒 {company_name} CALL 세션 종료")
                                
                        except Exception as call_error:
                            task_status[task_id]["log"].append(f"❌ CALL 수집 중 오류: {str(call_error)}")
                            print(f"CALL 크롤링 오류: {call_error}")
                
                else:
                    # 크롤링 모듈이 없는 경우 시뮬레이션
                    task_status[task_id]["log"].append("⚠️ 크롤링 모듈 없음 - 시뮬레이션 실행")
                    import time
                    time.sleep(3)
                    task_status[task_id]["files"].append(f"{company_name}_SMS_{start_date}_{end_date}.xlsx")
                    if company_name == "앤하우스":
                        task_status[task_id]["files"].append(f"{company_name}_CALL_{start_date}_{end_date}.xlsx")
                
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
                print(f"❌ 크롤링 심각한 오류: {e}")
                traceback.print_exc()
        
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
        if 'file' not in request.files:
            return jsonify({"error": "파일이 없습니다"}), 400
        
        file = request.files['file']
        company_name = request.form.get('company_name')
        file_index = request.form.get('file_index', '0')
        file_label = request.form.get('file_label', '')
        
        if file.filename == '':
            return jsonify({"error": "파일명이 없습니다"}), 400
        
        # 업로드 폴더 생성
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 파일 저장 (파일 인덱스와 라벨 포함)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{company_name}_{file_label}_{timestamp}_{file.filename}"
        filepath = os.path.join(upload_dir, filename)
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

@app.route('/api/auto-upload-collected', methods=['POST'])
def auto_upload_collected():
    """수집된 파일을 업로드 영역으로 자동 복사"""
    try:
        data = request.get_json()
        company_name = data.get('company_name')
        collected_filename = data.get('collected_filename')
        file_index = data.get('file_index', 0)
        file_label = data.get('file_label', '')
        
        print(f"🔄 자동 업로드: {company_name} - {collected_filename} ({file_label})")
        
        # 수집된 파일 찾기
        from pathlib import Path
        import glob
        import shutil
        
        possible_paths = [
            str(Path.home() / "Downloads"),
            str(Path.home() / "다운로드"),
            "./downloads"
        ]
        
        source_filepath = None
        for download_dir in possible_paths:
            if os.path.exists(download_dir):
                # 정확한 파일명 먼저 찾기
                test_path = os.path.join(download_dir, collected_filename)
                if os.path.exists(test_path):
                    source_filepath = test_path
                    break
                    
                # 유사한 파일명 찾기
                pattern = os.path.join(download_dir, f"*{collected_filename.split('_')[0]}*.xlsx")
                matches = glob.glob(pattern)
                if matches:
                    source_filepath = max(matches, key=os.path.getctime)
                    break
        
        if not source_filepath or not os.path.exists(source_filepath):
            return jsonify({"error": f"수집된 파일을 찾을 수 없습니다: {collected_filename}"}), 404
        
        # 업로드 폴더에 복사
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        uploaded_filename = f"{company_name}_{file_label}_{timestamp}_{collected_filename}"
        upload_filepath = os.path.join(upload_dir, uploaded_filename)
        
        # 파일 복사
        shutil.copy2(source_filepath, upload_filepath)
        
        print(f"✅ 자동 업로드 완료: {uploaded_filename}")
        
        return jsonify({
            "uploaded_filename": uploaded_filename,
            "original_filename": collected_filename,
            "file_index": file_index,
            "file_label": file_label,
            "message": "자동 업로드 완료"
        })
        
    except Exception as e:
        print(f"❌ 자동 업로드 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/process-file', methods=['POST'])
def process_file():
    """파일 전처리"""
    try:
        data = request.get_json()
        company_name = data.get('company_name')
        filename = data.get('filename')
        
        print(f"⚙️ 전처리 시작: {company_name}, {filename}")
        
        # 실제 전처리 로직 구현 필요
        # 지금은 시뮬레이션
        import time
        time.sleep(2)
        processed_filename = f"{company_name}_견적서_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return jsonify({
            "processed_filename": processed_filename,
            "message": "전처리 완료"
        })
        
    except Exception as e:
        print(f"❌ 전처리 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """파일 다운로드 - 브라우저 강제 다운로드"""
    try:
        print(f"📥 다운로드 요청: {filename}")
        
        # 파일 찾기 (기존 코드와 동일)
        from pathlib import Path
        import glob
        from urllib.parse import quote
        
        possible_paths = [
            str(Path.home() / "Downloads"),
            str(Path.home() / "다운로드"),
            "./downloads", 
            "./uploads"
        ]
        
        filepath = None
        for download_dir in possible_paths:
            if os.path.exists(download_dir):
                # 정확한 파일명 먼저 찾기
                test_path = os.path.join(download_dir, filename)
                if os.path.exists(test_path):
                    filepath = test_path
                    break
                    
                # 유사한 파일명 찾기
                pattern = os.path.join(download_dir, f"*{filename.split('_')[0]}*{filename.split('_')[1]}*.xlsx")
                matches = glob.glob(pattern)
                if matches:
                    filepath = max(matches, key=os.path.getctime)
                    print(f"📁 유사 파일 발견: {filepath}")
                    break
        
        if filepath and os.path.exists(filepath):
            print(f"✅ 파일 발견: {filepath}")
            
            # 강제 다운로드를 위한 응답 헤더 설정
            from flask import Response
            
            def generate():
                with open(filepath, 'rb') as f:
                    data = f.read(1024)
                    while data:
                        yield data
                        data = f.read(1024)
            
            # 한글 파일명을 위한 RFC 5987 표준 인코딩
            encoded_filename = quote(filename.encode('utf-8'))
            
            return Response(
                generate(),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={
                    'Content-Disposition': f'attachment; filename*=UTF-8\'\'{encoded_filename}',
                    'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'Cache-Control': 'no-cache',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Expose-Headers': 'Content-Disposition'
                }
            )
        else:
            print(f"⚠️ 파일 없음: {filename}")
            return jsonify({
                "error": f"파일을 찾을 수 없습니다: {filename}",
                "searched_paths": possible_paths
            }), 404
            
    except Exception as e:
        print(f"❌ 다운로드 오류: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)