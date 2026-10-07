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
            raise ValueError("owner user id or subject id not found")
        
    async def get_subjects(self, owner_user_id:str)->list[dict[str, Any]]:
        # Subject 정보 캐싱
        await self.__firebase_chacher.init_subjects(owner_user_id)

        # 캐싱된 모든 Subject 정보들 반환
        try:
            return self.__firebase_chacher.get_subjects(owner_user_id)
        except:
            raise ValueError("owner user id not found")

    async def create_subject(self, owner_user_id:str,
                             subject_id:str,
                             subject_number:int=0,
                             subject_name:str=""):
        # Subject 정보 캐싱
        await self.__firebase_chacher.init_subjects(owner_user_id)

        subject_id_already_exist = False
        try:
            self.__firebase_chacher.get_subject(owner_user_id, subject_id)
            subject_id_already_exist = True
        except:
            pass

        if(subject_id_already_exist):
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

    # about Wiki_Document
    async def get_wiki_document(self, owner_user_id:str, owner_subject_id:str, wiki_document_id:str):
        # Wiki_Document 정보 캐싱
        await self.__firebase_chacher.init_Xs("Wiki_Document", owner_user_id, owner_subject_id)

        # 캐싱된 Wiki_Document 정보 반환
        try:
            return self.__firebase_chacher.get_X("Wiki_Document", owner_user_id, owner_subject_id, wiki_document_id)
        except:
            raise ValueError("owner user id or owner subject id or wiki document id not found")
    
    async def get_wiki_documents(self, owner_user_id:str, owner_subject_id:str):
        # WikiDocument 정보 캐싱
        await self.__firebase_chacher.init_Xs("Wiki_Document", owner_user_id, owner_subject_id)

        # 캐싱된 모든 WikiDocument 정보들 반환
        try:
            return self.__firebase_chacher.get_Xs("Wiki_Document", owner_user_id, owner_subject_id)
        except:
            raise ValueError("owner user id or owner subject id not found")

    async def create_wiki_document(self, owner_user_id:str, owner_subject_id:str,
                                   wiki_document_id:str,
                                   wiki_document_content:str=""):
        # WikiDocument 정보 캐싱
        await self.__firebase_chacher.init_Xs("Wiki_Document", owner_user_id, owner_subject_id)

        wiki_document_id_already_exist = False
        try:
            self.__firebase_chacher.get_X("Wiki_Document", owner_user_id, owner_subject_id, wiki_document_id)
            wiki_document_id_already_exist = True
        except:
            pass

        if(wiki_document_id_already_exist):
            raise ValueError("wiki document id already exist")

        # WikiDocument 정보 생성
        await self.__firebase_chacher.create_X("Wiki_Document", {
            "owner_user_id":owner_user_id,
            "owner_subject_id":owner_subject_id,
            "wiki_document_id":wiki_document_id,
            "owned_problem_ids":[],
            "wiki_document_content":wiki_document_content
        })

        # 본인의 owner Subject를 가져와 본인을 하위관계로 연결한후 Subject를 동기화
        owner_subject = await self.get_subject(owner_user_id, owner_subject_id)
        owner_subject["owned_wiki_document_ids"] = owner_subject["owned_wiki_document_ids"] + [wiki_document_id]

        owner_subject["pending_sync"] = None

        await self.__firebase_chacher.subjects_to_firebase(owner_user_id)

    async def update_wiki_document(self, owner_user_id:str, owner_subject_id:str, wiki_document_id:str, new_datas:dict[str, Any]):
        # 업데이트할 WikiDocument정보 가져오기
        wiki_document = await self.get_wiki_document(owner_user_id, owner_subject_id, wiki_document_id)

        # 변경하고자 하는 데이터에 관계와 관련된 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if("id" in key):
                raise ValueError("cannot change relationship")

        # 변경하고자 하는 데이터에, 유저 정보에 존재하지 않는 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if(key not in wiki_document):
                raise ValueError("unknown subject elem contains in new_data")

        # 정보 수정 및 firebase와 동기화
        for key, value in new_datas.items():
            wiki_document[key] = value

        wiki_document["pending_sync"] = None
        
        await self.__firebase_chacher.Xs_to_firebase("Wiki_Document", owner_user_id, owner_subject_id)

