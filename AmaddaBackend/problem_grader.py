from typing import Any

class ProblemGrader:
    MODEL_NAME = "gemini-3.5-flash-lite"
    
    def __init__(self, gemini_api_key:str):
        self.__gemini_api_key = gemini_api_key

    def grade(self, grade_infos:list[dict[str, Any]])->list[dict[str, Any]]:
        '''
        채점을 수행하는 기능
        grade_infos의 각 요소는 아래와 같음
        {
            "id":str, # 채점을 수행하기 위한 아이디
            "problem_question":str,
            "problem_correct_answer":str,
            "user_answer":str
        }

        반환결과는 아래와 같음
        {
            "id":int, # targets에 있던 아이디와 대응되는 아이디
            "grade_state":str, # 채점 결과 "correct"(정답), "incorrect"(오답)중 하나
            "explanation":str # 해설 정답인 경우에는 빈 문자열, 오답인 경우에만 실제로 해설 내용이 존재
        }
        '''

        result = []

        for grade_info in grade_infos:
            result += [{
                "id":grade_info["id"],
                "grade_state":"incorrect",
                "explanation":"틀렸습니다"
            }]

        return result

''' 테스트시 아래를 사용
user_id = "iCVCfqIbzjNyVCODi5roL2yjSqz1"
subject_id="ba607739-7fe2-44f9-a54c-87c346cf6384"
wiki_document_id="fce0300e-f52f-477c-8a7f-ebf9330d9520"
'''