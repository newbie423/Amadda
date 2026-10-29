from typing import Any
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

# 객체 생성 및 공통 설정

app = FastAPI(title="Amadda User Account API")

# 1. 허용할 프론트엔드 도메인(Origin) 목록 설정
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://mae-neung.github.io",  # 🌟 GitHub Pages 도메인 추가 (경로는 제외)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # 등록된 프론트엔드 주소 허용
    allow_credentials=True,      # 로그인 세션/쿠키 사용 시 필수
    allow_methods=["*"],         # OPTIONS, POST 등 모든 메서드 허용
    allow_headers=["*"],         # Content-Type 등 모든 헤더 허용
)

logger = logging.getLogger(__name__)

# 공통 응답 함수


def success_response(message: str, data: Any = None):
    return {"success": True, "message": message, "data": data}


def error_response(error: Exception):
    # 상세한 예외는 서버 로그에 기록
    logger.error(
        "API 요청 처리 중 오류 발생", exc_info=(type(error), error, error.__traceback__)
    )

    message = str(error) or "요청 처리 중 오류가 발생했습니다."

    return JSONResponse(
        status_code=400, content={"success": False, "message": message, "data": None}
    )


# 각종 Amadda관련 객체 생성 및 의존성 주입

from AmaddaBackend.my_firebase import Firebase
from AmaddaBackend.firebase_chacher import FirebaseChacher
from AmaddaBackend.amadda_element_manager import AmaddaElementManager

from AmaddaBackend.firebase_signup_and_login import FirebaseSignUpAndLogin
from AmaddaBackend.lecture_material_text_extracter import LectureMaterialTextExtracter
from AmaddaBackend.problem_generator import ProblemGenerator
from AmaddaBackend.problem_grader import ProblemGrader

from AmaddaBackend.amadda_user_account_controller import AmaddaUserAccountController

from AmaddaBackend.amadda_subject_controller import AmaddaSubjectController
from AmaddaBackend.amadda_llmwiki_controller import AmaddaLLMWikiController
from AmaddaBackend.amadda_problem_controller import AmaddaProblemController

from AmaddaBackend.amadda_grade_controller import AmaddaGradeController

# env load
import os
from dotenv import load_dotenv

ENV_PATH = "AmaddaBackend/.env"
load_dotenv(dotenv_path=ENV_PATH)

# api keys
FIREBASE_KEY_JSON_PATH = (
    "AmaddaBackend/amadda-9d5ca-firebase-adminsdk-fbsvc-ba39acb065.json"
)
FIREBASE_CLIENT_KEY = "AIzaSyAf8UkeGCgVOHm_GluOUewYv7ROPBWH5Ds"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

firebase = Firebase(FIREBASE_KEY_JSON_PATH)
firebase_chacher = FirebaseChacher(firebase)
amadda_element_manager = AmaddaElementManager(firebase_chacher)

firebase_signup_and_login = FirebaseSignUpAndLogin(
    FIREBASE_KEY_JSON_PATH, FIREBASE_CLIENT_KEY
)
lecture_material_text_extracter = LectureMaterialTextExtracter()
problem_generator = ProblemGenerator(GEMINI_API_KEY)
problem_grader = ProblemGrader(GEMINI_API_KEY)

amadda_user_account_controller = AmaddaUserAccountController(
    firebase_signup_and_login=firebase_signup_and_login,
    amadda_element_manager=amadda_element_manager,
)
amadda_subject_controller = AmaddaSubjectController(amadda_element_manager)
amadda_llm_wiki_controller = AmaddaLLMWikiController(
    amadda_element_manager, lecture_material_text_extracter
)
amadda_problem_controller = AmaddaProblemController(
    amadda_element_manager, problem_generator
)
amadda_grade_controller = AmaddaGradeController(
    amadda_element_manager, problem_grader
)

# =========================================================
## AmaddaUserAccountController
# =========================================================


# 회원가입
class SignupRequest(BaseModel):
    email: str
    password: str
    password_check: str


@app.post("/users/signup")
async def user_signup(request: SignupRequest):
    try:
        await amadda_user_account_controller.user_signup(
            email=request.email,
            password=request.password,
            password_check=request.password_check,
        )

        return success_response("회원가입 요청이 완료되었습니다.")

    except Exception as error:
        return error_response(error)


# 1. 로그인

class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/users/login")
async def user_login(request: LoginRequest):
    try:
        user_id = amadda_user_account_controller.user_login(
            email=request.email, password=request.password
        )

        return success_response(
            message="로그인에 성공했습니다.", data={"user_id": user_id}
        )

    except Exception as error:
        return error_response(error)


# 2. 이메일 인증 메시지 재전송


class ResendEmailVerificationRequest(BaseModel):
    email: str