# pending Test
    # about Problem
    async def get_problem(self, owner_user_id:str, owner_subject_id:str, problem_id:str):
        # Problem 정보 캐싱
        await self.__firebase_chacher.init_Xs("Problem", owner_user_id, owner_subject_id)

        # 캐싱된 Problem 정보 반환
        try:
            return self.__firebase_chacher.get_X("Problem", owner_user_id, owner_subject_id, problem_id)
        except:
            raise ValueError("owner user id or owner subject id or problem id not found")
    
    async def get_problems(self, owner_user_id:str, owner_subject_id:str):
        # Problem 정보 캐싱
        await self.__firebase_chacher.init_Xs("Problem", owner_user_id, owner_subject_id)

        # 캐싱된 모든 Problem 정보들 반환
        try:
            return self.__firebase_chacher.get_Xs("Problem", owner_user_id, owner_subject_id)
        except:
            raise ValueError("owner user id or owner subject id not found")

    async def create_problem(self, owner_user_id:str, owner_subject_id:str, owner_wiki_document_id:str,
                             problem_id:str,
                             owning_user_answer_id:str,
                             owning_grade_id:str,
                             problem_type:str="",
                             problem_number:int=0,
                             problem_question:str="",
                             problem_correct_answer:str="",
                             problem_choices:list[str]=[]):
        # Problem 정보 캐싱
        await self.__firebase_chacher.init_Xs("Problem", owner_user_id, owner_subject_id)

        problem_id_already_exist = False
        try:
            self.__firebase_chacher.get_X("Problem", owner_user_id, owner_subject_id, problem_id)
            problem_id_already_exist = True
        except:
            pass

        if(problem_id_already_exist):
            raise ValueError("problem id already exist")

        # Problem 정보 생성
        await self.__firebase_chacher.create_X("Problem", {
            "owner_user_id":owner_user_id,
            "owner_subject_id":owner_subject_id,
            "owner_wiki_document_id":owner_wiki_document_id,
            "problem_id":problem_id,
            "owned_user_answer_id":owning_user_answer_id,
            "owned_grade_id":owning_grade_id,
            "problem_type":problem_type,
            "problem_number":problem_number,
            "problem_question":problem_question,
            "problem_correct_answer":problem_correct_answer,
            "problem_choices":problem_choices
        })

        # 본인의 owner Wiki_Document를 가져와 본인을 하위관계로 연결한후 Wiki Document를 동기화
        owner_wiki_document = await self.get_wiki_document(owner_user_id, owner_subject_id, owner_wiki_document_id)
        owner_wiki_document["owned_problem_ids"] = owner_wiki_document["owned_problem_ids"] + [problem_id]

        owner_wiki_document["pending_sync"] = None

        await self.__firebase_chacher.Xs_to_firebase("Wiki_Document", owner_user_id, owner_subject_id)

        # 본인에 대한 생성 이후 내부적으로 User_Answer과 Grade도 생성
        await self.__create_user_answer(owner_user_id, owner_subject_id, problem_id, owning_user_answer_id)
        await self.__create_grade(owner_user_id, owner_subject_id, problem_id, owning_grade_id)

    async def update_problem(self, owner_user_id:str, owner_subject_id:str, problem_id:str, new_datas:dict[str, Any]):
        # 업데이트할 Problem정보 가져오기
        problem = await self.get_problem(owner_user_id, owner_subject_id, problem_id)

        # 변경하고자 하는 데이터에 관계와 관련된 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if("id" in key):
                raise ValueError("cannot change relationship")

        # 변경하고자 하는 데이터에, 유저 정보에 존재하지 않는 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if(key not in problem):
                raise ValueError("unknown problem elem contains in new_data")

        # 정보 수정 및 firebase와 동기화
        for key, value in new_datas.items():
            problem[key] = value

        problem["pending_sync"] = None
        
        await self.__firebase_chacher.Xs_to_firebase("Problem", owner_user_id, owner_subject_id)

    # about User_Answer
    async def get_user_answer(self, owner_user_id:str, owner_subject_id:str, user_answer_id:str):
        # User_Answer 정보 캐싱
        await self.__firebase_chacher.init_Xs("User_Answer", owner_user_id, owner_subject_id)

        # 캐싱된 User_Answer 정보 반환
        try:
            return self.__firebase_chacher.get_X("User_Answer", owner_user_id, owner_subject_id, user_answer_id)
        except:
            raise ValueError("owner user id or owner subject id or user answer id not found")
        
    async def get_user_answers(self, owner_user_id:str, owner_subject_id:str):
        # Usesr_Answer 정보 캐싱
        await self.__firebase_chacher.init_Xs("User_Answer", owner_user_id, owner_subject_id)

        # 캐싱된 모든 Usesr_Answer 정보들 반환
        try:
            return self.__firebase_chacher.get_Xs("User_Answer", owner_user_id, owner_subject_id)
        except:
            raise ValueError("owner user id or owner subject id not found")
        
    async def __create_user_answer(self, owner_user_id:str, owner_subject_id:str, owner_problem_id:str,
                                 user_answer_id:str,
                                 user_answer:str="",
                                 user_answer_state:str="not_answered"):
        # User_Answer 정보 캐싱
        await self.__firebase_chacher.init_Xs("User_Answer", owner_user_id, owner_subject_id)

        user_answer_id_already_exist = False

        try:
            self.__firebase_chacher.get_X("User_Answer", owner_user_id, owner_subject_id, user_answer_id)
            user_answer_id_already_exist = True
        except:
            pass

        if(user_answer_id_already_exist):
            raise ValueError("user answer id already exist")

        # User_Answer 정보 생성
        await self.__firebase_chacher.create_X("User_Answer", {
            "owner_user_id":owner_user_id,
            "owner_subject_id":owner_subject_id,
            "owner_problem_id":owner_problem_id,
            "user_answer_id":user_answer_id,
            "user_answer":user_answer,
            "user_answer_state":user_answer_state
        })

        # 본인의 owner Problem을 가져와 본인을 하위관계로 연결한후 Problem를 동기화
        owner_problem = await self.get_problem(owner_user_id, owner_subject_id, owner_problem_id)
        owner_problem["owned_user_answer_id"] = user_answer_id

        owner_problem["pending_sync"] = None

        await self.__firebase_chacher.Xs_to_firebase("Problem", owner_user_id, owner_subject_id)

    async def update_user_answer(self, owner_user_id:str, owner_subject_id:str, user_answer_id:str, new_datas:dict[str, Any]):
        # 업데이트할 User_Answer정보 가져오기
        user_answer = await self.get_user_answer(owner_user_id, owner_subject_id, user_answer_id)

        # 변경하고자 하는 데이터에 관계와 관련된 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if("id" in key):
                raise ValueError("cannot change relationship")

        # 변경하고자 하는 데이터에, 유저 정보에 존재하지 않는 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if(key not in user_answer):
                raise ValueError("unknown user answer elem contains in new_data")

        # 정보 수정 및 firebase와 동기화
        for key, value in new_datas.items():
            user_answer[key] = value

        user_answer["pending_sync"] = None
        
        await self.__firebase_chacher.Xs_to_firebase("User_Answer", owner_user_id, owner_subject_id)

    # about Grade
    async def get_grade(self, owner_user_id:str, owner_subject_id:str, grade_id:str):
        # Grade 정보 캐싱
        await self.__firebase_chacher.init_Xs("Grade", owner_user_id, owner_subject_id)

        # 캐싱된 Grade 정보 반환
        try:
            return self.__firebase_chacher.get_X("Grade", owner_user_id, owner_subject_id, grade_id)
        except:
            raise ValueError("owner user id or owner subject id or grade id not found")

    async def get_grades(self, owner_user_id:str, owner_subject_id:str):
        # Grade 정보 캐싱
        await self.__firebase_chacher.init_Xs("Grade", owner_user_id, owner_subject_id)

        # 캐싱된 모든 Grade 정보들 반환
        try:
            return self.__firebase_chacher.get_Xs("Grade", owner_user_id, owner_subject_id)
        except:
            raise ValueError("owner user id or owner subject id not found")

    async def __create_grade(self, owner_user_id:str, owner_subject_id:str, owner_problem_id:str,
                                 grade_id:str,
                                 grade_state:str="not_graded",
                                 explanation:str=""):
        # Grade 정보 캐싱
        await self.__firebase_chacher.init_Xs("Grade", owner_user_id, owner_subject_id)

        grade_id_already_exist = False

        try:
            self.__firebase_chacher.get_X("Grade", owner_user_id, owner_subject_id, grade_id)
            grade_id_already_exist = True
        except:
            pass

        if(grade_id_already_exist):
            raise ValueError("grade id already exist")

        # Grade 정보 생성
        await self.__firebase_chacher.create_X("Grade", {
            "owner_user_id":owner_user_id,
            "owner_subject_id":owner_subject_id,
            "owner_problem_id":owner_problem_id,
            "grade_id":grade_id,
            "grade_state":grade_state,
            "explanation":explanation
        })

        # 본인의 owner Problem을 가져와 본인을 하위관계로 연결한후 Problem를 동기화
        owner_problem = await self.get_problem(owner_user_id, owner_subject_id, owner_problem_id)
        owner_problem["owned_grade_id"] = grade_id

        owner_problem["pending_sync"] = None

        await self.__firebase_chacher.Xs_to_firebase("Problem", owner_user_id, owner_subject_id)

    async def update_grade(self, owner_user_id:str, owner_subject_id:str, grade_id:str, new_datas:dict[str, Any]):
        # 업데이트할 Grade정보 가져오기
        grade = await self.get_grade(owner_user_id, owner_subject_id, grade_id)

        # 변경하고자 하는 데이터에 관계와 관련된 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if("id" in key):
                raise ValueError("cannot change relationship")

        # 변경하고자 하는 데이터에, 유저 정보에 존재하지 않는 요소가 포함된 경우 에러 발생
        for key in new_datas.keys():
            if(key not in grade):
                raise ValueError("unknown grade elem contains in new_data")

        # 정보 수정 및 firebase와 동기화
        for key, value in new_datas.items():
            grade[key] = value

        grade["pending_sync"] = None
        
        await self.__firebase_chacher.Xs_to_firebase("Grade", owner_user_id, owner_subject_id)

    # about delete

    # 임이의 사용자에 대한 캐싱된 모든 데이터를 삭제하는 메소드(로그 아웃 수행시)
    async def delete_user_all_chache_data(self, user_id:str):
        user = await self.get_user(user_id)
        
        all_x_elem_list = self.__firebase_chacher.get_all_x_elem_list()
        
        await self.__firebase_chacher.delete_user(user_id)
        await self.__firebase_chacher.delete_subjects(user_id)

        owned_subject_ids = user["owned_subject_ids"]
        
        for x_elem in all_x_elem_list:
            for subject_id in owned_subject_ids:
                await self.__firebase_chacher.delete_Xs(x_elem, user_id, subject_id)

    # 임이의 사용자에 대한 모든 캐셔 및 firebase에서 삭제하는 메소드(회원 탈퇴시)
    async def delete_user(self, user_id:str):
        # 삭제할 본인의 User정보 가져오기
        delete_user = await self.get_user(user_id)

        # 삭제할 User의, 모든 하위 관계들(Subjects) 아이디 가져오기
        delete_owned_subject_ids = delete_user["owned_subject_ids"]
        
        # 본인의 모든 하위 관계들(Subjects) 삭제하기
        for delete_owned_subject_id in delete_owned_subject_ids:
            await self.delete_subject(user_id, delete_owned_subject_id, True)

        # 본인 삭제하기(본인을 가장 마지막에 삭제해야함)
        await self.__firebase_chacher.delete_user(user_id, True)

    # 임이의 과목에 대한 모든 캐셔 및 firebase에서 삭제하는 메소드(과목 삭제시)
    async def delete_subject(self, owner_user_id:str, subject_id:str, owner_delete:bool=False):
        # 삭제할 본인의 Subject정보 가져오기
        delete_subject = await self.get_subject(owner_user_id, subject_id)

        if(owner_delete == False):
            # 삭제전 owner User로 부터 자신의 아이디 제거한뒤 User 동기화 하기
            owner_user = await self.get_user(owner_user_id)
            subject_index_from_owner_user = owner_user["owned_subject_ids"].index(subject_id)
            owner_user["owned_subject_ids"].pop(subject_index_from_owner_user)
            owner_user["pending_sync"] = None
            await self.__firebase_chacher.user_to_firebase(owner_user_id)

        # 삭제할 Subject의, 모든 하위 관계들(Wiki_Documents) 아이디 가져오기
        delete_owned_wiki_document_ids = delete_subject["owned_wiki_document_ids"]
        
        # 본인의 모든 하위 관계들(Wiki_Documents) 삭제하기
        for delete_owned_wiki_document_id in delete_owned_wiki_document_ids:
            await self.delete_wiki_document(owner_user_id, subject_id, delete_owned_wiki_document_id, True)

        # 본인 삭제하기(본인을 가장 마지막에 삭제해야함)
        await self.__firebase_chacher.delete_subject(owner_user_id, subject_id, True)

    # 임이의 위키 문서에 대한 모든 캐셔 및 firebase에서 삭제하는 메소드
    async def delete_wiki_document(self, owner_user_id:str, owner_subject_id:str, wiki_document_id:str, owner_delete:bool=False):
        # 삭제할 본인의 Wiki_Document정보 가져오기
        delete_wiki_document = await self.get_wiki_document(owner_user_id, owner_subject_id, wiki_document_id)

        if(owner_delete == False):
            # 삭제할 Wiki_Document의, owner Subject 아이디 가져오기
            owner_subject_id = delete_wiki_document["owner_subject_id"]
            
            # 삭제전 owner Subject로 부터 자신의 아이디 제거한뒤 Subject 동기화 하기
            owner_subject = await self.get_subject(owner_user_id, owner_subject_id)
            wiki_document_index_from_owner_subject = owner_subject["owned_wiki_document_ids"].index(wiki_document_id)
            owner_subject["owned_wiki_document_ids"].pop(wiki_document_index_from_owner_subject)
            owner_subject["pending_sync"] = None
            await self.__firebase_chacher.subjects_to_firebase(owner_user_id)

        # 삭제할 Problem의, 모든 하위 관계들(Problems) 아이디 가져오기
        delete_owned_problem_ids = delete_wiki_document["owned_problem_ids"]
        
        # 본인의 모든 하위 관계들(Problems) 삭제하기
        for owned_problem_id in delete_owned_problem_ids:
            await self.delete_problem(owner_user_id, owner_subject_id, owned_problem_id, True)

        # 본인 삭제하기(본인을 가장 마지막에 삭제해야함)
        await self.__firebase_chacher.delete_X("Wiki_Document", owner_user_id, owner_subject_id, wiki_document_id, True)

    # 임이의 문제 및 해당 문제와 연관된 사용자 답변 정보와 채점 정보를 캐셔 및 firebase에서 삭제하는 메소드
    async def delete_problem(self, owner_user_id:str, owner_subject_id:str, problem_id:str, owner_delete:bool=False):
        # 삭제할 본인의 Problem정보 가져오기
        delete_problem = await self.get_problem(owner_user_id, owner_subject_id, problem_id)

        if(owner_delete == False):
            # 삭제할 Problem의, owner wiki document 아이디 가져오기
            owner_wiki_document_id = delete_problem["owner_wiki_document_id"]

            # 삭제전 owner Wiki_Document로 부터 자신의 아이디 제거한뒤 Wiki_Document 동기화 하기
            owner_wiki_document = await self.get_wiki_document(owner_user_id, owner_subject_id, owner_wiki_document_id)
            problem_index_from_owner_wiki_document = owner_wiki_document["owned_problem_ids"].index(problem_id)
            owner_wiki_document["owned_problem_ids"].pop(problem_index_from_owner_wiki_document)

            owner_wiki_document["pending_sync"] = None
            await self.__firebase_chacher.Xs_to_firebase("Wiki_Document", owner_user_id, owner_subject_id)

        # 삭제할 Problem의, 하위 관계(User_Answer, Grade) 아이디 가져오기
        delete_owned_user_answer_id = delete_problem["owned_user_answer_id"]
        delete_owned_grade_id = delete_problem["owned_grade_id"]

        # 본인의 하위 관계(User_Answer, Grade) 삭제하기
        await self.__delete_user_answer(owner_user_id, owner_subject_id, delete_owned_user_answer_id)
        await self.__delete_grade(owner_user_id, owner_subject_id, delete_owned_grade_id)

        # 본인 삭제하기(본인을 가장 마지막에 삭제해야함)
        await self.__firebase_chacher.delete_X("Problem", owner_user_id, owner_subject_id, problem_id, True)

    # 임이의 사용자 답변 정보를 캐셔 및 firebase에서 삭제하는 메소드
    async def __delete_user_answer(self, owner_user_id:str, owner_subject_id:str, user_answer_id:str):
        await self.__firebase_chacher.delete_X("User_Answer", owner_user_id, owner_subject_id, user_answer_id, True)

    # 임이의 채점 정보를 캐셔 및 firebase에서 삭제하는 메소드
    async def __delete_grade(self, owner_user_id:str, owner_subject_id:str, grade_id:str):
        await self.__firebase_chacher.delete_X("Grade", owner_user_id, owner_subject_id, grade_id, True)

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

    #print(await aem.get_subject("user-100", "subject-1"))
    #print(await aem.get_subjects("user-1"))

    #await aem.create_subject("user-1", "subject-1", 1)
    #await aem.create_subject("user-1", "subject-2", 2)

    #await aem.update_subject("user-1", "subject-1", {"subject_name":"python"})

