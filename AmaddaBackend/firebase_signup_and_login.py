from typing import Any

import httpx
from firebase_admin import auth

from utils import get_or_initialize_firebase_app

class FirebaseSignUpAndLogin:
    def __init__(self, firebase_service_account_key_json: str, firebase_app_api_key: str,):
        self.__firebase_service_account_key_json = firebase_service_account_key_json
        self.__firebase_app_api_key = firebase_app_api_key

        # Firebase Admin SDK 초기화
        self.__firebase_app = get_or_initialize_firebase_app(self.__firebase_service_account_key_json)

    # 회원가입 기능
    def signup(self, email: str, password: str) -> dict[str, Any]:
        """
        email과 password를 사용하여 회원가입을 수행합니다.

        Returns:
            {
                "user_id": 사용자 UID,
                "id_token": 사용자의 ID Token
            }

        회원가입에 실패하면:
            ValueError("email이 중복됩니다")
        """

        # 1. Firebase Auth에 사용자 생성
        try:
            user = auth.create_user(
                email=email,
                password=password,
                app=self.__firebase_app
            )
        except Exception:
            raise ValueError("email이 중복됩니다")

        # 2. 방금 생성한 계정으로 로그인하여 ID Token 획득
        url = (
            "https://identitytoolkit.googleapis.com/v1/"
            "accounts:signInWithPassword"
            f"?key={self.__firebase_app_api_key}"
        )

        data = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        try:
            response = httpx.post(
                url,
                json=data
            )

            if response.status_code != 200:
                # 계정은 생성되었지만 ID Token 발급에 실패한 경우
                raise ValueError("회원가입 후 ID Token 발급에 실패했습니다")

            result = response.json()

        except ValueError:
            raise
        except Exception:
            raise ValueError("회원가입 후 ID Token 발급에 실패했습니다")

        return {
            "user_id": user.uid,
            "id_token":result["idToken"],
            "user_email_verified": user.email_verified
        }

    # 로그인 기능
    def login(self, email:str, password:str) -> dict[str, Any]:
        """
        email과 password를 사용하여 로그인합니다.

        Returns:
            {
                "user_id": 사용자 UID,
                "user_email_verified": 이메일 인증 여부
            }

        로그인에 실패하면:
            ValueError("email not exist or password invalid")
        """

        url = (
            "https://identitytoolkit.googleapis.com/v1/"
            "accounts:signInWithPassword"
            f"?key={self.__firebase_app_api_key}"
        )

        data = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        try:
            response = httpx.post(
                url,
                json=data
            )

            if response.status_code != 200:
                raise ValueError(
                    "email not exist or password invalid"
                )

            result = response.json()

            # Firebase UID
            uid = result["localId"]

            # Admin SDK를 통해 이메일 인증 여부 확인
            user = auth.get_user(
                uid,
                app=self.__firebase_app
            )

            return {
                "user_id": uid,
                "id_token":result["idToken"],
                "user_email_verified": user.email_verified
            }

        except ValueError:
            raise
        except Exception:
            raise ValueError(
                "email not exist or password invalid"
            )

    # 이메일 인증 메시지 발송 기능
    def send_email_verification(self, id_token: str) -> None:
        """
        ID Token을 사용하여 Firebase가 사용자에게
        이메일 인증 메시지를 발송합니다.
        """

        url = (
            "https://identitytoolkit.googleapis.com/v1/"
            "accounts:sendOobCode"
            f"?key={self.__firebase_app_api_key}"
        )

        data = {
            "requestType": "VERIFY_EMAIL",
            "idToken": id_token
        }

        try:
            response = httpx.post(
                url,
                json=data
            )

            if response.status_code != 200:
                raise ValueError("이메일 인증 메시지 발송에 실패했습니다")

        except ValueError:
            raise
        except Exception:
            raise ValueError("이메일 인증 메시지 발송에 실패했습니다")

    # 회원탈퇴 기능
    def delete(self, uid: str) -> None:
        """
        uid에 해당되는 Firebase 사용자 계정을 삭제합니다.
        """

        try:
            auth.delete_user(
                uid,
                app=self.__firebase_app
            )

        except Exception:
            raise ValueError("사용자 계정을 삭제하지 못했습니다")

# Test Code

def get_test_email():
    return "jjhqp1110@gmail.com"

def get_amadda_element_manager():
    return AmaddaElementManager(FirebaseChacher(Firebase("AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json")))
def get_firebase_signup_and_login():
    return FirebaseSignUpAndLogin("AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json",
                                  "AIzaSyAf8UkeGCgVOHm_GluOUewYv7ROPBWH5Ds",
                                  get_amadda_element_manager())

def Test_signup():
    fsal = get_firebase_signup_and_login()

    signup_data = fsal.signup(get_test_email(), "123456")
    print("회원가입 성공 :", signup_data)

def Test_login():
    fsal = get_firebase_signup_and_login()

    try:
        login_data = fsal.login(get_test_email(), "123456")
        print("로그인 성공 :", login_data)
    except:
        print("로그인 실패")

def Test_login_invalid_password():
    fsal = get_firebase_signup_and_login()
    
    try:
        login_data = fsal.login(get_test_email(), "12345")
    except:
        print("로그인 실패(비밀 번호 잘못됨)")

def Test_send_email_verification():
    fsal = get_firebase_signup_and_login()

    login_data = fsal.login("jjhqp1110@gmail.com", "123456")
    fsal.send_email_verification(login_data["id_token"])
    print("이메일 인증 메시지 전송 성공")

def Test_delete():
    fsal = get_firebase_signup_and_login()

    try:
        user_info = fsal.login("jjhqp1110@gmail.com", "123456")
        fsal.delete(user_info["user_id"])
        print("회원 탈퇴 성공")
    except:
        print("회원 탈퇴 실패")

def Test_signup_and_send_email_verification():
    fsal = get_firebase_signup_and_login()

    signup_data = fsal.signup(get_test_email(), "123456")
    id_token = signup_data["id_token"]
    signup_data["id_token"] = signup_data["id_token"][0:10] + "..."
    print("회원가입 성공 :", signup_data)
    fsal.send_email_verification(id_token)
    print("이메일 인증 메시지 발송 성공")

if(__name__ == "__main__"):
    pass



