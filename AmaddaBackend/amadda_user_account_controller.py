from typing import Any

from firebase_signup_and_login import FirebaseSignUpAndLogin
from my_firebase import Firebase
from firebase_chacher import FirebaseChacher
from amadda_element_manager import AmaddaElementManager

from datetime import datetime, timedelta

import os
import pickle

class Timer:
    def __init__(self):
        # Timer 생성 시점의 현재 시간을 저장
        self.__time = datetime.now()

    def check_elapsed(self, elapsed_second: float, now_time: datetime) -> bool:
        """
        기준시간(Timer 생성 시점 + elapsed_second)가 now_time을 넘어섰는지 확인합니다.

        Returns:
            True  : 기준 시간이 now_time과 동일하거나, 넘어섬
            False : 기준 시간이 아직 now_time을 넘어서지 않음
        """

        target_time = self.__time + timedelta(seconds=elapsed_second)

        return target_time <= now_time

class AmaddaUserAccountController:
    def __init__(self,
                 firebase_signup_and_login:FirebaseSignUpAndLogin,
                 amadda_element_manager:AmaddaElementManager):
        self.__firebase_signup_and_login:FirebaseSignUpAndLogin = firebase_signup_and_login
        self.__amadda_element_manager:AmaddaElementManager = amadda_element_manager

        self.__pending_validate_emails:dict[str, dict[str, Any]] = {}
        '''{
        f"{email}" : {
                "time":f"{Timer 객체}
                "value":{회원가입 정보(uid, idtoken등)}
                "password":{회원가입시의 비밀번호}
            }
        }'''

        self.__FILE_PATH = "AmaddaBackend/pending_validate_emails.pkl"
        self.__read_pending_validate_emails()

    # pending_validate_emails를 파일에서 읽어오는 메소드
    def __read_pending_validate_emails(self):
        """AmaddaBackend/pending_validate_emails.pkl에 직렬화로 저장되어 있는 내용을 읽어서

        self.__pending_validate_emails에 저장함. 파일이 없어서 읽지 못해 에러가 나는 경우 그냥 아무것도 하지
        않고 pass
        """
        try:
            with open(self.__FILE_PATH, "rb") as file:
                self.__pending_validate_emails = pickle.load(file)
        except FileNotFoundError:
            pass

    # pending_validate_emails를 파일에 쓰는 메소드
    def __write_pending_validate_emails(self):
        """self.__pending_validate_emails에 있는 내용을 직렬화로

        AmaddaBackend/pending_validate_emails.pkl에 저장함
        """
        os.makedirs(os.path.dirname(self.__FILE_PATH), exist_ok=True)

        with open(self.__FILE_PATH, "wb") as file:
            pickle.dump(self.__pending_validate_emails, file)

    # 회원가입 메소드
    async def user_signup(self, email:str, password:str, password_check:str):
        # - password와 password_check가 다를 경우 에러 발생(비밀번호 미일치 에러)
        if(password != password_check):
            raise ValueError("회원가입에 실패하였습니다 : 비밀번호가 일치하지 않습니다")
        
        # - password의 조합이 허용되지 않는 조합일경우 에러 발생(비밀번호 조합 에러)
        
        signup_data = None
        
        # 회원가입 시도
        # - 실패시 에러 발생(이메일 중복 또는 id token 생성 실패)
        signup_data = self.__firebase_signup_and_login.signup(email, password)
        
        # 성공했다는 뜻이기에 이메일 인증을 위해 pending_email_valids에 email을 키로, {}를 값으로 한뒤, {}안에 "time"을 키로, Timer객체를 값으로, "value"를 키로, 회원가입 정보를 값으로 하여 저장
        self.__pending_validate_emails[email] = {
            "time":Timer(),
            "value":signup_data,
            "password":password
        }

        self.__write_pending_validate_emails()
        
        # 회원가입된 사용자 정보속 uid를 사용해 elem manager를 사용하여 새로운 user를 생성한다
        await self.__amadda_element_manager.create_user(signup_data["user_id"])
        
        # 이메일 인증 메시지 전송후 성공 발생
        self.__firebase_signup_and_login.send_email_verification(signup_data["id_token"])

    # 로그인 메소드
    def user_login(self, email:str, password:str)->str:
        # 로그인 시도
        # - 실패시 에러 발생(아이디 미존재 또는 비밀번호 미일치 에러)
        login_data = None
        try:
            login_data = self.__firebase_signup_and_login.login(email, password)
        except:
            raise ValueError("아이디 미존재 또는 비밀번호 미일치")
        
        # 성공했다는 뜻이기에 이메일 인증 여부 확인
        # - 이메일 인증이 되지 않은 경우 에러 발생(이메일 미인증 에러)
        if(login_data["user_email_verified"] == False):
            raise ValueError("이메일이 미인증 상태입니다")
        
        # 이메일 인증이 되어 있는 경우이기에 pending_email_valids에 현재 이메일이 있다면 pop하기
        if(email in self.__pending_validate_emails):
            self.__pending_validate_emails.pop(email)
            self.__write_pending_validate_emails()
        
        #  사용자의 로그인 성공 반환(로그인 성공 + 사용자 아이디)
        return login_data["user_id"]

    # 이메일 인증 메시지 재전송 메소드
    def resend_email_verification(self, email:str):
        # - pending_email_valids에 현재 email이 key로 존재하지 않다면 에러 발생(이메일 인증 만료 에러) # 회원가입 부터 다시 수행 해야함
        if(email not in self.__pending_validate_emails):
            raise ValueError("이메일 인증 만료, 로그인이 되지 않는다면, 회원가입 부터 다시 수행해야 합니다")
        
        # pending_email_valids에 현재 email이 있다는 뜻이기에 현재 email에 해당되는 값의 id_token으로 이메일 전송
        id_token = self.__pending_validate_emails[email]["value"]["id_token"]
        
        try:
            self.__firebase_signup_and_login.send_email_verification(id_token)
        except:
            raise ValueError("인증 메시지 전송 실패, 요청이 너무 잦습니다, 마지막 인증 메시지 발송으로 부터 60초 후에 다시 시도해 주세요")

    # 로그아웃 메소드
    async def user_logout(self, user_id:str):
        # user_id에 해당되는 모든 캐싱된 데이터 삭제
        await self.__amadda_element_manager.delete_user_all_chache_data(user_id)
        
    # 회원탈퇴 메소드
    async def user_delete(self, user_id:str):
        # user_id에 해당되는 모든 캐싱 및 firebase 데이터 삭제
        await self.__amadda_element_manager.delete_user(user_id)
        
    # 인증이 되지 않은 사용자 이메일에 대해, 전달된 시간을 초과한 미인증 이메일에 대한 uid삭제
    async def delete_unvalid_emails_uid(self, elapsed_second:float=300.0):
        # 현재 시간을 임시적으로 저장한다
        now_datetime = datetime.now()
        
        # self.__pending_validate_emails에 존재하는 모든 키(email)에 대해 아래를 반복한다
        all_pending_validate_emails = list(self.__pending_validate_emails.keys())
        for pending_validate_email in all_pending_validate_emails:
        # 현재 email의 값속, "Time"에 있는 Timer객체가 생성된 시간에, elapsed_second를 더한 시간이, 현재 시간을 넘어서는지 확인한다
        # - 넘어서는 경우 현재 email을 self.__pending_validate_emails pop한뒤, 계정을 delete한다(넘어서지 않으면 아무것도 하지 않는다)
            time:Timer = self.__pending_validate_emails[pending_validate_email]["time"]
            if(time.check_elapsed(elapsed_second, now_datetime)):
                password:str = self.__pending_validate_emails[pending_validate_email]["password"]
                login_data = self.__firebase_signup_and_login.login(pending_validate_email, password)
                self.__pending_validate_emails.pop(pending_validate_email)
                await self.__amadda_element_manager.delete_user(login_data["user_id"])

        self.__write_pending_validate_emails()

    # FOR TEST

    def TEST_GET_PENDING_VALIDATE_EMAILS(self):
        return self.__pending_validate_emails

