from firebase_admin import firestore_async

from utils import get_or_initialize_firebase_app

class Firebase:
    def __init__(
        self,
        firebase_service_account_key_json: str
    ):
        # 기존 App이 있으면 가져오고,
        # 없으면 새로 초기화
        self.app = get_or_initialize_firebase_app(
            firebase_service_account_key_json
        )

        # 비동기 Firestore 연결
        self.db = firestore_async.client(
            app=self.app
        )

    # 전달된 collection에 data를 저장한 문서를 새롭게 생성합니다.
    async def create(self, collection: str, data: dict[str, any]):
        '''
        collection -> Firebase에서 생성을 수행할 컬렉션의 이름
        data -> 새롭게 생성할 문서의 내용

        새로운 데이터가 아닌 Firebase에서 가져온 데이터라면
        save를 사용합니다.
        '''

        if "document_id" in data:
            raise ValueError(
                "data is considered to be after load from firebase, "
                "use save method"
            )

        await self.db.collection(collection).add(data)

    # 전달된 collection의 document_id의 이름을 가진 문서를 data로 덮어씁니다.
    async def save(
        self,
        collection: str,
        data: dict[str, any]
        ):
        from copy import copy
        
        '''
        collection -> Firebase에서 저장할 컬렉션의 이름
        document_id -> 저장할 문서의 ID
        data -> 해당 문서에 저장할 내용
        '''

        if("document_id" not in data):
            raise ValueError(
                "new data cannot save to firebase, "
                "use create method"
                )

        data_copy = copy(data)

        document_id = data_copy.pop("document_id")

        await (
            self.db
            .collection(collection)
            .document(document_id)
            .set(data_copy)
        )

    # 전달된 collection의 모든 문서들 중
    # id_and_filter를 만족하는 모든 문서를 가져옵니다.
    async def load(
        self,
        collection: str,
        id_and_filter: dict[str, str]
    ) -> list[dict[str, any]]:
        '''
        collection -> Firebase에서 읽을 컬렉션의 이름
        id_and_filter -> 가져올 문서에 대한 조건

        전달된 모든 조건은 AND로 연결됩니다.
        '''

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

    # 전달된 collection속 해당되는 document_id를 가진 문서를 삭제합니다.
    async def delete(
        self,
        collection: str,
        document_id: str
    ):
        await (
            self.db
            .collection(collection)
            .document(document_id)
            .delete()
        )

# ===== TEST CODE

import asyncio

async def test():
    firebase = Firebase("amadda-68958-firebase-adminsdk-fbsvc-95a163b81f.json")

    await firebase.create("Subject-test", {
        "ownerUserId":"user-1",
        "subjectId":"subject-1",
        "ownedTableOfContentIds":["tableOfContent-1", "tableOfContent-2"],

        "subjectNumber":1,
        "subjectName":"the subject1"
    })

    await firebase.create("Subject-test", {
            "ownerUserId":"user-1",
            "subjectId":"subject-2",
            "ownedTableOfContentIds":["tableOfContent-4", "tableOfContent-5"],
    
            "subjectNumber":2,
            "subjectName":"the subject2"
    })

    user1_subjects = await firebase.load("Subject-test", {"ownerUserId":"user-1"})
    user2_subjects = await firebase.load("Subject-test", {"ownerUserId":"user-2"})

    print("user1 subjects = ", user1_subjects)
    print("user2 subjects = ", user2_subjects)

    user1_subjects[0]["ownedTableOfContentIds"].append("tableOfContent-6")

    await firebase.save("Subject-test", user1_subjects[0])

    await firebase.delete("Subject-test", user1_subjects[0]["document_id"])
    await firebase.delete("Subject-test", user1_subjects[1]["document_id"])

async def Test_delete():
    firebase = Firebase("amadda-68958-firebase-adminsdk-fbsvc-95a163b81f.json")

    await firebase.delete("User", "K9eQ8tkQEvG31KKUV0Mc")

if(__name__ == "__main__"):
    asyncio.run(test())

