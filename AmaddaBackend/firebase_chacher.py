from typing import Any

from my_firebase import Firebase

# 모든 정보의 내부에는 아래와 같은 특수 요소가 있다
# document_id -> firebase에서 문서를 가져왔을때 함께 포함되는 정보로
#   추후 다시 firebase에 저장할때는 해당 정보를 pop한뒤 저장한다
# pending_sync -> firebase에서 가져와 캐싱한 정보들중, 변경이 일어난 정보에 추가되는 요소로
#   추후 다시 firebase에 저장할때는 해당 요소가 있는 정보들에 대해서만, 해당 요소를 pop한뒤
#   firebase에 덮어쓴다

class FirebaseChacher:
    __ALL_X_ELEMS = [
        "WikiDocument"
        "Problem",
        "UserAnswer",
        "Grade",
    ]

    __ALL_ELEMS = [
        "User",
        "Subject"
    ] + __ALL_X_ELEMS

    def __init__(self, firebase:Firebase):
        self.__firebase:Firebase = firebase

        self.__elems: dict[str, dict[str | tuple, object]] = {}
        for elem in FirebaseChacher.__ALL_ELEMS:
            self.__elems[elem] = {}

        # self.__elems 구조
        """
        {
            "User": {
                user_id:user info,
                ...
            },

            "Subject": {
                user_id:{
                    subject_id:subject info,
                    ...
                    },
                ...
            },

            "나머지": { # TableOfContent를 대표로 작성함, 나머지 Summary, Problem등도 구조 동일
                (user_id, subject_id):{
                    table_of_content_id:table of content info,
                    ...
                    },
                ...
            }
        }
        """

    # X_name이 ALL_X_ELEMS에 포함되어 있는지 확인하는 내장 메소드
    def __is_X_name_contains(self, X_name):
        if X_name not in FirebaseChacher.__ALL_X_ELEMS:
            raise ValueError(f'X_name "{X_name}" is not defined')

    # ===== firebase에서 가져온 문서를 캐싱용 구조로 변경한뒤 캐싱하는 내장 메소드

    # firebase에서 가져온 user 문서의 데이터를, 캐싱용 구조로 변경한뒤, elem.User에 캐싱하는 내장 메소드
    def __chache_user(self: str, user_data_from_firebase: dict[str, any]):
        # - user_data_from_firebase에 "document_id"요소가 없으면 에러를 발생시킨다(새롭게 만든 데이터는 firebase에서 다시 가져와야 한다)
        if "document_id" not in user_data_from_firebase:
            raise ValueError("only chacheable user data from firebase")

        # user_data_from_firebase에서 "user_id"요소의 값을 가져온다
        user_id = user_data_from_firebase["user_id"]

        # 가져온 "user_id"요소의 값은 키로, user_data_from_firebase전체는 값으로하여, elems.User에 캐싱한다
        self.__elems["User"][user_id] = user_data_from_firebase

    # firebase에서 가져온 subject 문서의 데이터를, 캐싱용 구조로 변경한뒤, elem.Subject에 캐싱하는 내장 메소드
    def __chache_subject(self: str, subject_data_from_firebase: dict[str, any]):
        # - subject_data_from_firebase에 "document_id"요소가 없으면 에러를 발생시킨다
        if "document_id" not in subject_data_from_firebase:
            raise ValueError("only chacheable user data from firebase")

        # subject_data_from_firebase에서 "owner_user_id"와 "subject_id"요소의 값을 가져온다
        owner_user_id = subject_data_from_firebase["owner_user_id"]
        subject_id = subject_data_from_firebase["subject_id"]

        # - elem.Subejct에 "owner_user_id"요소가 키로 존재하지 않으면 "owner_user_id"요소의 값을 키로, {}를 값으로 하여 elem.Subject에 저장한다
        if owner_user_id not in self.__elems["Subject"]:
            self.__elems["Subject"][owner_user_id] = {}

        # elem.Subject에서, "owner_user_id"에 해당하는 값을 가져온다
        # elem.Subject에서 가져온 값에 "subject_id"를 키로, subject_data_from_firebase전체를 값으로 하여 elem.Subject.owner_user_id에 저장한뒤 종료한다
        self.__elems["Subject"][owner_user_id][subject_id] = subject_data_from_firebase

    # firebase에서 가져온 X 문서의 데이터를, 캐싱용 구조로 변경한뒤, elem.X에 캐싱하는 내장 메소드
    def __chache_X(self: str, X_name: str, X_data_from_firebase: dict[str, any]):
        # X_name이 유효한지 확인
        self.__is_X_name_contains(X_name)

        # - X_data_from_firebase에 "document_id"요소가 없으면 에러를 발생시킨다
        if "document_id" not in X_data_from_firebase:
            raise ValueError("only chacheable user data from firebase")

        # X_data_from_firebase에서 "owner_user_id"와 "owner_subject_id"요소의 값을 가져온다
        owner_user_id = X_data_from_firebase["owner_user_id"]
        owner_subject_id = X_data_from_firebase["owner_subject_id"]

        # - elem.X_name에 (owner_user_id, owner_subject_id)가 키로 존재하지 않으면 (owner_user_id, owner_subject_id)를 키로, {}를 값으로 하여 elem.X_name에 저장한다
        if (owner_user_id, owner_subject_id) not in self.__elems[X_name]:
            self.__elems[X_name][(owner_user_id, owner_subject_id)] = {}

        # elem.X_name에서, (owner_user_id, owner_subject_id)에 해당하는 값을 가져온다
        # elem.X_name에서 가져온 값에 f"{X_name.lower()}_id"를 키로, X_data_from_firebase전체를 값으로 하여 elem.X_name.(owner_user_id, owner_subject_id)에 저장한뒤 종료한다
        X_id: str = X_data_from_firebase[f"{X_name.lower()}_id"]
        self.__elems[X_name][(owner_user_id, owner_subject_id)][X_id] = X_data_from_firebase

    # ===== firebase에서 문서를 가져와 캐싱하는 메소드(초기에 한번만 수행)

    # user_id에 해당되는 user 정보를 firebase에서 가져와 캐싱하는 메소드
    async def init_user(self, user_id: str) -> bool:
        # elem.User에 user_id로 캐싱된 user 정보가 있는지 확인한다
        # -캐싱된 user 정보가 있는 경우 True를 반환한다
        if user_id in self.__elems["User"]:
            return True

        # 캐싱된 user 정보가 없기에 Firebase모듈을 사용하여 firebase.User에서 "user_id"요소가 user_id인 문서를 가져온다
        user_data_from_firebase: list[dict[str, any]] = await self.__firebase.load(
            "User", {"user_id": user_id}
        )

        # - firebase에서 가져온 문서가 없으면, False를 반환한다
        if user_data_from_firebase == []:
            return False

        # firebase에서 가져온 문서가 있기에, 가져온 user 문서를 self.__chache_user()를 사용하여 캐싱한뒤 True를 반환한다
        self.__chache_user(user_data_from_firebase[0])
        return True

    # user_id에 해당되는 모든 subject 정보들을 firebase에서 가져와 캐싱하는 메소드
    async def init_subjects(self, user_id: str) -> bool:
        # elem.Subject에 user_id로 캐싱된 subject 정보들이 있는지 확인한다
        # -캐싱된 subject 정보들이 있는 경우 True를 반환한다
        if user_id in self.__elems["Subject"]:
            return True

        # 캐싱된 subject 정보들이 없기에 Firebase모듈을 사용하여 firebase.Subject에서 "user_id"요소가 user_id인 모든 문서를 가져온다
        subject_data_from_firebase = await self.__firebase.load(
            "Subject", {"owner_user_id": user_id}
        )

        # - firebase에서 가져온 문서가 없으면, False를 반환한다
        if subject_data_from_firebase == []:
            return False

        # firebase에서 가져온 문서가 있기에, 가져온 모든 문서들을 전부 self.__chache_subejct()를 사용하여 캐싱한뒤 True를 반환한다
        for subject in subject_data_from_firebase:
            self.__chache_subject(subject)
        return True

    # user_id와 subject_id에 해당되는, User와 Subject를 제외한 다른 모든 정보들을, firebase에서 가져와 캐싱하는 메소드
    async def init_Xs(self, X_name: str, user_id: str, subject_id: str) -> bool:
        # elem.X_name에 (user_id, subject_id)로 캐싱된 Xs 정보들이 있는지 확인한다
        # -캐싱된 X_name 정보들이 있는 경우 True를 반환한다
        if (user_id, subject_id) in self.__elems[X_name]:
            return True

        # 캐싱된 X_name 정보들이 없기에 Firebase모듈을 사용하여 firebase.X_name에서 "user_id"요소가 user_id이면서, "subject_id"요소가 subject_id인 모든 문서를 가져온다
        X_data_from_firebase = await self.__firebase.load(
            X_name, {"owner_user_id": user_id, "owner_subject_id": subject_id}
        )

        # - firebase에서 가져온 문서가 없으면, False를 반환한다
        if X_data_from_firebase == []:
            return False

        # firebase에서 가져온 문서가 있기에, 가져온 모든 문서들을 전부 self.__chache_X()를 사용하여 캐싱한뒤 True를 반환한다
        for X in X_data_from_firebase:
            self.__chache_X(X_name, X)
        return True

    # ===== 캐싱된 정보에 대한 seek 또는 pop 읽기를 수행하는 메소드

    # user_id에 해당되는, 캐싱된 user 정보를 seek하거나 pop한뒤 반환하는 메소드
    def get_user(self, user_id: str, pop: bool = False) -> dict[str, any]:
        # elem.User의 user_id에 해당하는 값을 pop이 True일때는 pop하고, pop이 False일때는 가져오기만 한다
        # pop또는 seek한 user 데이터를 그대로 반환한다
        if pop == False:
            return self.__elems["User"][user_id]
        else:
            return self.__elems["User"].pop(user_id)

    # user_id - subject_id에 해당되는, 캐싱된 subject 정보를 seek하거나 pop한뒤 반환하는 메소드
    def get_subject(self, user_id: str, subject_id: str, pop: bool = False) -> dict[str, any]:
        # elem.Subject의 user_id에 해당하는 subject 정보들중, subject_id에 해당하는 정보만을, pop이 True일때는 pop하고, pop이 False일때는 가져오기만 한다
        # pop또는 seek한 subject 데이터를 그대로 반환한다
        subject = None

        if pop == False:
            subject = self.__elems["Subject"][user_id][subject_id]
        else:
            subject = self.__elems["Subject"][user_id].pop(subject_id)
            if self.__elems["Subject"][user_id] == {}:
                self.__elems["Subject"].pop(user_id)

        return subject

    # user_id에 해당되는, 캐싱된 모든 subject 정보를 seek하거나 pop한뒤 반환하는 메소드
    def get_subjects(self, user_id: str, pop: bool = False) -> list[dict[str, any]]:
        # elem.Subject의 user_id에 해당하는 모든 subject 정보들을, pop이 True일때는 pop하고, pop이 False일때는 가져오기만 한다
        # pop또는 seek한 모든 subject 데이터들을 그대로 반환한다
        subjects = []

        subjects_id = [
            subject["subject_id"]
            for subject in self.__elems["Subject"][user_id].values()
        ]

        for subject_id in subjects_id:
            subjects += [self.get_subject(user_id, subject_id, pop)]

        return subjects

    # (user_id, subject_id) - X_id에 해당되는, 캐싱된 X 정보를 seek하거나 pop한뒤 반환하는 메소드
    def get_X(self, X_name: str, user_id: str, subject_id: str, X_id: str, pop: bool = False) -> dict[str, any] | None:
        # elem.X_name의 (user, subject_id)에 해당하는 모든 X 정보들중, X_id에 해당하는 정보만을, pop이 True일때는 pop하고, pop이 False일때는 가져오기만 한다
        # pop또는 seek한 X 데이터를 그대로 반환한다
        X = None

        if pop == False:
            X = self.__elems[X_name][(user_id, subject_id)][X_id]
        else:
            X = self.__elems[X_name][(user_id, subject_id)].pop(X_id)
            if self.__elems[X_name][(user_id, subject_id)] == {}:
                self.__elems[X_name].pop((user_id, subject_id))

        return X

    # (user_id, subject_id)에 해당되는, 캐싱된 모든 X 정보들을 seek하거나 pop한뒤 반환하는 메소드
    def get_Xs(self, X_name: str, user_id: str, subject_id: str, pop: bool = False) -> list[dict[str, any]] | None:
        # elem.X_name의 (user, subject_id)에 해당하는 모든 X 정보들을, pop이 True일때는 pop하고, pop이 False일때는 가져오기만 한다
        # pop또는 seek한 모든 X 데이터들을 그대로 반환한다
        Xs = []

        X_id = f"{X_name.lower()}_id"
        Xs_id = [X[X_id] for X in self.__elems[X_name][(user_id, subject_id)].values()]

        for X_id in Xs_id:
            Xs += [self.get_X(X_name, user_id, subject_id, X_id, pop)]

        return Xs

    # ===== firebase에서 가져와 캐싱이 되었다는 전제가 적용된, 캐싱된 정보들중, 수정 사항이 있는 캐싱된 정보들만, firebase에 저장하여 동기화 하는 메소드

    # user_id에 해당하는, 캐싱된 user 정보를, 변경사항이 있을때만 firebase에 저장하여 동기화 하는 메소드
    async def user_to_firebase(self, user_id: str):
        # self.get_user()를 사용하여, elem.User에서 user_id에 해당하는 user 정보를 seek한다
        user_data = self.get_user(user_id)
        
        # - seek한 user 정보에 "pending_sync"라는 요소가 없으면, 종료한다
        if("pending_sync" not in user_data):
            return
        
        # seek한 user 정보에 "pending_sync"가 있다는 뜻이기에 "pending_sync"요소를 제거한다
        user_data.pop("pending_sync")
        
        # seek한 user 정보를 Firebase모듈의 save기능을 사용하여 firebase에 저장하고 종료한다
        await self.__firebase.save("User", user_data)

    # user_id에 해당하는, 캐싱된 모든 subject 정보들중, 변경사항이 있는 정보들만 firebase에 저장하여 동기화 하는 메소드
    async def subjects_to_firebase(self, user_id: str):
        # self.get_subjects()를 사용하여, elem.Subject에서 user_id에 해당하는 모든 subject 정보를 seek한다
        subject_datas = self.get_subjects(user_id)
        
        # seek한 모든 subject 정보들에 대하여 아래를 반복 수행한다
        # - 현재 subject 정보에 "pending_sync"라는 요소가 없으면, 무시하고 다음 subject 정보로 넘어간다
        # 현재 subject 정보에 "pending_sync"요소가 있다는 뜻이기에 "pending_sync"요소를 제거한다
        # 현재 subject 정보를, Firebase모듈의 save기능을 사용하여 firebase에 저장하고 종료한다
        for subject_data in subject_datas:
            if("pending_sync" in subject_data):
                subject_data.pop("pending_sync")
                await self.__firebase.save("Subject", subject_data)

    # (user_id, subject_id)에 해당하는 모든 X 정보들중, 변경사항이 있는 정보들만 firebase에 저장하여 동기화 하는 메소드
    async def Xs_to_firebase(self, X_name: str, user_id: str, subject_id: str):
        # self.get_Xs()에 X_name을 사용하여, elem.X에서 (user_id, subject_id)에 해당하는 모든 X 정보를 seek한다
        X_datas = self.get_Xs(X_name, user_id, subject_id)
        
        # seek한 모든 X 정보들에 대하여 아래를 반복 수행한다
        # - 현재 X 정보에 "pending_sync"라는 요소가 없으면, 무시하고 다음 X 정보로 넘어간다
        # 현재 X 정보에 "pending_sync"요소가 있다는 뜻이기에 현재 "pending_sync"요소를 제거한다
        # 현재 X 정보를, Firebase모듈의 save기능을 사용하여 firebase에 저장하고 종료한다
        for X_data in X_datas:
            if("pending_sync" in X_data):
                X_data.pop("pending_sync")
                await self.__firebase.save(X_name, X_data)

    # ===== 캐싱된 정보를 삭제하고, 추가로 삭제된 캐싱 정보에 해당하는 firebase에 있는 문서도 선택적으로 삭제하는 메소드

    # elem.User의 user_id에 해당하는 캐싱된 user 정보를 삭제하고, 추가로 삭제된 user 정보에 해당하는 firebase의 User 컬렉션속 문서도 선택적으로 삭제하는 메소드
    async def delete_user(self, user_id: str, firebase_delete: bool = False)->dict[str, Any]:
        # self.get_user(pop=True)를 사용하여 user_id에 해당하는 캐싱된 user 정보를 pop한뒤 가져온다
        delete_user = self.get_user(user_id, True)
        
        # - firebase_delete가 False인 경우, 그대로 종료한다
        if(firebase_delete == False):
            return
        
        # firebase_delete가 True라는 뜻이기에, pop해온 user 정보의 document_id와 Firebase모듈을 사용하여 firebase에서 문서를 delete 한다
        await self.__firebase.delete_with_document_id("User", delete_user["document_id"])

        return delete_user

    # elem.Subject의 user_id - subject_id에 해당하는 캐싱된 subject 정보를 삭제하고, 추가로 삭제된 subject 정보에 해당하는 firebase의 User 컬렉션속 문서도 선택적으로 삭제하는 메소드
    async def delete_subject(self, user_id: str, subject_id: str, firebase_delete: bool = False)->dict[str, Any]:
        # self.get_subject(pop=True)를 사용하여 user_id - subject_id에 해당하는 캐싱된 subject 정보를 pop한뒤 가져온다
        delete_subject = self.get_subject(user_id, subject_id, True)
        
        # - firebase_delete가 False인 경우, 그대로 종료한다
        if(firebase_delete == False):
            return
        
        # firebase_delete가 True라는 뜻이기에, pop해온 subject 정보의 document_id와 Firebase모듈을 사용하여 firebase에서 문서를 delete 한다
        await self.__firebase.delete_with_document_id("Subject", delete_subject["document_id"])

        return delete_subject

    # elem.Subject의 user_id에 해당하는 캐싱된 모든 subject 정보를 삭제하고, 추가로 삭제된 모든 subject 정보에 해당하는 firebase의 Subject 컬렉션속 문서들도 선택적으로 삭제하는 메소드
    async def delete_subjects(self, user_id: str, firebase_delete: bool = False):
        # self.get_subjects(pop=True)를 사용하여 user_id에 해당하는 캐싱된 모든 subject 정보들을 pop한뒤 가져온다
        delete_subjects = self.get_subjects(user_id, True)
        
        # - firebase_delete가 False인 경우, 그대로 종료한다
        if(firebase_delete == False):
            return
        
        # firebase_delete가 True라는 뜻이기에, pop해온 모든 subject 정보들의 document_id와 Firebase모듈을 사용하여 firebase에서 문서들을 delete 한다
        for delete_subject in delete_subjects:
            await self.__firebase.delete_with_document_id("Subject", delete_subject["document_id"])

        return delete_subjects

    # elem.X의 (user_id, subject_id) - X_id에 해당하는 캐싱된 X 정보를 삭제하고, 추가로 삭제된 X 정보에 해당하는 firebase의 X 컬렉션속 문서도 선택적으로 삭제하는 메소드
    async def delete_X(self, X_name: str, user_id: str, subject_id: str, X_id: str, firebase_delete: bool = False):
        # X_name과 self.get_X(pop=True)를 사용하여 (user_id, subject_id) - X_id에 해당하는 캐싱된 X 정보를 pop한뒤 가져온다
        delete_X = self.get_X(X_name, user_id, subject_id, X_id, True)
        
        # - firebase_delete가 False인 경우, 그대로 종료한다
        if(firebase_delete == False):
            return
        
        # firebase_delete가 True라는 뜻이기에, pop해온 X 정보의 document_id와 Firebase모듈을 사용하여 firebase에서 문서를 delete 한다
        await self.__firebase.delete_with_document_id(X_name, delete_X["document_id"])

        return delete_X

    # elem.X의 (user_id, subject_id)에 해당하는 캐싱된 모든 X 정보를 삭제하고, 추가로 삭제된 모든 X 정보에 해당하는 firebase의 X 컬렉션속 문서들도 선택적으로 삭제하는 메소드
    async def delete_Xs(self, X_name: str, user_id: str, subject_id: str, firebase_delete: bool = False):
        # X_name과 self.get_Xs(pop=True)를 사용하여 (user_id, subject_id)에 해당하는 캐싱된 모든 X 정보를 pop한뒤 가져온다
        delete_Xs = self.get_Xs(X_name, user_id, subject_id, True)
        
        # - firebase_delete가 False인 경우, 그대로 종료한다
        if(firebase_delete == False):
            return
        
        # firebase_delete가 True라는 뜻이기에, pop해온 모든 X 정보들의 document_id와 Firebase모듈을 사용하여 firebase에서 문서들을 delete 한다
        for delete_X in delete_Xs:
            await self.__firebase.delete_with_document_id(X_name, delete_X["document_id"])

        return delete_X

    # ===== 프로그램 내부에서 새롭게 생성된 정보를 firebase에 생성한뒤, 그대로 다시 가져와(document_id를 얻기 위함) 추가 캐싱을 수행하는 메소드

    # 프로그램 내부에서 새롭게 생성된 user 정보를 firebase에 생성한뒤, 그대로 다시 가져와 elem.User에 추가 캐싱을 수행하는 메소드
    async def create_user(self, user_data: dict[str, any]):
        # user_data를 Firebase모듈을 사용하여 firebase.User에 create한다
        await self.__firebase.create("User", user_data)

        # Firebase 모듈을 사용하여 firebase.User에서, "user_id"요소가 user_data속 user_id인 문서를 가져온다(document_id를 얻기 위함이며, 가져온 문서는 무조건 1개만 존재한다)
        user_data_from_firebase = await self.__firebase.load(
            "User", {"user_id": user_data["user_id"]}
        )

        # firebase.User에서 가져온 user문서를 self.__chache_user()를 사용하여 캐싱한뒤 종료한다
        self.__chache_user(user_data_from_firebase[0])

    # 프로그램 내부에서 새롭게 생성된 subejct 정보를 firebase에 생성한뒤, 그대로 다시 가져와 elem.Subject에 추가 캐싱을 수행하는 메소드
    async def create_subject(self, subject_data: dict[str, any]):
        # subject_data를 Firebase모듈을 사용하여 firebase.Subject에 create한다
        await self.__firebase.create("Subject", subject_data)

        # Firebase 모듈을 사용하여 firebase.Subject에서, "owner_user_id"요소가, subject_data속 owner_user_id이면서,
        #   "subject_id"요소가 subject_data속 subject_id인 문서를 가져온다(document_id를 얻기 위함이며, 가져온 문서는 무조건 1개만 존재한다)
        subject_data_from_firebase = await self.__firebase.load(
            "Subject",
            {
                "owner_user_id": subject_data["owner_user_id"],
                "subject_id": subject_data["subject_id"],
            },
        )

        # firebase.Subject에서 가져온 subject문서를 self.__chache_subject()를 사용하여 캐싱한뒤 종료한다
        self.__chache_subject(subject_data_from_firebase[0])

    # 프로그램 내부에서 새롭게 X 정보를 firebase에 생성한뒤, 그대로 다시 가져와 elem.X에 추가 캐싱을 수행하는 메소드
    async def create_X(self, X_name: str, X_data: dict[str, any]):
        # X_name이 ALL_X_ELEMS안에 없는 대상이면 에러를 발생시킨다
        self.__is_X_name_contains(X_name)

        # X_data를 Firebase 모듈을 사용하여 firebase.X_name에 create한다
        await self.__firebase.create(X_name, X_data)

        # Firebase 모듈을 사용하여 firebase.X_name에서, "owner_user_id"요소가, X_data속 owner_user_id이면서,
        #   "{X_name.lower()}_id"요소가 X_data속 {X_name.lower()}인 문서를 가져온다(document_id를 얻기 위함이며, 가져온 문서는 무조건 1개만 존재한다)
        X_id: str = f"{X_name.lower()}_id"
        X_data_from_firebase = await self.__firebase.load(
            X_name, {"owner_user_id": X_data["owner_user_id"], X_id: X_data[X_id]}
        )

        # firebase.X_name에서 가져온 X_name문서를 self.__chache_X()를 사용하여 캐싱한뒤 종료한다
        self.__chache_X(X_name, X_data_from_firebase[0])

    # ===== 테스트용 기능
    def recursion_get_elems(self, data: dict[str, any] | str, level=0):
        string = ""

        for k in data.keys():
            v = data[k]

            if isinstance(v, dict):
                string += (
                    ("-" * level)
                    + str(k)
                    + ":"
                    + "\n"
                    + self.recursion_get_elems(v, level + 1)
                    + "\n"
                )
            else:
                string += ("-" * level) + str(k) + ":" + str(v) + "\n"

        return string

    def PRINT_ELEMS(self, X_name: str):
        elems = self.__elems.get(X_name, self.__elems)

        string = self.recursion_get_elems(elems)

        return string

