import pandas as pd
import os
from pathlib import Path

def convert_xls_to_csv(xls_file_path, csv_file_path=None):
    if csv_file_path is None:
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
                # 첫 번째 행에 "통화내역"이 있으면 제거
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

def test_conversion():
    """변환 테스트 실행"""
    # 다운로드 폴더에서 .xls 파일 찾기
    download_dir = str(Path.home() / "Downloads")
    xls_files = [f for f in os.listdir(download_dir) if f.endswith('.xls')]
    
    if not xls_files:
        print("❌ 다운로드 폴더에 .xls 파일이 없습니다.")
        return
    
    # 가장 최근 .xls 파일 선택
    latest_xls = max(xls_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
    xls_file_path = os.path.join(download_dir, latest_xls)
    
    print(f"📁 변환 파일: {latest_xls}")
    
    # .xls → .csv 변환
    csv_file = convert_xls_to_csv(xls_file_path)
    
    if csv_file:
        print(f"✅ 변환 완료: {os.path.basename(csv_file)}")

if __name__ == "__main__":
    test_conversion()