@app.post("/users/resend-email-verification")
async def resend_email_verification(request: ResendEmailVerificationRequest):
    try:
        amadda_user_account_controller.resend_email_verification(email=request.email)

        return success_response("이메일 인증 메시지를 전송했습니다.")

    except Exception as error:
        return error_response(error)


# 3. 로그아웃


class LogoutRequest(BaseModel):
    user_id: str


@app.post("/users/logout")
async def user_logout(request: LogoutRequest):
    try:
        await amadda_user_account_controller.user_logout(user_id=request.user_id)

        return success_response("로그아웃에 성공했습니다.")

    except Exception as error:
        return error_response(error)


# 4. 회원탈퇴


class DeleteUserRequest(BaseModel):
    user_id: str


@app.delete("/users/delete")
async def user_delete(request: DeleteUserRequest):
    try:
        await amadda_user_account_controller.user_delete(user_id=request.user_id)

        return success_response("회원탈퇴가 완료되었습니다.")

    except Exception as error:
        return error_response(error)


# 5. 미인증 계정 삭제


class DeleteUnverifiedUsersRequest(BaseModel):
    elapsed_second: float = 300.0


@app.post("/users/delete-unverified")
async def delete_unvalid_emails_uid(request: DeleteUnverifiedUsersRequest):
    try:
        await amadda_user_account_controller.delete_unvalid_emails_uid(
            elapsed_second=request.elapsed_second
        )

        return success_response("미인증 계정 정리 작업이 완료되었습니다.")

    except Exception as error:
        return error_response(error)


# =========================================================
## AmaddaSubjectController
# =========================================================

from typing import Any
from pydantic import BaseModel


# 1. 사용자의 모든 과목 조회
class GetUserSubjectsRequest(BaseModel):
    user_id: str


@app.post("/subjects/get-all")
async def get_user_subjects(request: GetUserSubjectsRequest):
    try:
        subjects = await amadda_subject_controller.get_user_subjects(
            user_id=request.user_id,
        )

        return success_response(
            "사용자의 전체 과목 조회가 완료되었습니다.",
            data={"subjects": subjects},
        )

    except Exception as error:
        return error_response(error)


# 2. 과목 생성
class CreateSubjectRequest(BaseModel):
    user_id: str


@app.post("/subjects/create")
async def create_subject(request: CreateSubjectRequest):
    try:
        subject = await amadda_subject_controller.create_subject(
            user_id=request.user_id,
        )

        return success_response(
            "과목 생성이 완료되었습니다.",
            data={"subject": subject},
        )

    except Exception as error:
        return error_response(error)


# 3. 과목 정보 수정
class UpdateSubjectRequest(BaseModel):
    user_id: str
    subject_id: str
    new_datas: dict[str, Any]


@app.patch("/subjects/update")
async def update_subject(request: UpdateSubjectRequest):
    try:
        await amadda_subject_controller.update_subject(
            user_id=request.user_id,
            subject_id=request.subject_id,
            new_datas=request.new_datas,
        )

        return success_response(
            "과목 정보 수정이 완료되었습니다.",
        )

    except Exception as error:
        return error_response(error)


# 4. 과목 삭제
class DeleteSubjectRequest(BaseModel):
    user_id: str
    subject_id: str


@app.delete("/subjects/delete")
async def delete_subject(request: DeleteSubjectRequest):
    try:
        await amadda_subject_controller.delete_subject(
            user_id=request.user_id,
            subject_id=request.subject_id,
        )

        return success_response(
            "과목 삭제가 완료되었습니다.",
        )

    except Exception as error:
        return error_response(error)


# =========================================================
## AmaddaLLMWikiController
# =========================================================

from typing import Any

from fastapi import File, Form, UploadFile
from pydantic import BaseModel

# 1. 강의자료 파일 업로드


class UploadLectureMaterialsRequest(BaseModel):
    user_id: str
    subject_id: str


@app.post("/lecture-materials/upload")
async def upload_lecture_materials(
    user_id: str = Form(...),
    subject_id: str = Form(...),
    files: list[UploadFile] = File(...),
    file_types: list[str] = Form(...),
):
    try:
        if len(files) != len(file_types):
            raise ValueError("파일 개수와 파일 형식 개수가 일치하지 않습니다.")

        type_and_files: list[dict[str, Any]] = [
            {
                "type": file_type,
                "file": file,
            }
            for file_type, file in zip(file_types, files)
        ]

        await amadda_llm_wiki_controller.upload_file_lecture_materials(
            user_id=user_id,
            subject_id=subject_id,
            type_and_files=type_and_files,
        )

        return success_response("강의자료 업로드 및 처리가 완료되었습니다.")

    except Exception as error:
        return error_response(error)


# 2. URL을 통한 강의자료 업로드


