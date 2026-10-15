from typing import Any
import shutil
import os
import subprocess
import stat
import sys
from pathlib import Path
import yaml

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

# LLMBASE_API_KEY를 OPENAI_API_KEY로 연결
if not os.environ.get("OPENAI_API_KEY"):
    key = os.environ.get("LLMBASE_API_KEY")
    if key:
        os.environ["OPENAI_API_KEY"] = key

#print("LLMBASE_API_KEY 설정:", bool(os.getenv("LLMBASE_API_KEY")))
#print("OPENAI_API_KEY 설정:", bool(os.getenv("OPENAI_API_KEY")))

class LLMWIKI:
    def __init__(self):
        # 현재 main.py가
        #
        # Amadda/
        # ├── AmaddaBackend/
        # │   └── main.py
        # └── LLMWikis/
        #
        # 에 있다고 가정

        self.llmwikis_root = (
            Path(__file__).resolve().parent.parent / "LLMWikis"
        )

        self.llmwikis_root.mkdir(
            parents=True,
            exist_ok=True
        )

    def add_subject_llm_wiki_directory(self, user_id: str, subject_id: str):
        """
        특정 사용자의 특정 과목에 해당하는 LLMWiki 폴더를 생성합니다.

        생성되는 구조:

        LLMWikis/
        └── user_id/
            └── subject_id/
                ├── config.yaml
                ├── raw/
                ├── wiki/
                │   └── concepts/
                ├── outputs/
                └── meta/
        """
        
        project_dir = (
            self.llmwikis_root
            / user_id
            / subject_id
        )

        (project_dir / "raw").mkdir(
            parents=True,
            exist_ok=True
        )

        (project_dir / "wiki" / "concepts").mkdir(
            parents=True,
            exist_ok=True
        )

        (project_dir / "outputs").mkdir(
            parents=True,
            exist_ok=True
        )

        (project_dir / "meta").mkdir(
            parents=True,
            exist_ok=True
        )

        config = {
            "paths": {
                "raw": "./raw",
                "wiki": "./wiki",
                "concepts": "./wiki/concepts",
                "outputs": "./outputs",
                "meta": "./meta",
            },
            "llm": {
                "max_tokens": 4096,
            },
        }

        config_path = project_dir / "config.yaml"

        with config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                config,
                f,
                allow_unicode=True,
                sort_keys=False,
            )

        return project_dir

    def __remove_directory(self, path: Path):

        def remove_readonly(func, path, exc):
            os.chmod(path, stat.S_IWRITE)
            func(path)

        shutil.rmtree(
            path,
            onexc=remove_readonly
        )

    def delete_subject_llm_wiki_directory(self, user_id: str, subject_id: str):
        """
        특정 사용자의 특정 과목을 위해 생성했던 llm wiki 폴더를 삭제합니다.
        """

        project_dir = (
            self.llmwikis_root
            / user_id
            / subject_id
        )

        if project_dir.exists():
            self.__remove_directory(project_dir)

    def delete_user_llm_wiki_directory(self, user_id: str):
        """
        특정 사용자를 위해 생성했던 llm wiki 폴더를 삭제합니다
        """

        user_dir = self.llmwikis_root / user_id

        if user_dir.exists():
            self.__remove_directory(user_dir)

    def upload_lecture_material(self, user_id: str, subject_id: str, lecture_material_content: str):
        '''
        user_id와 subject_id에 해당되는 LLMWikis폴더 경로에
        lecture_material_content를 내용으로 하는 markdown파일을 생성하는 메소드
        '''
        #1 f"{self.llmwikis_root}/{user_id}/{subject_id}/raw/"폴더가 없으면 raise "folder not found for upload lecture material"하기, 있다면 아래를 실행
        #2 f"{self.llmwikis_root}/{user_id}/{subject_id}/raw/"폴더에 저장된 markdown폴더들의 개수를 센다(무조건 markdown파일만 존재하기에 예외처리는 필요 없습니다)
        #3 f"{self.llmwikis_root}/{user_id}/{subject_id}/raw/"에 lecture_material_content를 내용으로 삼는 markdown파일을 저장한다,
        #mardown이름은 f"lecture_material_{2번과정에서 센 mk폴더 개수 + 1}"과 같이 지어 기존 mk파일과 이름이 중복되지 않도록 한다(다른 방식을 사용해 주셔도 됩니다)

        raw_dir = (
            self.llmwikis_root
            / user_id
            / subject_id
            / "raw"
        )

        if not raw_dir.is_dir():
            raise FileNotFoundError(
                "folder not found for upload lecture material"
            )

        # 기존 강의자료 폴더 개수를 기준으로 새 번호 결정
        '''material_count = sum(
            1 for path in raw_dir.glob("lecture_material_*")
            if path.is_dir()
        )'''

        from uuid import uuid4

        material_dir = raw_dir / f"{str(uuid4())}"#f"lecture_material_{material_count + 1}"
        material_dir.mkdir()

        material_path = material_dir / "index.md"

        material_path.write_text(
            lecture_material_content,
            encoding="utf-8"
        )

    def summarize_lecture_material(self, user_id: str, subject_id: str):
        """
        해당 사용자의 과목에 저장된 강의자료를
        LLMWiki의 compile_all 기능으로 전체 컴파일합니다.
        """
        project_dir = (
            self.llmwikis_root
            / user_id
            / subject_id
        )

        raw_dir = project_dir / "raw"

        if not raw_dir.is_dir():
            raise FileNotFoundError(
                "folder not found for summarize lecture material"
            )

        # 새 Python 프로세스에서 UTF-8 모드를 활성화한 뒤 컴파일
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"

        script = """
import sys
from pathlib import Path
from llmwiki.compile import compile_all

project_dir = Path(sys.argv[1])
result = compile_all(base_dir=project_dir)

print(result)
"""

        subprocess.run(
            [sys.executable, "-c", script, str(project_dir)],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )

    def delete_lecture_material(self, user_id: str, subject_id: str):
        '''
        특정 사용자의 특정 과목에 해당되는 LLMWiki폴더 경로에 저장된 강의자료 파일들을 삭제하는 메소드(폴더는 삭제하지 않음)
        '''
        #1 f"{self.llmwikis_root}/{user_id}/{subject_id}/raw/"폴더가 없으면 raise "folder not found for delete lecture material"하기, 있다면 아래를 수행
        #2 f"{self.llmwikis_root}/{user_id}/{subject_id}/raw/"폴더에 존재하는 모든 markdown파일을 삭제하기(무조건 mk파일만 있는것이 전제되기에 예외처리는 필요 없습니다)

        raw_dir = (
            self.llmwikis_root
            / user_id
            / subject_id
            / "raw"
        )

        if not raw_dir.is_dir():
            raise FileNotFoundError(
                "folder not found for delete lecture material"
            )

        for path in raw_dir.iterdir():
            if path.is_dir():
                self.__remove_directory(path)
            else:
                path.unlink()

    def get_subject_all_llm_wiki_document_contents(self, user_id: str, subject_id: str) -> list[dict[str, Any]]:
        '''
        특정 사용자의 특정 과목에 해당되는 LLMWiki폴더 경로에 저장된 모든 요약된 llm_wiki_document들의 내용을 텍스트로 추출하여 반환해주는 메소드
        '''
        #1 f"{self.llmwikis_root}/{user_id}/{subject_id}/wiki/concepts/"폴더가 없으면 raise ""하기, 있다면 아래를 실행
        #2 f"{self.llmwikis_root}/{user_id}/{subject_id}/wiki/concepts/"에 존재하는 모든 markdown파일을 대상으로 아래를 실행, 예외처리는 필요없습니다, 무조건 md파일만 있는것이 전제됩니다
        #3 현재 md파일의 내용을 문자열의 형태로 읽어온뒤 아래와 같은 구조로 저장
        

        concepts_dir = (
            self.llmwikis_root
            / user_id
            / subject_id
            / "wiki"
            / "concepts"
        )

        if not concepts_dir.is_dir():
            raise FileNotFoundError(
                "folder not found for get llm wiki documents"
            )

        documents = []

        for md_file in sorted(concepts_dir.glob("*.md")):
            documents.append({
                "owner_user_id": user_id,
                "owner_subject_id": subject_id,
                "wiki_document_id": md_file.stem,
                "wiki_document_content": md_file.read_text(
                    encoding="utf-8"
                ),
            })

        return documents

    def get_subject_llm_wiki_document_content(self, user_id:str, subject_id:str, wiki_document_id:str):
        all_llm_wiki_document_contents = self.get_subject_all_llm_wiki_document_contents(user_id, subject_id)

        for llm_wiki_document_content in all_llm_wiki_document_contents:
            if(wiki_document_id == llm_wiki_document_content["wiki_document_id"]):
                return llm_wiki_document_content

        raise ValueError("wiki_document_id not found")

    def add_llm_wiki_document(self, user_id: str, subject_id: str, wiki_document_id: str, wiki_document_content: str):
        '''
        특정 사용자의 특정 과목에 해당되는 LLMWiki폴더 경로에, wiki_document_id를 파일명으로 하며,
        wiki_document_content를 내용으로 삼는, 위키 문서를 생성하는 메소드
        '''
        #1 f"{self.llmwikis_root}/{user_id}/{subject_id}/wiki/concepts/"폴더가 없으면 raise "folder not found for add llm wiki document" 하기, 있다면 아래를 실행
        #2 f"{self.llmwikis_root}/{user_id}/{subject_id}/wiki/concepts/"에 wiki_document_id를 이름으로 하면서, content를 내용으로 하는 markdown파일을 생성

        concepts_dir = (
            self.llmwikis_root
            / user_id
            / subject_id
            / "wiki"
            / "concepts"
        )

        if not concepts_dir.is_dir():
            raise FileNotFoundError(
                "folder not found for add llm wiki document"
            )

        document_path = concepts_dir / f"{wiki_document_id}.md"

        document_path.write_text(
            wiki_document_content,
            encoding="utf-8"
        )

