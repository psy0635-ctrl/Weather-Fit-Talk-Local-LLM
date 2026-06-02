"""WEATHER FIT TALK 화면 렌더링 함수 모음.

app.py에서 화면을 그리는 함수들을 분리한 파일입니다.
Streamlit 화면 출력과 관련된 모든 render_* 함수와
대화 기록을 문자열로 만드는 build_conversation_history가 여기에 있습니다.
"""

import html
import textwrap
from datetime import datetime

import streamlit as st

from core.tools import clean_text


def render_hero(
    location: str,
    weather_condition: str,
    temperature_range: str,
    wind_level: str,
    situation: str,
    style: str,
    use_web_search: bool,
) -> None:
    """상단 히어로 영역과 현재 설정 요약을 출력합니다."""
    # ──────────────────────────────────────────────────────────────────────────
    # [html.escape() 사용 이유]
    #
    # 사용자가 입력한 값을 HTML 문자열 안에 직접 삽입하면 XSS 공격이 가능합니다.
    # 예: 사용자가 location에 <script>alert('해킹')</script> 를 입력하면
    #     HTML로 그대로 렌더링되어 스크립트가 실행될 수 있습니다.
    #
    # html.escape()는 특수문자를 HTML 엔티티로 변환합니다:
    #   <  →  &lt;
    #   >  →  &gt;
    #   &  →  &amp;
    # 이렇게 하면 사용자 입력이 텍스트로만 표시되고 HTML로 실행되지 않습니다.
    # ──────────────────────────────────────────────────────────────────────────
    web_search_status = "ON" if use_web_search else "OFF"

    # ──────────────────────────────────────────────────────────────────────────
    # [동적 날짜 처리]
    #
    # datetime.now() → 현재 날짜와 시간을 가져옵니다.
    # .strftime('%b') → 월 이름을 3자리 약자로 변환합니다. (예: Jun, Jul)
    # .upper() → 소문자를 대문자로 바꿉니다. (예: jun → JUN)
    # .day → 오늘의 일(숫자)을 가져옵니다. (예: 2)
    # .year → 올해 연도를 가져옵니다. (예: 2026)
    # ──────────────────────────────────────────────────────────────────────────
    today = datetime.now()
    date_str = (
        f"{today.strftime('%b').upper()} &middot; "
        f"{today.day} &middot; "
        f"{today.year} &middot; SEOUL &middot; LOCAL MODEL"
    )

    # 여러 줄 f-string으로 히어로 HTML 블록을 만듭니다.
    # {html.escape(변수)} 패턴으로 모든 사용자 값을 이스케이프 처리합니다.
    hero_html = f"""
<div class="hero-nav">
    <div class="hero-nav-left">
        <span class="hero-nav-dot"></span>
        <span class="hero-nav-title">WEATHER FIT TALK</span>
    </div>
    <div class="hero-nav-center">{date_str}</div>
    <div class="hero-nav-right">
        <span class="hero-nav-green-dot"></span>
        LOCAL MODEL ACTIVE
    </div>
</div>
<div class="hero-caption-bar">
    VOL. 04 &times; WEATHER SERVICE &times; FASHION EDITORIAL &times; LOCAL LLM
</div>
<div class="hero-main">
    <div class="hero-left">
        <div class="hero-headline">
            <span class="hero-line-white">WEATHER</span>
            <div class="hero-line-row">
                <span class="hero-line-gold">FIT</span>
                <span class="hero-line-italic">talk.</span>
            </div>
        </div>
        <p class="hero-body">날씨, 기온, 바람, 상황을 종합 분석해 오늘 입기 좋은 코디를 추천하는 로컬 LLM 기반 AI 스타일리스트. 모든 추론은 당신의 머신 안에서.</p>
        <div class="hero-tags">
            <span class="hero-tag">TODAY {html.escape(weather_condition)} &middot; {html.escape(temperature_range)}</span>
            <span class="hero-tag">SCENE {html.escape(situation)}</span>
            <span class="hero-tag">STYLE {html.escape(style)}</span>
            <span class="hero-tag">MODEL gemma4:e4b</span>
        </div>
        <div class="hero-cta">
            <span class="hero-cta-line"></span>
            <span class="hero-cta-text">&mdash; ASK THE WEATHER STYLIST BELOW</span>
        </div>
    </div>
    <div class="hero-right">
        <div class="hero-card">
            <div class="hero-card-label">&mdash; AI WEATHER STYLIST</div>
            <div class="hero-weather-icon"></div>
            <div class="hero-stylist-name">WEATHER STYLIST</div>
            <p class="hero-stylist-desc">패션 에디터처럼 무드를 잡고, 날씨 비서처럼 현실적인 착용감을 챙깁니다. 8-레이어 프롬프트로 구성된 코디 큐레이션.</p>
            <div class="hero-stylist-vol">NO. 04 / SS26</div>
        </div>
        <div class="hero-card" style="margin-top:16px">
            <div class="hero-card-label">TODAY WEATHER OPTION</div>
            <div class="hero-option-row">
                <span class="hero-option-label">지역</span>
                <span class="hero-option-value">{html.escape(location)}</span>
            </div>
            <div class="hero-option-row">
                <span class="hero-option-label">날씨</span>
                <span class="hero-option-value">{html.escape(weather_condition)}</span>
            </div>
            <div class="hero-option-row">
                <span class="hero-option-label">기온</span>
                <span class="hero-option-value">{html.escape(temperature_range)}</span>
            </div>
            <div class="hero-option-row">
                <span class="hero-option-label">바람</span>
                <span class="hero-option-value">{html.escape(wind_level)}</span>
            </div>
            <div class="hero-option-row">
                <span class="hero-option-label">상황</span>
                <span class="hero-option-value">{html.escape(situation)}</span>
            </div>
            <div class="hero-option-row">
                <span class="hero-option-label">스타일</span>
                <span class="hero-option-value">{html.escape(style)}</span>
            </div>
            <div class="hero-option-row">
                <span class="hero-option-label">웹 검색</span>
                <span class="hero-option-value">{html.escape(web_search_status)}</span>
            </div>
        </div>
    </div>
</div>
<div class="hero-ticker-wrap">
    <div class="hero-ticker-track">
        <span class="hero-ticker-text">NO KEY &#10022; RUNS ON YOUR MACHINE &#10022; WEATHER &times; FASHION &times; LLM &#10022; </span>
        <span class="hero-ticker-text">NO KEY &#10022; RUNS ON YOUR MACHINE &#10022; WEATHER &times; FASHION &times; LLM &#10022; </span>
        <span class="hero-ticker-text">NO KEY &#10022; RUNS ON YOUR MACHINE &#10022; WEATHER &times; FASHION &times; LLM &#10022; </span>
        <span class="hero-ticker-text">NO KEY &#10022; RUNS ON YOUR MACHINE &#10022; WEATHER &times; FASHION &times; LLM &#10022; </span>
    </div>
</div>"""
    st.markdown(hero_html, unsafe_allow_html=True)


