
import asyncio
import inspect
from pathlib import Path
from typing import Any
from uuid import uuid4

import fastapi

from my_firebase import Firebase
from firebase_chacher import FirebaseChacher
from amadda_element_manager import AmaddaElementManager
from lecture_material_text_extracter import LectureMaterialTextExtracter
from my_llmwiki import LLMWiki


class AmaddaLLMWikiController:
    def __init__(
        self,
        amadda_element_manager: AmaddaElementManager,
        lecture_material_text_extracter: LectureMaterialTextExtracter,
    ):
        self.__amadda_element_manager = amadda_element_manager
        self.__lecture_material_text_extracter = (
            lecture_material_text_extracter
        )

        # 사용자별, 과목별 임시 상태
        self.__uploaded_lecture_materials: dict[
            str, dict[str, dict[str, Any]]
        ] = { # <<임시적인 파일이므로 나중에 {}로 초기화 해야함>>
            "user-1":{
                "subject-1":{
                    "now_uploading_count":0,
                    "now_summarized":False,
                    "extracted_text_contents":[]
                }
            }
        }

        # 동일 과목의 업로드와 요약이 겹치지 않도록 하는 잠금
        # 단, 이 잠금은 현재 컨트롤러 인스턴스 및 프로세스 내부에서만 유효
        self.__subject_locks: dict[tuple[str, str], asyncio.Lock] = {}

    def __get_subject_lock(
        self, user_id: str, subject_id: str
    ) -> asyncio.Lock:
        key = (user_id, subject_id)

        if key not in self.__subject_locks:
            self.__subject_locks[key] = asyncio.Lock()

        return self.__subject_locks[key]

    def __get_subject_state(
        self, user_id: str, subject_id: str
    ) -> dict[str, Any]:
        try:
            return self.__uploaded_lecture_materials[user_id][subject_id]
        except KeyError as e:
            raise ValueError(
                "사용자 또는 과목에 대한 업로드 상태가 존재하지 않습니다."
            ) from e

    def __initialize_subject_state(
        self, user_id: str, subject_id: str
    ) -> dict[str, Any]:
        user_state = self.__uploaded_lecture_materials.setdefault(
            user_id, {}
        )

        return user_state.setdefault(
            subject_id,
            {
                "now_uploading_count": 0,
                "now_summarized": False,
                "extracted_text_contents": [],
            },
        )

    async def __extract_text(
        self,
        file_type: str,
        file: fastapi.UploadFile,
    ) -> dict[str, Any]:
        """UploadFile을 bytes로 읽은 뒤 텍스트를 추출합니다."""

        extract_methods = {
            "mp3": self.__lecture_material_text_extracter.extract_text_from_mp3,
            "mp4": self.__lecture_material_text_extracter.extract_text_from_mp4,
            "pdf": self.__lecture_material_text_extracter.extract_text_from_pdf,
        }

        if file_type not in extract_methods:
            raise ValueError(
                f"지원하지 않는 파일 형식입니다: {file_type}"
            )

        # FastAPI UploadFile은 비동기 인터페이스로 읽습니다.
        file_bytes = await file.read()

        if not file_bytes:
            raise ValueError("업로드된 파일이 비어 있습니다.")

        method = extract_methods[file_type]

        # PDF OCR, FFmpeg 실행, Gemini API 호출 등은 동기 작업이므로
        # 별도 스레드에서 실행해 이벤트 루프의 블로킹을 줄입니다.
        result = await asyncio.to_thread(method, file_bytes)

        if not isinstance(result, dict):
            raise ValueError("텍스트 추출 결과가 딕셔너리가 아닙니다.")

        if "full_text" not in result:
            raise ValueError(
                "텍스트 추출 결과에 full_text 항목이 없습니다."
            )

        if not isinstance(result["full_text"], str):
            raise ValueError("추출된 full_text가 문자열이 아닙니다.")

        return result

    async def __upload_file_lecture_material(
        self,
        user_id: str,
        subject_id: str,
        file_type: str,
        file: fastapi.UploadFile,
    ) -> None:
        """파일 하나를 처리하고 추출된 텍스트를 임시 상태에 추가합니다."""

        state = self.__get_subject_state(user_id, subject_id)

        try:
            result = await self.__extract_text(file_type, file)
            full_text = result["full_text"]

            # 비어 있지 않은 텍스트만 요약 대기 목록에 추가합니다.
            if full_text.strip():
                state["extracted_text_contents"].append(full_text)
                state["now_summarized"] = False

        finally:
            # 성공, 실패와 관계없이 현재 파일의 카운트를 감소시킵니다.
            state["now_uploading_count"] = max(
                0, state["now_uploading_count"] - 1
            )

    async def upload_file_lecture_materials(
        self,
        user_id: str,
        subject_id: str,
        type_and_files: list[dict[str, Any]],
    ) -> None:
        """
        여러 강의자료 파일을 처리합니다.

        각 항목:
        {
            "type": "mp3" | "mp4" | "pdf",
            "file": fastapi.UploadFile
        }
        """

        # 과목 존재 여부를 확인합니다.
        await self.__amadda_element_manager.get_subject(
            user_id, subject_id
        )

        if not type_and_files:
            return

        # 모든 입력을 먼저 검증하여 잘못된 형식 때문에
        # 업로드 카운트가 잘못 남는 상황을 방지합니다.
        supported_types = {"mp3", "mp4", "pdf"}

        for item in type_and_files:
            if not isinstance(item, dict):
                raise ValueError("각 파일 항목은 딕셔너리여야 합니다.")

            if item.get("type") not in supported_types:
                raise ValueError(
                    f"지원하지 않는 파일 형식입니다: {item.get('type')}"
                )

            if "file" not in item or item["file"] is None:
                raise ValueError("파일 데이터가 없습니다.")

        lock = self.__get_subject_lock(user_id, subject_id)

        async with lock:
            state = self.__initialize_subject_state(
                user_id, subject_id
            )

            state["now_uploading_count"] += len(type_and_files)
            state["now_summarized"] = False

            # 현재 배치에서 아직 시작하지 않은 파일 수를 추적합니다.
            next_index = 0

            try:
                for index, item in enumerate(type_and_files):
                    next_index = index + 1

                    await self.__upload_file_lecture_material(
                        user_id=user_id,
                        subject_id=subject_id,
                        file_type=item["type"],
                        file=item["file"],
                    )

            except Exception:
                # 현재 파일의 카운트는 내부 finally에서 감소합니다.
                # 아직 처리하지 않은 파일들의 카운트도 정리합니다.
                remaining_count = len(type_and_files) - next_index

                state["now_uploading_count"] = max(
                    0,
                    state["now_uploading_count"] - remaining_count,
                )

                raise

    def __upload_url_lecture_material(
        self, user_id: str, subject_id: str, url: str
    ) -> None:
        """URL을 통한 강의자료 업로드: 추후 구현 예정."""
        pass

    def upload_url_lecture_materials(self, user_id:str, subject_id:str, urls:list[str])->list[str]:
        '''
        임이의 사용자의 임이의 과목에 urls에 있는 강의자료를 업로드 하는 기능
        urls들 중에서 업로드에 실패한 url들은 그대로 반환합니다
        '''
        pass

    def is_now_uploading_lecture_material(
        self, user_id: str, subject_id: str
    ) -> bool:
        """현재 파일 처리 중인지 확인합니다."""

        state = self.__get_subject_state(user_id, subject_id)

        return state["now_uploading_count"] > 0

    async def summarize_uploaded_lecture_materials(
        self, user_id: str, subject_id: str
    ) -> None:
        """대기 중인 텍스트를 요약하고 Firebase에 저장합니다."""

        lock = self.__get_subject_lock(user_id, subject_id)

        async with lock:
            state = self.__get_subject_state(user_id, subject_id)

            if state["now_uploading_count"] > 0:
                raise ValueError(
                    "강의자료 업로드가 진행 중이므로 요약할 수 없습니다."
                )

            pending_texts = list(state["extracted_text_contents"])

            if not pending_texts:
                raise ValueError("요약할 새로운 강의자료가 없습니다.")

            # 잠금을 획득한 상태에서 요약을 시작합니다.
            state["now_summarized"] = False

            try:
                # 위키 문서 조회
                # 캐시에 해당 정보가 없어 ValueError가 발생하면
                # 빈 리스트로 처리합니다.
                try:
                    wiki_documents = (
                        await self.__amadda_element_manager.get_wiki_documents(
                            user_id, subject_id
                        )
                    )
                except ValueError:
                    wiki_documents = []

                # 기존 위키 문서가 없으면 새로 생성
                if not wiki_documents:
                    wiki_document_id = str(uuid4())

                    await self.__amadda_element_manager.create_wiki_document(
                        user_id, subject_id, wiki_document_id
                    )

                    wiki_document = (
                        await self.__amadda_element_manager.get_wiki_document(
                            user_id, subject_id, wiki_document_id
                        )
                    )

                    if not wiki_document:
                        raise RuntimeError(
                            "새 위키 문서를 생성했지만 조회하지 못했습니다."
                        )

                else:
                    # 현재 설계는 과목당 첫 번째 위키 문서를 사용합니다.
                    wiki_document = wiki_documents[0]

                llmwiki = LLMWiki()

                # 기존 요약본을 초기값으로 설정합니다.
                existing_summary = (
                    wiki_document.get("wiki_document_content") or ""
                )
                llmwiki.set_summary(existing_summary)

                # LLMWiki는 동기 함수이므로 일반 호출합니다.
                for extracted_text in pending_texts:
                    llmwiki.summarize_lecture_material(extracted_text)

                summary = llmwiki.get_summary()

                # 요약 결과를 저장합니다.
                await self.__amadda_element_manager.update_wiki_document(
                    user_id,
                    subject_id,
                    wiki_document["wiki_document_id"],
                    {"wiki_document_content": summary},
                )

                # 저장 성공 후에만 대기 텍스트를 제거합니다.
                del state["extracted_text_contents"][:len(pending_texts)]

                state["now_summarized"] = (
                    len(state["extracted_text_contents"]) == 0
                    and state["now_uploading_count"] == 0
                )

            except Exception as e:
                # 실패 시 대기 텍스트를 보존합니다.
                state["now_summarized"] = False

                raise RuntimeError(
                    "강의자료 요약 또는 저장에 실패했습니다."
                ) from e

    def is_lecture_material_summarized(
        self, user_id: str, subject_id: str
    ) -> bool:
        """현재 대기 중인 텍스트가 없고 요약이 완료되었는지 확인합니다."""

        state = self.__get_subject_state(user_id, subject_id)

        return (
            state["now_summarized"]
            and state["now_uploading_count"] == 0
            and len(state["extracted_text_contents"]) == 0
        )

    async def get_all_wiki_documents(
        self, user_id: str, subject_id: str
    ) -> list[dict[str, Any]]:
        """과목에 속한 모든 위키 문서를 반환합니다."""

        return await self.__amadda_element_manager.get_wiki_documents(
            user_id, subject_id
        )

    # 테스트 전용: 내부 상태 확인
    def TEST_GET_UPLOADED_LECTURE_MATERIALS(self):
        return self.__uploaded_lecture_materials