# Test code

import asyncio

def get_email():
    return "jjhqp1110@gmail.com"
def get_password():
    return "123456"
def get_wrong_password():
    return "12345678"

aem = AmaddaElementManager(FirebaseChacher(firebase=Firebase("AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json")))
def get_amadda_element_manager():
    return aem
fsl = FirebaseSignUpAndLogin("AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json",
                                 "AIzaSyAf8UkeGCgVOHm_GluOUewYv7ROPBWH5Ds")
def get_firebase_signup_and_login():
    return fsl
def get_amadda_user_account_controller():
    
    return AmaddaUserAccountController(firebase_signup_and_login=get_firebase_signup_and_login(),
                                       amadda_element_manager=get_amadda_element_manager())

async def reset_environment_to_init_state():
    fsl = FirebaseSignUpAndLogin("AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json",
                                 "AIzaSyAf8UkeGCgVOHm_GluOUewYv7ROPBWH5Ds")

    try:
        login_data = fsl.login(get_email(), get_password())
        fsl.delete(login_data["user_id"])
    except:
        pass

'''
테스트 초기 상태 조건 -> 회원가입이 되어있지 않음
                    AmaddaUserAccountController의 self.TEST_GET_PENDING_VALIDATE_EMAILS()의 반환 결과에 아무것도 존재하지 않음
                    AmaddaElementManager의 self.TEST_GET_CHACHE("ALL")의 반환 결과의 User요소가 비어있음
                    firebase의 User컬렉션 요소가 비어있음
'''

