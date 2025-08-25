import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, storage
import tempfile

class AnhousePreprocessor:
    def __init__(self):
        """앤하우스 전처리 클래스 초기화"""
        self.setup_firebase()
        self.download_dir = str(Path.home() / "Downloads")
        
    def setup_firebase(self):
        """Firebase Storage 연결 설정"""
        load_dotenv()
        cred_dict = json.loads(os.environ["FIREBASE_PRIVATE_KEY"])
        bucket_name = os.getenv("STORAGE_BUCKET", "services-e42af.firebasestorage.app")
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app(
                credentials.Certificate(cred_dict),
                {"storageBucket": bucket_name}
            )
        
        self.bucket = storage.bucket()
        print(f"✅ Firebase Storage 연결 완료: {self.bucket.name}")
    
    def convert_xls_to_csv(self, xls_file_path):
        """XLS 파일을 CSV로 변환"""
        csv_file_path = xls_file_path.replace('.xls', '.csv')
        
        try:
            # pandas로 .xls 파일 읽기
            df = pd.read_excel(xls_file_path, engine='xlrd')
            df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
            print(f"✅ .xls → .csv 변환 완료: {csv_file_path}")
            return csv_file_path
        except Exception as e:
            # HTML 파일인 경우 처리
            try:
                with open(xls_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if '<html>' in content.lower():
                    df = pd.read_html(content)[0]
                    
                    # 제목 행 제거하고 헤더 설정
                    if len(df) > 0 and '통화내역' in str(df.iloc[0]).lower():
                        df = df.iloc[1:].reset_index(drop=True)
                    
                    # 첫 번째 행을 헤더로 설정
                    if len(df) > 0:
                        df.columns = df.iloc[0]
                        df = df.iloc[1:].reset_index(drop=True)
                    
                    df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
                    print(f"✅ HTML → .csv 변환 완료: {csv_file_path}")
                    return csv_file_path
            except Exception as e2:
                print(f"❌ 변환 실패: {e2}")
                return None
    
    def convert_all_xls_files(self):
        """다운로드 폴더의 모든 XLS 파일을 CSV로 변환"""
        xls_files = [f for f in os.listdir(self.download_dir) if f.endswith('.xls')]
        csv_files = []
        
        for xls_file in xls_files:
            xls_path = os.path.join(self.download_dir, xls_file)
            csv_path = self.convert_xls_to_csv(xls_path)
            if csv_path:
                csv_files.append(csv_path)
        
        return csv_files
    
    def find_anhous_templates(self):
        """Firebase Storage에서 앤하우스 견적서 템플릿 파일들 찾기"""
        templates = []
        
        for blob in self.bucket.list_blobs():
            if "앤하우스" in blob.name and blob.name.endswith(('.xlsx', '.xls')):
                templates.append(blob.name)
                print(f"📄 템플릿 발견: {blob.name}")
        
        return templates
    
    def download_template(self, template_name):
        """템플릿 파일을 임시 폴더에 다운로드"""
        try:
            blob = self.bucket.blob(template_name)
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, os.path.basename(template_name))
            
            blob.download_to_filename(temp_path)
            print(f"✅ 템플릿 다운로드 완료: {template_name}")
            return temp_path
        except Exception as e:
            print(f"❌ 템플릿 다운로드 실패: {e}")
            return None
    
    def get_call_data(self, csv_files):
        """CSV 파일에서 CALL 데이터 추출"""
        call_data = None
        
        for csv_file in csv_files:
            if "통화내역" in csv_file:
                try:
                    df = pd.read_csv(csv_file, encoding='utf-8-sig')
                    print(f"📊 CALL 데이터 로드: {len(df)}행")
                    call_data = df
                    break
                except Exception as e:
                    print(f"❌ CALL 데이터 로드 실패: {e}")
        
        return call_data
    
    def update_template(self, template_path, call_data, collection_date):
        """템플릿 파일 업데이트"""
        try:
            # Excel 파일 읽기
            with pd.ExcelFile(template_path) as xls:
                # 통화료 시트 읽기
                df = pd.read_excel(xls, sheet_name='통화료')
            
            # 날짜 정보 파싱
            date_obj = datetime.strptime(collection_date, '%Y-%m-%d')
            year_month = f"{date_obj.year}년 {date_obj.month}월"
            
            # H3 셀에 과금월 업데이트
            df.iloc[2, 7] = year_month  # H3 = (2, 7)
            
            # B7:L7 헤더 확인
            headers = df.iloc[6, 1:12].tolist()  # B7:L7
            print(f"📋 헤더: {headers}")
            
            # CALL 데이터에서 필요한 컬럼 찾기
            if call_data is not None:
                # 통화시간부터 콜종료시간까지 매핑
                column_mapping = {
                    '통화시간': '통화시간',
                    '콜시작시간': '콜시작시간', 
                    '대기시작시간': '대기시작시간',
                    '링시작시간': '링시작시간',
                    '통화시작시간': '통화시작시간',
                    '콜종료시간': '콜종료시간'
                }
                
                # 데이터 행 추가 (B8부터 시작)
                start_row = 7  # B8 = (7, 1)
                
                for idx, call_row in call_data.iterrows():
                    # 기준월 추가
                    df.iloc[start_row + idx, 1] = year_month  # B열
                    
                    # CALL 데이터 매핑
                    for template_col, call_col in column_mapping.items():
                        if call_col in call_data.columns:
                            col_idx = headers.index(template_col) + 1  # B7부터 시작하므로 +1
                            df.iloc[start_row + idx, col_idx] = call_row[call_col]
            
            # 업데이트된 파일 저장
            output_path = template_path.replace('.xlsx', '_updated.xlsx')
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='통화료', index=False)
            
            print(f"✅ 템플릿 업데이트 완료: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 템플릿 업데이트 실패: {e}")
            return None
    
    def process_anhous_data(self, collection_date):
        """앤하우스 데이터 전처리 메인 프로세스"""
        print("🚀 앤하우스 전처리 시작")
        
        # 0. 수집된 파일들을 CSV로 변환
        print("\n0️⃣ XLS 파일을 CSV로 변환")
        csv_files = self.convert_all_xls_files()
        
        # 1. Firebase에서 앤하우스 템플릿 파일들 찾기
        print("\n1️⃣ Firebase에서 앤하우스 템플릿 찾기")
        templates = self.find_anhous_templates()
        
        if not templates:
            print("❌ 앤하우스 템플릿을 찾을 수 없습니다.")
            return
        
        # 2. CALL 데이터 추출
        print("\n2️⃣ CALL 데이터 추출")
        call_data = self.get_call_data(csv_files)
        
        if call_data is None:
            print("❌ CALL 데이터를 찾을 수 없습니다.")
            return
        
        # 3. 각 템플릿 파일 업데이트
        print("\n3️⃣ 템플릿 파일 업데이트")
        updated_files = []
        
        for template in templates:
            print(f"\n📄 템플릿 처리: {template}")
            
            # 템플릿 다운로드
            template_path = self.download_template(template)
            if template_path:
                # 템플릿 업데이트
                updated_path = self.update_template(template_path, call_data, collection_date)
                if updated_path:
                    updated_files.append(updated_path)
        
        print(f"\n✅ 전처리 완료! 업데이트된 파일: {len(updated_files)}개")
        return updated_files

def main():
    """메인 함수"""
    # 수집 날짜 (예: 2025-05-01)
    collection_date = "2025-05-01"
    
    preprocessor = AnhousePreprocessor()
    updated_files = preprocessor.process_anhous_data(collection_date)
    
    if updated_files:
        print("\n📁 업데이트된 파일 목록:")
        for file in updated_files:
            print(f"   - {file}")

if __name__ == "__main__":
    main()