# For Test code

def get_amadda_element_manager():
    firebase = Firebase(
        "AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json"
    )
    firebase_cacher = FirebaseChacher(firebase)

    return AmaddaElementManager(firebase_cacher)

def get_lecture_material_text_extracter():
    return LectureMaterialTextExtracter()

def get_amadda_llm_wiki_controller():
    return AmaddaLLMWikiController(
        get_amadda_element_manager(),
        get_lecture_material_text_extracter(),
    )

# Test code

async def Test_upload_file_lecture_material():
    alwc = get_amadda_llm_wiki_controller()

    file_path = Path("AmaddaBackend/대가야_지식해적단.mp4")

    if not file_path.exists():
        raise FileNotFoundError(file_path)

    # 실제 FastAPI 요청에서는 FastAPI가 UploadFile을 전달합니다.
    # 단독 테스트에서는 파일 객체로 UploadFile을 구성합니다.
    with file_path.open("rb") as f:
        upload_file = fastapi.UploadFile(
            filename=file_path.name,
            file=f,
        )

        await alwc.upload_file_lecture_materials(
            "user-1",
            "subject-1",
            [
                {
                    "type": "mp4",
                    "file": upload_file,
                }
            ],
        )

    print(
        "업로드 중:",
        alwc.is_now_uploading_lecture_material(
            "user-1", "subject-1"
        ),
    )

    print(
        "업로드 상태:",
        alwc.TEST_GET_UPLOADED_LECTURE_MATERIALS(),
    )

