import json
from pathlib import Path


def _load_local_firebase_secret():
    project_root = Path(__file__).resolve().parents[2]
    candidate_files = [
        project_root / "firebase-credentials.json",
        *project_root.glob("*-firebase-adminsdk-*.json"),
    ]

    for key_file in candidate_files:
        if key_file.exists() and key_file.is_file():
            with open(key_file, "r", encoding="utf-8") as f:
                print(f"로컬 Firebase 키 파일 사용: {key_file.name}")
                return json.load(f)
    return None


def get_firebase_secret():
    local_secret = _load_local_firebase_secret()
    if local_secret:
        return local_secret

    raise FileNotFoundError(
        "Firebase 키 파일을 찾을 수 없습니다. "
        "프로젝트 루트에 'firebase-credentials.json' 또는 "
        "'*-firebase-adminsdk-*.json' 파일을 배치해주세요."
    )
