from typing import Any

class ProblemGrader:
    MODEL_NAME = "gemini-3.5-flash-lite"
    
    def __init__(self, gemini_api_key:str):
        self.__gemini_api_key = gemini_api_key

    def __generate_prompt(self)->str:
        pass

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

        for idx in range(len(grade_infos)):
            grade_info = grade_infos[idx]
            
            result += [{
                "id":grade_info["id"],
                "grade_state":"not_graded",
                "explanation":""
            }]

        return result

''' 테스트시 아래를 사용
user_id = "iCVCfqIbzjNyVCODi5roL2yjSqz1"
subject_id="ba607739-7fe2-44f9-a54c-87c346cf6384"
wiki_document_id="fce0300e-f52f-477c-8a7f-ebf9330d9520"
'''

test_grade_infos = [
    {
        "id": "90efd7f9-cb24-435c-8140-469a70ab9487",
        "problem_question": "자본주의와 대립하는 듯하면서도 평등과 분배를 강조하는 이데올로기의 이름을 쓰시오.",
        "problem_correct_answer": "사회주의",
        "user_answer": ""
    },
    {
        "id": "0dc46533-53a8-4238-ab07-d0a5925520ab",
        "problem_question": "사물을 치우침 없이 있는 그대로 중도적으로 바라봐야 지혜가 생긴다는 원리를 경물치지라고 한다.",
        "problem_correct_answer": "O",
        "user_answer": ""
    },
    {
        "id": "802d42a9-d6e3-4d3f-9189-b5d5f48d333d",
        "problem_question": "탐진치가 올바른 미래 개척을 방해하는 이유와, 이를 극복하기 위한 경물치지의 원리가 무엇인지 서술하시오.",
        "problem_correct_answer": "탐진치로 인해 보고 싶은 것만 보고 보기 싫은 것은 은폐하게 되므로 올바른 반성과 미래 개척이 불가능해진다. 이를 극복하기 위한 경물치지의 원리는 사물을 치우침 없이 있는 그대로 중도적으로 바라봐 지혜를 얻는 것이다.",
        "user_answer": ""
    },
    {
        "id": "c94c89f4-702c-4628-aa17-e0ca8bdb908e",
        "problem_question": "개벽사상에 포함되지 않는 것은?",
        "problem_correct_answer": "실학파",
        "user_answer": ""
    },
    {
        "id": "e52b1ea2-f73c-48a3-9c8d-e9ab9370e85a",
        "problem_question": "환웅의 건국 이념을 바탕으로 남북 분단과 이데올로기 대립을 극복하고 건설해야 할 국가의 명칭을 쓰시오.",
        "problem_correct_answer": "홍익 복지 국가",
        "user_answer": ""
    },
    {
        "id": "da26ee8f-751c-4333-97b0-b5aad415c4e2",
        "problem_question": "다음 중 자본주의에 대한 설명으로 옳은 것은?",
        "problem_correct_answer": "개신교 정신과 결합하여 물질적 풍요와 근대화를 이끌었다.",
        "user_answer": ""
    },
    {
        "id": "ee9e9eff-7bb8-4590-9a74-ef28eb83b00f",
        "problem_question": "정신 문명의 회복 없이 디지털 혁명으로 나아간다면 인류는 통제 중심의 유토피아를 맞이할 것이라고 경고한다.",
        "problem_correct_answer": "X",
        "user_answer": ""
    },
    {
        "id": "0066c5f4-ea25-4d56-a6b4-2df3a0ba5644",
        "problem_question": "강의 요약에서 주장하는 문명의 대전환(개벽의 완성)을 이루기 위해 물질 문명과 정신 문명 측면에서 각각 무엇을 수용하고 결합해야 하는지 설명하시오.",
        "problem_correct_answer": "물질 문명 측면에서는 자본주의와 사회주의의 장점을 수용하고 AI 및 디지털 혁명을 이루어야 하며, 정신 문명 측면에서는 홍익인간 이념과 인의예지의 인간성 혁명(양심 개벽)을 결합해야 한다.",
        "user_answer": ""
    }
]