from typing import Any

from AmaddaBackend.amadda_element_manager import AmaddaElementManager
from AmaddaBackend.problem_grader import ProblemGrader

class AmaddaGradeController:
    def __init__(self,
                 amadda_element_manager:AmaddaElementManager,
                 problem_grader:ProblemGrader):
        self.__amadda_element_manager:AmaddaElementManager = amadda_element_manager
        self.__problem_grader:ProblemGrader = problem_grader
        
        self.__problem_grade_process:dict[tuple, bool] = {}
        '''
        {
            (user_id, subject_id, wiki_document_id) : bool,
            ...
        }
        '''

    async def grade_problem(self, user_id:str, subject_id:str, wiki_document_id:str):
        key = (user_id, subject_id, wiki_document_id)
        
        if(key not in self.__problem_grade_process):
            self.__problem_grade_process[key] = True # 채점을 시작할 것이니 True
        
        # 문제의 질문과 정답 그리고 해당 문제에 대한 사용자의 답변을 가져와 채점을 수행할 수 있는 형태로 변환하기
        problems = await self.__amadda_element_manager.get_wiki_document_problems(user_id, subject_id, wiki_document_id)

        results_for_grading:list[dict[str, Any]] = []

        for problem in problems:
            user_answer = await self.__amadda_element_manager.get_user_answer(user_id,
                                                                              subject_id,
                                                                              problem["owned_user_answer_id"])
            results_for_grading += [{
                "id":problem["problem_id"], # 이곳에 problem_id를 사용
                "problem_question":problem["problem_question"],
                "problem_correct_answer":problem["problem_correct_answer"],
                "user_answer":user_answer["user_answer"]
            }]

        # 실제 채점 수행
        grade_results:list[dict[str, Any]] = None
        
        try:
            grade_results = self.__problem_grader.grade(results_for_grading)
        except:
            self.__problem_grade_process[key] = False # 채점에 실패하였으니 채점중이 아니기에 False
            raise

        # 채점 결과를 인덱싱
        indexed_grade_results = {}
        
        for grade_result in grade_results:
            indexed_grade_results[grade_result["id"]] = grade_result
        
        # 채점 결과를 토대로 데이터 베이스속 적절한 실제 채점 데이터의 요소를 갱신
        # 모든 문제마다 소유하고 있는 채점 데이터의 아이디를 가져와 해당 채점 데이터를 갱신
        for problem in problems:
            id = problem["problem_id"]
            grade_id = problem["owned_grade_id"]

            grade_result = indexed_grade_results[id]
            grade_update_result = {
                "grade_state":grade_result["grade_state"],
                "explanation":grade_result["explanation"]
            }
            await self.__amadda_element_manager.update_grade(user_id, subject_id, grade_id, grade_update_result)
        
        self.__problem_grade_process[key] = False # 채점 완료 되었으니 False

    def is_problem_grading(self, user_id:str, subject_id:str, wiki_document_id:str)->bool:
        '''
        문제가 채점되고 있는지 확인하는 기능
        채점되고 있으면 True, 아니면 False를 반환
        '''
        return self.__problem_grade_process.get((user_id, subject_id, wiki_document_id), False)

    async def get_all_grades(self, user_id:str, subject_id:str, wiki_document_id:str) -> list[dict[str, Any]]:
        '''
        임이의 위키 문서를 기반으로 생성된 모든 문제에 대한 채점 데이터를 반환하는 기능
        '''
        return await self.__amadda_element_manager.get_wiki_document_grades(user_id, subject_id, wiki_document_id)