# Test code

def get_llmwiki():
    return LLMWIKI()

def Test_add_subject_llm_wiki_directory():
    lw = get_llmwiki()

    lw.add_subject_llm_wiki_directory("user-1", "subject-1")
    lw.add_subject_llm_wiki_directory("user-1", "subject-2")
    lw.add_subject_llm_wiki_directory("user-2", "subject-1")

def Test_delete_subject_llm_wiki_directory():
    lw = get_llmwiki()

    lw.delete_subject_llm_wiki_directory("user-1", "subject-1")

def Test_delete_user_llm_wiki_directory():
    lw = get_llmwiki()

    lw.delete_user_llm_wiki_directory("user-1")
    lw.delete_user_llm_wiki_directory("user-2")

def Test_upload_lecture_material():
    lw = get_llmwiki()
    lw.upload_lecture_material("user-1", "subject-1", '''# Python

## 개요
Python은 높은 생산성과 가독성을 중시하는 프로그래밍 언어이다.
네덜란드의 프로그래머 귀도 반 로섬이 1991년도에 개발하고 1994년에 정식 출시한 인터프리터형 프로그래밍 언어.

직관적이고 쉬운 문법과 다양하고 풍부한 라이브러리들을 바탕으로 한 강력한 생태계를 가지고 있어 프로그래밍 교육, 인공지능, 데이터 분석 및 빅데이터, 백엔드, 프론트엔드, 웹 스크래핑 등 다양한 분야에서 사용되며, 이에 힘입어 2024 TIOBE 인덱스 기준 프로그래밍 언어 순위 1위이기도 하다.

실행할 수 있는 의사코드(Executable pseudocode)라고 불릴 정도로 문법이 단순하며 매우 미려하다. 학습 난이도 역시 초보자가 배우기 쉽기에 프로그래밍 입문용으로 많이 추천된다.[2] 앱을 만드는 데는 부적합하지만 시스템 유틸리티나 자동화에는 적합하여 행정 시스템의 문서 정리 등 생산성 및 실무에서 사용률도 높다.

## 특징
- 간결한 문법
- 다양한 라이브러리
- 높은 확장성

## 활용 분야
- 웹 개발
- 데이터 분석
- AI
- 자동화''')
    lw.upload_lecture_material("user-1", "subject-1", '''양자역학(量子力學, quantum mechanics), 또는 양자물리학(量子物理學, quantum physics)은 원자와 이를 이루는 아원자입자 등 미시 세계와, 그러한 계에서 일어나는 현상을 탐구하는 현대물리학의 한 분야이다.

주로 미시 세계에 활용되고 있지만 거시 세계와도 밀접한 관련을 갖고 있다. 현실의 모든 거시적 존재들도 결국은 원자의 결합으로 이루어져 있다는 점에서 봤을 때 거시 세계 또한 미시 세계의 성질에 영향을 받아야 하기 때문이다

게임 엔진(game engine)은 비디오 게임 개발에 필수적인 2D 그래픽 렌더링 엔진, 2D 애니메이션, 3D 그래픽 렌더링, 3D 캐릭터 애니메이션, 물리 엔진, 스크립트 시스템, 메모리 관리 및 스레드 처리, 사운드 엔진, 오디오 인터페이스 시스템, 게임 인공지능 시스템, 네트워크 처리, UI 시스템, 프레임워크와 라이브러리, 에셋, 소스 코드 설계 및 코딩 등 기능들을 제공하는 소프트웨어를 일컫는다. 하드웨어(그래픽 카드)에 직접 접근해야 하는 렌더링 같은 부분은 OpenGL 등을 이용하기도 한다.

태초의 게임 엔진이 나무토막이나 모래상자 수준이었다면 현대의 게임 엔진은 자동차 생산 라인이라고 봐도 무방할 정도로 많은 기능을 제공한다.

시뮬레이션에는 모형 (Model)이 필수적인데, 모형이란 말을 들으면 우리는 실물을 본떠 플라스틱이나 나무로 만들어낸 물건을 연상하며 실제로 그런 실물 모형도 시뮬레이션에 이용되지만, 시뮬레이션에 사용되는 모형 중에는 동물이나 물리적 현상[1], 수식(수학적 모델) 등 다양한 것들이 포함된다. 대표적인 모형의 예는 다음과 같다.
실물 모형: 인체 모형, 건물 모형 등을 이용한 실물 시뮬레이션을 종종 시행한다. 인체 모형으로 가장 유명한 것이 바로 충돌 테스트에 사용하는 크래시 더미(crash dummy, 충돌용 인형)다. 심지어 사람의 시체도 인체 모형으로 이용되는 경우가 있다.(실험용으로 기증받은 시신을 사고 관련 시뮬레이션에 이용) 건물 모형은 대개 군사 분야에서 이용되곤 하는데, 핵실험에서 모형 건물들을 지어놓고 근처에서 핵폭탄을 터뜨려 건물이 어떻게 되는지 관찰하곤 했다.
동물 모형: 약학에서 가장 많이 사용된다. 인간에게 사용할 의약품을 시험할 때, 초기 단계에서는 우선 실험 동물들에게 투여해 각종 독성을 알아보고, 여기서 결과가 양호할 경우 임상시험(인체 실험)을 하겠다고 FDA나 식약처 같은 기관에 신청을 한다. 즉 이런 실험 동물들은 인체의 모형으로 이용되는 것이다. 이러한 모의실험을 위한 동물 모형은 무수히 개발되어 있으며, 특히 특정 유전자를 조작해 인간의 유전적 상태를 모형화한 녹인(knock-in) 마우스나 기니피그 등이 시판되고 있다.
세포 모형: 동물 모형의 일종으로, 동물 전체가 아니라 그 세포만을 모형으로 이용한다. 약학이 발전하며 점점 중요해지고 있는 모형이다. 유명한 세포 모형으로 헬라 세포주(한 여성의 암세포를 배양해 만든 세포 모형), CHO(chinese hamster ovary, 중국비단털쥐 난소) 세포주 등이 있다.
컴퓨터 모형: 오늘날 일반적으로 가장 많이 이용되는 모형이 바로 컴퓨터 모형이다. 컴퓨터의 성능이 엄청나게 발전했기 때문에, 과거 실물이나 동물을 사용해 실시하던 시뮬레이션도 오늘날에는 컴퓨터로 실시하는 것이 가능하다. 이런 컴퓨터 모의실험을 '컴퓨터 시뮬레이션'이라 부르며, 약학이나 의학에서는 컴퓨터 시뮬레이션으로 실시한 시험을 인 실리코(in silico) 시험이라 부른다.[2]
오늘날엔 핵실험도 컴퓨터로 한다. 물론 북한처럼 실물 원자탄으로 핵실험을 하는 나라도 있긴 하지만, 미국은 모든 핵폭탄 실험을 전부 슈퍼컴퓨터를 이용한 시뮬에이션으로 하고 있다. 핵분열 연쇄반응을 나노초 단위로 시뮬레이션하는 것이라 컴퓨터 능력이 엄청나게 좋지 않으면 불가능하다고 한다.

이해를 돕기 위해 예를 들어 보자. 한 과학자가 "태풍의 눈에 원자폭탄을 터뜨리면 태풍을 소멸시킬 수 있을 것이다"라는 가설을 세웠는데, 이 가설을 입증하려면 태풍이 불 때 원자폭탄을 그 중심에서 터뜨려봐야 하겠지만 이는 현실적으로 불가능하다. 따라서 태풍과 원자탄 폭발의 모형을 만들고, 이론상 계산값이나 실제 측정값을 적용해 모의실험 및 그 결과를 관찰한 후 "실제로 해봐도 이런 결과가 나올 것이다"라고 보고하는 것이 일반적이다. 이렇게 모형을 이용한 실험을 모의실험, 시뮬레이션이라 부른다.

시뮬레이션에서 얻어진 결과의 유효성(validity), 즉 정확도는 당연히 그 시뮬레이션에 사용된 모형의 품질에 전적으로 좌우된다. 엉터리 모형을 사용한 시뮬레이션의 결과는 당연히 무의미하다. 실제 현상(태풍 등)이나 시스템(인체 등)을 정확히 모형화하는 것은 매우 어려운 일이다. 어떤 학자가 만들어낸 모형을 이용한 시뮬레이션이 실제 현상/시스템에서 관찰되는 결과와 일치하는 결과를 반복적/일관적으로 도출할 경우, 해당 모형은 학계에서 인정받으며 널리 이용되게 된다. 많은 과학자들이 다양한 실험(사고실험 포함)에서 모형을 검증한 후 '이 모형 진짜 좋다'라고 인정할 경우 학계 표준으로 쓰이게 된다.''')