def render_user_message(content: str) -> None:
    """사용자 질문을 오른쪽 말풍선 형태로 출력합니다."""
    # 사용자 입력을 먼저 clean_text로 정리하고, html.escape로 이스케이프합니다.
    # .replace("\n", "<br>") → 줄바꿈을 HTML 줄바꿈 태그로 바꿔서 화면에서도 줄이 나뉩니다.
    safe = html.escape(clean_text(content)).replace("\n", "<br>")

    # ──────────────────────────────────────────────────────────────────────────
    # [textwrap.dedent() 사용 이유]
    #
    # 함수 안에서 여러 줄 문자열을 들여쓰면(indented) 앞에 공백이 붙습니다.
    # 예를 들어 함수 안에서:
    #   html = """
    #           <div>안녕</div>
    #           """
    # 이 문자열은 실제로 "        <div>안녕</div>" 처럼 앞에 공백이 많이 붙습니다.
    # textwrap.dedent()는 공통으로 들어간 앞쪽 공백을 자동으로 제거합니다.
    # HTML 출력 품질에는 영향 없지만 실수로 공백이 남는 걸 방지합니다.
    # ──────────────────────────────────────────────────────────────────────────
    st.markdown(
        textwrap.dedent(
            f"""
            <div class="user-question-wrap">
                <div class="user-question-card">
                    <div class="user-question-label">USER REQUEST</div>
                    <div class="user-question-text">{safe}</div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_ai_message(content: str) -> None:
    """AI 답변을 아바타와 함께 출력합니다."""
    cleaned = clean_text(content)
    # \n\n(단락 구분)은 <br><br>로, \n(줄바꿈)은 <br>로 변환합니다.
    safe_answer = html.escape(cleaned).replace("\n\n", "<br><br>").replace("\n", "<br>")

    # ──────────────────────────────────────────────────────────────────────────
    # [st.columns() 사용 이유]
    #
    # st.columns([0.14, 0.86])은 화면을 두 개의 열(column)로 나눕니다.
    #   첫 번째 열: 전체 너비의 14% → 아바타(작은 WEATHER STYLIST 카드)
    #   두 번째 열: 전체 너비의 86% → AI 답변 카드
    #
    # with avatar_col: → 이 블록 안에서 출력되는 내용은 왼쪽(14%) 열에 배치됨.
    # with answer_col: → 이 블록 안에서 출력되는 내용은 오른쪽(86%) 열에 배치됨.
    # ──────────────────────────────────────────────────────────────────────────
    avatar_col, answer_col = st.columns([0.14, 0.86])

    with avatar_col:
        st.markdown(
            textwrap.dedent(
                """
                <div class="weather-avatar-card">
                    <div class="weather-avatar-icon"></div>
                    <div class="mini-name">WEATHER<br>STYLIST</div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    with answer_col:
        st.markdown(
            textwrap.dedent(
                f"""
                <div class="weather-answer-card">
                    <div class="weather-answer-label">WEATHER STYLIST</div>
                    <div class="weather-answer-text">{safe_answer}</div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )


def render_try_prompt() -> None:
    """첫 화면에 예시 질문을 보여줍니다."""
    # 채팅 기록이 비어 있을 때, 사용자가 바로 따라 해볼 수 있는 예시 질문을 보여줍니다.
    st.markdown(
        textwrap.dedent(
            """
            <div class="try-box">
                <div class="try-title">01 &middot; TRY THIS PROMPT</div>
                <div class="try-text">
                    오늘 비 오고 바람도 좀 불어. 등교 갈 때 춥지 않으면서 깔끔하게 입고 싶어.
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def build_conversation_history(messages: list[dict[str, str]]) -> str:
    """최근 대화 기록을 프롬프트에 넣기 좋은 짧은 문자열로 만듭니다."""
    # ──────────────────────────────────────────────────────────────────────────
    # LLM이 앞 대화를 기억할 수 있도록 최근 대화를 프롬프트에 포함시킵니다.
    # 왜 6개만 넣나?
    #   너무 많은 대화를 넣으면 프롬프트가 길어져 LLM 처리 속도가 느려집니다.
    #   또한 LLM은 너무 긴 입력에서 중간 내용을 잊는 경향(lost in the middle)이 있습니다.
    #
    # messages[-6:] → 리스트의 마지막 6개 항목을 가져옵니다.
    #   파이썬에서 음수 인덱스는 뒤에서부터 셉니다.
    #   -1 → 마지막, -6 → 뒤에서 6번째
    #   [-6:] → 뒤에서 6번째부터 끝까지 = 최근 6개
    # ──────────────────────────────────────────────────────────────────────────
    lines = []
    for message in messages[-6:]:
        # message["role"]은 "user" 또는 "assistant" 입니다.
        role = "사용자" if message["role"] == "user" else "AI"
        lines.append(f"{role}: {clean_text(message['content'])}")
    return "\n".join(lines)