async def Test_user_signup():
    await reset_environment_to_init_state()

    email = get_email()
    password = get_password()
    wrong_password = get_wrong_password()

    aem = get_amadda_element_manager()
    auac = get_amadda_user_account_controller()

    # test 1 회원가입이 되어있지 않을때 비밀번호를 다르게 하여 user_signup() 수행시 에러 발생
    try:
        await auac.user_signup(email, password, wrong_password)
        print("test 1 False")
    except:
        print("test 1 True")

    # test 2 회원가입이 되어있지 않을때 user_signup() 수행시 성공 + 
    # AmaddaUserAccountController의 self.TEST_GET_PENDING_VALIDATE_EMAILS()의 반환 결과에 사용한 email이 key로 저장됨
    # AmaddaElementManager의 self.TEST_GET_CHACHE()의 반환 결과의 User요소에 요소가 1개 생성됨 + firebase의 User에 문서가 1개 생성됨
    try:
        await auac.user_signup(email, password, password)
        print("test 2 user_signup True")
    except:
        print("test 2 user_signup False")
    try:
        pve = auac.TEST_GET_PENDING_VALIDATE_EMAILS()
        if(email in pve and len(pve) == 1):
            print("test 2 pending validate email True")
        else:
            raise
    except:
        print("test 2 pending validate email False")
    try:
        if(len(aem.TEST_GET_CHACHE()["User"]) == 1):
            print("test 3 chache True")
        else:
            raise
    except:
        print("test 3 chache False")

    # test 3 회원가입이 되어있을때 user_singup() 수행시 에러 발생
    try:
        await auac.user_signup(email, password, password)
        print("test 3 False")
    except:
        print("test 3 True")

    '''
    1 아이디가 없을때 user_login 수행 -> 에러발생
    5 user_signup 성공 이후 + 이메일 미인증 상태 일때 user_login 수행 -> 에러발생
    6 user_signup 성공 이후 + 이메일 인증 상태 일때 user_login 수행 -> 성공, 반환값 있음
                                                                pending_validate_emails에서 email에 대한 정보가 삭제됨
    6-1 user_singup 성공 이후 + 이메일 미인증 일때, delete_unvalid_emails_uid 수행
    6-2 
    '''