def Test_summarize_lecture_material():
    lw = get_llmwiki()
    lw.summarize_lecture_material("user-1", "subject-1")

def Test_delete_lecture_material():
    lw = get_llmwiki()
    lw.delete_lecture_material("user-1", "subject-1")

def Test_get_subject_all_llm_wiki_document_content():
    lw = get_llmwiki()
    all_llm_wiki_document_content = lw.get_subject_all_llm_wiki_document_contents("user-1", "subject-1")
    print(all_llm_wiki_document_content)

def Test_get_subject_llm_wiki_document_content():
    lw = get_llmwiki()
    llm_wiki_document_content = lw.get_subject_llm_wiki_document_content("user-1", "subject-1", "simulation")
    print(llm_wiki_document_content)

def Test_add_llm_wiki_document():
    lw = get_llmwiki()
    lw.add_llm_wiki_document("user-1", "subject-1", "python", '''---
created: '2026-10-14T06:59:48.906988+00:00'
sources:
- plugin: unknown
  title: lecture_material_2
  url: ''
summary: 높은 생산성과 뛰어난 가독성을 중시하는 인터프리터형 프로그래밍 언어.
tags:
- 프로그래밍 언어
- 소프트웨어
- 파이썬
title: 파이썬 (Python)
updated: '2026-10-14T06:59:48.906988+00:00'
---

## 한국어

### 개요
[[파이썬]](Python)은 네덜란드의 프로그래머 [[귀도 반 로섬]](Guido van Rossum)이 1991년에 개발하고 1994년에 정식 출시한 인터프리터형 프로그래밍 언어이다. 높은 생산성과 가독성을 핵심 가치로 지향하며, 2024년 TIOBE 인덱스 기준 프로그래밍 언어 순위 1위를 기록하였다.

### 주요 특징
- **간결하고 미려한 문법**: 직관적이고 단순하여 "실행할 수 있는 의사코드(Executable pseudocode)"라고 불릴 만큼 가독성이 높다. 학습 난이도가 낮아 프로그래밍 입문자 교육용으로 적합하다.
- **풍부한 라이브러리와 생태계**: 다양하고 강력한 표준 및 외부 라이브러리 생태계를 갖추고 있다.
- **높은 확장성**: 여러 분야의 도구 및 기술과 쉽게 연계하여 활용할 수 있다.
- **실무 활용성**: 일반적인 애플리케이션(앱) 개발에는 다소 부적합한 측면이 있으나, 시스템 유틸리티 개발, 업무 자동화, 행정 문서 정리 등 생산성 향상과 실무 작업에서 높은 활용률을 보인다.

### 활용 분야
- **[[웹 개발]]**: 백엔드, 프론트엔드, 웹 스크래핑
- **[[데이터 분석]]**: 빅데이터 수집 및 데이터 처리·분석
- **[[인공지능]](AI)**: 머신러닝, 딥러닝 등 최신 인공지능 분야
- **자동화 및 시스템 관리**: 업무 자동화 및 시스템 유틸리티 구현
- **프로그래밍 교육**: 초보자를 위한 소프트웨어 입문 교육''')

