"""WEATHER FIT TALK core 패키지.

──────────────────────────────────────────────────────────────────────────────
[패키지(Package)란?]

파이썬에서 여러 .py 파일을 하나의 폴더로 묶은 것을 "패키지"라고 합니다.
폴더 안에 __init__.py 파일이 있으면 파이썬은 그 폴더를 패키지로 인식합니다.

이 프로젝트의 core/ 폴더 구조:
    core/
    ├── __init__.py   ← 지금 이 파일 (패키지의 대문)
    ├── prompts.py    ← LLM에 보낼 프롬프트 조립 담당
    ├── tools.py      ← 날씨/스타일 추론, 검색, 텍스트 정제 보조 함수 담당
    └── ui.py         ← Streamlit 화면 렌더링 함수 담당

──────────────────────────────────────────────────────────────────────────────
[__init__.py의 역할]

__init__.py는 패키지의 "대문" 역할을 합니다.
이 파일에서 함수를 한 번에 모아두면, 사용하는 쪽(app.py)에서 훨씬 간단하게 쓸 수 있습니다.

예를 들어 __init__.py가 없거나 비어 있으면:
    from core.prompts import build_weather_fit_prompt  # 경로가 길다
    from core.tools import search_duckduckgo           # 파일 이름까지 써야 한다

__init__.py에서 한 번에 모아두면:
    from core import build_weather_fit_prompt, search_duckduckgo  # 짧고 깔끔하다

어느 방법이든 동작은 같습니다. __init__.py는 편의를 위한 설정입니다.
──────────────────────────────────────────────────────────────────────────────
"""


# ──────────────────────────────────────────────────────────────────────────────
# prompts.py에서 함수 가져오기
#
# "from 파일 import 함수명" 형태입니다.
# core.prompts → core 폴더 안의 prompts.py 파일을 의미합니다.
#
# build_weather_fit_prompt: 여러 layer 문자열을 합쳐 Ollama에 보낼
#                           최종 프롬프트를 만드는 함수입니다.
# ──────────────────────────────────────────────────────────────────────────────
from core.prompts import build_weather_fit_prompt

# ──────────────────────────────────────────────────────────────────────────────
# tools.py에서 함수 여러 개 한 번에 가져오기
#
# 가져올 함수가 많을 때는 소괄호 () 안에 줄바꿈해서 나열합니다.
# 이렇게 하면 한 줄이 너무 길어지지 않아 읽기 편합니다.
#
# 각 함수가 하는 일:
#   build_context_summary       : 최종 결정된 조건(날씨, 스타일 등)을 프롬프트용 문장으로 정리
#   build_style_keywords        : 선택 스타일과 선호 색상을 추천 방향 키워드로 변환
#   build_weather_keywords      : 날씨·기온·바람 조건을 추천에 쓸 키워드 문자열로 변환
#   choose_auto_style           : 스타일이 "자동 추천"일 때 날씨·상황에 맞는 후보를 반환
#   clean_text                  : AI 답변에서 HTML/CSS/코드 조각을 제거하고 순수 텍스트만 반환
#   contains_any                : 문장 안에 특정 키워드 중 하나라도 있는지 확인 (True/False)
#   get_weather_warning         : 오늘 조건에서 피하면 좋은 옷차림 힌트를 문자열로 반환
#   infer_style_from_user_input : 사용자 문장에서 스타일 힌트를 찾아 사이드바보다 우선 적용
#   infer_weather_from_user_input: 사용자 문장에서 날씨·기온·바람 힌트를 찾아 dict로 반환
#   merge_user_weather_with_sidebar: 사용자 입력 날씨와 사이드바 날씨를 비교해 최종값 결정
#   search_duckduckgo           : DuckDuckGo 검색 결과를 프롬프트용 짧은 문자열로 정리
# ──────────────────────────────────────────────────────────────────────────────
from core.tools import (
    build_context_summary,
    build_style_keywords,
    build_weather_keywords,
    choose_auto_style,
    clean_text,
    contains_any,
    get_weather_warning,
    infer_style_from_user_input,
    infer_weather_from_user_input,
    merge_user_weather_with_sidebar,
    search_duckduckgo,
)

# ──────────────────────────────────────────────────────────────────────────────
# ui.py에서 Streamlit 화면 렌더링 함수 가져오기
#
# 각 함수가 하는 일:
#   build_conversation_history  : 최근 대화 기록을 프롬프트에 넣기 좋은 문자열로 변환
#   render_ai_message           : AI 답변을 아바타 카드와 함께 화면에 출력
#   render_hero                 : 상단 히어로 영역(제목, 날씨 요약 카드)을 출력
#   render_try_prompt           : 첫 화면에 예시 질문 안내 박스를 출력
#   render_user_message         : 사용자 질문을 말풍선 형태로 화면에 출력
# ──────────────────────────────────────────────────────────────────────────────
from core.ui import (
    build_conversation_history,
    render_ai_message,
    render_hero,
    render_try_prompt,
    render_user_message,
)


# ──────────────────────────────────────────────────────────────────────────────
# __all__: 이 패키지의 "공식 공개 목록"
#
# __all__은 "from core import *" 처럼 * 로 전부 가져올 때
# 실제로 어떤 이름들을 내보낼지 명시하는 리스트입니다.
#
# 직접 "from core import 함수명" 처럼 이름을 지정할 때는 __all__ 유무와 관계없이 동작합니다.
# __all__의 진짜 역할은 두 가지입니다:
#   1. "이 패키지에서 외부로 공개되는 함수가 어떤 것인지" 문서화
#   2. from core import * 사용 시 불필요한 내부 변수가 딸려나오는 것을 방지
#
# 정리하면: __all__은 선택 사항이지만 있으면 코드의 의도가 명확해집니다.
# ──────────────────────────────────────────────────────────────────────────────
__all__ = [
    "build_weather_fit_prompt",        # prompts.py
    "build_context_summary",           # tools.py
    "build_style_keywords",            # tools.py
    "build_weather_keywords",          # tools.py
    "choose_auto_style",               # tools.py
    "clean_text",                      # tools.py
    "contains_any",                    # tools.py
    "get_weather_warning",             # tools.py
    "infer_style_from_user_input",     # tools.py
    "infer_weather_from_user_input",   # tools.py
    "merge_user_weather_with_sidebar", # tools.py
    "search_duckduckgo",               # tools.py
    "build_conversation_history",      # ui.py
    "render_ai_message",               # ui.py
    "render_hero",                     # ui.py
    "render_try_prompt",               # ui.py
    "render_user_message",             # ui.py
]
