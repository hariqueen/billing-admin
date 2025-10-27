import pandas as pd
from datetime import datetime
from .config import ExpenseConfig

class ExpenseDataProcessor:
    """지출결의서 데이터 처리 클래스"""
    
    def __init__(self):
        self.config = ExpenseConfig()
    
    def load_file(self, file_path):
        """파일 로드 (다양한 인코딩 시도)"""
        try:
            if file_path.endswith('.csv'):
                # 다양한 인코딩 시도
                encodings = ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr', 'latin-1']
                
                for encoding in encodings:
                    try:
                        print(f"{encoding} 인코딩으로 파일 읽기 시도...")
                        data = pd.read_csv(file_path, encoding=encoding)
                        print(f"{encoding} 인코딩으로 파일 읽기 성공")
                        print(f"   데이터 형태: {data.shape[0]}행 x {data.shape[1]}열")
                        print(f"   컬럼: {list(data.columns)}")
                        return data
                    except UnicodeDecodeError:
                        print(f"{encoding} 인코딩 실패")
                        continue
                    except Exception as e:
                        print(f"{encoding} 인코딩으로 읽기 실패: {e}")
                        continue
                
                raise Exception("지원되는 인코딩으로 파일을 읽을 수 없습니다")
            else:
                return pd.read_excel(file_path)
        except Exception as e:
            raise Exception(f"파일을 읽을 수 없습니다: {e}")
    
    def process_data(self, data, category, start_date, end_date):
        """데이터 처리 및 필터링"""
        try:
            print(f"데이터 처리 시작:")
            print(f"   카테고리: {category}")
            print(f"   조회 기간: {start_date} ~ {end_date}")
            print(f"   원본 데이터 컬럼: {list(data.columns)}")
            print(f"   데이터 샘플 (첫 3행):")
            for i, (idx, row) in enumerate(data.head(3).iterrows()):
                print(f"     {i+1}: {row.to_dict()}")
            
            # 날짜 형식 변환
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")
            
            # 데이터 전처리
            processed_data = []
            
            for index, row in data.iterrows():
                # 실제 컬럼명에 맞게 매핑
                processed_row = {
                    'category': category,
                    'amount': self.clean_amount(row.get('매출금액', 0)),
                    'standard_summary': self.clean_text_field(row.get('표준적요', '')),
                    'evidence_type': self.format_evidence_type(row.get('증빙유형', '')),
                    'note': self.clean_text_field(row.get('적요', '')),
                    'project': self.clean_text_field(row.get('프로젝트', '')),
                    'start_date': start_date,
                    'end_date': end_date,
                    'original_data': row.to_dict()
                }
                processed_data.append(processed_row)
            
            return processed_data
            
        except Exception as e:
            raise Exception(f"데이터 처리 중 오류: {e}")
        
    def format_evidence_type(self, value):
        """증빙유형 포맷팅 - 앞에 00 추가"""
        try:
            if pd.isna(value) or value == '':
                return ''
            
            # 문자열로 변환하고 공백 제거
            str_value = str(value).strip()
            
            # 빈 문자열이면 그대로 반환
            if not str_value:
                return ''
            
            # 소숫점 제거 (3.0 → 3)
            if '.' in str_value:
                str_value = str_value.split('.')[0]
            
            # 숫자인지 확인
            try:
                int_value = int(float(str_value))
                # 한 자리 숫자면 앞에 00 추가 (3 → 003)
                if 0 <= int_value <= 9:
                    return f"00{int_value}"
                # 두 자리 숫자면 앞에 0 추가 (12 → 012)
                elif 10 <= int_value <= 99:
                    return f"0{int_value}"
                # 세 자리 이상이면 그대로
                else:
                    return str(int_value)
            except (ValueError, TypeError):
                # 숫자가 아니면 그대로 반환
                return str_value
                
        except Exception:
            return str(value) if value is not None else ''
        
    def clean_text_field(self, value):
        """텍스트 필드 정리 - 소숫점 제거"""
        try:
            if pd.isna(value) or value == '':
                return ''
            
            # 숫자형 데이터인 경우 정수로 변환
            if isinstance(value, (int, float)):
                if pd.isna(value):
                    return ''
                # 정수로 변환
                return str(int(value))
            
            # 문자열인 경우
            str_value = str(value).strip()
            
            # 빈 문자열이면 그대로 반환
            if not str_value:
                return ''
            
            # 숫자로만 구성되어 있고 소숫점이 있는 경우
            try:
                # 숫자로 변환 가능한지 확인
                float_val = float(str_value)
                # 정수로 변환
                return str(int(float_val))
            except (ValueError, TypeError):
                # 숫자가 아니면 그대로 반환
                return str_value
                
        except Exception:
            return str(value) if value is not None else ''

    def clean_amount(self, amount):
        """금액에서 쉼표, 소숫점, 공백 제거하고 정수로 변환"""
        try:
            if isinstance(amount, (int, float)):
                # 숫자형이면 정수로 변환
                return str(int(amount))
            elif isinstance(amount, str):
                # 문자열이면 모든 특수문자 제거 후 정수 변환
                cleaned = amount.replace(',', '').replace(' ', '').replace('.0', '').replace('.00', '')
                # 소숫점이 있으면 소숫점 이하 제거
                if '.' in cleaned:
                    cleaned = cleaned.split('.')[0]
                # 빈 문자열이면 0 반환
                if not cleaned:
                    return "0"
                return str(int(float(cleaned)))
            else:
                return "0"
        except (ValueError, TypeError):
            return "0"
    
    def parse_date(self, date_str):
        """날짜 문자열 파싱"""
        try:
            # 다양한 날짜 형식 지원
            formats = ["%Y%m%d", "%Y-%m-%d", "%Y.%m.%d", "%m/%d/%Y"]
            for fmt in formats:
                try:
                    return datetime.strptime(str(date_str), fmt)
                except:
                    continue
            raise ValueError("지원하지 않는 날짜 형식")
        except:
            return datetime.now()
