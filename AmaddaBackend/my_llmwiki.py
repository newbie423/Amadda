import time

import os

from google import genai
from google.genai import errors

from dotenv import load_dotenv
load_dotenv()  # .env 파일 로드

class LLMWiki:
    """강의자료 요약 및 누적 요약본 통합 클래스."""

    MODEL_NAME = "gemini-3.5-flash-lite"

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        # 2. API 키가 없거나 빈 문자열인지 확인
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError(
                "GEMINI_API_KEY 환경 변수가 설정되지 않았거나 유효하지 않습니다."
            )

        # 3. 클라이언트 초기화 및 기본 속성 설정
        self._client = genai.Client(api_key=api_key.strip())
        self._summary = ""

  # -------------------------
    # 내부 Gemini 호출
    # -------------------------
    
    def _generate_text(self, prompt: str) -> str:
        """Gemini 호출 및 일시적인 서버 오류에 대한 재시도."""

        max_attempts = 4

        for attempt in range(max_attempts):
            try:
                response = self._client.models.generate_content(
                    model=self.MODEL_NAME,
                    contents=prompt,
                )

                result = response.text

                if not isinstance(result, str) or not result.strip():
                    raise RuntimeError(
                        "Gemini에서 유효한 텍스트 응답을 받지 못했습니다."
                    )

                return result.strip()

            except errors.ServerError:
                # 마지막 시도라면 오류를 호출자에게 전달한다.
                if attempt == max_attempts - 1:
                    raise

                # 2초, 4초, 8초 순으로 대기한다.
                wait_seconds = 2 ** (attempt + 1)

                '''print(
                    f"Gemini 서버 오류 발생. "
                    f"{wait_seconds}초 후 재시도합니다. "
                    f"({attempt + 1}/{max_attempts})"
                )'''

                time.sleep(wait_seconds)

        raise RuntimeError("Gemini 요청에 실패했습니다.")


    # -------------------------
    # 요약본 관리
    # -------------------------

    def get_summary(self) -> str:
        """현재 누적 요약본을 반환한다."""
        return self._summary

    def set_summary(self, summary: str) -> None:
        """외부에서 전달받은 기존 요약본을 설정한다."""
        if not isinstance(summary, str):
            raise TypeError("요약본은 문자열이어야 합니다.")

        self._summary = summary.strip()

    # -------------------------
    # 강의자료 요약
    # -------------------------

    def __summarize_lecture_material_content(self, lecture_material_content: str) -> str:
        """
        강의자료를 요약하여 반환한다.
        이 메서드만 호출하면 누적 요약본은 변경되지 않는다.
        """
        if not isinstance(lecture_material_content, str):
            raise TypeError("강의자료는 문자열이어야 합니다.")

        content = lecture_material_content.strip()

        if not content:
            raise ValueError("강의자료가 비어 있습니다.")

        prompt = f"""
당신은 강의자료를 정리하는 학습 보조 AI입니다.

다음 자료를 학습에 활용하기 좋은 요약본으로 작성하세요.

[작성 지침]
1. 핵심 개념, 정의, 원리 및 중요한 정보를 보존하세요.
2. 중복되는 설명은 제거하고 논리적으로 정리하세요.
3. 강의 대본, 교과서, 발표자료의 키워드 등
   다양한 입력 형식을 고려하세요.
4. 키워드만 주어진 경우, 근거 없이 세부 내용을 만들어 내지 마세요.
5. 원문에 없는 사실을 임의로 추가하지 마세요.
6. 중요한 용어와 개념 사이의 관계를 명확하게 표현하세요.
7. 불필요한 서론과 반복을 최소화하세요.
8. 한국어로 작성하고, 적절한 제목과 항목을 사용하세요.

[강의자료]
{content}

[요약본]
""".strip()

        return self._generate_text(prompt)

    # -------------------------
    # 요약본 통합
    # -------------------------

    def __integrate_summary(self, new_summary: str) -> str:
        """
        기존 요약본과 새 요약본을 통합한다.
        성공한 경우에만 누적 요약본을 갱신한다.
        """
        if not isinstance(new_summary, str):
            raise TypeError("새 요약본은 문자열이어야 합니다.")

        new_summary = new_summary.strip()

        if not new_summary:
            raise ValueError("통합할 요약본이 비어 있습니다.")

        # 첫 번째 요약본이라면 추가 API 호출 없이 저장한다.
        if not self._summary:
            self._summary = new_summary
            return self._summary

        prompt = f"""
당신은 여러 강의자료의 요약본을 통합하는 AI입니다.

기존 요약본과 새로운 요약본을 하나의 일관된 최종 요약본으로
통합하세요.

[통합 지침]
1. 두 요약본의 핵심 정보와 중요한 세부 내용을 보존하세요.
2. 중복되는 내용은 하나로 합치세요.
3. 새 요약본에만 존재하는 중요한 정보도 반영하세요.
4. 관련 개념은 서로 연결하여 논리적으로 구성하세요.
5. 기존 요약본의 중요한 내용이 새 자료에 없더라도 삭제하지 마세요.
6. 두 자료의 내용이 충돌하면 임의로 한쪽을 선택하지 말고
   차이점을 명시하세요.
7. 근거가 없는 사실을 추가하지 마세요.
8. 한국어로 작성하고 제목과 항목을 적절하게 사용하세요.
9. 최종 통합 요약본만 출력하세요.

[기존 요약본]
{self._summary}

[새로운 요약본]
{new_summary}

[최종 통합 요약본]
""".strip()

        # API 호출이 실패하면 아래 대입문까지 실행되지 않으므로
        # 기존 요약본이 유지된다.
        integrated = self._generate_text(prompt)
        self._summary = integrated

        return self._summary

    # -------------------------
    # 강의자료 처리
    # -------------------------

    def summarize_lecture_material(self, lecture_material_content: str) -> str:
        """강의자료 요약 → 기존 요약본과 통합 → 결과 반환."""
        new_summary = self.__summarize_lecture_material_content(
            lecture_material_content
        )

        return self.__integrate_summary(new_summary)