async def Test_wiki_document():
    aem = get_amadda_element_manager()

    # wiki document id의 경우 llmwiki의 특성상 문서의 제목이 id가 됩니다
    #print(await aem.get_wiki_document("user-1", "subject-1", "variable"))
    #print(await aem.get_wiki_documents("user-1", "subject-1"))

    #await aem.create_wiki_document("user-1", "subject-1", "variable")
    #await aem.create_wiki_document("user-1", "subject-1", "function")

    #await aem.update_wiki_document("user-1", "subject-1", "variable", {"wiki_document_content":"변수는 메모리에 저장된 데이터에 대한 접근권한을 획득할 수 있는 존재이다"})

async def Test_problem():
    aem = get_amadda_element_manager()

    #await aem.create_problem("user-1", "subject-1", "variable", "problem-1", "user_answer-1", "grade-1")
    #await aem.create_problem("user-1", "subject-1", "variable", "problem-2", "user_answer-2", "grade-2")

    #print(await aem.get_problem("user-1", "subject-1", "problem-1"))
    #print(await aem.get_problems("user-1", "subject-1"))

    #await aem.update_problem("user-1", "subject-1", "problem-1", {"problem_question":"변수의 역할은?"})

async def Test_user_answer():
    aem = get_amadda_element_manager()

    #print(await aem.get_user_answer("user-1", "subject-1", "user_answer-1"))
    #print(await aem.get_user_answers("user-1", "subject-1"))

    #await aem.update_user_answer("user-1", "subject-1", "user_answer-1", {"user_answer":"변수는 메모리에 저장된 데이터에 대한 접근권한을 얻을 수 있는 존재이다"})

