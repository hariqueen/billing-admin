import os
import json
from dotenv import load_dotenv
load_dotenv()
import firebase_admin
from firebase_admin import credentials, firestore

class DatabaseManager:
    """Firebase 데이터베이스 관리"""
    
    def __init__(self):
        self.db = self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Firebase 초기화"""
        if not firebase_admin._apps:
            # 환경변수에서 전체 JSON 문자열 가져오기
            firebase_json = os.getenv("FIREBASE_PRIVATE_KEY", "")
            if not firebase_json:
                raise ValueError("환경변수가 비어 있습니다.")
            
            # JSON 문자열 → 딕셔너리로 파싱
            cred_dict = json.loads(firebase_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        
        return firestore.client()
    
    def get_accounts_by_type(self, account_type):
        """타입별 계정 조회"""
        from backend.data_collection.config import AccountConfig
        
        if account_type == "sms":
            companies = list(AccountConfig.SMS_CONFIG.keys())
            config_map = AccountConfig.SMS_CONFIG
        else:  # call
            companies = list(AccountConfig.CALL_CONFIG.keys())
            config_map = AccountConfig.CALL_CONFIG
        
        accounts = []
        for company in companies:
            docs = self.db.collection("accounts") \
                .where("company_name", "==", company) \
                .where("account_type", "==", account_type) \
                .get()
            if docs:
                account = docs[0].to_dict()
                if account is not None:
                    account['config'] = config_map.get(company)
                    accounts.append(account)
                    print(f"  {company} {account_type.upper()} 계정 로드")
                else:
                    print(f"  {company} {account_type.upper()} 계정 데이터가 없습니다.")
        
        return accounts
    
    def get_all_accounts(self):
        """모든 계정 정보 조회"""
        try:
            print("🔍 Firebase에서 모든 계정 조회 시작...")
            docs = self.db.collection("accounts").get()
            accounts = []
            print(f"📊 Firebase에서 {len(docs)}개의 문서를 찾았습니다.")
            
            for doc in docs:
                account = doc.to_dict()
                account['id'] = doc.id
                print(f"📋 계정 데이터: {account}")
                accounts.append(account)
            
            print(f"✅ 총 {len(accounts)}개의 계정을 로드했습니다.")
            return accounts
        except Exception as e:
            print(f"❌ 모든 계정 조회 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def add_account_legacy(self, company_name, account_type, url, username, password, notes="", status="active"):
        """새 계정 추가 (레거시 메서드)"""
        try:
            account_data = {
                'company_name': company_name,
                'account_type': account_type,
                'site_url': url,
                'username': username,
                'password': password,
                'notes': notes,
                'status': status,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref = self.db.collection("accounts").add(account_data)
            print(f"✅ 계정 추가 완료: {company_name} ({account_type})")
            return doc_ref[1].id
        except Exception as e:
            print(f"❌ 계정 추가 오류: {e}")
            raise e
    
    def update_account_legacy(self, account_id, company_name, account_type, url, username, password, notes="", status="active"):
        """계정 정보 수정 (레거시 메서드)"""
        try:
            account_data = {
                'company_name': company_name,
                'account_type': account_type,
                'site_url': url,
                'username': username,
                'password': password,
                'notes': notes,
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            self.db.collection("accounts").document(account_id).update(account_data)
            print(f"✅ 계정 수정 완료: {company_name} ({account_type})")
        except Exception as e:
            print(f"❌ 계정 수정 오류: {e}")
            raise e
    
    def delete_account(self, account_id):
        """계정 삭제"""
        try:
            self.db.collection("accounts").document(account_id).delete()
            print(f"✅ 계정 삭제 완료: {account_id}")
        except Exception as e:
            print(f"❌ 계정 삭제 오류: {e}")
            raise e
    
    def get_account_by_id(self, account_id):
        """ID로 특정 계정 조회"""
        try:
            doc = self.db.collection("accounts").document(account_id).get()
            if doc.exists:
                account = doc.to_dict()
                account['id'] = doc.id
                return account
            else:
                return None
        except Exception as e:
            print(f"❌ 계정 조회 오류: {e}")
            return None
    
    def add_account(self, account_data):
        """새 계정 추가 (JSON 데이터로)"""
        try:
            company_name = account_data.get('company_name')
            account_type = account_data.get('account_type')
            
            # ID를 {이름}_{계정타입} 형식으로 생성
            custom_id = f"{company_name}_{account_type}"
            
            account_data['created_at'] = firestore.SERVER_TIMESTAMP
            
            # 수동으로 ID를 지정하여 문서 생성
            doc_ref = self.db.collection("accounts").document(custom_id)
            doc_ref.set(account_data)
            
            print(f"✅ 계정 추가 완료: {company_name} ({account_type}) - ID: {custom_id}")
            return custom_id
        except Exception as e:
            print(f"❌ 계정 추가 오류: {e}")
            raise e
    
    def update_account(self, account_id, account_data):
        """계정 정보 수정 (JSON 데이터로)"""
        try:
            account_data['updated_at'] = firestore.SERVER_TIMESTAMP
            self.db.collection("accounts").document(account_id).update(account_data)
            print(f"✅ 계정 수정 완료: {account_data.get('company_name')} ({account_data.get('account_type')})")
        except Exception as e:
            print(f"❌ 계정 수정 오류: {e}")
            raise e