async def Test_summarize_uploaded_lecture_materials():
    alwc = get_amadda_llm_wiki_controller()
    await alwc.summarize_uploaded_lecture_materials("user-1", "subject-1")

async def Test_upload_and_summarize_when_existing():
    alwc = get_amadda_llm_wiki_controller()

    # 강의자료 업로드
    file_path = Path("AmaddaBackend/미국_영토_확장_지식해적단.mp3")

    if not file_path.exists():
        raise FileNotFoundError(file_path)

    # 실제 FastAPI 요청에서는 FastAPI가 UploadFile을 전달합니다.
    # 단독 테스트에서는 파일 객체로 UploadFile을 구성합니다.
    with file_path.open("rb") as f:
        upload_file = fastapi.UploadFile(
            filename=file_path.name,
            file=f,
        )

        await alwc.upload_file_lecture_materials(
            "user-1",
            "subject-1",
            [
                {
                    "type": "mp3",
                    "file": upload_file,
                }
            ],
        )

    # 강의자료 요약
    await alwc.summarize_uploaded_lecture_materials("user-1", "subject-1")

async def Test_get_all_wiki_documents():
    alwc = get_amadda_llm_wiki_controller()

    all_wiki_documents:list = await alwc.get_all_wiki_documents("user-1", "subject-1")

    for wiki_document in all_wiki_documents:
        wiki_document["wiki_document_content"] = wiki_document["wiki_document_content"][:100]

    print(len(all_wiki_documents))
    print(all_wiki_documents)

if __name__ == "__main__":
    asyncio.run(Test_get_all_wiki_documents())
    pass

    