# Test code

if __name__ == "__main__":
    wiki = LLMWiki()

    # 첫 번째 강의자료:
    # 중복 설명과 여러 개념을 포함
    lecture1 = """
    Python은 문법이 간결하고 코드의 가독성이 높은 프로그래밍 언어이다.
    Python은 읽기 쉬운 코드를 작성할 수 있어 프로그램 개발과 유지보수에 유리하다.

    Python은 웹 개발, 데이터 분석, 인공지능 개발, 업무 자동화 등
    다양한 분야에서 사용된다.
    특히 반복적인 작업을 자동화하는 데 활용할 수 있다.

    데이터 분석에서는 데이터를 정리하고 가공하는 과정이 중요하다.
    pandas는 표 형태의 데이터를 처리하고 분석하는 데 활용되는 라이브러리이다.
    pandas를 사용하면 데이터의 선택, 필터링, 결측값 처리 등을 수행할 수 있다.

    NumPy는 배열과 수치 연산을 효율적으로 처리하기 위한 라이브러리이다.
    NumPy는 대량의 숫자 데이터를 계산하거나 다차원 배열을 다룰 때 유용하다.

    Python은 인공지능 분야에서도 널리 활용된다.
    머신러닝은 데이터를 바탕으로 패턴을 학습하는 방법이다.
    """

    summary1 = wiki.summarize_lecture_material(lecture1)

    print("===== 1차 강의자료 통합 요약본 =====")
    print(summary1)

    # 두 번째 강의자료:
    # 기존 개념을 다른 표현으로 반복하고,
    # 앞서 소개한 개념을 구체화
    lecture2 = """
    Python의 높은 가독성은 간결한 문법과 관련이 있다.
    코드를 이해하기 쉽다는 특성은 여러 개발자가 함께 작업할 때도 도움이 된다.

    데이터 분석 작업에서는 원본 데이터를 정리하고 필요한 정보만 추출해야 한다.
    pandas는 데이터프레임을 이용해 행과 열 단위로 데이터를 관리할 수 있다.
    또한 누락된 값을 확인하거나 조건에 맞는 데이터만 선택할 수 있다.

    NumPy는 다차원 배열을 지원하며, 배열을 이용한 수치 계산을 효율적으로 수행한다.
    따라서 데이터 분석 과정에서 대량의 수치 데이터를 계산할 때 활용할 수 있다.
    pandas와 NumPy는 모두 데이터 처리에 사용되지만, 주요 기능에는 차이가 있다.

    머신러닝은 데이터를 통해 규칙이나 패턴을 학습하는 과정이다.
    학습한 모델은 새로운 데이터에 대한 예측이나 분류에 활용할 수 있다.
    scikit-learn은 Python에서 머신러닝 알고리즘을 적용할 수 있도록 지원하는 라이브러리이다.

    Python은 반복 작업을 자동화하는 데도 활용된다.
    자동화는 사람이 직접 반복하던 작업을 프로그램이 대신 수행하도록 만드는 것이다.
    """

    summary2 = wiki.summarize_lecture_material(lecture2)

    print("\n===== 2차 강의자료 통합 후 최종 요약본 =====")
    print(summary2)

    print("\n===== 최종 누적 요약본 확인 =====")
    print(wiki.get_summary())



