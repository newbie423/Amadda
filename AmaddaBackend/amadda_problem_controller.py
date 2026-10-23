from typing import Any
from uuid import uuid4

from AmaddaBackend.my_firebase import Firebase
from AmaddaBackend.firebase_chacher import FirebaseChacher
from AmaddaBackend.amadda_element_manager import AmaddaElementManager
from AmaddaBackend.problem_generator import ProblemGenerator

class AmaddaProblemController:
    def __init__(self,
                 amadda_element_manager:AmaddaElementManager,
                 problem_generator:ProblemGenerator):
        self.__amadda_element_manager:AmaddaElementManager = amadda_element_manager
        self.__problem_generator:ProblemGenerator = problem_generator

        self.__problem_generate_progress:dict[tuple, Any] = {}
        '''
        {
            (user_id, subject_id, wiki_document_id):False # 현재 임이의 유저의 임이의 과목에 대해 문제가 생성되고 있는지 확인하기 위함
        }
        '''

    async def create_problems(self, user_id:str, subject_id:str, wiki_document_id:str, generate_rule:dict[str, any]) -> None:
        '''
        문제를 생성하는 기능

        [generate_rule 요소]

        문제 총 개수
        "total_count": 10,

        문제 유형별 개수(총 합이 total_count와 동일해야함)
        "problem_type_counts": {"ox": 2, "select": 4, "short": 3, "long": 1},

        문제 난이도 "easy", "medium", "hard"중 하나>
        "difficulty": "medium",

        집중적으로 생성할 문제의 관련 키워드>
        "focus_keywords": ["가야", "고대 기록 매체", "미국의 영토 확장"],

        문제 출제 범위 "balanced"(전체 골고루, focus_keywords는 무시됨) "focused"(focus_keywords에 있는 것을 중점으로)
        "coverage": "balanced"
        '''
        # 유저의 과목이 존재하는지 가져오는 기능(없으면 에러가 발생)
        await self.__amadda_element_manager.get_subject(user_id, subject_id)

        if((user_id, subject_id, wiki_document_id) not in self.__problem_generate_progress):
            self.__problem_generate_progress[(user_id, subject_id, wiki_document_id)] = False

        if(self.__problem_generate_progress[(user_id, subject_id, wiki_document_id)]):
            raise ValueError("이미 문제를 생성중입니다, 문제 생성이 완료된 후 다시 시도하세요")

        # 사용자의 기존 모든 문제들 가져오기
        existing_problems:list[dict[str, Any]] = None
        
        try:
            # 아직 한번도 문제를 만든적이 없다면 에러가 발생됨
            existing_problems = await self.__amadda_element_manager.get_wiki_document_problems(user_id, subject_id, wiki_document_id)
        except:
            existing_problems = []

        created_problems:list[dict, Any] = None

        # wiki_document_content 가져오기
        wiki_document = await self.__amadda_element_manager.get_wiki_document(user_id, subject_id, wiki_document_id)
        wiki_document_content = wiki_document["wiki_document_content"]
        
        try:
            self.__problem_generate_progress[(user_id, subject_id, wiki_document_id)] = True
            
            # problem generator를 사용하여 문제를 생성하기
            created_problems = self.__problem_generator.generate_problem(generate_rule, wiki_document_content, existing_problems)
        except:
            self.__problem_generate_progress[(user_id, subject_id, wiki_document_id)] = False
            raise ValueError("문제 생성에 실패하였습니다")

        # amadda element manager를 사용하여 생성된 문제들을 데이터 베이스에 저장하기
        existing_problems_count = len(existing_problems)

        for idx in range(len(created_problems)):
            created_problem = created_problems[idx]
            
            await self.__amadda_element_manager.create_problem(
                owner_user_id=user_id,
                owner_subject_id=subject_id,
                owner_wiki_document_id=wiki_document_id,
                problem_id=str(uuid4()),
                owning_user_answer_id=str(uuid4()),
                owning_grade_id=str(uuid4()),
                problem_type=created_problem["problem_type"],
                problem_number=existing_problems_count + idx + 1,
                problem_question = created_problem["problem_question"],
                problem_correct_answer=created_problem["problem_correct_answer"],
                problem_options=created_problem["problem_options"]
            )
        self.__problem_generate_progress[(user_id, subject_id, wiki_document_id)] = False
        
    def is_problem_creating(self, user_id:str, subject_id:str, wiki_document_id:str) -> bool:
        '''
        문제가 생성되고 있는지 확인하는 기능
        생성되고 있으면 True, 아니면 False를 반환
        '''
        return self.__problem_generate_progress.get((user_id, subject_id, wiki_document_id), False)
        
    async def get_all_problems(self, user_id:str, subject_id:str, wiki_document_id:str) -> list[dict[str, Any]]:
        '''
        임이의 위키 문서를 기반으로 생성된 모든 문제 데이터를 반환하는 기능
        '''
        return await self.__amadda_element_manager.get_wiki_document_problems(user_id, subject_id, wiki_document_id)

    async def get_all_user_answers(self, user_id:str, subject_id:str, wiki_document_id:str) -> list[dict[str, Any]]:
        '''
        임이의 위키 문서를 기반으로 생성된 모든 문제에 대한 사용자 답변 데이터를 반환하는 기능
        '''
        return await self.__amadda_element_manager.get_wiki_document_user_answers(user_id, subject_id, wiki_document_id)

    async def update_user_answer(self, user_id:str, subject_id:str, user_answer_id:str, new_datas:dict[str, Any]) -> None:
        '''
        사용자 풀이 데이터를 갱신하는 기능
        new_datas의 구조는 아래와 같음
        {
            "user_answer":str
            "user_answer_state":str # "answered", "not_answered"중 하나
        }
        '''
        await self.__amadda_element_manager.update_user_answer(user_id, subject_id, user_answer_id, new_datas)

    async def delete_problem(self, user_id:str, subject_id:str, problem_id:str) -> None:
        '''
        임이의 문제를 삭제하는 기능
        '''

        # 문제를 가져옴(없다면 에러가 발생)
        delete_problem = await self.__amadda_element_manager.get_problem(user_id, subject_id, problem_id)

        # 가져온 문제의 소유 위키 문서를 토대로 다른 모든 문제들도 가져옴(위의 코드에서 에러가 발생하지 않으면 마찬가지로 발생하지 않음)
        all_problems = await self.__amadda_element_manager.get_wiki_document_problems(user_id, subject_id, delete_problem["owner_wiki_document_id"])

        # 삭제할 문제의 번호
        delete_problem_number = delete_problem["problem_number"]

        # 삭제한 문제의 번호보다 높은 번호를 가진 모든 문제의 번호를 -1하기
        for idx in range(len(all_problems)):
            now_problem = all_problems[idx]
            now_problem_id = now_problem["problem_id"]
            now_problem_number = now_problem["problem_number"]
            
            if(now_problem_number > delete_problem_number):
                await self.__amadda_element_manager.update_problem(user_id, subject_id, now_problem_id, {
                    "problem_number" : now_problem_number - 1
                })

        # 문제를 삭제하기
        await self.__amadda_element_manager.delete_problem(user_id, subject_id, delete_problem["problem_id"])

