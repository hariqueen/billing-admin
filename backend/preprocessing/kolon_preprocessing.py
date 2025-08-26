import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from openpyxl.styles import PatternFill, Border, Side
import re

class KolonPreprocessor:
    def __init__(self):
        self.download_dir = str(Path.home() / "Downloads")
        
    def convert_xls_to_csv(self, xls_file_path):
        """XLS/XLSX/CSV 파일을 CSV로 변환 또는 확인"""
        try:
            print(f"🔍 변환 시작: {os.path.basename(xls_file_path)}")
            print(f"   원본 파일: {xls_file_path}")
            
            # 파일 확장자 확인
            if xls_file_path.endswith('.csv'):
                # 이미 CSV 파일인 경우 변환 필요 없음
                print(f"   이미 CSV 파일입니다")
                try:
                    # CSV 파일 읽어서 데이터 확인만
                    df = pd.read_csv(xls_file_path)
                    print(f"   데이터 형태: {df.shape[0]}행 x {df.shape[1]}열")
                    print(f"   컬럼: {list(df.columns)}")
                    print(f"✅ CSV 파일 확인 완료")
                    return xls_file_path
                except Exception as e:
                    print(f"❌ CSV 파일 읽기 실패: {e}")
                    return None
            elif xls_file_path.endswith('.xlsx'):
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
                        print(f"   HTML 테이블 형태 감지")
                        df = pd.read_html(xls_file_path)[0]
                        print(f"   데이터 형태: {df.shape[0]}행 x {df.shape[1]}열")
                        print(f"   컬럼: {list(df.columns)}")
                        
                        # CSV로 저장
                        # 원본 파일명에서 확장자만 변경하여 CSV 저장
                        csv_path = os.path.splitext(xls_file_path)[0] + '.csv'
                        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                        print(f"✅ HTML → .csv 변환 완료: {csv_path}")
                        return csv_path
                    else:
                        # 일반 Excel 파일 처리
                        print(f"   일반 Excel 파일로 읽기 시도...")
                        df = pd.read_excel(xls_file_path)
                        print(f"   데이터 형태: {df.shape[0]}행 x {df.shape[1]}열")
                        print(f"   컬럼: {list(df.columns)}")
                        # 원본 파일명에서 확장자만 변경하여 CSV 저장
                        csv_path = os.path.splitext(xls_file_path)[0] + '.csv'
                        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                        print(f"✅ Excel → .csv 변환 완료: {csv_path}")
                        return csv_path
                except UnicodeDecodeError:
                    # 인코딩 오류 시 Excel로 읽기 시도
                    print(f"   인코딩 오류, Excel로 읽기 시도...")
                    df = pd.read_excel(xls_file_path)
                    print(f"   데이터 형태: {df.shape[0]}행 x {df.shape[1]}열")
                    print(f"   컬럼: {list(df.columns)}")
                    csv_path = xls_file_path.replace('.xls', '.csv')
                    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                    print(f"✅ Excel → .csv 변환 완료: {csv_path}")
                    return csv_path
                
        except Exception as e:
            print(f"❌ 변환 실패: {xls_file_path}, 오류: {e}")
            return None

    def parse_korean_datetime(self, date_str):
        """한글 날짜를 datetime으로 변환"""
        try:
            # "2025년 7월 30일 오후 10:13" 형식 파싱
            pattern = r'(\d{4})년\s+(\d{1,2})월\s+(\d{1,2})일\s+(오전|오후)\s+(\d{1,2}):(\d{2})'
            match = re.match(pattern, date_str)
            if match:
                year, month, day, ampm, hour, minute = match.groups()
                hour = int(hour)
                if ampm == '오후' and hour < 12:
                    hour += 12
                elif ampm == '오전' and hour == 12:
                    hour = 0
                return datetime(int(year), int(month), int(day), hour, int(minute))
        except Exception as e:
            print(f"날짜 파싱 실패: {date_str}, 오류: {e}")
        return None

    def preprocess_jaegyeong_data(self, df):
        """재경팀 데이터 전처리"""
        try:
            # 날짜 컬럼 전처리
            df["매출일자"] = df["매출일자"].astype(str).str.zfill(8)
            df["승인시각"] = df["승인시각"].astype(str).str.zfill(6)
            df["날짜"] = df["매출일자"] + df["승인시각"]
            df["날짜변환"] = df["날짜"].str.slice(0, 12)
            df["일자"] = df["날짜"].str.slice(0, 8)
            
            # 거래ID 추가
            df["거래ID"] = range(1, len(df) + 1)
            
            # 숫자 데이터 전처리
            numeric_cols = ["매출금액", "현지거래금액", "원화환산금액", "해외접수달러금액"]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
            
            print("✅ 재경팀 데이터 전처리 완료")
            return df
        except Exception as e:
            print(f"❌ 재경팀 데이터 전처리 실패: {e}")
            return None

    def preprocess_openai_data(self, df):
        """OpenAI 데이터 전처리"""
        try:
            # 날짜 전처리
            df["datetime"] = df["날짜"].apply(self.parse_korean_datetime)
            df["날짜변환"] = df["datetime"].dt.strftime("%Y%m%d%H%M")
            df["일자"] = df["datetime"].dt.strftime("%Y%m%d")
            
            # 금액 전처리 (공백 제거 후 $ 제거)
            df["금액(USD)"] = pd.to_numeric(
                df["금액"].str.strip().str.replace('$', '').str.replace(',', ''),
                errors='coerce'
            )
            
            print("✅ OpenAI 데이터 전처리 완료")
            return df
        except Exception as e:
            print(f"❌ OpenAI 데이터 전처리 실패: {e}")
            return None

    def match_data(self, df_jaegyeong, df_openai):
        """두 데이터프레임을 매칭"""
        try:
            # 데이터 병합 (날짜와 금액으로 매칭)
            print("🔄 데이터 매칭 시작...")
            print(f"   재경팀 데이터: {len(df_jaegyeong)}건")
            print(f"   OpenAI 데이터: {len(df_openai)}건")
            
            merged = pd.merge(
                df_jaegyeong,
                df_openai[["일자", "금액(USD)", "계정"]],
                how="left",
                left_on="일자",
                right_on="일자"
            )
            
            # 금액 차이가 0.5 USD 이내인 경우만 매칭으로 인정
            merged["금액차이"] = abs(merged["해외접수달러금액"] - merged["금액(USD)"])
            merged = merged[merged["금액차이"] <= 0.5]
            
            # 매칭/미매칭 데이터 분리
            matched_data = merged[~merged["계정"].isna()].copy()
            unmatched_data = df_jaegyeong[~df_jaegyeong["일자"].isin(matched_data["일자"])].copy()
            
            # 중복 제거
            matched_data = matched_data.drop_duplicates(subset=["거래ID"])
            
            print(f"✅ 데이터 매칭 완료 (매칭: {len(matched_data)}건, 미매칭: {len(unmatched_data)}건)")
            return matched_data, unmatched_data
        except Exception as e:
            print(f"❌ 데이터 매칭 실패: {e}")
            return None, None

    def create_summary_data(self, kolon_df):
        """요약 데이터 생성"""
        try:
            # 주요 월 찾기
            main_month = kolon_df['매출일자'].iloc[0][4:6]
            
            # 날짜 목록 생성
            dates = []
            
            # 이전 월의 데이터 확인
            prev_month_data = kolon_df[kolon_df['매출일자'].str[4:6] != main_month]
            if not prev_month_data.empty:
                # 이전 월의 데이터 추가
                for _, row in prev_month_data.iterrows():
                    dates.append(row['매출일자'])
            
            # 주요 월의 1일부터 말일까지 생성
            year = kolon_df['매출일자'].iloc[0][:4]
            last_day = 31 if main_month in ['01', '03', '05', '07', '08', '10', '12'] else \
                      30 if main_month in ['04', '06', '09', '11'] else \
                      29 if main_month == '02' and int(year) % 4 == 0 else 28
            
            # 주요 월의 모든 날짜 추가
            for day in range(1, last_day + 1):
                dates.append(f"{year}{main_month}{str(day).zfill(2)}")
            
            # 데이터 딕셔너리 생성
            summary_data = {
                '날짜': [],
                '승인금액(USD)': [],
                '승인금액(원화)': []
            }
            
            # 합계 계산
            usd_sum = kolon_df['해외접수달러금액'].sum()
            krw_sum = kolon_df['원화환산금액'].sum()
            
            # 합계 행 추가
            summary_data['날짜'].append('합계')
            summary_data['승인금액(USD)'].append(usd_sum)
            summary_data['승인금액(원화)'].append(krw_sum)
            
            # 날짜별 데이터 행 추가
            for date in dates:
                date_data = kolon_df[kolon_df['매출일자'] == date]
                summary_data['날짜'].append(f"{date[:4]}.{date[4:6]}.{date[6:]}")
                
                if not date_data.empty:
                    summary_data['승인금액(USD)'].append(date_data['해외접수달러금액'].sum())
                    summary_data['승인금액(원화)'].append(date_data['원화환산금액'].sum())
                else:
                    summary_data['승인금액(USD)'].append(0)
                    summary_data['승인금액(원화)'].append(0)
            
            print("✅ 요약 데이터 생성 완료")
            return summary_data
            
        except Exception as e:
            print(f"❌ 요약 데이터 생성 실패: {e}")
            return None

    def save_kolon_excel(self, kolon_df, output_path):
        """코오롱 전용 Excel 파일 저장"""
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 1. 요약 시트 생성
                summary_data = self.create_summary_data(kolon_df)
                if summary_data:
                    # 데이터프레임 생성
                    summary_df = pd.DataFrame(summary_data)
                    
                    # 워크시트 생성
                    worksheet = writer.book.create_sheet("요약", 0)
                    
                    # 헤더 추가 (2행에 추가)
                    worksheet.cell(row=2, column=2, value="")  # B2
                    worksheet.cell(row=2, column=3, value="승인금액(USD)")  # C2
                    worksheet.cell(row=2, column=4, value="승인금액(원화)")  # D2
                    
                    # 데이터 입력 (3행부터)
                    current_row = 3
                    for i in range(len(summary_data['날짜'])):
                        worksheet.cell(row=current_row, column=2, value=summary_data['날짜'][i])
                        worksheet.cell(row=current_row, column=3, value=summary_data['승인금액(USD)'][i])
                        worksheet.cell(row=current_row, column=4, value=summary_data['승인금액(원화)'][i])
                        current_row += 1
                    
                    # 테두리 스타일 정의
                    thin_border = Border(
                        left=Side(style='thin'),
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
                    
                    # 데이터가 있는 마지막 행 찾기
                    max_row = len(summary_data['날짜']) + 2  # 헤더 행 + 데이터 행
                    
                    # B,C,D열에 테두리와 스타일 적용
                    for row in range(2, max_row + 1):  # 2행부터 마지막 행까지
                        for col in range(2, 5):  # B(2), C(3), D(4)열
                            cell = worksheet.cell(row=row, column=col)
                            cell.border = thin_border
                            
                            # sum 행에만 배경색 적용
                            if row == 3:  # 3행에 합계가 위치
                                green_fill = PatternFill(start_color='92D050', end_color='92D050', fill_type='solid')
                                cell.fill = green_fill
                
                # 2. 코오롱 해외결제 시트
                kolon_df.to_excel(writer, sheet_name="코오롱 해외결제", index=False)
                
            print(f"✅ Excel 파일 저장 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Excel 파일 저장 실패: {e}")
            return False

    def process_kolon_data(self, collection_date):
        """코오롱 데이터 전처리 메인 함수"""
        try:
            print("🚀 코오롱 데이터 전처리 시작")
            
            # 1. temp_processing 폴더에서 코오롱 파일 찾기
            temp_dir = "temp_processing"
            if not os.path.exists(temp_dir):
                print("❌ temp_processing 폴더를 찾을 수 없습니다")
                return False
            
            kolon_files = []
            for filename in os.listdir(temp_dir):
                if "코오롱" in filename and filename.endswith((".xls", ".xlsx", ".csv")):
                    file_path = os.path.join(temp_dir, filename)
                    kolon_files.append(file_path)
            
            if len(kolon_files) != 2:
                print(f"❌ 코오롱 파일이 2개 필요합니다. 현재: {len(kolon_files)}개")
                return False
            
            # 2. CSV 변환
            csv_files = []
            for file_path in kolon_files:
                csv_path = self.convert_xls_to_csv(file_path)
                if csv_path:
                    csv_files.append(csv_path)
            
            if len(csv_files) != 2:
                print("❌ CSV 변환 실패")
                return False
            
            print(f"✅ 변환 완료: {len(csv_files)}개 파일")
            
            # 3. 데이터 읽기
            print("📂 변환된 CSV 파일 목록:")
            for f in csv_files:
                print(f"   - {f}")
                
            # 파일 찾기 (파일 내용으로 구분)
            jaegyeong_files = []
            openai_files = []
            
            for f in csv_files:
                try:
                    df = pd.read_csv(f)
                    if '매출일자' in df.columns:  # 재경팀 데이터
                        jaegyeong_files.append(f)
                    elif '날짜' in df.columns:  # OpenAI 데이터
                        openai_files.append(f)
                except Exception as e:
                    print(f"❌ 파일 읽기 실패: {f}, 오류: {e}")
            
            if not jaegyeong_files:
                print("❌ 재경팀 데이터 파일을 찾을 수 없습니다")
                return False
            if not openai_files:
                print("❌ OpenAI 데이터 파일을 찾을 수 없습니다")
                return False
                
            jaegyeong_file = jaegyeong_files[0]
            openai_file = openai_files[0]
            
            # 재경팀 데이터 로드 (빈 행 제거)
            df_jaegyeong = pd.read_csv(jaegyeong_file).dropna(how='all')
            
            # OpenAI 데이터 로드
            df_openai = pd.read_csv(openai_file)
            
            print(f"✅ 데이터 로드 완료 (재경팀: {len(df_jaegyeong)}행, OpenAI: {len(df_openai)}행)")
            
            # 4. 데이터 전처리
            df_jaegyeong = self.preprocess_jaegyeong_data(df_jaegyeong)
            if df_jaegyeong is None:
                return False
                
            df_openai = self.preprocess_openai_data(df_openai)
            if df_openai is None:
                return False
            
            print("✅ 데이터 전처리 완료")
            
            # 5. 데이터 매칭
            matched_data, unmatched_data = self.match_data(df_jaegyeong, df_openai)
            if matched_data is None:
                return False
            
            print(f"✅ 데이터 매칭 완료 (매칭: {len(matched_data)}건, 미매칭: {len(unmatched_data)}건)")
            
            # 6. 결과 파일 생성
            # 6.1. 매칭 결과 CSV 저장
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            collection_month = datetime.strptime(collection_date, '%Y-%m-%d').strftime('%Y%m')
            
            # 1. OpenAI 매칭결과 파일 생성 (모든 데이터)
            openai_filename = f"OpenAI매칭결과_{date_str}_{collection_month}.csv"
            openai_path = os.path.join(self.download_dir, openai_filename)
            
            # OpenAI 데이터로부터 결과 생성
            result_df = pd.DataFrame({
                '매출일자': df_openai['datetime'].dt.strftime('%Y%m%d'),  # YYYYMMDD 형식
                '승인시각': df_openai['datetime'].dt.strftime('%H%M%S'),  # HHMMSS 형식
                '매출금액': df_openai['금액(USD)'],
                '계정': df_openai['계정'],  # 원본 계정값 사용
                '표준적요': 156,  # 고정값
                '증빙유형': '003',  # 고정값
                '적요': 'OpenAI_GPT API 토큰 비용_' + df_openai['계정'],  # 계정별 적요
                '프로젝트': df_openai['계정']  # 계정값을 프로젝트로 사용
            })
            
            result_df.to_csv(openai_path, index=False, encoding='utf-8-sig')
            print(f"✅ OpenAI 매칭결과 CSV 저장 완료: {openai_filename}")
            
            # 2. 코오롱 매칭결과 파일 생성 (매칭된 데이터만)
            matched_filename = f"코오롱_매칭결과_{date_str}_{collection_month}.csv"
            matched_path = os.path.join(self.download_dir, matched_filename)
            matched_data.to_csv(matched_path, index=False, encoding='utf-8-sig')
            
            print(f"✅ 매칭 결과 CSV 저장 완료: {matched_filename}")
            
            # 6.2. 요약 보고서 Excel 저장
            report_filename = f"코오롱_청구내역서_{date_str}_{collection_month}.xlsx"
            report_path = os.path.join(self.download_dir, report_filename)
            
            if self.save_kolon_excel(matched_data, report_path):
                print(f"✅ 청구내역서 Excel 저장 완료: {report_filename}")
                return True
            else:
                print("❌ 청구내역서 Excel 저장 실패")
                return False
            
        except Exception as e:
            import traceback
            print(f"❌ 전처리 실패: {e}")
            print(f"상세 에러: {traceback.format_exc()}")
            return False