# ===== TEST CODE

import asyncio

def get_firebase_chacher():
    return FirebaseChacher(Firebase("AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json"))

async def Test_user_create():
    fc = get_firebase_chacher()

    await fc.create_user(
        {
            "user_id": "user-1",  # firebase auth의 UID 사용
            "owned_subject_id": ["subject-1", "subject-2"],
        }
    )

    print(fc.PRINT_ELEMS("User"))

async def Test_subject_create():
    fc = get_firebase_chacher()

    await fc.create_subject(
        {
            "owner_user_id": "user-1",
            "subject_id": "subject-1",
        }
    )

    await fc.create_subject(
        {
            "owner_user_id": "user-1",
            "subject_id": "subject-2",
        }
    )

    await fc.create_subject(
            {
                "owner_user_id": "user-1",
                "subject_id": "subject-3",
            }
        )

    await fc.create_subject(
        {
            "owner_user_id": "user-2",
            "subject_id": "subject-1",
        }
    )

    print(fc.PRINT_ELEMS("Subject"))

async def Test_X_create():
    fc = get_firebase_chacher()

    X_name = "Summary"

    x_id = f"{X_name.lower()}_id"

    await fc.create_X(
        X_name,
        {"owner_user_id": "user-1", "owner_subject_id": "subject-1", x_id: "summary-1"},
    )

    await fc.create_X(
        X_name,
        {"owner_user_id": "user-1", "owner_subject_id": "subject-1", x_id: "summary-2"},
    )

    await fc.create_X(
            X_name,
            {"owner_user_id": "user-1", "owner_subject_id": "subject-2", x_id: "summary-1"},
        )

    print(X_name, "=", fc.PRINT_ELEMS(X_name))

    X_name = "Problem"

    x_id = f"{X_name.lower()}_id"

    await fc.create_X(
        X_name,
        {"owner_user_id": "user-1", "owner_subject_id": "subject-1", x_id: "problem-1"},
    )

    await fc.create_X(
        X_name,
        {"owner_user_id": "user-1", "owner_subject_id": "subject-1", x_id: "problem-2"},
    )

    print(X_name, "=", fc.PRINT_ELEMS(X_name))

