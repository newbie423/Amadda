from firebase_admin import firestore_async

from utils import get_or_initialize_firebase_app


class Firebase:
    def __init__(self, firebase_service_account_key_json: str):
        # 기존 App이 있으면 가져오고,
        # 없으면 새로 초기화
        self.app = get_or_initialize_firebase_app(firebase_service_account_key_json)

        # 비동기 Firestore 연결
        self.db = firestore_async.client(app=self.app)

    # 전달된 collection에 data를 저장한 문서를 새롭게 생성합니다.
    async def create(self, collection: str, data: dict[str, any]):
        """
        collection -> Firebase에서 생성을 수행할 컬렉션의 이름
        data -> 새롭게 생성할 문서의 내용

        새로운 데이터가 아닌 Firebase에서 가져온 데이터라면
        save를 사용합니다.
        """

        if "document_id" in data:
            raise ValueError(
                "data is considered to be after load from firebase, use save method"
            )

        await self.db.collection(collection).add(data)

    # 전달된 collection의 document_id의 이름을 가진 문서를 data로 덮어씁니다.
    async def save(self, collection: str, data: dict[str, any]):
        from copy import copy

        """
        collection -> Firebase에서 저장할 컬렉션의 이름
        document_id -> 저장할 문서의 ID
        data -> 해당 문서에 저장할 내용
        """

        if "document_id" not in data:
            raise ValueError("new data cannot save to firebase, " "use create method")

        data_copy = copy(data)

        document_id = data_copy.pop("document_id")

        await self.db.collection(collection).document(document_id).set(data_copy)

    # 전달된 collection의 모든 문서들 중
    # id_and_filter를 만족하는 모든 문서를 가져옵니다.
    async def load(
        self, collection: str, id_and_filter: dict[str, str]
    ) -> list[dict[str, any]]:
        """
        collection -> Firebase에서 읽을 컬렉션의 이름
        id_and_filter -> 가져올 문서에 대한 조건

        전달된 모든 조건은 AND로 연결됩니다.
        """

        query = self.db.collection(collection)

        # 전달받은 모든 조건을 AND로 연결
        for key, value in id_and_filter.items():
            query = query.where(key, "==", value)

        docs = query.stream()

        result = []

        async for doc in docs:
            data = doc.to_dict()

            # Firestore의 document_id도 함께 반환
            data["document_id"] = doc.id

            result.append(data)

        return result

    '''# 전달된 collection속 해당되는 document_id를 가진 문서를 삭제합니다.
    async def delete_with_document_id(self, collection: str, document_id: str):
        await self.db.collection(collection).document(document_id).delete()'''

    # 전달된 collection의 delete_filter를 만족하는 모든 문서를 삭제합니다
    async def delete_with_filter(
        self,
        collection: str,
        delete_filter: dict[str, any]
    ):
        """
        전달된 collection에서 delete_filter의 모든 조건을 만족하는
        모든 문서를 삭제합니다.

        예:
            collection = "Problem"
            delete_filter = {
                "owner_user_id": "user-1",
                "owner_subject_id": "subject-1"
            }

        위 조건이라면 다음 두 조건을 모두 만족하는
        Problem 컬렉션의 모든 문서를 삭제합니다.

            owner_user_id == "user-1"
            AND
            owner_subject_id == "subject-1"
        """

        query = self.db.collection(collection)

        # delete_filter의 모든 조건을 AND로 연결
        for field, value in delete_filter.items():
            query = query.where(field, "==", value)

        # 조건에 해당하는 문서 조회
        docs = await query.get()

        # 조회된 모든 문서 삭제
        for doc in docs:
            await doc.reference.delete()
        
# ===== TEST CODE

import asyncio

def get_firebase():
    return Firebase(
        "AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json"
    )

async def Test_create():
    firebase = get_firebase()

    await firebase.create("User", {"user_id": "user-1"})
    await firebase.create("User", {"user_id": "user-2"})
    await firebase.create("User", {"user_id": "user-3"})

    await firebase.create(
        "Subject", {"owner_user_id": "user-1", "subject_id": "subject-1"}
    )
    await firebase.create(
        "Subject", {"owner_user_id": "user-1", "subject_id": "subject-2"}
    )

    await firebase.create(
        "Problem",
        {
            "owner_user_id": "user-1",
            "owner_subject_id": "subject-1",
            "problem_id": "problem-1",
        },
    )
    await firebase.create(
        "Problem",
        {
            "owner_user_id": "user-1",
            "owner_subject_id": "subject-1",
            "problem_id": "problem-2",
        },
    )
    await firebase.create(
        "Problem",
        {
            "owner_user_id": "user-1",
            "owner_subject_id": "subject-1",
            "problem_id": "problem-3",
        },
    )

    await firebase.create(
        "UserAnswer",
        {
            "owner_user_id": "user-1",
            "owner_subject_id": "subject-1",
            "user_answer_id": "user_answer-1",
        },
    )
    await firebase.create(
        "UserAnswer",
        {
            "owner_user_id": "user-1",
            "owner_subject_id": "subject-1",
            "user_answer_id": "user_answer-2",
        },
    )

async def Test_delete_with_document_id():
    firebase = get_firebase()

    await firebase.delete_with_document_id("User", "cN8Un0HuPxo7RAFYaB9S")

async def Test_delete_with_filter():
    firebase = get_firebase()

    await firebase.delete_with_filter("User", {"user_id":"user-1"})

    await firebase.delete_with_filter("Subject", {"owner_user_id":"user-1"})

    await firebase.delete_with_filter("Problem", {"owner_user_id":"user-1", "owner_subject_id":"subject-1"})

if __name__ == "__main__":
    asyncio.run(Test_delete_with_filter())
    
