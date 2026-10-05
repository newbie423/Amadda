from typing import Any

from my_firebase import Firebase
from firebase_chacher import FirebaseChacher

class AmaddaElementManager:
    def __init__(self, firebase_chacher:FirebaseChacher):
        self.__firebase_chacher = firebase_chacher

    # about User
    async def get_user(self, user_id:str)->dict[str, Any]:
        # user 정보 캐싱
        await self.__firebase_chacher.init_user(user_id)

        # 캐싱된 User 정보 반환
        try:
            return self.__firebase_chacher.get_user(user_id)
        except:
            raise ValueError("user not found")

    async def create_user(self, user_id:str, user_name:str=""):
        # User 정보 캐싱후 캐싱에 성공하면 user가 존재한다는 뜻이기에 에러 발생
        if(await self.__firebase_chacher.init_user(user_id) == True):
            raise ValueError("user id already exist")
        
        # User 정보 생성
        await self.__firebase_chacher.create_user({
            "user_id":user_id,
            "name":user_name,
            "owned_subject_ids":[]
        })
    
    async def update_user(self, user_id:str, new_datas:dict[str, Any]):
        # 업데이트할 User정보 가져오기
        user = await self.get_user(user_id)

        # 변경하고자 하는 데이터에 관계와 관련된 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if("id" in key):
                raise ValueError("cannot change relationship")

        # 변경하고자 하는 데이터에, 유저 정보에 존재하지 않는 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if(key not in user):
                raise ValueError("unknown user elem contains in new_data")

        # 정보 수정 및 firebase와 동기화
        for key, value in new_datas.items():
            user[key] = value

        user["pending_sync"] = None
        
        await self.__firebase_chacher.user_to_firebase(user_id)

    # about Subject
    async def get_subject(self, owner_user_id:str, subject_id:str)->dict[str, Any]:
        # Subject 정보 캐싱
        await self.__firebase_chacher.init_subjects(owner_user_id)

        # 캐싱된 Subject 정보 반환
        try:
            return self.__firebase_chacher.get_subject(owner_user_id, subject_id)
        except:
            raise ValueError("user id or subject id not found")
        
    async def get_subjects(self, owner_user_id:str)->list[dict[str, Any]]:
        # Subject 정보 캐싱
        await self.__firebase_chacher.init_subjects(owner_user_id)

        # 캐싱된 모든 Subject 정보들 반환
        try:
            return self.__firebase_chacher.get_subjects(owner_user_id)
        except:
            raise ValueError("subjects not found")

    async def create_subject(self, owner_user_id:str,
                             subject_id:str,
                             subject_number:int,
                             subject_name:str=""):
        # Subject 정보 캐싱
        await self.__firebase_chacher.init_subjects(owner_user_id)

        subject_already_exist = False
        try:
            self.__firebase_chacher.get_subject(owner_user_id, subject_id)
            subject_already_exist = True
        except:
            pass

        if(subject_already_exist):
            raise ValueError("subject id already exist")

        # Subject 정보 생성
        await self.__firebase_chacher.create_subject({
            "owner_user_id":owner_user_id,
            "subject_id":subject_id,
            "owned_wiki_document_ids":[],
            "subject_number":subject_number,
            "subject_name":subject_name
        })

        # 본인의 owner User를 가져와 본인을 하위관계로 연결한후 User를 동기화
        owner_user = await self.get_user(owner_user_id)
        owner_user["owned_subject_ids"] = owner_user["owned_subject_ids"] + [subject_id]

        owner_user["pending_sync"] = None

        await self.__firebase_chacher.user_to_firebase(owner_user_id)

    async def update_subject(self, owner_user_id:str, subject_id:str, new_datas:dict[str, Any]):
        # 업데이트할 Subject정보 가져오기
        subject = await self.get_subject(owner_user_id, subject_id)

        # 변경하고자 하는 데이터에 관계와 관련된 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if("id" in key):
                raise ValueError("cannot change relationship")

        # 변경하고자 하는 데이터에, 유저 정보에 존재하지 않는 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if(key not in subject):
                raise ValueError("unknown subject elem contains in new_data")

        # 정보 수정 및 firebase와 동기화
        for key, value in new_datas.items():
            subject[key] = value

        subject["pending_sync"] = None
        
        await self.__firebase_chacher.subjects_to_firebase(owner_user_id)

    # about WikiDocument
    async def get_wiki_document(self, owner_user_id:str, owner_subject_id:str, wiki_document_id:str): pass
    async def get_wiki_documents(self, owner_user_id:str, owner_subject_id:str): pass

    async def create_wiki_document(self, owner_user_id:str, owner_subject_id:str,
                                   wiki_document_id:str,
                                   wiki_document_content:str):pass

    async def update_wiki_document(self, owner_user_id:str, owner_subject_id:str, wiki_document_id:str, new_datas:dict[str, Any]): pass

    # about Problem
    async def get_problem(self, owner_user_id:str, owner_subject_id:str, problem_id:str): pass
    async def get_problems(self, owner_user_id:str, owner_subject_id:str): pass

        # "내부적으로 UserAnswer과 Grade의 create을 사용하여 관계까지 한번에 생성하기"
    async def create_problem(self, owner_user_id:str, owner_subject_id:str, owner_wiki_document_id:str,
                             problem_id:str,
                             problem_type:str,
                             problem_number:str,
                             problem_question:str,
                             problem_correct_answer:str,
                             problem_choices:list[str]):pass

    async def update_problem(self, owner_user_id:str, owner_subject_id:str, problem_id:str, new_datas:dict[str, Any]): pass

    # about UserAnswer
    async def get_user_answer(self, owner_user_id:str, owner_subject_id:str, oppnent_problem_id:str): pass
    async def get_user_answers(self, owner_user_id:str, owner_subject_id:str): pass

    async def __create_user_answer(self, owner_user_id:str, owner_subject_id:str, oppenent_problem_id:str,
                                 user_answer_id:str,
                                 user_answer:str="",
                                 user_answer_state:str="not_answered"): pass

    async def update_user_answer(self, owner_user_id:str, owner_subject_id:str, oppenent_problem_id:str, user_answer_id:str, new_data:dict[str, Any]): pass

    # about Grade
    async def get_grade(self, owner_user_id:str, owner_subject_id:str, oppnent_problem_id:str): pass
    async def get_grades(self, owner_user_id:str, owner_subject_id:str): pass

    async def __create_grade(self, owner_user_id:str, owner_subject_id:str, oppenent_problem_id:str,
                                 grade_id:str,
                                 grade_state:str="not_graded",
                                 explanation:str=""): pass

    async def update_grade(self, owner_user_id:str, owner_subject_id:str, oppenent_problem_id:str, grade_id:str, new_data:dict[str, Any]): pass


    # about delete

    async def delete_user(self, user_id:str, firebase_delete:bool=False): pass
    
    async def delete_subject(self, owner_user_id:str, subject_id:str, firebase_delete:bool=False): pass

    async def delete_wiki_document(self, owner_user_id:str, owner_subject_id:str, firebase_delete:bool=False): pass

        # 내부적으로 user_answer과 grade도 삭제하기
    async def delete_problem(self, owner_user_id:str, owner_subject_id:str, problem_id:str, firebase_delete:bool=False): pass

    async def __delete_user_answer(self, owner_user_id:str, owner_subject_id:str, user_answer_id:str, firebase_delete:bool=False): pass

    async def __delete_grade(self, owner_user_id:str, owner_subject_id:str, grade_id:str, firebase_delete:bool=False): pass

    # for test

    def TEST_GET_CHACHE(self, X_name:str):
        return self.__firebase_chacher.PRINT_ELEMS(X_name)

# Test code

import asyncio

def get_amadda_element_manager():
    return AmaddaElementManager(FirebaseChacher(Firebase("AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json")))

async def Test_user():
    aem = get_amadda_element_manager()

    #print(await aem.get_user("user-1"))

    #await aem.create_user("user-1", "kevin")
    #await aem.create_user("user-2", "alice")

    #await aem.create_user("user-1", "dennis")

    #await aem.update_user("user-1", {"name1":"kelly"})
    #await aem.update_user("user-1", {"owned_subjct_ids":[]})
    #await aem.update_user("user-1", {"name":"kelly"})

    print(aem.TEST_GET_CHACHE("ALL"))

async def Test_subject():
    aem = get_amadda_element_manager()

    #print(await aem.get_subject("user-1", "subject-1"))
    #print(await aem.get_subjects("user-1"))

    #await aem.create_subject("user-1", "subject-1", 1)
    #await aem.create_subject("user-1", "subject-2", 2)

    await aem.update_subject("user-1", "subject-1", {"subject_names":"python"})

if(__name__ == "__main__"):
    asyncio.run(Test_subject())


