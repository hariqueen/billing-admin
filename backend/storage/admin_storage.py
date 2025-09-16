import os
import json
from datetime import datetime

class AdminStorage:
    """통합 어드민 데이터 저장소 (메모리 캐시 없음 - 항상 파일에서 읽기)"""
    
    def __init__(self, storage_file="admin_storage.json"):
        self.storage_file = storage_file
        # 메모리 캐시 제거 - 항상 파일에서 직접 읽어옴
        self.ensure_file_exists()
    
    def ensure_file_exists(self):
        """저장소 파일이 존재하지 않으면 기본 구조로 생성"""
        if not os.path.exists(self.storage_file):
            default_data = {
                "bill_amounts": {},
                "processed_files": {}
            }
            self.save_data_direct(default_data)
            print(f"기본 저장소 파일 생성: {self.storage_file}")
    
    def load_data(self):
        """저장된 데이터 로드 (메모리 캐시 없음)"""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"어드민 데이터 로드 실패: {e}")
            return {
                "bill_amounts": {},
                "processed_files": {}
            }
    
    def save_data_direct(self, data):
        """데이터를 직접 JSON 파일에 저장"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"어드민 데이터 저장 완료")
        except Exception as e:
            print(f"어드민 데이터 저장 실패: {e}")
    
    # === 고지서 금액 관련 메서드 ===
    
    def get_bill_amounts(self):
        """고지서 금액 정보 조회 (항상 파일에서 읽기)"""
        data = self.load_data()
        return data.get("bill_amounts", {})
    
    def update_bill_amount(self, company_name, amount, update_date):
        """고지서 금액 정보 업데이트 (파일에서 읽고 저장)"""
        data = self.load_data()
        if "bill_amounts" not in data:
            data["bill_amounts"] = {}
        
        data["bill_amounts"][company_name] = {
            "amount": amount,
            "update_date": update_date
        }
        self.save_data_direct(data)
        print(f"{company_name} 고지서 금액 업데이트: {amount}")
    
    def batch_update_bill_amounts(self, bill_data):
        """고지서 금액 일괄 업데이트 (파일에서 읽고 저장)"""
        data = self.load_data()
        if "bill_amounts" not in data:
            data["bill_amounts"] = {}
        
        data["bill_amounts"].update(bill_data)
        self.save_data_direct(data)
        print(f"고지서 금액 일괄 업데이트: {len(bill_data)}개 고객사")
    
    # === 청구서 결과 관련 메서드 ===
    
    def get_processed_files(self):
        """청구서 처리 결과 조회 (항상 파일에서 읽기)"""
        data = self.load_data()
        return data.get("processed_files", {})
    
    def save_processed_files(self, company_name, processed_files):
        """청구서 처리 결과 저장 (파일에서 읽고 저장)"""
        data = self.load_data()
        if "processed_files" not in data:
            data["processed_files"] = {}
        
        data["processed_files"][company_name] = {
            "processed_files": processed_files,
            "timestamp": datetime.now().isoformat()
        }
        self.save_data_direct(data)
        print(f"{company_name} 청구서 결과 저장: {len(processed_files)}개 파일")
    
    def clear_processed_files(self, company_name):
        """특정 회사의 청구서 결과 초기화 (파일에서 읽고 저장)"""
        data = self.load_data()
        if "processed_files" in data and company_name in data["processed_files"]:
            del data["processed_files"][company_name]
            self.save_data_direct(data)
            print(f"{company_name} 청구서 결과 초기화")
    
    # === 마이그레이션 메서드 ===
    
    def migrate_from_separate_files(self):
        """기존 분리된 파일들에서 데이터 마이그레이션 (한 번만 실행)"""
        try:
            # 이미 마이그레이션이 완료된 경우 스킵
            bill_file = "bill_amounts_storage.json"
            processed_file = "processed_files_storage.json"
            
            # 기존 파일이 없으면 마이그레이션 불필요
            if not os.path.exists(bill_file) and not os.path.exists(processed_file):
                return True
            
            print("🔄 기존 파일들 마이그레이션 시작...")
            migrated_data = False
            
            # 현재 데이터 로드
            current_data = self.load_data()
            
            # 1. bill_amounts_storage.json에서 마이그레이션
            if os.path.exists(bill_file):
                with open(bill_file, 'r', encoding='utf-8') as f:
                    bill_data = json.load(f)
                    # 기존 데이터와 병합 (덮어쓰지 않고 병합)
                    if "bill_amounts" not in current_data:
                        current_data["bill_amounts"] = {}
                    current_data["bill_amounts"].update(bill_data)
                    print(f"고지서 데이터 마이그레이션: {len(bill_data)}개 고객사")
                    migrated_data = True
            
            # 2. processed_files_storage.json에서 마이그레이션
            if os.path.exists(processed_file):
                with open(processed_file, 'r', encoding='utf-8') as f:
                    processed_data = json.load(f)
                    # 기존 데이터와 병합
                    if "processed_files" not in current_data:
                        current_data["processed_files"] = {}
                    current_data["processed_files"].update(processed_data)
                    print(f"청구서 결과 데이터 마이그레이션: {len(processed_data)}개 고객사")
                    migrated_data = True
            
            # 데이터가 마이그레이션된 경우만 저장
            if migrated_data:
                self.save_data_direct(current_data)
                
                # 기존 파일들 백업 후 삭제
                import shutil
                if os.path.exists(bill_file):
                    shutil.move(bill_file, f"{bill_file}.backup")
                    print(f"{bill_file} → {bill_file}.backup으로 백업")
                
                if os.path.exists(processed_file):
                    shutil.move(processed_file, f"{processed_file}.backup")
                    print(f"{processed_file} → {processed_file}.backup으로 백업")
                
                print("데이터 마이그레이션 완료!")
            
            return True
            
        except Exception as e:
            print(f"마이그레이션 실패: {e}")
            return False
