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
        from config import AccountConfig
        
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
