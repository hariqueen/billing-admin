import boto3
import json
import os
from botocore.exceptions import ClientError


def get_firebase_secret():
    """AWS Secrets Manager에서 Firebase 키를 가져옵니다."""
    # 먼저 환경변수 확인
    if os.getenv("FIREBASE_PRIVATE_KEY"):
        print("환경변수에서 Firebase 키 사용")
        return json.loads(os.getenv("FIREBASE_PRIVATE_KEY"))
    
    # 환경변수가 없으면 AWS Secrets Manager 시도
    secret_name = "FIREBASE_PRIVATE_KEY"
    region_name = "ap-northeast-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']
    return json.loads(secret)