async def Test_init_user():
    fc = get_firebase_chacher()

    print("user1 init : ", await fc.init_user("user-1"))
    print("user1 init : ", await fc.init_user("user-1"))
    print("user2 init : ", await fc.init_user("user-2"))

    print(fc.PRINT_ELEMS("User"))

async def Test_init_subject():
    fc = get_firebase_chacher()

    print("user1 subject init : ", await fc.init_subjects("user-1"))
    print("user1 subject init : ", await fc.init_subjects("user-1"))
    print("user2 subject init : ", await fc.init_subjects("user-3"))

    print(fc.PRINT_ELEMS("Subject"))

async def Test_init_X():
    fc = get_firebase_chacher()

    X_name = "Summary"

    print(f"user1, {X_name}1 : ", await fc.init_Xs(X_name, "user-1", "subject-1"))
    print(f"user2, {X_name}1 : ", await fc.init_Xs(X_name, "user-2", "subject-1"))

    print(fc.PRINT_ELEMS("Summary"))

async def Test_get_user_data():
    fc = get_firebase_chacher()

    await fc.init_user("user-1")
    print("user-1 seek : ", fc.get_user("user-1"))
    print("after seek : ", fc.PRINT_ELEMS("User"))
    print("user-1 pop : ", fc.get_user("user-1", True))
    print("after pop : ", fc.PRINT_ELEMS("User"))

    print("all : ", fc.PRINT_ELEMS("ALL"))

