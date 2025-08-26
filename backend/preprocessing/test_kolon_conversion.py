#!/usr/bin/env python3
"""코오롱 XLS → CSV 변환 테스트"""

import pandas as pd
import os
from pathlib import Path

def test_xls_to_csv_conversion():
    """XLS 파일을 CSV로 변환하는 테스트"""
    
    # 테스트할 파일 경로
    xls_file = "상세매출내역해외목록 (5).xls"
    
    print("=" * 50)
    print("코오롱 XLS → CSV 변환 테스트")
    print("=" * 50)
    
    # 파일 존재 확인
    if not os.path.exists(xls_file):
        print(f"❌ 파일을 찾을 수 없습니다: {xls_file}")
        print(f"   현재 디렉토리: {os.getcwd()}")
        print(f"   현재 디렉토리의 파일들:")
        for file in os.listdir("."):
            if file.endswith(('.xls', '.xlsx', '.csv')):
                print(f"     - {file}")
        return
    
    print(f"📂 원본 파일: {xls_file}")
    print(f"📊 파일 크기: {os.path.getsize(xls_file):,} bytes")
    
    try:
        # XLS 파일 읽기 시도
        print(f"\n🔍 XLS 파일 읽기 시도...")
        
        # 여러 방법으로 시도
        df = None
        
        # 방법 1: 일반적인 Excel 읽기
        try:
            df = pd.read_excel(xls_file, engine='xlrd')
            print(f"   ✅ xlrd 엔진으로 성공")
        except Exception as e1:
            print(f"   ❌ xlrd 엔진 실패: {e1}")
            
            # 방법 2: openpyxl 엔진 시도
            try:
                df = pd.read_excel(xls_file, engine='openpyxl')
                print(f"   ✅ openpyxl 엔진으로 성공")
            except Exception as e2:
                print(f"   ❌ openpyxl 엔진 실패: {e2}")
                
                # 방법 3: HTML 형태로 읽기 (앤하우스 방식)
                try:
                    with open(xls_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if '<table' in content.lower():
                        print(f"   🔍 HTML 테이블 형태 감지, pandas.read_html 사용")
                        tables = pd.read_html(xls_file)
                        if tables:
                            df = tables[0]
                            print(f"   ✅ HTML 테이블로 읽기 성공")
                        else:
                            print(f"   ❌ HTML 테이블이 비어있음")
                    else:
                        print(f"   ❌ HTML 테이블 형태가 아님")
                except Exception as e3:
                    print(f"   ❌ HTML 읽기 실패: {e3}")
        
        if df is None:
            print(f"❌ 모든 방법으로 파일 읽기 실패")
            return
        
        # 데이터 정보 출력
        print(f"\n📊 변환된 데이터 정보:")
        print(f"   행 수: {len(df):,}")
        print(f"   열 수: {len(df.columns):,}")
        print(f"   컬럼명: {list(df.columns)}")
        
        # 첫 5행 미리보기
        print(f"\n🔍 데이터 미리보기 (첫 5행):")
        print(df.head())
        
        # CSV로 저장
        csv_filename = xls_file.replace('.xls', '.csv')
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ CSV 변환 완료: {csv_filename}")
        print(f"   CSV 파일 크기: {os.path.getsize(csv_filename):,} bytes")
        
        # 변환된 CSV 파일 검증
        print(f"\n🔍 변환된 CSV 파일 검증:")
        csv_df = pd.read_csv(csv_filename)
        print(f"   CSV 행 수: {len(csv_df):,}")
        print(f"   CSV 열 수: {len(csv_df.columns):,}")
        
        if len(df) == len(csv_df) and len(df.columns) == len(csv_df.columns):
            print(f"   ✅ 데이터 무결성 확인됨")
        else:
            print(f"   ⚠️ 데이터 불일치 감지")
        
        # 데이터 타입 정보
        print(f"\n📋 데이터 타입 정보:")
        for col in df.columns:
            print(f"   {col}: {df[col].dtype}")
        
        # 빈 값 확인
        print(f"\n🔍 빈 값 확인:")
        null_counts = df.isnull().sum()
        for col, null_count in null_counts.items():
            if null_count > 0:
                print(f"   {col}: {null_count}개 빈 값")
        
        return csv_filename
        
    except Exception as e:
        print(f"❌ 변환 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_xls_to_csv_conversion()
    if result:
        print(f"\n🎉 변환 성공! 결과 파일: {result}")
    else:
        print(f"\n💥 변환 실패")
