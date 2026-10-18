from typing import Any
from uuid import uuid4

from AmaddaBackend.amadda_element_manager import AmaddaElementManager

class AmaddaSubjectController:
    def __init__(self, amadda_element_manager:AmaddaElementManager):
        self.__amadda_element_manager:AmaddaElementManager = amadda_element_manager

    async def get_user_subjects(self, user_id: str) -> list[dict[str, Any]]:
        """
        사용자의 모든 과목 정보 가져오기 기능
        """
        subjects: list[dict[str, Any]] = await self.__amadda_element_manager.get_subjects(user_id)

        subjects.sort(key=lambda subject: subject["subject_number"])

        return subjects
        
    async def create_subject(self, user_id:str) -> dict[str, Any]:
        """
        과목 생성 기능
        """
        all_subjects:list[dict[str, Any]] = None

        try:
            all_subjects = await self.__amadda_element_manager.get_subjects(user_id)
        except:
            all_subjects = []
        
        subject_id = str(uuid4())

        subject_number = len(all_subjects) + 1
        
        await self.__amadda_element_manager.create_subject(user_id, subject_id, subject_number)

        subject = await self.__amadda_element_manager.get_subject(user_id, subject_id)

        return subject
    
    async def update_subject(self, user_id:str, subject_id:str, new_datas:dict[str, Any]) -> None:
        """
        과목 정보 변경 기능
        new_datas에는 변경하고자 하는 데이터를 아래와 같이 입력
        {
            "subject_name":str # 과목 이름
            "subject_number":int # 과목 번호
        }
        위에 작성된 요소만 변경 가능
        """
        await self.__amadda_element_manager.update_subject(user_id, subject_id, new_datas)
        
    async def delete_subject(self, user_id:str, subject_id:str) -> None:
        """
        과목 삭제 기능
        """
        # 삭제할 과목 가져오기(없으면 에러 발생)
        delete_subject = await self.__amadda_element_manager.get_subject(user_id, subject_id)
        
        all_subjects:list[dict[str, Any]] = None
        
        try:
            all_subjects = await self.__amadda_element_manager.get_subjects(user_id)
        except:
            all_subjects = []
        
        delete_subject_number = delete_subject["subject_number"]
        
        # 삭제할 과목보다 번호가 높은 과목들의 번호만 -1하기
        for idx in range(len(all_subjects)):
            now_subject = all_subjects[idx]
            now_subject_id = now_subject["subject_id"]
            now_subject_number = now_subject["subject_number"]
            
            if(now_subject_number > delete_subject_number):
                await self.__amadda_element_manager.update_subject(user_id, now_subject_id, {
                    "subject_number":now_subject_number - 1
                })

        # 과목 삭제
        await self.__amadda_element_manager.delete_subject(user_id, delete_subject["subject_id"])