async def Test_grade():
    aem = get_amadda_element_manager()

    #print(await aem.get_grade("user-1", "subject-1", "grade-1"))
    #print(await aem.get_grades("user-1", "subject-1"))

    #await aem.update_grade("user-1", "subject-1", "grade-1", {"grade_state":"correct"})

    #print(aem.TEST_GET_CHACHE("ALL"))

async def Test_problem_delete():
    aem = get_amadda_element_manager()

    #await aem.create_user("user-1")
    #await aem.create_subject("user-1", "subject-1")
    #await aem.create_wiki_document("user-1", "subject-1", "variable")

    #await aem.create_problem("user-1", "subject-1", "variable", "problem-1", "user_answer-1", "grade-1")

    #print("before :", aem.TEST_GET_CHACHE("ALL"))
    #await aem.delete_problem("user-1", "subject-1", "problem-1")
    #print("after :", aem.TEST_GET_CHACHE("ALL"))

async def Test_wiki_document_delete():
    aem = get_amadda_element_manager()

    #await aem.create_user("user-1")
    #await aem.create_subject("user-1", "subject-1")
    #await aem.create_wiki_document("user-1", "subject-1", "variable")
    #await aem.create_problem("user-1", "subject-1", "variable", "problem-1", "user_answer-1", "grade-1")
    #await aem.create_problem("user-1", "subject-1", "variable", "problem-2", "user_answer-2", "grade-2")

    #await aem.delete_wiki_document("user-1", "subject-1", "variable")