# For Test code
def get_amddda_element_manager():
    f = Firebase("AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json")
    fc = FirebaseChacher(f)
    return AmaddaElementManager(fc)
def get_problem_generator():
    return ProblemGenerator()

def get_amadda_problem_controller():
    return AmaddaProblemController(get_amddda_element_manager(),
                                   get_problem_generator())

def get_wiki_document_id():
    return "1d51e449-4b2f-4cc0-bc4b-6dc72c01402f"

# Test code
import asyncio

async def Test_create_problems():
    apc = get_amadda_problem_controller()

    generate_rule = {
        "total_count": 10,
        "problem_type_counts": {"ox": 2, "select": 4, "short": 3, "long": 1},
        "difficulty": "medium",
        "focus_keywords": ["가야", "고대 기록 매체", "미국의 영토 확장"],
        "coverage": "balanced",
    }

    wiki_document_id = get_wiki_document_id()

    await apc.create_problems("user-1", "subject-1", wiki_document_id, generate_rule)

async def Test_get_all_problems():
    apc = get_amadda_problem_controller()

    all_problems = await apc.get_all_problems("user-1", "subject-1", get_wiki_document_id())

    for problem in all_problems:
        print(problem)

async def Test_get_all_user_answers():
    apc = get_amadda_problem_controller()

    all_user_answers = await apc.get_all_user_answers("user-1", "subject-1", get_wiki_document_id())
    
    for user_answer in all_user_answers:
        print(user_answer)

async def Test_delete_problem():
    apc = get_amadda_problem_controller()

    problem_id = "7238a0ef-837e-40af-b1e7-47c6ab73a2e1"

    await apc.delete_problem("user-1", "subject-1", problem_id)

if(__name__ == "__main__"):
    asyncio.run(Test_delete_problem())
    pass


    