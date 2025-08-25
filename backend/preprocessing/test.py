import os, json, firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, storage

# 1) .env 로드 + 서비스계정 JSON 읽기 (요청하신 라인 그대로)
load_dotenv()
cred_dict = json.loads(os.environ["FIREBASE_PRIVATE_KEY"])

# 2) 정확한 버킷명 지정 (환경변수 STORAGE_BUCKET이 있으면 우선 사용)
BUCKET_NAME = os.getenv("STORAGE_BUCKET", "services-e42af.firebasestorage.app")

# 3) Admin SDK 초기화
if not firebase_admin._apps:
    firebase_admin.initialize_app(
        credentials.Certificate(cred_dict),
        {"storageBucket": BUCKET_NAME}
    )

# 4) 버킷에서 파일명만 나열 (접두사 지정 가능: 예 'templates/')
prefix = os.getenv("LIST_PREFIX", "")  # 예: LIST_PREFIX=templates/
bucket = storage.bucket()
print("bucket:", bucket.name)

for blob in bucket.list_blobs(prefix=prefix):
    if not blob.name.endswith("/"):  # 폴더 형태 객체 제외
        print(blob.name)