async def Test_subject_delete():
    aem = get_amadda_element_manager()

    #await aem.create_user("user-1", "kevin")
    #await aem.create_subject("user-1", "subject-1", subject_name="python")
    #await aem.create_wiki_document("user-1", "subject-1", "variable")
    #await aem.create_wiki_document("user-1", "subject-1", "function")
    #await aem.create_problem("user-1", "subject-1", "variable", "problem-1", "user_answer-1", "grade-1")

    #print(aem.TEST_GET_CHACHE("ALL"))
    #await aem.delete_subject("user-1", "subject-1")
    #print(aem.TEST_GET_CHACHE("ALL"))

async def Test_user_delete():
    aem = get_amadda_element_manager()

    #await aem.create_user("user-1", "kevin")
    #await aem.create_subject("user-1", "subject-1", subject_name="python")
    #await aem.create_subject("user-1", "subject-2", subject_name="electronics")
    #await aem.create_wiki_document("user-1", "subject-1", "variable")

    await aem.delete_user("user-1")

async def Test_delete_user_all_chache_data():
    aem = get_amadda_element_manager()
    '''
    await aem.create_user("user-1", "kevin")
    await aem.create_user("user-2", "alice")

    await aem.create_subject("user-1", "subject-1", subject_name="python")
    await aem.create_subject("user-1", "subject-2", subject_name="electronics")

    await aem.create_wiki_document("user-1", "subject-1", "variable")
    await aem.create_wiki_document("user-1", "subject-1", "function")

    await aem.create_problem("user-1", "subject-1", "variable", "problem-1", "user_answer-1", "grade-1")
    '''
    '''
    await aem.get_user("user-1")
    await aem.get_user("user-2")
    await aem.get_wiki_documents("user-1", "subject-1")
    '''
    #print(aem.TEST_GET_CHACHE("ALL"))
    #await aem.delete_user_all_chache_data("user-1")
    #print(aem.TEST_GET_CHACHE("ALL"))


if(__name__ == "__main__"):
    asyncio.run(Test_delete_user_all_chache_data())


