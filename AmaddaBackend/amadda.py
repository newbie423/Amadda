from firebase_signup_and_login import FirebaseSignUpAndLogin
from firebase_chacher import FirebaseChacher
from firebase import Firebase

class Amadda:
    def __init__(self,
                 firebase_singup_and_login:FirebaseSignUpAndLogin,
                 firebase_chacher:FirebaseChacher):
        
        self.__firebase_singup_and_login:FirebaseSignUpAndLogin = firebase_singup_and_login
        self.__firebase_chacher:FirebaseChacher = firebase_chacher

        #<<프론트엔드에서 실제로 사용가능한 모든 기능 종류및 동작 정의하기>>

    async def test_print(self):
        print("test")

# ===== TEST CODE

import asyncio
def get_amadda():
    firebase_service_account_key_json = "AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json"
    firebase_app_api_key = "AIzaSyAf8UkeGCgVOHm_GluOUewYv7ROPBWH5Ds"

    # firebase와의 직접적인 통신을 수행하는 객체
    firebase = Firebase(firebase_service_account_key_json=firebase_service_account_key_json)
    # firebase를 사용하여 문서와 python내부 캐싱데이터간 동기화를 수행하는 객체
    firebase_chacher = FirebaseChacher(firebase=firebase)
    # firebase의 auth기능을 사용하여 회원가입, 로그인, 삭제를 수행하는 객체
    firebase_signup_and_login = FirebaseSignUpAndLogin(firebase_service_account_key_json=firebase_service_account_key_json,
                                                       firebase_app_api_key=firebase_app_api_key)

    # llm wiki?등을 사용하여 사용자로 부터 강의자료를 업로드 받고
    # 이를 토대로 질문, 문제 생성을 수행하는 객체?(프로토타입으로 제작후 실제 사용할 객체들은 세분화 하기)
    
    # 전달 받은 문제(문제 질문, 정답 포함)와, 사용자의 풀이 정보를 토대로 채점을 한뒤 해설을 수행하는 객체
    # 내부적으로 llm은 선택적으로 사용(선다형, ox형의 경우 맞으면 해설 패스, 서술형의 경우는 llm 사용필요
    # (프로토타입 제작한것 정리한뒤 래핑구조 설계필요)

    
    amadda = Amadda(
        firebase_singup_and_login=firebase_signup_and_login,
        firebase_chacher=firebase_chacher
    )

    return amadda

async def Test():
    amadda = get_amadda()

    await amadda.test_print()

if(__name__ == "__main__"):
    asyncio.run(Test())