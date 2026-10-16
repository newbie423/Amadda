import json
from typing import Any

from google import genai
from google.genai import types

import os
from dotenv import load_dotenv


class ProblemGenerator:
    MODEL_NAME = "gemini-3.5-flash-lite"

    PROBLEM_TYPES = {"ox", "select", "short", "long"}
    DIFFICULTIES = {"easy", "medium", "hard"}
    COVERAGE_TYPES = {"balanced", "focused"}

    # Gemini에게 요청할 JSON 응답 구조
    RESPONSE_SCHEMA = {
        "type": "OBJECT",
        "properties": {
            "problems": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "problem_type": {
                            "type": "STRING",
                            "enum": ["ox", "select", "short", "long"],
                        },
                        "problem_question": {"type": "STRING"},
                        "problem_correct_answer": {"type": "STRING"},
                        "problem_options": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                        },
                    },
                    "required": [
                        "problem_type",
                        "problem_question",
                        "problem_correct_answer",
                        "problem_options",
                    ],
                    "propertyOrdering": [
                        "problem_type",
                        "problem_question",
                        "problem_correct_answer",
                        "problem_options",
                    ],
                },
            }
        },
        "required": ["problems"],
        "propertyOrdering": ["problems"],
    }

    def __init__(self):
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "환경변수 GEMINI_API_KEY를 찾을 수 없습니다. "
                ".env 파일을 확인해 주세요."
            )

        self.__client = genai.Client(api_key=api_key)

    def __validate_rule(self, generate_rule: dict[str, Any]) -> None:
        """문제 생성 규칙의 필수 항목과 값을 검증합니다."""

        required_keys = {
            "total_count",
            "problem_type_counts",
            "difficulty",
            "focus_keywords",
            "coverage",
        }

        missing_keys = required_keys - generate_rule.keys()

        if missing_keys:
            raise ValueError(
                f"생성 규칙에 필수 항목이 없습니다: {sorted(missing_keys)}"
            )

        total_count = generate_rule["total_count"]

        if (
            not isinstance(total_count, int)
            or isinstance(total_count, bool)
            or total_count < 1
        ):
            raise ValueError("total_count는 1 이상의 정수여야 합니다.")

        type_counts = generate_rule["problem_type_counts"]

        if not isinstance(type_counts, dict):
            raise ValueError("problem_type_counts는 딕셔너리여야 합니다.")

        if set(type_counts.keys()) != self.PROBLEM_TYPES:
            raise ValueError(
                "problem_type_counts에는 ox, select, short, long "
                "네 가지 유형을 모두 지정해야 합니다."
            )

        for problem_type, count in type_counts.items():
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ValueError(
                    f"{problem_type}의 문제 수는 0 이상의 정수여야 합니다."
                )

        if sum(type_counts.values()) != total_count:
            raise ValueError("유형별 문제 수의 합은 total_count와 같아야 합니다.")

        if generate_rule["difficulty"] not in self.DIFFICULTIES:
            raise ValueError("difficulty는 easy, medium, hard 중 하나여야 합니다.")

        if generate_rule["coverage"] not in self.COVERAGE_TYPES:
            raise ValueError("coverage는 balanced 또는 focused여야 합니다.")

        keywords = generate_rule["focus_keywords"]

        if not isinstance(keywords, list) or not all(
            isinstance(keyword, str) and keyword.strip() for keyword in keywords
        ):
            raise ValueError("focus_keywords는 비어 있거나 문자열 목록이어야 합니다.")

    def __texting_problems_type_and_question(
        self, problem_and_type: list[dict[str, Any]]
    ) -> str:
        return "\n".join(
            f"({problem['problem_type']})/({problem['problem_question']})"
            for problem in problem_and_type
        )

    def __generate_prompt(
        self,
        generate_rule: dict[str, Any],
        wiki_document_content: str,
        existing_problems: list[dict[str, Any]],
    ) -> str:
        """생성 규칙, 강의 요약, 기존 문제를 프롬프트로 구성합니다."""

        type_counts = generate_rule["problem_type_counts"]

        type_names = {
            "ox": "O/X 문제",
            "select": "객관식 문제",
            "short": "단답형 문제",
            "long": "서술형 문제",
        }

        counts_text = "\n".join(
            f"- {type_names[t]}: {type_counts[t]}개"
            for t in ("ox", "select", "short", "long")
        )

        keywords = generate_rule["focus_keywords"]

        if keywords:
            keywords_text = ", ".join(keywords)
        else:
            keywords_text = "지정된 키워드 없음"

        coverage_instructions = {
            "balanced": ("요약에 포함된 여러 주제를 가능한 한 고르게 출제하세요."),
            "focused": (
                "지정된 집중 키워드와 관련된 내용을 우선 출제하세요. "
                "다만 해당 키워드만으로 출제하기 어렵다면 "
                "요약의 관련 내용도 활용하세요."
            ),
        }

        # 기존 문제에서 문제 유형과 질문만 추출
        existing_problems_text = self.__texting_problems_type_and_question(
            existing_problems
        )

        return f"""
당신은 강의자료를 기반으로 학습 평가 문제를 만드는 도우미입니다.

[출제 기준 자료]
아래 자료에 실제로 포함된 정보만 사용하세요.
자료에 없는 사실을 임의로 추가하지 마세요.

<wiki_document>
{wiki_document_content}
</wiki_document>

[생성 규칙]
전체 문제 수: {generate_rule["total_count"]}개

유형별 문제 수:
{counts_text}

전체 난이도: {generate_rule["difficulty"]}
집중 키워드: {keywords_text}

출제 범위:
{coverage_instructions[generate_rule["coverage"]]}

[문제 유형 규칙]
- ox: O/X 문제. 정답은 "O" 또는 "X"로 작성하세요.
  보기 목록은 빈 배열 []로 반환하세요.
- select: 객관식 문제. 보기 4개를 작성하고,
  정답은 보기 중 하나와 정확히 일치하도록 작성하세요.
- short: 단답형 문제. 핵심 정답을 간결하게 작성하세요.
  보기 목록은 빈 배열 []로 반환하세요.
- long: 서술형 문제. 정답에 포함되어야 할 핵심 내용을
  모범 답안 형태로 작성하세요.
  보기 목록은 빈 배열 []로 반환하세요.

[기존 문제]
다음은 이미 출제된 문제 유형과 질문입니다.
가능한 한 질문의 내용과 관점이 겹치지 않도록 새 문제를 만드세요.

{existing_problems_text}

[출력 규칙]
- 요청한 전체 문제 수와 유형별 문제 수를 정확히 지키세요.
- 문제 질문과 정답은 명확하고 이해하기 쉽게 작성하세요.
- 객관식 보기에는 정답이 반드시 하나 포함되어야 합니다.
- 문제마다 정답을 반드시 작성하세요.
- 문제 해설이나 추가 설명은 별도 필드로 만들지 마세요.
- JSON 객체만 반환하세요. Markdown 코드 블록이나 다른 문장은 넣지 마세요.
- 응답은 다음 구조를 따라야 합니다.

{{
  "problems": [
    {{
      "problem_type": "select",
      "problem_question": "문제 질문",
      "problem_correct_answer": "정답",
      "problem_options": ["보기1", "보기2", "보기3", "보기4"]
    }}
  ]
}}
"""

    def __parse_problem_json(
        self, problem_string: str, expected_count: int
    ) -> list[dict[str, Any]]:
        """LLM의 JSON 응답을 파싱하고 기본적인 유효성을 검사합니다."""

        try:
            parsed = json.loads(problem_string)
        except json.JSONDecodeError as exc:
            raise ValueError("Gemini 응답을 JSON으로 파싱할 수 없습니다.") from exc

        if not isinstance(parsed, dict):
            raise ValueError("응답의 최상위 구조는 JSON 객체여야 합니다.")

        problems = parsed.get("problems")

        if not isinstance(problems, list):
            raise ValueError("'problems'는 리스트여야 합니다.")

        if len(problems) != expected_count:
            raise ValueError(
                f"요청한 문제 수는 {expected_count}개이지만 "
                f"{len(problems)}개가 반환되었습니다."
            )

        required_fields = {
            "problem_type",
            "problem_question",
            "problem_correct_answer",
            "problem_options",
        }

        for index, problem in enumerate(problems, start=1):
            if not isinstance(problem, dict):
                raise ValueError(f"{index}번 문제의 형식이 잘못되었습니다.")

            if not required_fields.issubset(problem.keys()):
                raise ValueError(f"{index}번 문제에 필수 필드가 없습니다.")

            problem_type = problem["problem_type"]
            question = problem["problem_question"]
            answer = problem["problem_correct_answer"]
            options = problem["problem_options"]

            if problem_type not in self.PROBLEM_TYPES:
                raise ValueError(f"{index}번 문제의 유형이 올바르지 않습니다.")

            if not isinstance(question, str) or not question.strip():
                raise ValueError(f"{index}번 문제의 질문이 비어 있습니다.")

            if not isinstance(answer, str) or not answer.strip():
                raise ValueError(f"{index}번 문제의 정답이 비어 있습니다.")

            if not isinstance(options, list) or not all(
                isinstance(option, str) for option in options
            ):
                raise ValueError(f"{index}번 문제의 보기 형식이 잘못되었습니다.")

            if problem_type == "select":
                if len(options) != 4:
                    raise ValueError(f"{index}번 객관식 문제는 보기가 4개여야 합니다.")

                if not all(option.strip() for option in options):
                    raise ValueError(f"{index}번 객관식 문제에 빈 보기가 있습니다.")

                if answer not in options:
                    raise ValueError(f"{index}번 문제의 정답이 보기에 없습니다.")

            elif options:
                raise ValueError(
                    f"{index}번 {problem_type} 문제의 보기 목록은 "
                    "빈 배열이어야 합니다."
                )

            if problem_type == "ox" and answer not in {"O", "X"}:
                raise ValueError(f"{index}번 O/X 문제의 정답은 O 또는 X여야 합니다.")

        return [
            {
                "problem_type": problem["problem_type"],
                "problem_question": problem["problem_question"],
                "problem_correct_answer": problem["problem_correct_answer"],
                "problem_options": problem["problem_options"],
            }
            for problem in problems
        ]

    def generate_problem(
        self,
        generate_rule: dict[str, Any],
        wiki_document_content: str,
        existing_problems: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        강의 요약을 기반으로 문제를 생성합니다.
        generate_rule예시
        {
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
        }

        반환 문제 예시:
        [
            {
                "problem_type": "select",
                "problem_question": "대한민국의 수도는?",
                "problem_correct_answer": "서울",
                "problem_options": ["부산", "서울", "대구", "인천"]
            }
        ]
        """

        self.__validate_rule(generate_rule)

        if (
            not isinstance(wiki_document_content, str)
            or not wiki_document_content.strip()
        ):
            raise ValueError("강의 요약 내용이 비어 있습니다.")

        if existing_problems is None:
            existing_problems = []

        if not isinstance(existing_problems, list):
            raise ValueError("기존 문제 목록은 리스트여야 합니다.")

        prompt = self.__generate_prompt(
            generate_rule=generate_rule,
            wiki_document_content=wiki_document_content,
            existing_problems=(existing_problems),
        )

        response = self.__client.models.generate_content(
            model=self.MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=self.RESPONSE_SCHEMA,
                temperature=0.3,
            ),
        )

        if not response.text:
            raise ValueError("Gemini가 빈 응답을 반환했습니다.")

        problems = self.__parse_problem_json(
            problem_string=response.text, expected_count=generate_rule["total_count"]
        )

        # 실제 반환된 유형별 개수도 확인합니다.
        actual_counts = {
            problem_type: sum(
                problem["problem_type"] == problem_type for problem in problems
            )
            for problem_type in self.PROBLEM_TYPES
        }

        if actual_counts != generate_rule["problem_type_counts"]:
            raise ValueError(
                "반환된 유형별 문제 수가 요청한 규칙과 다릅니다. "
                f"요청: {generate_rule['problem_type_counts']}, "
                f"결과: {actual_counts}"
            )

        return problems

# For Test code

def get_problem_generator():
    return ProblemGenerator()

def get_summary():
    return """# 가야의 역사·고고학, 고대 기록 매체 및 미국의 영토 확장과 초강대국 형성 과정 통합 요약

## 1. 가야의 역사와 고고학적 중요성

### ① 개요 및 명칭
* **공식 명칭:** 통일신라시대 대신 **'남북국 시대'** (통일신라와 발해 공존) 사용.
* **사국시대 논란:** 삼국시대(고구려·백제·신라) 중 실제 삼국이었던 시기는 마지막 98년에 불과하며, 그전에는 가야를 포함한 **'사국시대'**로 볼 수 있음. 
* **가야의 성격:** 단일 중앙집권 국가가 아닌, 고대 그리스의 폴리스들처럼 **여러 소국이 합종연행하며 문화적 동질성을 공유한 연맹체(문화권역)**.

### ② 가야의 핵심 특징: 철과 바다
* **철기 문화:** 태백·소백산맥의 양질의 철을 바탕으로 일찍부터 철기 문화 발달 (철제 갑옷, 무기, 제철 유적 출토).
* **해상 무역:** 복잡한 해안선과 다도해의 입지를 활용해 한나라(낙랑군)부터 왜(일본)까지 아우르는 **국제적 철 무역 네트워크** 구축 ("철의 나라, 바다의 나라").
* **문화적 유산:** 전통 악기 **'가야금'**(대가야 가실왕이 우륵에게 지시해 제작)의 기원.

### ③ 가야의 역사적 전개 (두 개의 시즌)
* **시즌 1: 금관가야 (3~4세기 패권국)**
  * **위치:** 낙동강 하구 (당시 김해도 바다였음), 해상국가.
  * **전성기:** 철 무역으로 막대한 부를 축적, 백제 및 왜와 동맹을 맺고 신라의 전신인 사로국을 압박함.
  * **쇠퇴:** 광개토대왕이 이끈 고구려 원군(5만 명)의 개입으로 대패, 낙동강 하구를 신라에 빼앗기며 위상 하락.
  * **결말:** 532년 신라에 항복. 왕족은 진골로 편입 (삼국통일의 명장 김유신이 금관가야 왕족의 후손).
* **시즌 2: 대가야 (5~6세기 패권국)**
  * **위치:** 경북 고령군 일대 (내륙 중심), 이후 섬진강 하구 확보로 해상 무역 재개.
  * **문화:** 가야금 12곡조 제정 등 소국들 간의 문화적 동질성 유지.
  * **멸망:** 백제와 신라의 팽창 속에서 신라와의 동맹 파투 및 백제의 개입(관산성 전투 패배) 등으로 고립. 562년 신라 진흥왕에 의해 멸망.
  * **결말:** 최후까지 저항하여 지배층 강제 이주 및 기록 말살형에 처해짐.

### ④ 가야사 연구의 한계와 고고학적 중요성
* **기록의 부족:** 자체적인 기록이 거의 없어 《삼국사기》, 《삼국유사》, 중국, 일본의 기록에 의존해야 함. 가야사 연구의 90% 이상이 **무덤(고분) 출토 유물**에 의존함.
* **가야고분군 (유네스코 세계유산):** 
  * 2023년 김해, 함안, 합천, 고령, 고성, 남원, 창녕의 7개 고분군이 유네스코 세계유산으로 등재됨.
  * **고령 지산동 고분군:** 대가야 최고 지배층의 무덤으로 700기 이상의 봉분이 산등성이를 따라 조성됨. 
  * **순장 문화:** 지산동 44호분 등에서 대규모 순장(40여 명) 및 피장자에 대한 높은 예우가 확인되어 강력한 왕권을 방증함.
* **일제강점기의 피해:** 임나일본부설 입증을 목적으로 한 일본의 마구잡이 도굴로 다수의 유물이 유출 및 훼손됨. 현재 대가야사 복원을 위한 재발굴 조사(지산동 5호분 등)와 고도(古都) 지정 등 다양한 복원 사업이 진행 중.

---

## 2. 종이 이전 시대, 세계 각지의 고대 기록 매체

인류가 종이를 사용하기 이전, 각 지역의 기후와 환경에 맞춰 발달한 고대 기록 매체의 종류와 특징은 다음과 같습니다.

### ① 중국: 간독과 백서
* **간독 (죽간과 목독):** 대나무(죽간)나 나무(목독)를 쪼개어 만든 길쭉한 조각을 가죽이나 끈으로 엮어 만든 기록 매체. 구하기 쉽고 가공이 쉬워 후한 시대 종이 발명 후에도 500년 이상 사용됨. 틀린 내용은 전용 칼로 긁어내고 재사용 가능하나, 부피가 크고 무거움.
* **백서:** 기록용으로 사용된 비단. 죽간보다 가볍고 크기 조절이 자유로워 천자의 칙서, 외교 문서, 중요 그림 등에 사용되었으나 비용 부담이 큼.

### ② 인도 아대륙 및 동남아시아: 패엽 (패엽경)
* **정의 및 제작:** 종려나무(야자수)의 넓고 두꺼운 잎을 가공하여 만든 기록 매체 (잎 자르기 $\rightarrow$ 건조·압착·삶기 $\rightarrow$ 표면 갈기).
* **작성 방법 및 용도:** 날카로운 철필로 글자를 새긴 뒤 유성 잉크를 발라 닦아냄. 주로 불경(패엽경) 등 종교 경전 및 그림용으로 사용되었으나, 습한 기후와 나뭇잎 재질 특성상 습기, 곰팡이, 해충에 취약하여 현재 남아있는 유물이 적음.

### ③ 메소포타미아: 점토판
* **정의 및 작성:** 티그리스·유프라테스 강가의 진흙을 빚어 만든 기록 매체(수메르인 발명, 기원전 3200년경). 뾰족하게 깎은 갈대로 진흙 위에 글자를 새겨 쐐기 문자가 탄생함.
* **특징:** 재료가 사실상 무한하며 잉크가 불필요하고, 문질러 수정이 가능함. 보존 기한이 무제한에 가까우며, 화재 시 더 단단하게 구워져 보존율이 높음. 신분 보증을 위해 둥근 인장을 굴려 찍음. 단, 무겁고 깨지기 쉬워 장거리 운반에 불리함.

### ④ 이집트: 파피루스
* **정의 및 특징:** 나일강변의 갈대 줄기 속을 잘라 겹쳐 엮고 건조·압착하여 만든 기록 매체. 삼베 같은 결이 있고 두껍고 빳빳하며 두루마리 형태로 사용됨. 지중해 세계의 표준 기록 매체였으나 이집트에서만 독점 생산되어 공급량 변동이 컸음.

### ⑤ 유럽 및 지중해 세계: 양피지
* **정의 및 발달 배경:** 양, 염소, 송아지의 가죽으로 만든 기록 매체. 이집트의 파피루스 수출 통제 대응 및 서유럽의 습한 기후 환경이 결합하여 발달함. 서로마 제국 멸망 후 무역망 붕괴로 대중화됨.
* **특징:** 매우 비싸고 제작이 어렵지만 질기고 오래 보관 가능함. 두루마리가 아닌 오늘날의 책 형태인 **'코덱스(Codex)'** 제작이 가능하여 기독교 성경 필사에 널리 활용됨.

---

## 3. 고대 기록 매체의 의의
* 고대 인류는 **나무(간독/패엽), 진흙(점토판), 갈대(파피루스), 가죽(양피지)** 등 각 지역에서 구하기 쉬운 재료를 활용해 기록 매체를 발전시켰음.
* 이후 제작 단가, 무게, 두께, 내구성, 휴대성 등 대부분의 속성에서 우위를 가진 **종이**의 발명과 제지술의 전파로 인해 기존의 모든 기록 매체는 대체됨.

---

## 4. 미국의 영토 확장과 초강대국 형성 과정

### ① 개요 및 지리적 배경
* **미국의 영토적 우위:** 전 세계 3위의 면적(약 983만 $\text{km}^2$)이나, 온화한 기후, 풍부한 수자원과 자원, 내륙 수운의 용이성, 분리 독립 세력 부재 등 **실질적인 가치 측면에서 세계 1위**의 영토를 보유함.
* **확장 특징:** 동부 13개 식민지에서 시작해 불과 100여 년 만에 대서양, 태평양, 북극해를 아우르는 영토를 평화적 거래와 전쟁 등을 통해 신속하게 완성함.

### ② 미국의 기원: 영국령 13개 식민지 (1776년 이전)
* **타 열강과의 비교:**
  * **에스파냐:** 사막·고산 지대 중심, 원주민 공존 소규모 정착촌, 일확천금 추구.
  * **프랑스:** 북극권 추운 지역 중심, 탐험가·사업가 위주.
  * **영국 13개 식민지:** 온화한 기후와 뛰어난 토질, 청교도 중심의 대규모 가족 단위 자영농 유입으로 영구적 백인 정착지와 강력한 인구·경제 성장 이룩.
* **영국의 억제 정책:** 
  * 7년 전쟁(1763) 승리 후 영토 분쟁을 막기 위해 애팔래치아 산맥 서쪽 정착 금지.
  * 전쟁 재정 충당을 위한 식민지 세금 인상.
  * **결과:** 식민지인의 반발을 불러일으켜 독립의 도화선이 됨.

### ③ 독립과 초기 영토 확장 (1776년 ~ 1810년대)
* **미합중국 건국과 독립 전쟁 (1776~1783):**
  * 1776년 독립 선언 후 8년 간의 전쟁 끝에 승리(1783년 파리 조약).
  * 미시시피 강 동쪽부터 오대호 남쪽까지 영토 확보.
* **루이지애나 매입 (1803년):**
  * 프랑스(나폴레옹)로부터 미시시피 강 서쪽의 거대한 루이지애나 영토를 **단돈 1,500만 달러(1평방 킬로미터당 7달러)**에 매입.
  * **의의:** 역사상 최대 규모의 평화적 영토 거래로 미국 영토가 두 배로 확장됨.
* **미영 전쟁 (1812년):**
  * 무승부로 끝났으나, 연방 차원의 강력한 군사력과 유럽 세력 차단의 필요성을 절감하는 계기가 됨.

### ④ 국경 정리와 대륙 횡단 (1810년대 ~ 1850년대)
* **주요 경계 조정:**
  * **영국과 합의 (1818):** 루이지애나 북쪽 경계를 북위 49도선으로 확정.
  * **에스파냐와 조약 (1819):** 플로리다 반도를 획득하고 서쪽 경계 조정.
  * **러시아와 조약 (1825):** 러시아가 북위 54도 40분 선 이남의 영유권 포기.
  * **오리건 컨트리:** 영국과 공동 통치로 보류.
* **먼로 독트린 (1823):** 신대륙은 미국의 영역이며 유럽은 더 이상 간섭하지 말 것 선언.
* **텍사스 병합과 미국-멕시코 전쟁 (1846~1848):**
  * 멕시코 이민 문제로 독립한 텍사스 공화국이 1845년 미국 연방에 가입.
  * 미국-멕시코 전쟁 승리(1848)로 알타 캘리포니아, 누에보 멕시코 획득 및 리오그란데 강으로 국경 확정.
  * 1853년 개조르다 구매를 통해 소노라 주 북부 평원 추가 확보.
  * **결과:** 북위 49도선 이남, 리오그란데 강 이북의 북아메리카 전 영역(대서양~태평양) 장악.

### ⑤ 남북 전쟁과 알래스카 매입 (1861년 ~ 1867년)
* **남북 전쟁 (1861~1865):**
  * 산업 중심의 북부와 노예제 중심의 남부 간의 갈등으로 발발.
  * 북부의 승리로 연방 재통일 및 분리될 수 없는 강력한 단일 국가로 확립.
* **알래스카 매입 (1867년):**
  * 영국을 견제하고 완충지를 확보하려는 러시아 제국의 제안으로 **720만 달러**에 매입.
  * **의의:** 대서양·태평양에 이어 북극해까지 세력권을 넓히고 영국의 팽창을 저지함.

### ⑥ 요약된 영토별 핵심 경제·전략적 역할
* **오대호 연안 (독립 당시 획득):** 미국의 산업화와 번영을 이끈 공업 지대.
* **루이지애나 (프랑스로부터 매입):** 식량을 책임지는 곡창 지대 및 수운 교통로.
* **서남부 영토 (멕시코로부터 획득):** 자원과 첨단 산업의 중심지.
* **알래스카 (러시아로부터 매입):** 자원 창고이자 북극해 전진 기지."""

# Test code

def Test_generate_problem():
    pg = get_problem_generator()
    summary = get_summary()

    generate_rule = {
        "total_count": 10,
        "problem_type_counts": {"ox": 2, "select": 4, "short": 3, "long": 1},
        "difficulty": "medium",
        "focus_keywords": ["가야", "고대 기록 매체", "미국의 영토 확장"],
        "coverage": "balanced",
    }

    existing_problems = [
    {
        "problem_type": "ox",
        "problem_question": "금관가야는 3~4세기에 철 무역으로 막대한 부를 축적하며 패권국으로 자리 잡았다.",
        "problem_correct_answer": "O",
        "problem_options": [],
    },
    {
        "problem_type": "ox",
        "problem_question": "메소포타미아의 점토판은 종이 발명 전 사용된 기록 매체 중 무겁고 깨지기 쉬워 장거리 운반에 매우 유리했다.",
        "problem_correct_answer": "X",
        "problem_options": [],
    },
    {
        "problem_type": "select",
        "problem_question": "대가야의 최후와 관련이 없는 역사적 사실은 무엇인가?",
        "problem_correct_answer": "광개토대왕이 이끈 고구려 원군의 개입으로 멸망하였다.",
        "problem_options": [
            "경북 고령군 일대를 중심으로 발전하였다.",
            "광개토대왕이 이끈 고구려 원군의 개입으로 멸망하였다.",
            "가야금 12곡조를 제정하는 등 문화적 동질성을 유지하였다.",
            "562년 신라 진흥왕에 의해 멸망하였다.",
        ],
    },
    {
        "problem_type": "select",
        "problem_question": "종이 이전의 고대 기록 매체와 그 지역의 연결이 올바른 것은?",
        "problem_correct_answer": "인도 아대륙 및 동남아시아 - 종려나무 잎을 가공한 패엽",
        "problem_options": [
            "중국 - 양피지로 만든 코덱스",
            "이집트 - 대나무를 쪼개 만든 간독",
            "인도 아대륙 및 동남아시아 - 종려나무 잎을 가공한 패엽",
            "유럽 및 지중해 세계 - 나일강변의 파피루스 만으로 책 제작",
        ],
    },
    {
        "problem_type": "select",
        "problem_question": "미국의 영토 확장 과정에 대한 설명으로 옳은 것은?",
        "problem_correct_answer": "루이지애나는 프랑스로부터 1803년에 매입하였다.",
        "problem_options": [
            "루이지애나는 프랑스로부터 1803년에 매입하였다.",
            "알래스카는 영국으로부터 매입하였다.",
            "텍사스는 에스파냐와의 조약을 통해 획득하였다.",
            "플로리다는 멕시코와의 전쟁 이후 병합하였다.",
        ],
    },
    {
        "problem_type": "select",
        "problem_question": "미국의 영토별 경제 및 전략적 역할 연결로 가장 적절한 것은?",
        "problem_correct_answer": "루이지애나 - 식량을 책임지는 곡창 지대 및 수운 교통로",
        "problem_options": [
            "오대호 연안 - 자원 창고이자 북극해 전진 기지",
            "루이지애나 - 식량을 책임지는 곡창 지대 및 수운 교통로",
            "서남부 영토 - 미국의 산업화와 번영을 이끈 공업 지대",
            "알래스카 - 자원과 첨단 산업의 중심지",
        ],
    },
    {
        "problem_type": "short",
        "problem_question": "대가야에서 가야금 12곡조를 제정하도록 지시한 왕의 이름은 무엇인가?",
        "problem_correct_answer": "가실왕",
        "problem_options": [],
    },
    {
        "problem_type": "short",
        "problem_question": "서유럽에서 습한 기후 환경과 양피지 등과 결합하여 발달한, 오늘날의 책 형태를 가리키는 용어는 무엇인가?",
        "problem_correct_answer": "코덱스",
        "problem_options": [],
    },
    {
        "problem_type": "short",
        "problem_question": "미국이 신대륙은 미국의 영역이며 유럽은 더 이상 간섭하지 말 것을 선언한 1823년의 외교 원칙 이름은 무엇인가?",
        "problem_correct_answer": "먼로 독트린",
        "problem_options": [],
    },
    {
        "problem_type": "long",
        "problem_question": "가야사 연구의 90% 이상이 특정 유물에 의존하고 있는 이유와, 그 유물을 대표하는 2023년 유네스코 세계유산 등재 사례에 대해 서술하시오.",
        "problem_correct_answer": "가야는 자체적인 기록이 거의 없어 《삼국사기》, 《삼국유사》 등의 외부 기록에 의존해야 하며 연구의 90% 이상이 무덤(고분) 출토 유물에 의존합니다. 이를 대표하여 2023년에는 김해, 함안, 합천, 고령, 고성, 남원, 창녕의 7개 가야고분군이 유네스코 세계유산으로 등재되었습니다.",
        "problem_options": [],
    },
    {
        "problem_type": "ox",
        "problem_question": "가야사 연구의 90% 이상은 기록 부족으로 인해 무덤에서 출토된 유물에 의존하고 있다.",
        "problem_correct_answer": "O",
        "problem_options": [],
    },
    {
        "problem_type": "ox",
        "problem_question": "메소포타미아의 점토판은 종이가 발명된 이후에도 500년 이상 널리 사용되었다.",
        "problem_correct_answer": "X",
        "problem_options": [],
    },
    {
        "problem_type": "select",
        "problem_question": "대가야의 가실왕의 지시로 우륵이 만들었다고 전해지는 전통 악기의 이름은 무엇인가?",
        "problem_correct_answer": "가야금",
        "problem_options": ["거문고", "가야금", "대금", "해금"],
    },
    {
        "problem_type": "select",
        "problem_question": "인도 아대륙 및 동남아시아 지역에서 종려나무 잎을 가공하여 불경 등을 기록하는 데 사용한 매체는 무엇인가?",
        "problem_correct_answer": "패엽",
        "problem_options": ["간독", "백서", "패엽", "양피지"],
    },
    {
        "problem_type": "select",
        "problem_question": "미국이 프랑스로부터 루이지애나 영토를 매입한 연도는 언제인가?",
        "problem_correct_answer": "1803년",
        "problem_options": ["1776년", "1803년", "1848년", "1867년"],
    },
    {
        "problem_type": "select",
        "problem_question": "다음 중 2023년 유네스코 세계유산으로 등재된 가야 고분군 중 대가야의 최고 지배층 무덤이 위치한 곳은 어디인가?",
        "problem_correct_answer": "고령 지산동 고분군",
        "problem_options": [
            "고령 지산동 고분군",
            "김해 대성동 고분군",
            "함안 말이산 고분군",
            "합천 옥전 고분군",
        ],
    },
    {
        "problem_type": "short",
        "problem_question": "양, 염소, 송아지의 가죽으로 만들어져 오늘날의 책 형태인 '코덱스' 제작에 널리 활용된 고대 기록 매체는 무엇인가?",
        "problem_correct_answer": "양피지",
        "problem_options": [],
    },
    {
        "problem_type": "short",
        "problem_question": "미국이 러시아 제국으로부터 720만 달러에 매입한 지역의 이름은 무엇인가?",
        "problem_correct_answer": "알래스카",
        "problem_options": [],
    },
    {
        "problem_type": "short",
        "problem_question": "신대륙은 미국의 영역이며 유럽은 더 이상 간섭하지 말 것을 선언한 1823년의 외교 원칙은 무엇인가?",
        "problem_correct_answer": "먼로 독트린",
        "problem_options": [],
    },
    {
        "problem_type": "long",
        "problem_question": "미국이 영국의 13개 식민지에서 출발하여 대서양, 태평양, 북극해를 아우르는 초강대국으로 성장하는 과정에서 활용한 영토 확장 방식의 주요 사례를 서술하시오.",
        "problem_correct_answer": "미국은 평화적 거래(프랑스로부터의 루이지애나 매입, 러시아로부터의 알래스카 매입), 전쟁 및 병합(텍사스 병합과 미국-멕시코 전쟁을 통한 서남부 영토 획득), 그리고 조약을 통한 국경 정리 등을 통해 신속하게 영토를 확장하며 초강대국으로 성장하였다.",
        "problem_options": [],
    },
]

    problems = pg.generate_problem(
        generate_rule=generate_rule,
        wiki_document_content=summary,
        existing_problems=existing_problems,
    )

    for index, problem in enumerate(problems, start=1):
        print(f"\n--- 문제 {index} ---")
        print(f"유형: {problem['problem_type']}")
        print(f"질문: {problem['problem_question']}")
        print(f"정답: {problem['problem_correct_answer']}")
        print(f"보기: {problem['problem_options']}")

    print(problems)

if __name__ == "__main__":
    Test_generate_problem()
