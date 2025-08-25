import os
import pandas as pd
from datetime import datetime
from io import StringIO
import firebase_admin
from firebase_admin import credentials, storage

class EnhancedAnhousePreprocessor:
    def __init__(self):
        self.bucket = None
        self.setup_firebase()
        
        # 팀별 파일 매핑
        self.team_file_mapping = {
            "CS팀": "annhouse_CS.xlsx",
            "사업지원팀": "annhouse.xlsx", 
            "엔하우스": "annhouse_TS.xlsx"
        }
    
    def setup_firebase(self):
        """Firebase Storage 연결 설정"""
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate("firebase-credentials.json")
                firebase_admin.initialize_app(cred, {
                    'storageBucket': 'your-project-id.appspot.com'
                })
            self.bucket = storage.bucket()
            print("✅ Firebase Storage 연결 완료")
        except Exception as e:
            print(f"❌ Firebase 연결 실패: {e}")
    
    def convert_xls_to_csv(self, xls_file_path):
        """XLS 파일을 CSV로 변환"""
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
                
        except Exception as e:
            print(f"❌ 변환 실패: {xls_file_path}, 오류: {e}")
            return None
    
    def convert_all_collected_files(self):
        """수집된 모든 XLS 파일을 CSV로 변환"""
        csv_files = []
        
        # Downloads 폴더 검색
        downloads_dir = os.path.expanduser("~/Downloads")
        for filename in os.listdir(downloads_dir):
            if filename.startswith("통화내역") and filename.endswith(".xls"):
                file_path = os.path.join(downloads_dir, filename)
                csv_path = self.convert_xls_to_csv(file_path)
                if csv_path:
                    csv_files.append(csv_path)
        
        # uploads 폴더 검색
        uploads_dir = "uploads"
        if os.path.exists(uploads_dir):
            for filename in os.listdir(uploads_dir):
                if filename.startswith("앤하우스_CALL") and filename.endswith(".xls"):
                    file_path = os.path.join(uploads_dir, filename)
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
            temp_dir = os.path.join(os.getcwd(), "temp_templates")
            os.makedirs(temp_dir, exist_ok=True)
            
            local_path = os.path.join(temp_dir, template_name)
            blob.download_to_filename(local_path)
            
            return local_path
        except Exception as e:
            print(f"❌ 템플릿 다운로드 실패: {e}")
            return None
    
    def get_call_data_by_team(self, csv_files, collection_date):
        """CSV 파일들에서 팀별 CALL 데이터 분류"""
        team_data = {}
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                
                if '팀' in df.columns:
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
    
    def update_template_with_team_data(self, template_path, team_data, collection_date):
        """템플릿 파일을 팀별 데이터로 업데이트"""
        try:
            # Excel 파일 읽기
            with pd.ExcelFile(template_path) as xls:
                df = pd.read_excel(xls, sheet_name='통화료')
            
            # 날짜 정보 파싱
            date_obj = datetime.strptime(collection_date, '%Y-%m-%d')
            year_month = f"{date_obj.year}년 {date_obj.month}월"
            
            # H3 셀에 과금월 업데이트
            if df.shape[0] > 2 and df.shape[1] > 7:
                df.iloc[2, 7] = year_month
            
            # 헤더 확인
            headers = []
            if df.shape[0] > 6 and df.shape[1] > 11:
                headers = df.iloc[6, 1:12].tolist()
            
            # 팀별 데이터 처리
            current_row = 7
            
            for team, data_list in team_data.items():
                print(f"🔧 {team} 데이터 처리 중...")
                
                for team_df in data_list:
                    column_mapping = {
                        '통화시간': '통화시간',
                        '콜시작시간': '콜시작시간', 
                        '대기시작시간': '대기시작시간',
                        '링시작시간': '링시작시간',
                        '통화시작시간': '통화시작시간',
                        '콜종료시간': '콜종료시간'
                    }
                    
                    for idx, call_row in team_df.iterrows():
                        if current_row < df.shape[0]:
                            # 기준월 추가
                            if df.shape[1] > 1:
                                df.iloc[current_row, 1] = year_month
                            
                            # CALL 데이터 매핑
                            for template_col, call_col in column_mapping.items():
                                if call_col in team_df.columns and template_col in headers:
                                    try:
                                        col_idx = headers.index(template_col) + 1
                                        if col_idx < df.shape[1]:
                                            df.iloc[current_row, col_idx] = call_row[call_col]
                                    except ValueError:
                                        pass
                        
                        current_row += 1
                
                # 파일명 생성
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
                
                # uploads 폴더에 저장
                upload_dir = "uploads"
                os.makedirs(upload_dir, exist_ok=True)
                output_path = os.path.join(upload_dir, new_filename)
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='통화료', index=False)
            
            print(f"✅ 템플릿 업데이트 완료: {new_filename}")
            return output_path
            
        except Exception as e:
            print(f"❌ 템플릿 업데이트 실패: {e}")
            return None
    
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
            updated_files = []
            
            for template_name in templates:
                # 팀 매칭
                template_team = None
                if 'annhouse_CS' in template_name:
                    template_team = "CS팀"
                elif 'annhouse_TS' in template_name:
                    template_team = "엔하우스"
                elif template_name == 'annhouse.xlsx':
                    template_team = "사업지원팀"
                
                if template_team and template_team in team_data:
                    # 템플릿 다운로드 및 업데이트
                    template_path = self.download_template(template_name)
                    if template_path:
                        updated_path = self.update_template_with_team_data(
                            template_path, 
                            {template_team: team_data[template_team]}, 
                            collection_date
                        )
                        if updated_path:
                            updated_files.append(updated_path)
            
            print(f"✅ 전처리 완료: {len(updated_files)}개 파일 업데이트")
            return True
            
        except Exception as e:
            print(f"❌ 전처리 실패: {e}")
            return False
