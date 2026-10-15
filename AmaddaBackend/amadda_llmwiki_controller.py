from my_firebase import Firebase
from firebase_chacher import FirebaseChacher
from amadda_element_manager import AmaddaElementManager
from my_llmwiki import LLMWiki

class AmaddaLLMWikiController:
    def __init__(self, llmwiki:LLMWiki, amadda_element_manager:AmaddaElementManager):
        self.__llmwiki = llmwiki
        self.__amadda_element_manager = amadda_element_manager


# Test code
def get_llmwiki():
    return LLMWiki("gemini_api_key.json")
def get_amadda_element_manager():
    f = Firebase("AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json")
    fc = FirebaseChacher(f)
    return AmaddaElementManager(fc)
def get_amadda_llm_wiki_controller():
    return AmaddaLLMWikiController(get_llmwiki(), get_amadda_element_manager())



if(__name__ == "__main__"):
    pass

