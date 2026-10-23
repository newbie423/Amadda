import asyncio
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

    async def grade_problem(self, user_id: str, subject_id: str, wiki_document_id: str):
        """
        임의의 위키 문서 속 모든 문제들을 채점하는 기능
        """

        key = (user_id, subject_id, wiki_document_id)

        if self.is_problem_grading(user_id, subject_id, wiki_document_id):
            raise ValueError(
                "채점이 이미 진행중입니다. 채점이 완료된 이후 다시 시도해 주세요."
            )

        # 채점 시작 상태를 먼저 설정
        # 동시에 요청되는 중복 채점 방지
        self.__problem_grade_process[key] = True

        try:
            # 문제 정보 가져오기
            problems = await self.__amadda_element_manager.get_wiki_document_problems(
                user_id,
                subject_id,
                wiki_document_id
            )

            # 가져온 문제들중 정답은 제외하기(incorrect 또는 not_graded만 찾기)
            not_correct_problems = []
            
            for problem in problems:
                grade_id = problem["owned_grade_id"]
                grade = await self.__amadda_element_manager.get_grade(user_id, subject_id, grade_id)
                if(grade["grade_state"] != "correct"):
                    not_correct_problems += [problem]

            problems = not_correct_problems # 변수명 그대로 사용하기

            results_for_grading: list[dict[str, Any]] = []

            for problem in problems:
                user_answer = await self.__amadda_element_manager.get_user_answer(
                    user_id,
                    subject_id,
                    problem["owned_user_answer_id"]
                )

                results_for_grading.append({
                    "id": problem["problem_id"],
                    "problem_question": problem["problem_question"],
                    "problem_correct_answer": problem["problem_correct_answer"],
                    "user_answer": user_answer["user_answer"]
                })

            # 동기 함수를 별도의 스레드에서 실행
            grade_results: list[dict[str, Any]] = await asyncio.to_thread(
                self.__problem_grader.grade,
                results_for_grading
            )

            # 채점 결과 인덱싱
            indexed_grade_results = {
                grade_result["id"]: grade_result
                for grade_result in grade_results
            }

            # 채점 결과를 데이터베이스에 반영
            for problem in problems:
                problem_id = problem["problem_id"]
                grade_id = problem["owned_grade_id"]

                grade_result = indexed_grade_results[problem_id]

                grade_update_result = {
                    "grade_state": grade_result["grade_state"],
                    "explanation": grade_result["explanation"]
                }

                await self.__amadda_element_manager.update_grade(
                    user_id,
                    subject_id,
                    grade_id,
                    grade_update_result
                )

        finally:
            # 성공, 예외 발생, 취소 등 종료 경로에서 상태 정리
            self.__problem_grade_process[key] = False

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