class UploadLectureMaterialUrlsRequest(BaseModel):
    user_id: str
    subject_id: str
    urls: list[str]


@app.post("/lecture-materials/upload-urls")
async def upload_lecture_material_urls(
    request: UploadLectureMaterialUrlsRequest,
):
    try:
        failed_urls = amadda_llm_wiki_controller.upload_url_lecture_materials(
            user_id=request.user_id,
            subject_id=request.subject_id,
            urls=request.urls,
        )

        return success_response(
            "URL 강의자료 업로드 처리가 완료되었습니다.",
            data={"failed_urls": failed_urls},
        )

    except Exception as error:
        return error_response(error)


# 3. 강의자료 업로드 진행 상태 확인


class IsNowUploadingLectureMaterialRequest(BaseModel):
    user_id: str
    subject_id: str


@app.post("/lecture-materials/is-uploading")
async def is_now_uploading_lecture_material(
    request: IsNowUploadingLectureMaterialRequest,
):
    try:
        is_uploading = amadda_llm_wiki_controller.is_now_uploading_lecture_material(
            user_id=request.user_id,
            subject_id=request.subject_id,
        )

        return success_response(
            "강의자료 업로드 상태를 조회했습니다.",
            data={"is_uploading": is_uploading},
        )

    except Exception as error:
        return error_response(error)


# 4. 업로드한 강의자료 요약


class SummarizeUploadedLectureMaterialsRequest(BaseModel):
    user_id: str
    subject_id: str


@app.post("/lecture-materials/summarize")
async def summarize_uploaded_lecture_materials(
    request: SummarizeUploadedLectureMaterialsRequest,
):
    print(amadda_llm_wiki_controller.TEST_GET_UPLOADED_LECTURE_MATERIALS())

    try:
        await amadda_llm_wiki_controller.summarize_uploaded_lecture_materials(
            user_id=request.user_id,
            subject_id=request.subject_id,
        )

        return success_response("강의자료 요약 및 저장이 완료되었습니다.")

    except Exception as error:
        return error_response(error)


# 5. 강의자료 요약 완료 상태 확인


class IsLectureMaterialSummarizedRequest(BaseModel):
    user_id: str
    subject_id: str


@app.post("/lecture-materials/is-summarized")
async def is_lecture_material_summarized(
    request: IsLectureMaterialSummarizedRequest,
):
    try:
        is_summarized = amadda_llm_wiki_controller.is_lecture_material_summarized(
            user_id=request.user_id,
            subject_id=request.subject_id,
        )

        return success_response(
            "강의자료 요약 상태를 조회했습니다.",
            data={"is_summarized": is_summarized},
        )

    except Exception as error:
        return error_response(error)


# 6. 과목의 전체 위키 문서 조회


class GetAllWikiDocumentsRequest(BaseModel):
    user_id: str
    subject_id: str


@app.post("/wiki-documents/get-all")
async def get_all_wiki_documents(
    request: GetAllWikiDocumentsRequest,
):
    try:
        wiki_documents = await amadda_llm_wiki_controller.get_all_wiki_documents(
            user_id=request.user_id,
            subject_id=request.subject_id,
        )

        return success_response(
            "위키 문서 조회가 완료되었습니다.",
            data={"wiki_documents": wiki_documents},
        )

    except Exception as error:
        return error_response(error)


# =========================================================
## AmaddaProblemController
# =========================================================


from typing import Any

from pydantic import BaseModel

# 1. 문제 생성


class CreateProblemsRequest(BaseModel):
    user_id: str
    subject_id: str
    wiki_document_id: str
    generate_rule: dict[str, Any]


@app.post("/problems/create")
async def create_problems(request: CreateProblemsRequest):
    try:
        await amadda_problem_controller.create_problems(
            user_id=request.user_id,
            subject_id=request.subject_id,
            wiki_document_id=request.wiki_document_id,
            generate_rule=request.generate_rule,
        )

        return success_response("문제 생성이 완료되었습니다.")

    except Exception as error:
        return error_response(error)


# 2. 문제 생성 진행 상태 확인


class IsProblemCreatingRequest(BaseModel):
    user_id: str
    subject_id: str
    wiki_document_id: str


@app.post("/problems/is-creating")
async def is_problem_creating(request: IsProblemCreatingRequest):
    try:
        is_creating = amadda_problem_controller.is_problem_creating(
            user_id=request.user_id,
            subject_id=request.subject_id,
            wiki_document_id=request.wiki_document_id,
        )

        return success_response(
            "문제 생성 상태를 조회했습니다.",
            data={"is_creating": is_creating},
        )

    except Exception as error:
        return error_response(error)


# 3. 전체 문제 조회


class GetAllProblemsRequest(BaseModel):
    user_id: str
    subject_id: str
    wiki_document_id: str


