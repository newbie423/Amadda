import asyncio

from firebase_admin import auth
import httpx

from utils import get_or_initialize_firebase_app

class FirebaseSignUpAndLogin:
    def __init__(self,
                 firebase_service_account_key_json: str,
                 firebase_app_api_key: str):
        self.__firebase_service_account_key_json = firebase_service_account_key_json
        self.__firebase_app_api_key = firebase_app_api_key

        # Firebase Admin SDK 초기화 자체는 동기 API
        self.__firebase_app = get_or_initialize_firebase_app(self.__firebase_service_account_key_json)

    async def signup(self, email: str, password: str) -> str:
        """
        Firebase Authentication 회원가입

        Returns:
            str: 생성된 Firebase UID
        """

        # Firebase Admin SDK의 auth.create_user()는
        # 현재 비동기 API를 제공하지 않으므로 별도 스레드에서 실행
        try:
            user = await asyncio.to_thread(
                auth.create_user,
                email=email,
                password=password,
                app=self.__firebase_app
            )
        except:
            raise ValueError("already exist user email")

        return user.uid

    async def login(self, email: str, password: str) -> str | None:
        """
        Firebase Authentication 로그인

        Returns:
            str | None: 로그인 성공 시 Firebase UID
        """

        url = (
            "https://identitytoolkit.googleapis.com/v1/"
            f"accounts:signInWithPassword"
            f"?key={self.__firebase_app_api_key}"
        )

        data = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=data
            )

        if response.status_code != 200:
            raise ValueError("id not found or invalid password")

        result = response.json()

        return result["localId"]

    async def delete(self, uid: str):
        """
        Firebase Authentication 사용자 삭제
        """

        # auth.delete_user() 역시 동기 API이므로
        # 별도 스레드에서 실행
        try:
            await asyncio.to_thread(
                auth.delete_user,
                uid,
                app=self.__firebase_app
            )
        except:
            raise ValueError("uid is not exist")

# Test Code

async def Test_signup():
    fsl = FirebaseSignUpAndLogin(firebase_service_account_key_json="amadda-68958-firebase-adminsdk-fbsvc-95a163b81f.json",
                                 firebase_app_api_key="AIzaSyArEx7ET5pbc5645xKKaCz6MNAuvVxHjGs")
    print("first signup :", await fsl.signup("a@example.com", "123456"))
    print("second signup :", await fsl.signup("a@example.com", "123456"))

async def Test_login():
    fsl = FirebaseSignUpAndLogin(firebase_service_account_key_json="amadda-68958-firebase-adminsdk-fbsvc-95a163b81f.json",
                                 firebase_app_api_key="AIzaSyArEx7ET5pbc5645xKKaCz6MNAuvVxHjGs")
    print("login with correct password :", await fsl.login("a@example.com", "123456"))
    print("login with incorrect password :"); await fsl.login("a@example.com", "12345")

async def Test_delete():
    fsl = FirebaseSignUpAndLogin(firebase_service_account_key_json="amadda-68958-firebase-adminsdk-fbsvc-95a163b81f.json",
                                     firebase_app_api_key="AIzaSyArEx7ET5pbc5645xKKaCz6MNAuvVxHjGs")

    uid = await fsl.login("a@example.com", "123456")
    print("exist uid delete :"); await fsl.delete(uid)
    print("not exist uid delete :"); await fsl.delete("awlkjdaslfkjalskdjlfkalksdf") # 존재하지 않는 uid 삭제

if(__name__ == "__main__"):
    asyncio.run(Test_signup())