async def Test_user_login():
    await reset_environment_to_init_state()

    email = get_email()
    password = get_password()
    wrong_password = get_wrong_password()

    aem = get_amadda_element_manager()
    auac = get_amadda_user_account_controller()

    # test 1 계정이 생성되어 있지 않을때 user_login 수행 -> 에러 발생
    try:
        auac.user_login(email, password)
        print("test 1 False")
    except:
        print("test 1 True")

    # test 2 signup 성공 이후, 인증 메일을 클릭 하지 않았을때, user_login 수행 -> 에러 발생
    await auac.user_signup(email, password, password)
    try:
        auac.user_login(email, password)
        print("test 2 False")
    except:
        print("test 2 True")

    # ※ 이곳에서 중단점을 설정한뒤 아래의 테스트의 조건이 만족되었을때 마저 수행

    # test 3 signup 성공 이후, 인증 메일을 클릭한 이후, user_login 수행 -> 성공 + 
    # AmaddaUserAccountController의 self.TEST_GET_PENDING_VALIDATE_EMAILS()의 반환 결과에 key로 있었던 email이 사라짐
    try:
        result = auac.user_login(email, password)
        print("test 3 user login", type(result) == str)
        print("test 3 pending validate emails", auac.TEST_GET_PENDING_VALIDATE_EMAILS() == {})
    except:
        print("test 3 False")

    # test 4 signup 성공 이후, 인증 메일을 클릭한 이후, 비밀번호를 틀리게 하여 user_login 수행 -> 에러 발생
    try:
        result = auac.user_login(email, wrong_password)
        print("test 3 False")
    except:
        print("test 3 True")

async def Test_resend_email_verification():
    await reset_environment_to_init_state()

    email = get_email()
    password = get_password()
    wrong_password = get_wrong_password()

    aem = get_amadda_element_manager()
    auac = get_amadda_user_account_controller()

    # test 1 signup 성공 이후(pending_validate_emails에 회원가입한 email이 key로 있는 상태일때)
    # resend_email_verification() 수행 -> 성공 + email로 새롭게 메시지가 와야함(직접 확인 필요)
    await auac.user_signup(email, password, password)

    from time import sleep
    sleep(70)
    
    try:
        auac.resend_email_verification(email)
        print("test 1 직접 확인 필요, 이전 signup과 합쳐서 메시지 총 2개")
    except:
        print("test 1 False")

    # ※ 이곳에서 중단점을 설정한뒤 아래의 테스트의 조건이 만족되었을때 마저 수행

    # test 2 signup 성공 이후, 이메일 인증 확인 이후, login 성공 이후(pending_validate_emails에 email이 key에서 제거되었을때)
    # resend_email_verification() 수행 -> 에러 발생
    auac.user_login(email, password) # user login시 pending_validate_emails에서 잘 pop이 되는지도 확인이 필요
    sleep(70)
    try:
        auac.resend_email_verification(email) # pending_va...이 비어있어서 raise ValueError("이메일 인증 만료...가 raise되는지 확인이 필요
        print("test 2 False")
    except:
        print("test 2 True")

async def Test_user_logout():
    await reset_environment_to_init_state()

    email = get_email()
    password = get_password()
    wrong_password = get_wrong_password()

    aem = get_amadda_element_manager()
    auac = get_amadda_user_account_controller()

    # test 1 signup과 login 성공이후(AEM의 self.TEST_GET_CHACHE()의 반환 결과의 User요소에 요소가 1개 있는 상태일때 + firebase User에 문서가 있는 상태일때)
    # user_logout() 수행 -> AEM의 self.TEST_GET_CHACHE()의 반환 결과의 User요소에 아무것도 남지 않음 + firebase User에 있는 문서는 그대로 유지
    await auac.user_signup(email, password, password)
    user_id = auac.user_login(email, password)
    try:
        print(aem.TEST_GET_CHACHE()["User"])
        await auac.user_logout(user_id)
        print("Test 1 logout True")
        print("Test 1 amadda elem manager chache", aem.TEST_GET_CHACHE()["User"] == {})
    except:
        print("test 1 False")

async def Test_user_delete():
    await reset_environment_to_init_state()

    email = get_email()
    password = get_password()
    wrong_password = get_wrong_password()

    aem = get_amadda_element_manager()
    auac = get_amadda_user_account_controller()

    # test 1 signup과 login 성공이후(AEM의 self.TEST_GET_CHACHE()의 반환 결과의 User요소에 요소가 1개 있는 상태일때 + firebase User에 문서가 있는 상태일때)
    # user_logout() 수행 -> AEM의 self.TEST_GET_CHACHE()의 반환 결과의 User요소에 아무것도 남지 않음 + firebase User에 있던 문서도 삭제됨
    await auac.user_signup(email, password, password)
    user_id = auac.user_login(email, password)
    try:
        print(aem.TEST_GET_CHACHE()["User"])
        await auac.user_delete(user_id)
        print("Test 1 user delete True")
        print("Test 1 amadda elem manager chache", aem.TEST_GET_CHACHE()["User"] == {})
    except:
        print("test 1 False")