async def Test_get_subject_data():
    fc = get_firebase_chacher()

    await fc.init_Xs("Summary", "user-1", "subject-1")
    print("user-1 subject-1 seek : ", fc.get_subject("user-1", "subject-1"))
    print("after seek : ", fc.PRINT_ELEMS("Subject"))
    print("user-1 subject-1 pop : ", fc.get_subject("user-1", "subject-1", True))
    print("user-1 subject-1 pop : ", fc.get_subject("user-1", "subject-2", True))
    print("after pop : ", fc.PRINT_ELEMS("Subject"))

    print("all : ", fc.PRINT_ELEMS("ALL"))

async def Test_get_subjects_data():
    fc = get_firebase_chacher()

    await fc.init_subjects("user-1")
    print("user-1 subjects seek : ", fc.get_subjects("user-1"))
    print("after seek : ", fc.PRINT_ELEMS("Subject"))
    print("user-1 subjects pop : ", fc.get_subjects("user-1", True))
    print("after pop : ", fc.PRINT_ELEMS("Subject"))

    print("all : ", fc.PRINT_ELEMS("ALL"))

async def Test_get_X_data():
    fc = get_firebase_chacher()

    await fc.init_Xs("Summary", "user-1", "subject-1")
    print(
        "user-1 subject-1 summary-1 seek : ",
        fc.get_X("Summary", "user-1", "subject-1", "summary-1"),
    )
    print("after seek : ", fc.PRINT_ELEMS("Summary"))
    print(
        "user-1 subject-1 summary-1 pop : ",
        fc.get_X("Summary", "user-1", "subject-1", "summary-1", True),
    )
    print(
        "user-1 subject-1 summary-1 pop : ",
        fc.get_X("Summary", "user-1", "subject-1", "summary-2", True),
    )
    print("after pop : ", fc.PRINT_ELEMS("Summary"))

    print("all : ", fc.PRINT_ELEMS("ALL"))

