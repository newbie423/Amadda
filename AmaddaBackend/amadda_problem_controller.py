from my_firebase import Firebase
from firebase_chacher import FirebaseChacher
from amadda_element_manager import AmaddaElementManager
from problem_generator import ProblemGenerator

class AmaddaProblemController:
    def __init__(self,
                 amadda_element_manager:AmaddaElementManager,
                 problem_generator:ProblemGenerator):
        self.__amadda_element_manager = amadda_element_manager
        self.__problem_generator = problem_generator

    <여기 부터 마저 이어서 작성하기>

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

# Test code
import asyncio

async def Test():
    apc = get_amadda_problem_controller()

if(__name__ == "__main__"):
    asyncio.run(Test())


    