async def Test_delete_unvalid_emails_uid():
    await reset_environment_to_init_state()

    email = get_email()
    password = get_password()
    wrong_password = get_wrong_password()

    aem = get_amadda_element_manager()
    auac = get_amadda_user_account_controller()

    # test 1 signup성공 이후(AUAC의 self.TEST_GET_PENDING_VALIDATE_EMAILS()의 반환 결과에 사용한 email이 key로 저장되어 있는 상태일때)
    # 인증 만료 제한 기간이 지나지 않았을때, delete_unvalid_emails_uid()수행 -> pending_validate_emails에 그대로 email이 key로 저장되어 있어야함
    await auac.user_signup(email, password, password)
    try:
        await auac.delete_unvalid_emails_uid(300)
        pve = auac.TEST_GET_PENDING_VALIDATE_EMAILS()
        print("Test 1", email in pve and len(pve) == 1)
    except:
        print("Test 1 False")
    
    from time import sleep
    sleep(1) # 인증 만료 시간을 보냄

    # test 2 위의 테스트에서 이어서 수행, 인증 만료 제한 기간이 지났을때, delete_unvalid_emails_uid()수행 -> pending_validate_emails에 key로 저장된 email이 삭제됨
    try:
        print("Test 2 chache check", str(aem.TEST_GET_CHACHE()["User"])[:10])
        print("Test 2 pending validate emails check :", str(auac.TEST_GET_PENDING_VALIDATE_EMAILS())[:10])
        await auac.delete_unvalid_emails_uid(0.5)
        print("Test 2 chache check", str(aem.TEST_GET_CHACHE()["User"])[:10])
        print("Test 2 pending validate emails check :", str(auac.TEST_GET_PENDING_VALIDATE_EMAILS())[:10])
        print("Test 2", auac.TEST_GET_PENDING_VALIDATE_EMAILS() == {})
    except:
        print("Test 2 False")

async def Test_pending_valid_emails_remain():
    email = get_email()
    password = get_password()
    wrong_password = get_wrong_password()

    auac = get_amadda_user_account_controller()

    way = 1 # 매번 프로그램을 실행하여 테스트시, 1부터 시작하여 1씩 더해가면서 수행, 도중에 테스트 실패시 way == 3에 있는 테스트 초기화만 따로 수행하기

    if(way == 1):        
        # 이곳에 중단점을 설정한뒤 user_signup의 내부로 타고 들어가 pending_valid_emails에 아무것도 없다면 테스트 성공
        await auac.user_signup("test_mail1@example.com", password, password)

    if(way == 2):
        # 이곳에 중단점을 설정한뒤 user_signup의 내부로 타고 들어가 pending_valid_emails에
        # "test_mail1@example.com"이 key로 잘 유지되어 있는지 확인하기, 잘 유지되어 있다면 테스트 성공
        await auac.user_signup("test_mail2@example.com", password, password)

    if(way == 3):
        # 이곳에 중단점을 설정한뒤 delete_user_signupp의 내부로 타고 들어가 pending_valid_emails에
        # test_mail1과 2가 key로 잘 유지되어 있는지 확인하기, 잘 유지되어 있고, 내부에서 잘 삭제까지 하면 테스트 성공
        await auac.delete_unvalid_emails_uid(0)

        # 다시 테스트 초기의 상태로 되돌리기
        # "AmaddaBackend/pending_valid_emails.pkl"는 직접 삭제 필요
        fsl = get_firebase_signup_and_login()
        try:
            login_data = fsl.login("test_mail1@example.com", password)
            fsl.delete(login_data["user_id"])
        except:
            pass
        try:
            login_data = fsl.login("test_mail2@example.com", password)
            fsl.delete(login_data["user_id"])
        except:
            pass

if(__name__ == "__main__"):
    #asyncio.run(())
    pass