async def Test_get_Xs_data():
    fc = get_firebase_chacher()

    await fc.init_Xs("Summary", "user-1", "subject-1")
    print(
        "user-1 subject-1 summaries seek : ",
        fc.get_Xs("Summary", "user-1", "subject-1"),
    )
    print("after seek : ", fc.PRINT_ELEMS("Summary"))
    print("user-1 subjects pop : ", fc.get_Xs("Summary", "user-1", "subject-1", True))
    print("after pop : ", fc.PRINT_ELEMS("Summary"))

    print("all : ", fc.PRINT_ELEMS("ALL"))

async def Test_user_to_firebase():
    fc = get_firebase_chacher()

    await fc.init_user("user-1")
    user_data = fc.get_user("user-1")
    user_data["pending_sync"] = None
    user_data["test_key1"] = "test data1"
    await fc.user_to_firebase("user-1")

    print(fc.PRINT_ELEMS("User"))

async def Test_subject_to_firebase():
    fc = get_firebase_chacher()

    await fc.init_subjects("user-1")
    subject_datas = fc.get_subjects("user-1")
    subject_data = subject_datas[0]
    subject_data["pending_sync"] = None
    subject_data["test_key1"] = "test subject data1"
    await fc.subjects_to_firebase("user-1")

    print(fc.PRINT_ELEMS("Subject"))

