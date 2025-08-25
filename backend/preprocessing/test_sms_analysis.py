#!/usr/bin/env python3
"""SMS 데이터 분석 테스트"""

import pandas as pd

def analyze_sms_data():
    """SMS 데이터의 문자유형과 발신번호를 분석"""
    try:
        # SMS CSV 파일 읽기
        sms_file = "temp_processing/앤하우스_SMS 데이터_20250825_190037_발송이력_system_202585925185940.csv"
        df = pd.read_csv(sms_file)
        
        print("=" * 50)
        print("SMS 데이터 분석")
        print("=" * 50)
        
        print(f"📊 총 데이터 수: {len(df)}행")
        print(f"📋 컬럼: {list(df.columns)}")
        
        print("\n🔍 발송상태별 분포:")
        print(df['발송상태'].value_counts())
        
        print("\n🔍 문자유형별 분포:")
        print(df['문자유형'].value_counts())
        
        # 성공 전달만 필터링
        success_df = df[df['발송상태'] == '성공(전달)']
        print(f"\n✅ 성공 전달 건수: {len(success_df)}건")
        
        print("\n🔍 성공 전달 중 문자유형별 분포:")
        print(success_df['문자유형'].value_counts())
        
        # 발신번호 분석
        success_df['발신번호_정리'] = success_df['발신번호'].astype(str).str.replace('.0', '')
        print("\n🔍 발신번호별 분포:")
        print(success_df['발신번호_정리'].value_counts())
        
        # 각 팀별 SMS 분석
        teams = {
            "CS팀": "15888298",
            "엔하우스": "15884611", 
            "사업지원팀": "15880656"
        }
        
        for team, sender in teams.items():
            team_data = success_df[success_df['발신번호_정리'] == sender]
            print(f"\n📈 {team} (발신번호: {sender}):")
            print(f"   총 건수: {len(team_data)}건")
            if len(team_data) > 0:
                print(f"   문자유형별:")
                msg_counts = team_data['문자유형'].value_counts()
                for msg_type, count in msg_counts.items():
                    print(f"     {msg_type}: {count}건")
        
        print("\n🔍 문자유형 고유값 확인:")
        unique_types = df['문자유형'].unique()
        for msg_type in unique_types:
            print(f"   '{msg_type}'")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_sms_data()
