import firebase_admin
from firebase_admin import credentials

def get_or_initialize_firebase_app(
    firebase_service_account_key_json: str
):
    """
    Firebase Admin App이 이미 존재하면 가져오고,
    존재하지 않으면 새로 초기화한다.
    """

    try:
        # 이미 초기화된 default app 가져오기
        return firebase_admin.get_app()

    except ValueError:
        # 아직 초기화되지 않았다면 새로 초기화
        cred = credentials.Certificate(
            firebase_service_account_key_json
        )

        return firebase_admin.initialize_app(cred)