@app.post("/problems/get-all")
async def get_all_problems(request: GetAllProblemsRequest):
    try:
        problems = await amadda_problem_controller.get_all_problems(
            user_id=request.user_id,
            subject_id=request.subject_id,
            wiki_document_id=request.wiki_document_id,
        )

        return success_response(
            "전체 문제 조회가 완료되었습니다.",
            data={"problems": problems},
        )

    except Exception as error:
        return error_response(error)


# 4. 전체 사용자 답변 조회


class GetAllUserAnswersRequest(BaseModel):
    user_id: str
    subject_id: str
    wiki_document_id: str


@app.post("/problems/get-all-user-answers")
async def get_all_user_answers(request: GetAllUserAnswersRequest):
    try:
        user_answers = await amadda_problem_controller.get_all_user_answers(
            user_id=request.user_id,
            subject_id=request.subject_id,
            wiki_document_id=request.wiki_document_id,
        )

        return success_response(
            "전체 사용자 답변 조회가 완료되었습니다.",
            data={"user_answers": user_answers},
        )

    except Exception as error:
        return error_response(error)


# 5. 사용자 답변 수정


class UpdateUserAnswerRequest(BaseModel):
    user_id: str
    subject_id: str
    user_answer_id: str
    new_datas: dict[str, Any]


@app.patch("/problems/user-answers/update")
async def update_user_answer(request: UpdateUserAnswerRequest):
    try:
        await amadda_problem_controller.update_user_answer(
            user_id=request.user_id,
            subject_id=request.subject_id,
            user_answer_id=request.user_answer_id,
            new_datas=request.new_datas,
        )

        return success_response("사용자 답변 수정이 완료되었습니다.")

    except Exception as error:
        return error_response(error)


# 6. 문제 삭제


class DeleteProblemRequest(BaseModel):
    user_id: str
    subject_id: str
    problem_id: str


@app.delete("/problems/delete")
async def delete_problem(request: DeleteProblemRequest):
    try:
        await amadda_problem_controller.delete_problem(
            user_id=request.user_id,
            subject_id=request.subject_id,
            problem_id=request.problem_id,
        )

        return success_response("문제 삭제가 완료되었습니다.")

    except Exception as error:
        return error_response(error)


# =========================================================
## AmaddaGradeController
# =========================================================

# 1. 문제 채점
class GradeProblemRequest(BaseModel):
    user_id: str
    subject_id: str
    wiki_document_id: str


@app.post("/grades/grade")
async def grade_problem(request: GradeProblemRequest):
    try:
        await amadda_grade_controller.grade_problem(
            user_id=request.user_id,
            subject_id=request.subject_id,
            wiki_document_id=request.wiki_document_id,
        )

        return success_response("문제 채점이 완료되었습니다.")

    except Exception as error:
        return error_response(error)


# 2. 문제 채점 진행 상태 확인
class IsProblemGradingRequest(BaseModel):
    user_id: str
    subject_id: str
    wiki_document_id: str


@app.post("/grades/is-grading")
async def is_problem_grading(request: IsProblemGradingRequest):
    try:
        is_grading = amadda_grade_controller.is_problem_grading(
            user_id=request.user_id,
            subject_id=request.subject_id,
            wiki_document_id=request.wiki_document_id,
        )

        return success_response(
            "문제 채점 상태를 조회했습니다.",
            data={"is_grading": is_grading},
        )

    except Exception as error:
        return error_response(error)


# 3. 전체 채점 결과 조회
class GetAllGradesRequest(BaseModel):
    user_id: str
    subject_id: str
    wiki_document_id: str


@app.post("/grades/get-all")
async def get_all_grades(request: GetAllGradesRequest):
    try:
        grades = await amadda_grade_controller.get_all_grades(
            user_id=request.user_id,
            subject_id=request.subject_id,
            wiki_document_id=request.wiki_document_id,
        )

        return success_response(
            "전체 채점 결과 조회가 완료되었습니다.",
            data={"grades": grades},
        )

    except Exception as error:
        return error_response(error)

# =========================================================
# 서버 실행 uvicorn AmaddaBackend.main:app --reload
# =========================================================
@app.get("/")
async def index():
    way = 1
    
    if(way == 1):
        return FileResponse("./AmaddaFrontend/AmaddaUserAccountController.html")
    elif(way == 2):
        return FileResponse("./AmaddaFrontend/AmaddaSubjectController.html")
    elif(way == 3):
        return FileResponse("./AmaddaFrontend/AmaddaLLMWikiController.html")
    elif(way == 4):
        return FileResponse("./AmaddaFrontend/AmaddaProblemController.html")
    elif(way == 5):
        return FileResponse("./AmaddaFrontend/AmaddaGradeController.html")