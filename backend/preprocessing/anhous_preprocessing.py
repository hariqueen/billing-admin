import os
import re
import shutil
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
import firebase_admin
from firebase_admin import credentials, storage
from backend.utils.secrets_manager import get_firebase_secret

class AnhousPreprocessor:
    def __init__(self, download_dir="downloads"):
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
        self.setup_firebase()
    
    def setup_firebase(self):
        """Firebase Storage 연결 설정"""
        try:
            from dotenv import load_dotenv
            
            load_dotenv()
            cred_dict = get_firebase_secret()
            
            BUCKET_NAME = os.getenv("STORAGE_BUCKET", "services-e42af.firebasestorage.app")
            
            # 기존 앱이 있으면 삭제하고 새로 초기화
            if firebase_admin._apps:
                firebase_admin.delete_app(firebase_admin.get_app())
            
            firebase_admin.initialize_app(
                credentials.Certificate(cred_dict),
                {"storageBucket": BUCKET_NAME}
            )
            
            self.bucket = storage.bucket()
            print("✅ Firebase Storage 연결 완료")
        except Exception as e:
            print(f"❌ Firebase 연결 실패: {e}")
            self.bucket = None
    
    def convert_xls_to_csv(self, xls_file_path):
        """XLS/XLSX 파일을 CSV로 변환"""
        try:
            print(f"🔍 변환 시작: {os.path.basename(xls_file_path)}")
            print(f"   원본 파일: {xls_file_path}")
            
            # 파일 확장자 확인
            if xls_file_path.endswith('.xlsx'):
                # Excel 파일 처리
                print(f"   Excel 파일로 읽기 시도...")
                df = pd.read_excel(xls_file_path)
                print(f"   데이터 형태: {df.shape[0]}행 x {df.shape[1]}열")
                print(f"   컬럼: {list(df.columns)}")
                csv_path = xls_file_path.replace('.xlsx', '.csv')
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                print(f"✅ Excel → .csv 변환 완료: {csv_path}")
                return csv_path
            else:
                # XLS 파일 처리 (HTML 내용인지 확인)
                try:
                    with open(xls_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # HTML 내용인지 확인
                    if '<html' in content.lower() or '<table' in content.lower():
                        # HTML 테이블 파싱
                        df = pd.read_html(StringIO(content))[0]
                        
                        # 첫 번째 행이 제목인 경우 제거
                        if df.shape[0] > 0 and '통화내역' in str(df.iloc[0, 0]):
                            df = df.iloc[1:]
                        
                        # 헤더 설정
                        if df.shape[0] > 0:
                            df.columns = df.iloc[0]
                            df = df.iloc[1:]
                        
                        # CSV로 저장
                        csv_path = xls_file_path.replace('.xls', '.csv')
                        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                        print(f"✅ HTML → .csv 변환 완료: {csv_path}")
                        return csv_path
                    else:
                        # 일반 Excel 파일 처리
                        df = pd.read_excel(xls_file_path)
                        csv_path = xls_file_path.replace('.xls', '.csv')
                        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                        print(f"✅ Excel → .csv 변환 완료: {csv_path}")
                        return csv_path
                except UnicodeDecodeError:
                    # 인코딩 오류 시 Excel로 읽기 시도
                    df = pd.read_excel(xls_file_path)
                    csv_path = xls_file_path.replace('.xls', '.csv')
                    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                    print(f"✅ Excel → .csv 변환 완료: {csv_path}")
                    return csv_path
                
        except Exception as e:
            print(f"❌ 변환 실패: {xls_file_path}, 오류: {e}")
            return None
    
    def convert_all_collected_files(self):
        """업로드된 파일들만 CSV로 변환"""
        csv_files = []
        
        # temp_processing 폴더에서 앤하우스 파일 검색
        temp_dir = "temp_processing"
        if os.path.exists(temp_dir):
            anhous_files = []
            for filename in os.listdir(temp_dir):
                if "앤하우스" in filename and filename.endswith((".xls", ".xlsx")):
                    file_path = os.path.join(temp_dir, filename)
                    anhous_files.append((file_path, os.path.getmtime(file_path)))
            
            # 최신 파일 2개만 선택 (SMS, CALL)
            anhous_files.sort(key=lambda x: x[1], reverse=True)
            latest_files = anhous_files[:2]
            
            for file_path, _ in latest_files:
                csv_path = self.convert_xls_to_csv(file_path)
                if csv_path:
                    csv_files.append(csv_path)
        
        return csv_files
    
    def find_anhous_templates(self):
        """Firebase Storage에서 앤하우스 템플릿 파일들 찾기"""
        if not self.bucket:
            return []
        
        templates = []
        blobs = self.bucket.list_blobs()
        
        for blob in blobs:
            if 'annhouse' in blob.name.lower():
                templates.append(blob.name)
                print(f"✅ 템플릿 발견: {blob.name}")
        
        return templates
    
    def download_template(self, template_name):
        """템플릿 파일 다운로드"""
        if not self.bucket:
            return None
        
        try:
            blob = self.bucket.blob(template_name)
            temp_dir = os.path.join(os.getcwd(), "temp_processing")
            os.makedirs(temp_dir, exist_ok=True)
            
            local_path = os.path.join(temp_dir, template_name)
            blob.download_to_filename(local_path)
            print(f"✅ {template_name} 템플릿 다운로드 완료: {local_path}")
            return local_path
        except Exception as e:
            print(f"❌ 템플릿 다운로드 실패: {e}")
            return None
    
    def get_call_data_by_team(self, csv_files, collection_date):
        """CSV 파일들에서 팀별 CALL 데이터 분류"""
        team_data = {}
        
        for csv_file in csv_files:
            try:
                # 고객번호 컬럼을 문자열로 읽어서 앞의 0이 사라지지 않도록 함
                df = pd.read_csv(csv_file, dtype={'고객번호': str})
                
                if '팀' in list(df.columns):
                    teams = df['팀'].unique()
                    print(f"📊 CSV 파일 분석: {csv_file}")
                    print(f"   팀 종류: {teams}")
                    
                    for team in teams:
                        team_df = df[df['팀'] == team].copy()
                        if team not in team_data:
                            team_data[team] = []
                        team_data[team].append(team_df)
                        print(f"   ✅ {team} 데이터: {len(team_df)}행")
                        
            except Exception as e:
                print(f"❌ CSV 파일 읽기 실패: {csv_file}, 오류: {e}")
        
        return team_data
    
    def update_template_with_team_data(self, template_path, team_data, collection_date, template_team, csv_files):
        """템플릿 파일에 팀별 데이터 업데이트 (원본 템플릿 유지)"""
        try:
            import shutil
            from openpyxl import load_workbook
            
            print(f"🔧 {template_team} 데이터 처리 중...")
            
            # 원본 템플릿 파일 복사
            date_obj = datetime.strptime(collection_date, '%Y-%m-%d')
            date_prefix = f"{str(date_obj.year)[2:]}{date_obj.month:02d}"
            
            base_name = os.path.basename(template_path)
            if 'annhouse_CS' in base_name:
                team_suffix = 'CS'
            elif 'annhouse_TS' in base_name:
                team_suffix = 'TS'
            elif base_name == 'annhouse.xlsx':
                team_suffix = '창업'
            else:
                team_suffix = 'unknown'
            
            new_filename = f"{date_prefix}_앤하우스 수수료 청구내역서_{team_suffix}.xlsx"
            
            # 다운로드 폴더에 저장
            download_dir = os.path.expanduser("~/Downloads")
            os.makedirs(download_dir, exist_ok=True)
            output_path = os.path.join(download_dir, new_filename)
            
            # 원본 템플릿 복사
            shutil.copy2(template_path, output_path)
            
            # 워크북 로드
            workbook = load_workbook(output_path)
            
            # 통화료 시트 가져오기
            if '통화료' in workbook.sheetnames:
                sheet = workbook['통화료']
            else:
                print("❌ 통화료 시트를 찾을 수 없습니다")
                return None
            
            # 해당 팀의 데이터만 처리
            if template_team not in team_data:
                print(f"❌ {template_team} 데이터를 찾을 수 없습니다")
                return None
            
            team_dataframes = team_data[template_team]
            if not team_dataframes:
                print(f"❌ {template_team} 데이터가 없습니다")
                return None
            
            # DataFrame 객체를 직접 사용 (CSV 파일 경로가 아님)
            df = team_dataframes[0]  # 첫 번째 DataFrame
            
            # 날짜 정보 추출
            year_month = f"{date_obj.year}년 {date_obj.month}월"
            
            # H3 셀에 과금월 정보 추가
            print(f"🔧 H3 셀에 과금월 설정 시도: {year_month}")
            print(f"   현재 시트: {sheet.title}")
            print(f"   H3 셀 위치: row=3, column=8")
            
            sheet.cell(row=3, column=8).value = year_month  # H3 셀
            
            # 설정 확인
            h3_value = sheet.cell(row=3, column=8).value
            print(f"✅ H3 셀에 과금월 설정 완료: {h3_value}")
            
            # 시트명과 텍스트 날짜 업데이트
            print(f"🔧 시트명 및 날짜 텍스트 업데이트 시작")
            self.update_sheet_dates(workbook, year_month)
            print(f"✅ 시트명 및 날짜 텍스트 업데이트 완료")
            
            # SMS 데이터 처리 및 세부내역 시트 업데이트
            print(f"🔧 SMS 데이터 처리 시작")
            self.process_sms_data(workbook, template_team, csv_files)
            print(f"✅ SMS 데이터 처리 완료")
            
            # 기존 데이터 지우기 (8행부터)
            for row in range(8, sheet.max_row + 1):
                for col in range(1, sheet.max_column + 1):
                    sheet.cell(row=row, column=col).value = None
            
            # 데이터 처리
            current_row = 8
            
            column_mapping = {
                '통화시간': 'C',
                '콜시작시간': 'D', 
                '대기시작시간': 'E',
                '링시작시간': 'F',
                '통화시작시간': 'G',
                '콜종료시간': 'H'
            }
            
            # 계산 함수들 정의
            import math
            
            def calculate_settlement_type(customer_number):
                """정산구분 계산: 010으로 시작하면 이동전화, 아니면 시내/시외"""
                return "이동전화" if str(customer_number).strip().startswith('010') else "시내/시외"
            
            def calculate_seconds(call_time):
                """초단위 환산: HH:MM:SS 형식을 초로 변환"""
                try:
                    time_str = str(call_time)
                    if len(time_str) >= 8 and time_str.count(':') == 2:
                        hours, minutes, seconds = map(int, time_str.split(':'))
                        return hours * 3600 + minutes * 60 + seconds
                    return 0
                except:
                    return 0
            
            def calculate_billing_units(settlement_type, total_seconds):
                """과금구간 계산"""
                divisor = 10 if settlement_type == "이동전화" else 180
                return math.ceil(total_seconds / divisor)
            
            def calculate_billing_amount(settlement_type, billing_units):
                """과금금액 계산"""
                rate = 10 if settlement_type == "이동전화" else 30
                return billing_units * rate
            
            for idx, call_row in df.iterrows():
                # 기준월 추가 (B열)
                sheet.cell(row=current_row, column=2).value = year_month
                
                # CALL 데이터 매핑
                for call_col, excel_col in column_mapping.items():
                    if call_col in list(df.columns):
                        try:
                            col_letter = excel_col
                            col_idx = ord(col_letter) - ord('A') + 1
                            sheet.cell(row=current_row, column=col_idx).value = call_row[call_col]
                        except Exception as e:
                            print(f"데이터 매핑 오류: {e}")
                
                # 추가 계산 필드들
                try:
                    # 고객번호와 통화시간 가져오기
                    customer_number = call_row.get('고객번호', '')
                    call_time = call_row.get('통화시간', '00:00:00')
                    
                    # 계산 수행
                    settlement_type = calculate_settlement_type(customer_number)
                    total_seconds = calculate_seconds(call_time)
                    billing_units = calculate_billing_units(settlement_type, total_seconds)
                    billing_amount = calculate_billing_amount(settlement_type, billing_units)
                    
                    # 엑셀에 값 입력
                    sheet.cell(row=current_row, column=9).value = settlement_type      # I열: 정산구분
                    sheet.cell(row=current_row, column=10).value = total_seconds      # J열: 초단위 환산
                    sheet.cell(row=current_row, column=11).value = billing_units      # K열: 과금구간
                    sheet.cell(row=current_row, column=12).value = billing_amount     # L열: 과금금액
                    
                except Exception as e:
                    print(f"❌ 계산 오류 (행 {current_row}): {e}")
                
                current_row += 1
            
            # 파일 저장
            workbook.save(output_path)
            workbook.close()
            
            print(f"✅ 템플릿 업데이트 완료: {new_filename}")
            return output_path
            
        except Exception as e:
            import traceback
            print(f"❌ 템플릿 업데이트 실패: {e}")
            print(f"🔍 상세 오류: {traceback.format_exc()}")
            return None
    
    def update_sheet_dates(self, workbook, year_month):
        """시트명과 텍스트의 날짜를 수집한 년/월로 업데이트"""
        try:
            import re
            
            # 1. 시트명 업데이트 (예: "2025년 6월" → "2025년 5월")
            for sheet in workbook.worksheets:
                if re.match(r'\d{4}년 \d{1,2}월', sheet.title):
                    old_title = sheet.title
                    sheet.title = year_month
                    print(f"   📝 시트명 변경: {old_title} → {year_month}")
                    break
            
            # 2. B1-E1 병합 셀 텍스트 업데이트
            target_sheet = None
            for sheet in workbook.worksheets:
                if sheet.title == year_month:
                    target_sheet = sheet
                    break
            
            if target_sheet:
                # B1 셀의 텍스트 확인 및 업데이트
                b1_cell = target_sheet.cell(row=1, column=2)
                if b1_cell.value and isinstance(b1_cell.value, str):
                    old_text = b1_cell.value
                    # 날짜 패턴 찾아서 교체 (예: "2025년 6월" → "2025년 5월")
                    new_text = re.sub(r'\d{4}년 \d{1,2}월', year_month, old_text)
                    if new_text != old_text:
                        b1_cell.value = new_text
                        print(f"   📝 B1 셀 텍스트 변경: {old_text} → {new_text}")
            
            # 3. 대외공문 시트의 텍스트 및 수식 업데이트
            if '대외공문' in [sheet.title for sheet in workbook.worksheets]:
                doc_sheet = workbook['대외공문']
                
                # B13 셀 업데이트
                b13_cell = doc_sheet.cell(row=13, column=2)
                if b13_cell.value and isinstance(b13_cell.value, str):
                    old_text = b13_cell.value
                    new_text = re.sub(r'\d{4}년 \d{1,2}월', year_month, old_text)
                    if new_text != old_text:
                        b13_cell.value = new_text
                        print(f"   📝 대외공문 B13 셀 변경: {old_text} → {new_text}")
                
                # B16 셀 업데이트 (B,C,D,E,F,G 16행 병합)
                b16_cell = doc_sheet.cell(row=16, column=2)
                if b16_cell.value and isinstance(b16_cell.value, str):
                    old_text = b16_cell.value
                    new_text = re.sub(r'2025년\d{1,2}월', year_month, old_text)
                    if new_text == old_text:
                        new_text = re.sub(r'\d{4}년\d{1,2}월', year_month, old_text)
                    if new_text != old_text:
                        b16_cell.value = new_text
                        print(f"   📝 대외공문 B16 셀 변경: {old_text} → {new_text}")
                
                # 수식 업데이트 (시트명 참조 변경)
                self.update_formula_references(doc_sheet, year_month)
                        
        except Exception as e:
            print(f"❌ 시트 날짜 업데이트 오류: {e}")
    
    def update_formula_references(self, doc_sheet, year_month):
        """대외공문 시트의 수식에서 시트명 참조 업데이트"""
        try:
            import re
            
            # 수식이 있을 수 있는 셀들 확인 (24행, 25행 등)
            cells_to_check = [
                (24, 2), (24, 3), (24, 4),  # B24, C24, D24
                (25, 2), (25, 3), (25, 4),  # B25, C25, D25
                (26, 2), (26, 3), (26, 4),  # B26, C26, D26
                (27, 2), (27, 3), (27, 4),  # B27, C27, D27
            ]
            
            for row, col in cells_to_check:
                cell = doc_sheet.cell(row=row, column=col)
                if cell.value and isinstance(cell.value, str) and cell.value.startswith('='):
                    old_formula = cell.value
                    # 수식에서 시트명 참조 패턴 찾아서 교체
                    # 예: ='2025년 6월'!C4 → ='2025년 5월'!C4
                    new_formula = re.sub(r"'(\d{4}년 \d{1,2}월)'!", f"'{year_month}'!", old_formula)
                    if new_formula != old_formula:
                        cell.value = new_formula
                        print(f"   📝 대외공문 {chr(64+col)}{row} 셀 수식 변경: {old_formula} → {new_formula}")
                        
        except Exception as e:
            print(f"❌ 수식 참조 업데이트 오류: {e}")
    
    def process_sms_data(self, workbook, template_team, csv_files):
        """SMS 데이터 처리 및 세부내역 시트 업데이트"""
        try:
            # SMS CSV 파일 찾기 (변환된 CSV 파일들 중에서)
            sms_file = None
            for csv_file in csv_files:
                if 'SMS' in csv_file and csv_file.endswith('.csv'):
                    sms_file = csv_file
                    break
            
            if not sms_file:
                print("   ⚠️ SMS CSV 파일을 찾을 수 없습니다")
                print(f"   🔍 사용 가능한 파일: {csv_files}")
                return
            
            print(f"   📂 SMS 파일 발견: {sms_file}")
            
            # SMS 데이터 읽기 (CSV 파일)
            sms_df = pd.read_csv(sms_file)
            print(f"   📊 SMS 데이터 로드: {len(sms_df)}행")
            print(f"   📋 컬럼: {list(sms_df.columns)}")
            
            # 발송상태가 "성공(전달)"인 것만 필터링
            success_df = sms_df[sms_df['발송상태'] == '성공(전달)']
            print(f"   ✅ 성공 전달 건수: {len(success_df)}건")
            
            # 발신번호를 문자열로 변환하고 정리
            success_df['발신번호_정리'] = success_df['발신번호'].astype(str).str.replace('.0', '')
            
            # 템플릿별 발신번호 매핑 (하이픈 제거된 형태로 비교)
            sender_mapping = {
                "CS팀": "15888298",
                "엔하우스": "15884611", 
                "사업지원팀": "15880656"
            }
            
            print(f"   🔍 발신번호 샘플: {success_df['발신번호_정리'].head(10).tolist()}")
            
            # 해당 템플릿의 발신번호로 필터링
            target_sender = sender_mapping.get(template_team)
            if template_team == "사업지원팀":
                # 사업지원팀의 경우 15880656 또는 NULL/빈값 모두 포함
                team_sms_df = success_df[
                    (success_df['발신번호_정리'] == '15880656') | 
                    (success_df['발신번호'].isna()) | 
                    (success_df['발신번호'] == '') |
                    (success_df['발신번호_정리'] == 'nan')
                ]
            elif target_sender:
                team_sms_df = success_df[success_df['발신번호_정리'] == target_sender]
            else:
                team_sms_df = success_df.iloc[0:0]  # 빈 DataFrame
            
            print(f"   🎯 {template_team} 해당 SMS 건수: {len(team_sms_df)}건")
            
            # 문자유형별 카운트
            counts = {"SMS": 0, "LMS": 0, "TALK": 0}
            
            print(f"   📋 문자유형 샘플: {team_sms_df['문자유형'].value_counts().head()}")
            
            for _, row in team_sms_df.iterrows():
                msg_type = row.get('문자유형', '')
                
                if msg_type == "SMS":
                    counts["SMS"] += 1
                elif msg_type == "LMS/MMS":
                    counts["LMS"] += 1
                elif msg_type == "TALK(알림톡)":
                    counts["TALK"] += 1
            
            print(f"   📈 SMS: {counts['SMS']}건, LMS/MMS: {counts['LMS']}건, TALK: {counts['TALK']}건")
            
            # 세부내역 시트 업데이트
            self.update_detail_sheet(workbook, counts)
            
        except Exception as e:
            print(f"❌ SMS 데이터 처리 오류: {e}")
    
    def update_detail_sheet(self, workbook, counts):
        """세부내역 시트의 D13-D16 셀 업데이트"""
        try:
            if '세부내역' in [sheet.title for sheet in workbook.worksheets]:
                detail_sheet = workbook['세부내역']
                
                # D13-D16 셀에 건수 입력
                detail_sheet.cell(row=13, column=4).value = counts["SMS"]    # D13: SMS 건수
                detail_sheet.cell(row=14, column=4).value = counts["LMS"]    # D14: LMS/MMS 건수
                detail_sheet.cell(row=15, column=4).value = 0                # D15: 0으로 설정
                detail_sheet.cell(row=16, column=4).value = counts["TALK"]   # D16: 알림톡 건수
                
                print(f"   ✅ 세부내역 시트 업데이트 완료 - D13:{counts['SMS']}, D14:{counts['LMS']}, D15:0, D16:{counts['TALK']}")
            else:
                print("   ⚠️ 세부내역 시트를 찾을 수 없습니다")
                
        except Exception as e:
            print(f"❌ 세부내역 시트 업데이트 오류: {e}")
    
    def process_anhous_data(self, collection_date):
        """앤하우스 데이터 전처리 메인 함수"""
        try:
            print("🚀 앤하우스 데이터 전처리 시작")
            
            # 1. CSV 변환
            csv_files = self.convert_all_collected_files()
            print(f"✅ 변환 완료: {len(csv_files)}개 파일")
            
            # 2. 템플릿 찾기
            templates = self.find_anhous_templates()
            if not templates:
                print("❌ 앤하우스 템플릿 파일을 찾을 수 없습니다")
                return False
            
            # 3. 팀별 데이터 분류
            team_data = self.get_call_data_by_team(csv_files, collection_date)
            if not team_data:
                print("❌ 팀별 데이터를 찾을 수 없습니다")
                return False
            
            # 4. 템플릿 업데이트
            print("🔧 템플릿 파일 업데이트 중...")
            print(f"   발견된 템플릿: {templates}")
            print(f"   사용 가능한 팀: {list(team_data.keys())}")
            updated_files = []
            
            for template_name in templates:
                print(f"🔍 템플릿 처리 시작: {template_name}")
                # 팀 매칭
                template_team = None
                if 'annhouse_CS' in template_name:
                    template_team = "CS팀"
                elif 'annhouse_TS' in template_name:
                    template_team = "엔하우스"
                elif template_name == 'annhouse.xlsx':
                    template_team = "사업지원팀"
                
                print(f"   매칭된 팀: {template_team}")
                print(f"   사용 가능한 팀: {list(team_data.keys())}")
                
                if template_team and template_team in team_data:
                    print(f"🔧 {template_name} 템플릿 처리 시작 (팀: {template_team})")
                    # 템플릿 다운로드 및 업데이트
                    template_path = self.download_template(template_name)
                    if template_path:
                        print(f"✅ 템플릿 다운로드 완료: {template_path}")
                        updated_path = self.update_template_with_team_data(
                            template_path, 
                            {template_team: team_data[template_team]}, 
                            collection_date,
                            template_team,
                            csv_files
                        )
                        if updated_path:
                            updated_files.append(updated_path)
                            print(f"✅ 템플릿 업데이트 완료: {updated_path}")
                    else:
                        print(f"❌ 템플릿 다운로드 실패: {template_name}")
                else:
                    print(f"⚠️ 템플릿 매칭 실패: {template_name} (팀: {template_team})")
            
            print(f"✅ 전처리 완료: {len(updated_files)}개 파일 업데이트")
            
            # temp_processing 폴더 정리
            self.cleanup_temp_folder()
            
            return True
            
        except Exception as e:
            print(f"❌ 전처리 실패: {e}")
            return False
    
    def cleanup_temp_folder(self):
        """temp_processing 폴더 정리"""
        try:
            temp_dir = "temp_processing"
            if os.path.exists(temp_dir):
                # 모든 파일 삭제
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"🗑️ 삭제: {filename}")
                
                print("✅ temp_processing 폴더 정리 완료")
            else:
                print("⚠️ temp_processing 폴더가 존재하지 않습니다")
        except Exception as e:
            print(f"❌ 폴더 정리 실패: {e}")