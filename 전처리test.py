import openpyxl
from pathlib import Path

def modify_excel_invoice(file_path, output_file_name="테스트 결과.xlsx"):
    """
    기존 엑셀 파일의 구조를 유지하면서 특정 셀의 값만 변경
    
    Args:
        file_path (str): 원본 엑셀 파일 경로
        output_file_name (str): 저장할 파일명
    """
    try:
        # 원본 엑셀 파일 열기
        workbook = openpyxl.load_workbook(file_path)
        
        # 첫 번째 시트 선택 (시트명을 모르므로 인덱스로 접근)
        first_sheet = workbook.worksheets[0]
        
        print(f"첫 번째 시트명: {first_sheet.title}")
        print("기존 값 확인:")
        print(f"D24: {first_sheet['D24'].value}")
        print(f"E24: {first_sheet['E24'].value}")
        print(f"F25: {first_sheet['F25'].value}")
        
        # 특정 셀에 값 입력
        first_sheet['D24'] = 600000
        first_sheet['E24'] = 600000
        first_sheet['F25'] = 600000
        
        print("\n값 변경 완료:")
        print(f"D24: {first_sheet['D24'].value}")
        print(f"E24: {first_sheet['E24'].value}")
        print(f"F25: {first_sheet['F25'].value}")
        
        # 모든 시트 정보 출력
        print(f"\n전체 시트 개수: {len(workbook.worksheets)}")
        for i, sheet in enumerate(workbook.worksheets, 1):
            print(f"시트 {i}: {sheet.title}")
        
        # 파일 저장 (모든 시트 포함)
        workbook.save(output_file_name)
        print(f"\n파일이 '{output_file_name}'로 저장되었습니다.")
        
        # 파일 닫기
        workbook.close()
        
        return True
        
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return False
    except Exception as e:
        print(f"오류가 발생했습니다: {str(e)}")
        return False

# 사용 예시
if __name__ == "__main__":
    # 파일 경로 설정
    input_file = "2507_앤하우스_상담시스템 수수료 청구내역서_창업.xlsx"
    
    # 파일 존재 확인
    if Path(input_file).exists():
        print(f"'{input_file}' 파일을 처리합니다...")
        modify_excel_invoice(input_file)
    else:
        print(f"'{input_file}' 파일이 현재 디렉토리에 없습니다.")
        print("파일 경로를 확인해주세요.")

# 추가: 여러 파일을 일괄 처리하는 함수
def batch_modify_invoices(file_list, values_dict):
    """
    여러 청구서 파일을 일괄로 처리
    
    Args:
        file_list (list): 처리할 파일 경로 리스트
        values_dict (dict): 셀 위치와 값의 딕셔너리 예: {'D24': 600000, 'E24': 600000}
    """
    for file_path in file_list:
        try:
            workbook = openpyxl.load_workbook(file_path)
            first_sheet = workbook.worksheets[0]
            
            # 딕셔너리의 모든 셀에 값 적용
            for cell_address, value in values_dict.items():
                first_sheet[cell_address] = value
            
            # 파일명 생성 (원본 파일명_수정 형태)
            original_name = Path(file_path).stem
            output_name = f"{original_name}_수정.xlsx"
            
            workbook.save(output_name)
            workbook.close()
            print(f"처리 완료: {output_name}")
            
        except Exception as e:
            print(f"'{file_path}' 처리 중 오류: {str(e)}")

# 사용 예시 2: 일괄 처리
# files = ["파일1.xlsx", "파일2.xlsx", "파일3.xlsx"]
# values = {'D24': 600000, 'E24': 600000, 'F25': 600000}
# batch_modify_invoices(files, values)