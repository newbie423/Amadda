from typing import Any

from client_return_format import ClientReturnFormat
from firebase_signup_and_login import FirebaseSignUpAndLogin
from my_firebase import Firebase
from firebase_chacher import FirebaseChacher
from amadda_element_manager import AmaddaElementManager

from datetime import datetime, timedelta

class Timer:
    def __init__(self):
        # Timer 생성 시점의 현재 시간을 저장
        self.__time = datetime.now()

    def check_elapsed(self, shift_second: float, now_time: datetime) -> bool:
        """
        Timer 생성 시점 + shift_second가
        now_time을 넘어섰는지 확인합니다.

        Returns:
            True  : 기준 시간이 now_time보다 이전이거나 같음
            False : 아직 기준 시간이 지나지 않음
        """

        target_time = self.__time + timedelta(seconds=shift_second)

        return target_time <= now_time

class AmaddaUserAccountController:
    def __init__(self,
                 firebase_signup_and_login:FirebaseSignUpAndLogin,
                 amadda_elem_manager:AmaddaElemManager):
        self.__firebase_signup_and_login:FirebaseSignUpAndLogin = firebase_signup_and_login
        self.__amadda_elem_manager:AmaddaElemManager = amadda_elem_manager

        self.__pending_email_valids:dict[str, str] = {}
        self.__email_valid_limit_minute = 5

    # 회원가입 메소드
    async def user_signup(self, email:str, password:str, password_check:str)->str:
        # - password와 password_check가 다를 경우 에러 반환(비밀번호 미일치 에러)
        # - password의 조합이 허용되지 않는 조합일경우 에러 반환(비밀번호 조합 에러)
        # 회원가입 시도
        # - 실패시 에러 반환(이메일 중복 에러)
        # 성공했다는 뜻이기에 이메일 인증 메시지 전송후 성공 반환(회원가입 및 인증 메시지 전송 성공)
        pass

    # 로그인 메소드
    async def user_login(self, email:str, password:str)->dict[str, Any]|str:
        # 로그인 시도
        # - 실패시 에러 반환(아이디 미존재 또는 비밀번호 미일치 에러)
        # 성공했다는 뜻이기에 이메일 인증 여부 확인
        # - 이메일 인증이 되지 않은 경우 에러 반환(이메일 미인증 에러)
        # 이메일 인증이 되었다는 뜻이기에 사용자의 로그인 성공 반환(로그인 성공) # 로그인 정보 포함
        pass

    # 이메일 인증 메시지 재전송 메소드
    async def resend_email_verification(self, id_token:str):
        try:
            self.__firebase_signup_and_login.send_email_verification(id_token)
            return ClientReturnFormat.Success("인증 메시지 전송 성공")
        except:
            return ClientReturnFormat.Error("인증 메시지 전송 실패")

    # 로그아웃 메소드
    async def user_logout(self, user_id:str):
        # user_id에 해당되는 모든 캐싱된 데이터 삭제
        pass
        
    # 회원탈퇴 메소드
    async def user_delete(self, user_id:str):
        # user_id에 해당되는 모든 캐싱된 데이터 삭제
        # user_id에 해당되는 모든 firebase속 문서들 삭제
        pass
        
    # 인증이 되지 않은 사용자 이메일에 대해, 전달된 시간을 초과한 미인증 이메일에 대한 uid삭제
    @staticmethod
    async def DeleteUnvaliEmailUid(elapsed_second:int=5*60):
        pass

# Test code

import asyncio

def get_AmaddaUserAccountController():
    firebase_signup_and_login = FirebaseSignUpAndLogin("AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json",
                           "AIzaSyAf8UkeGCgVOHm_GluOUewYv7ROPBWH5Ds")
    firebase_chacher = FirebaseChacher(firebase=Firebase("AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json"))
    
    return AmaddaUserAccountController(firebase_signup_and_login=firebase_signup_and_login,
                                       firebase_chacher=firebase_chacher)

def Test_signup():
    pass

if(__name__ == "__main__"):
    pass


