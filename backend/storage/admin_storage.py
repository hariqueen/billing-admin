import os
import json
import time
import fcntl
from datetime import datetime

class AdminStorage:
    """통합 어드민 데이터 저장소 (메모리 캐시 없음 - 항상 파일에서 읽기)"""
    
    def __init__(self, storage_file="admin_storage.json"):
        # 기본 저장 위치를 temp_processing으로 고정해 Docker 볼륨에 영속 저장한다.
        if storage_file == "admin_storage.json":
            storage_dir = os.path.join(os.getcwd(), "temp_processing")
            os.makedirs(storage_dir, exist_ok=True)
            self.storage_file = os.path.join(storage_dir, storage_file)

            # 기존 루트 파일이 있으면 1회 마이그레이션
            legacy_file = os.path.join(os.getcwd(), "admin_storage.json")
            if os.path.exists(legacy_file) and not os.path.exists(self.storage_file):
                try:
                    with open(legacy_file, "r", encoding="utf-8") as src, open(self.storage_file, "w", encoding="utf-8") as dst:
                        dst.write(src.read())
                    print(f"기존 저장소 마이그레이션 완료: {legacy_file} -> {self.storage_file}")
                except Exception as migrate_error:
                    print(f"기존 저장소 마이그레이션 실패: {migrate_error}")
        else:
            self.storage_file = storage_file
        self.lock_file = f"{self.storage_file}.lock"
        # 메모리 캐시 제거 - 항상 파일에서 직접 읽어옴
        self.ensure_file_exists()
    
    def _acquire_lock(self, timeout=5):
        """파일 락 획득 (최대 timeout 초 대기)"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 락 파일 열기 (exclusive 모드)
                lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(lock_fd)
                return True
            except FileExistsError:
                # 락이 이미 있으면 잠시 대기
                time.sleep(0.1)
            except Exception as e:
                print(f"락 획득 실패: {e}")
                return False
        return False
    
    def _release_lock(self):
        """파일 락 해제"""
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except Exception as e:
            print(f"락 해제 실패: {e}")
    
    def ensure_file_exists(self):
        """저장소 파일이 존재하지 않으면 기본 구조로 생성, 존재하면 필수 섹션 추가"""
        if not os.path.exists(self.storage_file):
            default_data = {
                "bill_amounts": {},
                "processed_files": {},
                "uploaded_files": {},
                "collected_files": {},
                "wconcept_settings": {
                    "license_count": 40,
                    "license_cost": 80000,
                    "updated_at": None
                }
            }
            self.save_data_direct(default_data)
            print(f"기본 저장소 파일 생성: {self.storage_file}")
        else:
            # 기존 파일에 필수 섹션이 없으면 추가
            try:
                data = self.load_data()
                needs_update = False
                
                if "uploaded_files" not in data:
                    data["uploaded_files"] = {}
                    needs_update = True
                if "collected_files" not in data:
                    data["collected_files"] = {}
                    needs_update = True
                if "wconcept_settings" not in data:
                    data["wconcept_settings"] = {
                        "license_count": 40,
                        "license_cost": 80000,
                        "updated_at": None
                    }
                    needs_update = True
                if "sk_settings" not in data:
                    data["sk_settings"] = {
                        "license_cost": 80000,
                        "updated_at": None
                    }
                    needs_update = True
                
                if needs_update:
                    self.save_data_direct(data)
                    print(f"저장소 파일 구조 업데이트: {self.storage_file}")
            except Exception as e:
                print(f"저장소 파일 구조 확인 실패: {e}")
    
    def load_data(self):
        """저장된 데이터 로드 (메모리 캐시 없음, 락 사용)"""
        if not self._acquire_lock():
            print("락 획득 실패, 기본값 반환")
            return {
                "bill_amounts": {},
                "processed_files": {},
                "uploaded_files": {},
                "collected_files": {},
                "wconcept_settings": {
                    "license_count": 40,
                    "license_cost": 80000,
                    "updated_at": None
                }
            }
        
        try:
            # 파일이 비어있거나 손상된 경우 처리
            if not os.path.exists(self.storage_file) or os.path.getsize(self.storage_file) == 0:
                return {
                    "bill_amounts": {},
                    "processed_files": {},
                    "uploaded_files": {},
                    "collected_files": {},
                    "wconcept_settings": {
                        "license_count": 40,
                        "license_cost": 80000,
                        "updated_at": None
                    }
                }
            
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                # 파일 락 적용 (읽기 중 다른 프로세스가 쓰지 못하도록)
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock (읽기)
                    content = f.read()
                    if not content.strip():
                        return {
                            "bill_amounts": {},
                            "processed_files": {},
                            "uploaded_files": {},
                            "collected_files": {},
                            "wconcept_settings": {
                                "license_count": 40,
                                "license_cost": 80000,
                                "updated_at": None
                            }
                        }
                    return json.loads(content)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
        except json.JSONDecodeError as e:
            print(f"어드민 데이터 로드 실패 (JSON 파싱 오류): {e}")
            # 손상된 파일 백업
            try:
                backup_file = f"{self.storage_file}.backup_{int(time.time())}"
                if os.path.exists(self.storage_file):
                    os.rename(self.storage_file, backup_file)
                    print(f"손상된 파일 백업: {backup_file}")
            except:
                pass
            return {
                "bill_amounts": {},
                "processed_files": {},
                "uploaded_files": {},
                "collected_files": {},
                "wconcept_settings": {
                    "license_count": 40,
                    "license_cost": 80000,
                    "updated_at": None
                }
            }
        except Exception as e:
            print(f"어드민 데이터 로드 실패: {e}")
            return {
                "bill_amounts": {},
                "processed_files": {},
                "uploaded_files": {},
                "collected_files": {},
                "wconcept_settings": {
                    "license_count": 40,
                    "license_cost": 80000,
                    "updated_at": None
                }
            }
        finally:
            self._release_lock()
    
    def save_data_direct(self, data):
        """데이터를 직접 JSON 파일에 저장 (필수 섹션 보장, 락 사용)"""
        if not self._acquire_lock(timeout=10):
            print("락 획득 실패, 저장 취소")
            return False
        
        try:
            # 필수 섹션 보장 (기존 파일에 없을 수 있음)
            if "uploaded_files" not in data:
                data["uploaded_files"] = {}
            if "collected_files" not in data:
                data["collected_files"] = {}
            if "wconcept_settings" not in data:
                data["wconcept_settings"] = {
                    "license_count": 40,
                    "license_cost": 80000,
                    "updated_at": None
                }
            if "sk_settings" not in data:
                data["sk_settings"] = {
                    "license_cost": 80000,
                    "updated_at": None
                }
            
            # 임시 파일에 먼저 저장 (원자적 쓰기)
            temp_file = f"{self.storage_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock (쓰기)
                try:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # 디스크에 강제 쓰기
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # 원자적 이동 (rename은 원자적 연산)
            os.rename(temp_file, self.storage_file)
            print(f"어드민 데이터 저장 완료")
            return True
        except Exception as e:
            print(f"어드민 데이터 저장 실패: {e}")
            # 임시 파일 정리
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
            return False
        finally:
            self._release_lock()
    
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
    
    def clear_all(self):
        """모든 데이터 초기화 (bill_amounts와 processed_files 모두 비우기)"""
        default_data = {
            "bill_amounts": {},
            "processed_files": {},
            "uploaded_files": {},
            "collected_files": {},
            "wconcept_settings": {
                "license_count": 40,
                "license_cost": 80000,
                "updated_at": None
            },
            "sk_settings": {
                "license_cost": 80000,
                "updated_at": None
            }
        }
        self.save_data_direct(default_data)
        print("admin_storage.json 전체 초기화 완료")
    
    # === 업로드된 파일 관련 메서드 ===
    
    def get_uploaded_files(self):
        """업로드된 파일 목록 조회"""
        data = self.load_data()
        return data.get("uploaded_files", {})
    
    def save_uploaded_files(self, company_name, uploaded_files):
        """업로드된 파일 목록 저장"""
        data = self.load_data()
        if "uploaded_files" not in data:
            data["uploaded_files"] = {}
        data["uploaded_files"][company_name] = uploaded_files
        self.save_data_direct(data)
        print(f"{company_name} 업로드된 파일 목록 저장: {len(uploaded_files)}개")
    
    # === 수집된 파일 관련 메서드 ===
    
    def get_collected_files(self):
        """수집된 파일 목록 조회"""
        data = self.load_data()
        return data.get("collected_files", {})
    
    def save_collected_files(self, company_name, collected_files):
        """수집된 파일 목록 저장"""
        data = self.load_data()
        if "collected_files" not in data:
            data["collected_files"] = {}
        data["collected_files"][company_name] = collected_files
        self.save_data_direct(data)
        print(f"{company_name} 수집된 파일 목록 저장: {len(collected_files)}개")

    # === W컨셉 라이선스 설정 관련 메서드 ===

    def get_wconcept_settings(self):
        """W컨셉 실행 팝업 기본값 조회"""
        data = self.load_data()
        settings = data.get("wconcept_settings", {})
        return {
            "license_count": int(settings.get("license_count", 40) or 40),
            "license_cost": int(settings.get("license_cost", 80000) or 80000),
            "updated_at": settings.get("updated_at")
        }

    def save_wconcept_settings(self, license_count=None, license_cost=None):
        """W컨셉 실행 팝업 기본값 저장"""
        data = self.load_data()
        if "wconcept_settings" not in data:
            data["wconcept_settings"] = {}

        current = data["wconcept_settings"]
        if license_count is not None:
            current["license_count"] = int(license_count)
        if license_cost is not None:
            current["license_cost"] = int(license_cost)
        current["updated_at"] = datetime.now().isoformat()

        self.save_data_direct(data)
        print(
            f"W컨셉 설정 저장: license_count={current.get('license_count')}, "
            f"license_cost={current.get('license_cost')}"
        )

    def get_sk_settings(self):
        """SK일렉링크 실행 팝업 기본값 조회"""
        data = self.load_data()
        settings = data.get("sk_settings", {})
        return {
            "license_cost": int(settings.get("license_cost", 80000) or 80000),
            "updated_at": settings.get("updated_at")
        }

    def save_sk_settings(self, license_cost=None):
        """SK일렉링크 실행 팝업 기본값 저장"""
        data = self.load_data()
        if "sk_settings" not in data:
            data["sk_settings"] = {}

        current = data["sk_settings"]
        if license_cost is not None:
            current["license_cost"] = int(license_cost)
        current["updated_at"] = datetime.now().isoformat()

        self.save_data_direct(data)
        print(f"SK일렉링크 설정 저장: license_cost={current.get('license_cost')}")
    
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