async def Test_X_to_firebase():
    fc = get_firebase_chacher()

    await fc.init_Xs("Summary", "user-1", "subject-1")
    X_datas = fc.get_Xs("Summary", "user-1", "subject-1")
    X_data = X_datas[0]
    X_data["pending_sync"] = None
    X_data["test_key1"] = "test summary data1"
    await fc.Xs_to_firebase("Summary", "user-1", "subject-1")

    print(fc.PRINT_ELEMS("Summary"))

async def Test_delete_user():
    fc = get_firebase_chacher()

    await fc.init_user("user-1")
    print(fc.PRINT_ELEMS("ALL"))
    await fc.delete_user("user-1", True)
    print(fc.PRINT_ELEMS("ALL"))

async def Test_delete_subject():
    fc = get_firebase_chacher()

    await fc.init_subjects("user-1")
    print(fc.PRINT_ELEMS("ALL"))
    await fc.delete_subject("user-1", "subject-1", True)
    print(fc.PRINT_ELEMS("ALL"))

async def Test_delete_subjects():
    fc = get_firebase_chacher()
    
    await fc.init_subjects("user-1")
    print(fc.PRINT_ELEMS("ALL"))
    await fc.delete_subjects("user-1", True)
    print(fc.PRINT_ELEMS("ALL"))

async def Test_delete_X():
    fc = get_firebase_chacher()

    await fc.init_Xs("Summary", "user-1", "subject-2")
    print(fc.PRINT_ELEMS("ALL"))
    await fc.delete_X("Summary", "user-1", "subject-2", "summary-1", True)
    print(fc.PRINT_ELEMS("ALL"))

async def Test_delete_Xs():
    fc = get_firebase_chacher()
    
    await fc.init_Xs("Summary", "user-1", "subject-1")
    print(fc.PRINT_ELEMS("ALL"))
    await fc.delete_Xs("Summary", "user-1", "subject-1", True)
    print(fc.PRINT_ELEMS("ALL"))

if __name__ == "__main__":
    asyncio.run(Test_init_user())