if(__name__ == "__main__"):
    Test_summarize_lecture_material()

'''
venv의 llmwiki의 compile.py의

DEFAULT_SECTION_HEADERS와 SYSYEM_PROMPT와 COMPILE_ARTICLE_FORMAT을 아래와 같이 변경해야 한국어로만 위키 문서가 요약됩니다

DEFAULT_SECTION_HEADERS: list[tuple[str, str]] = [
    ("english", "## 한국어"),
    #("english", "## English"),
    #("中文", "## 中文"),
    #("日本語", "## 日本語"),
]

SYSTEM_PROMPT = """You are a knowledge base compiler. Your job is to read raw source documents
and produce structured wiki articles in markdown format.

Rules:
- Write all wiki articles in Korean only.
- Write clear, well-organized articles with proper headings.
- Use [[wiki-link]] syntax for cross-references to other concepts.
- Include a brief summary at the top of each article.
- Categorize content into clear concepts.
- Maintain factual accuracy. Do not invent information not in the source.
- Use backlinks to connect related concepts.
- Output valid markdown with YAML frontmatter.
- Write the title, summary, and article body in Korean.
- Regardless of the source language, summarize and organize the content in Korean.
- Do not create English, Chinese, or Japanese versions of the same article.
- Keep technical terms, proper nouns, and code in their original form when necessary.
- Use a single Korean article for each concept.
- Use the same wiki-link slug consistently across related articles.
"""

# Example article format shown inside the user prompt.
# Override this to change the per-section instructions the LLM sees.
COMPILE_ARTICLE_FORMAT = """## 한국어

한국어로 작성한 위키 문서입니다.
개념을 명확하게 설명하고, 필요한 경우 [[다른 개념]] 형식으로 연결합니다."""

'''

