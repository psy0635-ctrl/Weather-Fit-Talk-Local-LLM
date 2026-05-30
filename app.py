"""WEATHER FIT TALK 메인 실행 파일.

이 파일은 Streamlit 화면을 만들고, 사용자가 입력한 조건을 정리한 뒤,
Ollama 로컬 LLM에 프롬프트를 보내 코디 추천 답변을 화면에 보여줍니다.

처음 읽을 때는 아래 순서로 보면 이해하기 쉽습니다.
1. 기본 설정과 모델 목록
2. 화면을 그리는 함수들
3. 사이드바 입력값
4. 사용자가 질문했을 때 실행되는 처리 흐름
"""

# html: Python 기본 내장 라이브러리.
#       html.escape()  → 사용자 입력의 특수문자(<, >, &)를 안전한 HTML 문자로 바꿔줌.
#       html.unescape() → &amp;, &lt; 같은 HTML 엔티티를 원래 문자로 되돌림.
import html

# re: Python 기본 내장 라이브러리. 정규식(Regular Expression)을 쓰기 위한 모듈.
#     re.sub(패턴, 대체값, 문자열) → 패턴에 매칭된 모든 곳을 대체값으로 바꿈.
import re

# textwrap: Python 기본 내장 라이브러리.
#           textwrap.dedent()는 여러 줄 문자열에서 공통으로 들여쓰기된 공백을 제거함.
#           함수 안에 들여쓴 여러 줄 문자열을 HTML로 쓸 때 앞쪽 공백을 깔끔하게 제거하려고 사용.
import textwrap

# requests: 외부 라이브러리(pip install). HTTP 요청(GET/POST)을 보내는 도구.
#           여기서는 Ollama 서버에 POST 요청으로 프롬프트를 보내고 답변을 받는 데 사용.
import requests

# streamlit: 외부 라이브러리(pip install). Python 코드만으로 웹 앱을 만드는 프레임워크.
#            st.sidebar, st.chat_input, st.markdown 등으로 화면 요소를 쉽게 만들 수 있음.
import streamlit as st

# core/prompts.py는 LLM에 전달할 긴 프롬프트를 조립하는 역할만 담당합니다.
from core.prompts import build_weather_fit_prompt

# core/tools.py에는 날씨/스타일 추론, 검색, 키워드 생성처럼 재사용 가능한 함수들이 있습니다.
from core.tools import (
    build_context_summary,
    build_style_keywords,
    build_weather_keywords,
    choose_auto_style,
    get_weather_warning,
    infer_style_from_user_input,
    infer_weather_from_user_input,
    merge_user_weather_with_sidebar,
    search_duckduckgo,
)


# Streamlit 앱의 브라우저 탭 이름, 아이콘, 화면 폭 같은 기본 설정입니다.
# layout="wide"   → 화면을 브라우저 전체 폭으로 사용. 기본값은 좁은 가운데 정렬.
# initial_sidebar_state="expanded" → 앱을 켤 때 사이드바가 처음부터 열려 있도록 설정.
st.set_page_config(
    page_title="WEATHER FIT TALK",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ──────────────────────────────────────────────────────────────────────────────
# [st.session_state 개념 설명]
#
# Streamlit은 사용자가 버튼을 누르거나 채팅을 입력할 때마다
# app.py 코드를 위에서부터 아래로 처음부터 다시 실행합니다.
# 즉, 일반 변수는 매 실행마다 초기화됩니다.
#
# st.session_state는 새로 고침/재실행 사이에도 값을 유지하는 특별한 딕셔너리입니다.
# 채팅 기록처럼 계속 쌓아야 하는 데이터는 반드시 session_state에 저장해야 합니다.
#
# 예: st.session_state["messages"] = [{"role": "user", "content": "안녕"}]
#     다음 실행에서도 이 값이 그대로 남아 있음.
# ──────────────────────────────────────────────────────────────────────────────

# 채팅 기록을 저장할 session_state 키 이름입니다.
# 버전이 바뀌면 키 이름도 바꿔서 이전 기록이 충돌하지 않게 합니다.
CHAT_STATE_KEY = "weather_fit_clean_messages_v4"

# Ollama에서 사용할 기본 모델과 대안 모델 목록입니다.
DEFAULT_LLM_MODEL = "gemma4:e4b"
BACKUP_LLM_MODELS = ["gemma3:4b", "gemma3:1b"]

# *BACKUP_LLM_MODELS 는 "리스트를 펼쳐서 넣기" 입니다.
# 결과: ["gemma4:e4b", "gemma3:4b", "gemma3:1b"]
# *없이 쓰면: ["gemma4:e4b", ["gemma3:4b", "gemma3:1b"]] 처럼 리스트가 중첩됩니다.
LLM_MODEL_OPTIONS = [DEFAULT_LLM_MODEL, *BACKUP_LLM_MODELS]


def load_css(file_name: str) -> None:
    """외부 CSS 파일을 Streamlit 화면에 적용합니다."""
    # style.css 파일을 읽어서 Streamlit 페이지 안에 <style> 태그로 넣습니다.
    # st.markdown의 unsafe_allow_html=True 옵션을 써야 HTML/CSS 코드가 그대로 적용됩니다.
    # 이렇게 해야 별도 웹 서버 없이도 CSS가 적용됩니다.
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            css = file.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("style.css 파일을 찾을 수 없습니다. app.py와 같은 폴더에 있는지 확인해주세요.")


# ──────────────────────────────────────────────────────────────────────────────
# [COLOR FIX: JavaScript DOM 직접 조작]
#
# Streamlit은 화면이 업데이트될 때 자체 CSS를 강하게 덮어씁니다.
# 그래서 style.css만으로는 입력창 글자색이나 버튼 색상이 제대로 유지되지 않는 경우가 있습니다.
#
# 해결책: JavaScript로 DOM 요소를 직접 찾아 스타일을 강제 지정합니다.
#   - document.querySelectorAll(선택자) → CSS 선택자에 해당하는 모든 요소를 가져옴
#   - el.style.setProperty('속성', '값', 'important') → !important로 스타일 강제 적용
#   - setInterval(함수, 500) → 0.5초마다 함수를 반복 실행 (Streamlit이 리렌더링해도 색상이 유지됨)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<script>
function applyColorFix() {
    // 채팅 입력창 텍스트 색상 고정
    const chatTextareas = document.querySelectorAll(
        '[data-testid="stChatInput"] textarea'
    );
    chatTextareas.forEach(el => {
        el.style.setProperty('color', '#F0EBE0', 'important');
        el.style.setProperty('-webkit-text-fill-color', '#F0EBE0', 'important');
        el.style.setProperty('caret-color', '#F0EBE0', 'important');
        el.style.setProperty('background', 'transparent', 'important');
    });

    // 사이드바 텍스트 입력창(지역) 색상 고정
    const sidebarInputs = document.querySelectorAll(
        '[data-testid="stSidebar"] input'
    );
    sidebarInputs.forEach(el => {
        el.style.setProperty('color', '#F0EBE0', 'important');
        el.style.setProperty('-webkit-text-fill-color', '#F0EBE0', 'important');
        el.style.setProperty('caret-color', '#F0EBE0', 'important');
        el.style.setProperty('background-color', 'rgba(240,235,224,0.08)', 'important');
    });

    // 채팅 입력창 배경 고정
    const chatInputWrap = document.querySelectorAll(
        '[data-testid="stChatInput"] > div'
    );
    chatInputWrap.forEach(el => {
        el.style.setProperty('background', 'rgba(240,235,224,0.06)', 'important');
        el.style.setProperty('border', '1px solid rgba(240,235,224,0.18)', 'important');
        el.style.setProperty('border-radius', '10px', 'important');
    });

    // 전송 버튼 색상
    const submitBtns = document.querySelectorAll(
        '[data-testid="stChatInputSubmitButton"]'
    );
    submitBtns.forEach(el => {
        el.style.setProperty('background', '#C8A96E', 'important');
        el.style.setProperty('color', '#0E0E10', 'important');
        el.style.setProperty('border-radius', '6px', 'important');
    });
}

// 페이지 로드 후 즉시 실행
applyColorFix();

// Streamlit이 리렌더링할 때마다 재적용 (500ms 간격)
setInterval(applyColorFix, 500);
</script>
""", unsafe_allow_html=True)
# ──────────────────────────────────────────────────────────────────────────────
# END COLOR FIX
# ──────────────────────────────────────────────────────────────────────────────


def clean_text(text: str) -> str:
    """AI 답변에서 HTML/CSS/코드 조각을 제거하고 일반 텍스트만 남깁니다."""
    # LLM이 실수로 HTML, CSS, 코드블록을 답변에 섞어 보내는 경우가 있습니다.
    # 이 함수는 화면에 보여주기 전에 그런 조각을 단계별로 제거합니다.

    # text가 None이나 다른 타입이어도 안전하게 문자열로 변환합니다.
    text = str(text or "")

    # ── HTML 엔티티 반복 디코딩 ──────────────────────────────────────────────
    # html.unescape()는 &amp; → &, &lt; → <, &#39; → ' 처럼 HTML 엔티티를 원래 문자로 바꿉니다.
    # 왜 최대 6번 반복하냐?
    #   LLM이 &amp;amp;amp; 처럼 여러 겹으로 인코딩된 문자를 보내는 경우가 있기 때문입니다.
    #   한 번만 디코딩하면 &amp;amp; → &amp; (아직 인코딩 남음)
    #   두 번 디코딩하면 &amp;amp; → & (완전 해제)
    #   결과가 더 이상 안 바뀌면(unescaped == text) 일찍 종료합니다.
    for _ in range(6):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped

    # 줄바꿈 문자를 \n으로 통일합니다. (Windows는 \r\n, Mac 구형은 \r)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # ── 정규식으로 코드/HTML 블록 제거 ───────────────────────────────────────
    # re.sub(패턴, 대체값, 대상문자열) → 패턴에 맞는 부분을 모두 대체값으로 교체합니다.
    # [\s\S]*? 는 "줄바꿈 포함 모든 문자, 최소한으로 매칭" 을 의미합니다.
    #   \s  → 공백, 탭, 줄바꿈 포함 공백 문자
    #   \S  → 공백이 아닌 문자
    #   *?  → 0번 이상, 하지만 최대한 짧게(non-greedy) 매칭

    # 백틱 3개로 감싼 코드블록 제거 (예: ```python ... ```)
    text = re.sub(r"```[\s\S]*?```", "", text)
    # 물결 3개로 감싼 코드블록 제거 (예: ~~~코드~~~)
    text = re.sub(r"~~~[\s\S]*?~~~", "", text)

    # <style>, <script>, <iframe> 태그와 그 안의 내용을 모두 제거합니다.
    # flags=re.IGNORECASE → 대문자/소문자 구분 없이 매칭 (<STYLE>, <Style> 모두 제거)
    text = re.sub(r"<\s*(style|script|iframe)\b[^>]*>[\s\S]*?</\s*\1\s*>", "", text, flags=re.IGNORECASE)

    # CSS @media 블록 제거 (예: @media (max-width: 600px) { ... })
    text = re.sub(r"@media\b[^{]*\{[\s\S]*?\}", "", text, flags=re.IGNORECASE)

    # 간단한 CSS 규칙 제거 (예: .class-name { color: red; })
    # (?m) → 여러 줄 모드: ^는 줄의 시작, $는 줄의 끝을 의미
    text = re.sub(r"(?m)^\s*[\w.#:-]+\s*\{[^}]*\}\s*$", "", text)

    # <br> 태그를 줄바꿈 문자로 변환합니다.
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)

    # 블록 요소의 닫는 태그를 줄바꿈으로 변환합니다. (예: </div> → \n)
    text = re.sub(r"</\s*(div|p|li|section|article|h1|h2|h3|h4|h5|h6)\s*>", "\n", text, flags=re.IGNORECASE)

    # 나머지 모든 HTML 태그 제거 (<태그명 ...>)
    # [^>]+ → > 를 제외한 모든 문자가 1개 이상
    text = re.sub(r"<[^>]+>", "", text)

    # ── LLM이 내부 UI 클래스명을 그대로 출력하는 경우 차단 ───────────────────
    # 가끔 LLM이 앱의 HTML 클래스명이나 속성 이름을 그대로 답변에 포함하는 경우가 있습니다.
    # 이런 단어들이 답변에 보이면 사용자가 혼란스럽기 때문에 공백으로 교체합니다.
    blocked_patterns = [
        r"\bWEATHER\s*STYLIST\s*TALKING\b",
        r"\bUSER\s*WEATHER\s*REQUEST\b",
        r"\b(ai-message|ai-bubble|ai-answer|message-label|chat-row|ai-row)\b",
        r"\b(user-message|user-message-wrap|ai-message-wrap|ai-avatar-box)\b",
        r"\b(weather-mini-icon|mini-cloud|mini-rain|mini-name)\b",
        r"\b(class|div|span|style|onclick|onload|href|src|id)\s*[:=]",
        r"\bclass\s*=\s*['\"][^'\"]*['\"]",
        r"javascript:\s*",
    ]
    for pattern in blocked_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    # ── 마크다운 서식 기호 제거 ───────────────────────────────────────────────
    # ** (굵게), __ (굵게), ~~ (취소선), ` (인라인 코드)
    text = text.replace("**", "").replace("__", "").replace("~~", "").replace("`", "")

    # HTML 엔티티 잔재 처리
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")

    # HTML 속성값 기호 잔재 제거 (예: ="값", ='값', "> )
    text = text.replace('="', "").replace("='", "").replace('">', "").replace("'>", "")

    # ── 공백/줄바꿈 정규화 ───────────────────────────────────────────────────
    # 연속된 스페이스/탭을 하나로 줄임
    text = re.sub(r"[ \t]+", " ", text)
    # 줄 시작 부분의 공백/탭 제거
    text = re.sub(r"\n[ \t]+", "\n", text)
    # 줄 끝 부분의 공백/탭 제거
    text = re.sub(r"[ \t]+\n", "\n", text)
    # 3줄 이상 연속 빈 줄을 최대 2줄로 줄임
    text = re.sub(r"\n{3,}", "\n\n", text)

    # ── 줄 단위로 HTML 태그처럼 보이는 줄 제거 ───────────────────────────────
    # 남은 텍스트를 줄 단위로 나눠서 HTML/CSS 잔재 줄을 걸러냅니다.
    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip(" \t")  # 앞뒤 공백/탭 제거
        lower = line.lower()

        # "div", "/div", "class" 등으로 시작하는 줄 제거
        if lower.startswith(("div ", "/div", "class ", "style ", "span ", "/span")):
            continue

        # 줄 안에 HTML/CSS 관련 단어가 포함된 줄 제거
        if any(token in lower for token in ["class=", "<div", "</div", "<span", "</span", "{", "}"]):
            continue

        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def ask_ollama(prompt: str, model: str = DEFAULT_LLM_MODEL) -> str:
    """Ollama 로컬 LLM에 프롬프트를 보내고 답변을 반환합니다."""
    # ──────────────────────────────────────────────────────────────────────────
    # [Ollama API 호출 설명]
    #
    # Ollama는 로컬 컴퓨터에서 LLM을 실행하는 프로그램입니다.
    # Ollama가 켜지면 http://localhost:11434 주소로 HTTP API를 제공합니다.
    #
    # requests.post(url, json=데이터) 는 서버에 POST 요청을 보냅니다.
    # POST 요청 = "이 데이터를 처리해서 결과를 돌려줘" 라는 HTTP 방식.
    #
    # json 파라미터 설명:
    #   "model"       → 사용할 Ollama 모델 이름 (예: "gemma4:e4b")
    #   "prompt"      → LLM에 전달할 질문/지시 문자열
    #   "stream"      → False면 답변이 완성될 때까지 기다렸다가 한 번에 받음.
    #                   True면 글자가 완성될 때마다 조금씩 스트리밍으로 받음.
    #   "temperature" → LLM 답변의 창의성/일관성 조절 (0.0~2.0)
    #                   0.0 → 항상 가장 확률 높은 단어만 선택 (일관된 답)
    #                   1.0 → 기본값, 적당히 창의적
    #                   2.0 → 매우 창의적이지만 엉뚱한 답 가능
    #                   0.4로 설정한 이유: 코디 추천은 너무 창의적이면 이상해지므로 낮게 고정.
    #
    # timeout=180: 3분 안에 응답이 없으면 오류 발생. LLM이 오래 걸릴 수 있어서 길게 설정.
    # ──────────────────────────────────────────────────────────────────────────
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.4},
        },
        timeout=180,
    )

    # HTTP 응답 코드가 4xx, 5xx 이면 예외를 발생시킵니다.
    # 200 OK 가 아니면 문제가 있다는 뜻이므로 여기서 미리 차단합니다.
    response.raise_for_status()

    # response.json()은 Ollama가 돌려준 JSON 응답을 Python 딕셔너리로 파싱합니다.
    # {"response": "오늘은 청바지에...", "done": true, ...} 형태에서 "response" 값만 꺼냅니다.
    # .get("response", "답변을 가져오지 못했습니다.") → "response" 키가 없으면 기본 문구를 반환.
    return clean_text(response.json().get("response", "답변을 가져오지 못했습니다."))


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

    # 여러 줄 f-string으로 히어로 HTML 블록을 만듭니다.
    # {html.escape(변수)} 패턴으로 모든 사용자 값을 이스케이프 처리합니다.
    hero_html = f"""
<div class="hero-nav">
    <div class="hero-nav-left">
        <span class="hero-nav-dot"></span>
        <span class="hero-nav-title">WEATHER FIT TALK</span>
    </div>
    <div class="hero-nav-center">MAY &middot; 24 &middot; 2026 &middot; SEOUL &middot; LOCAL MODEL</div>
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


# ──────────────────────────────────────────────────────────────────────────────
# [앱 실행 시작 지점]
# 위에서 함수들을 정의했고, 아래부터는 실제로 실행되는 코드입니다.
# Streamlit은 이 파일을 위에서 아래로 순서대로 실행합니다.
# ──────────────────────────────────────────────────────────────────────────────

# 앱 시작 시 CSS를 먼저 적용합니다.
load_css("static/style.css")

# ──────────────────────────────────────────────────────────────────────────────
# [MutationObserver: DOM 변화 감지 스크립트]
#
# Streamlit은 사용자 상호작용이 있을 때마다 DOM(화면 구조)을 새로 그립니다.
# 이때 CSS가 초기화되어 스타일이 풀리는 경우가 있습니다.
#
# MutationObserver는 DOM에 변화가 생길 때마다 자동으로 함수를 호출하는 웹 API입니다.
#   new MutationObserver(콜백함수) → DOM 변화를 감시하는 객체 생성
#   .observe(대상, {childList: true, subtree: true})
#       → document.body(전체 페이지)의 하위 요소 변화를 모두 감시
#
# setInterval(fix, 300) → 0.3초마다 fix() 함수를 실행 (이중 보호)
# 이 두 가지 방법을 같이 써서 Streamlit 리렌더링 후에도 스타일이 유지되게 합니다.
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<script>
(function() {
    function fix() {
        // Chat textarea
        document.querySelectorAll(
            '[data-testid="stChatInput"] textarea'
        ).forEach(function(el) {
            el.style.setProperty('color','#F0EBE0','important');
            el.style.setProperty('-webkit-text-fill-color','#F0EBE0','important');
            el.style.setProperty('caret-color','#F0EBE0','important');
            el.style.setProperty('background','transparent','important');
        });

        // Chat input wrapper
        document.querySelectorAll(
            '[data-testid="stChatInput"] > div'
        ).forEach(function(el) {
            el.style.setProperty('background','rgba(240,235,224,0.06)','important');
            el.style.setProperty('border','1px solid rgba(240,235,224,0.20)','important');
            el.style.setProperty('border-radius','10px','important');
        });

        // Bottom container
        document.querySelectorAll(
            '[data-testid="stBottomBlockContainer"]'
        ).forEach(function(el) {
            el.style.setProperty('background','#111113','important');
        });

        // Sidebar text inputs
        document.querySelectorAll(
            '[data-testid="stSidebar"] input'
        ).forEach(function(el) {
            el.style.setProperty('color','#F0EBE0','important');
            el.style.setProperty('-webkit-text-fill-color','#F0EBE0','important');
            el.style.setProperty('caret-color','#F0EBE0','important');
            el.style.setProperty('background','rgba(240,235,224,0.08)','important');
            el.style.setProperty('border','1px solid rgba(240,235,224,0.20)','important');
        });

        // Submit button
        document.querySelectorAll(
            '[data-testid="stChatInputSubmitButton"], ' +
            '[data-testid="stChatInput"] button'
        ).forEach(function(el) {
            el.style.setProperty('background','#C8A96E','important');
            el.style.setProperty('color','#0E0E10','important');
            el.style.setProperty('border-radius','6px','important');
        });

        // Sidebar toggle button
        document.querySelectorAll(
            '[data-testid="collapsedControl"] button, ' +
            '[data-testid="stSidebarCollapsedControl"] button, ' +
            '[data-testid="stSidebarCollapseButton"] button, ' +
            'button[aria-label="Open sidebar"], ' +
            'button[aria-label="Close sidebar"]'
        ).forEach(function(el) {
            el.style.setProperty('background','#C8A96E','important');
            el.style.setProperty('border','2px solid #C8A96E','important');
            el.style.setProperty('border-radius','50%','important');
            el.style.setProperty('min-width','38px','important');
            el.style.setProperty('min-height','38px','important');
            el.style.setProperty('display','flex','important');
            el.style.setProperty('visibility','visible','important');
            el.style.setProperty('opacity','1','important');
            el.style.setProperty('z-index','9999999','important');
        });

        document.querySelectorAll(
            '[data-testid="collapsedControl"] button svg *, ' +
            '[data-testid="stSidebarCollapsedControl"] button svg *, ' +
            '[data-testid="stSidebarCollapseButton"] button svg *, ' +
            'button[aria-label="Open sidebar"] svg *, ' +
            'button[aria-label="Close sidebar"] svg *'
        ).forEach(function(el) {
            el.style.setProperty('fill','#0E0E10','important');
            el.style.setProperty('stroke','#0E0E10','important');
            el.style.setProperty('opacity','1','important');
        });
    }

    // Run immediately
    fix();
    // Run every 300ms to survive Streamlit rerenders
    setInterval(fix, 300);
    // Run on any DOM mutation
    new MutationObserver(fix).observe(
        document.body,
        { childList: true, subtree: true }
    );
})();
</script>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# [사이드바 UI 구성]
# st.sidebar.xxx() → 왼쪽 패널에 요소를 추가합니다.
# ──────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🌦️ WEATHER FIT SETTINGS")
st.sidebar.caption("날씨와 상황에 맞는 코디 조건을 선택하세요.")

if st.sidebar.button("대화 초기화", use_container_width=True):
    # 버튼을 누르면 채팅 기록과 마지막 추천 옵션을 지우고 앱을 새로 그립니다.
    # st.session_state[키] = [] → 해당 키의 값을 빈 리스트로 초기화
    # st.session_state.pop(키, None) → 키가 있으면 삭제, 없어도 오류 없이 None 반환
    # st.rerun() → 현재 실행을 멈추고 app.py를 처음부터 다시 실행
    st.session_state[CHAT_STATE_KEY] = []
    st.session_state.pop("last_final_options", None)
    st.rerun()

st.sidebar.markdown("---")

# 어떤 Ollama 모델로 답변을 만들지 선택합니다.
# selectbox는 드롭다운 메뉴입니다. 선택된 값을 반환합니다.
model_name = st.sidebar.selectbox(
    "Local LLM Model",
    LLM_MODEL_OPTIONS,
)

st.sidebar.markdown("### 🌐 WEB SEARCH")

# 체크하면 DuckDuckGo 검색 결과를 프롬프트 참고 정보로 추가합니다.
# value=False → 기본적으로 체크 해제
# help= → 마우스 hover 시 설명 말풍선이 뜸
use_web_search = st.sidebar.checkbox(
    "DuckDuckGo 검색 사용",
    value=False,
    help="체크하면 사용자 질문과 날씨 조건을 바탕으로 DuckDuckGo 검색 결과를 참고합니다.",
)

# 검색 결과를 몇 개까지 가져올지 선택합니다.
search_result_count = st.sidebar.selectbox(
    "검색 결과 개수",
    [3, 5, 7],
    index=0,  # index=0 → 기본 선택 항목: 3개
)

# 아래 값들은 사용자가 직접 채팅에 쓰지 않아도 기본 조건으로 사용됩니다.
location = st.sidebar.text_input("지역", value="서울")

weather_condition = st.sidebar.selectbox(
    "오늘의 날씨",
    ["맑음", "흐림", "비", "눈", "안개", "미세먼지", "폭염", "추위", "일교차 큼"],
)

temperature_range = st.sidebar.selectbox(
    "기온",
    ["영하", "0~5도", "6~10도", "11~15도", "16~20도", "21~25도", "26~30도", "31도 이상"],
    index=4,  # index=4 → 기본 선택 항목: "16~20도" (0부터 시작하므로 4번째)
)

wind_level = st.sidebar.selectbox(
    "바람",
    ["거의 없음", "약함", "보통", "강함"],
)

situation = st.sidebar.selectbox(
    "오늘의 상황",
    ["등교", "발표", "데이트", "카페", "면접", "출근", "여행", "친구 모임", "운동/산책"],
)

style = st.sidebar.selectbox(
    "원하는 스타일",
    ["자동 추천", "미니멀", "캐주얼", "스트릿", "포멀", "깔끔한 스타일", "힙한 스타일", "편한 스타일"],
)

body_type = st.sidebar.selectbox(
    "체형",
    ["관계없음", "마른 체형", "보통 체형", "큰 체형", "키가 작은 편", "키가 큰 편"],
)

color_preference = st.sidebar.selectbox(
    "선호 색상",
    ["관계없음", "무채색", "블랙", "화이트", "네이비", "베이지", "밝은 색"],
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    textwrap.dedent(
        """
        <div class="sidebar-meta">
            <div class="sidebar-meta-row">
                <span class="sidebar-meta-label">PROJECT</span>
                <span class="sidebar-meta-value">WEATHER FIT TALK</span>
            </div>
            <div class="sidebar-meta-row">
                <span class="sidebar-meta-label">RUNTIME</span>
                <span class="sidebar-meta-value">OLLAMA &middot; LOCAL</span>
            </div>
            <div class="sidebar-meta-row">
                <span class="sidebar-meta-label">BUILD</span>
                <span class="sidebar-meta-value">PARK &middot; SY</span>
            </div>
        </div>
        """
    ),
    unsafe_allow_html=True,
)

# 화면 상단(히어로 영역)에 보여줄 현재 선택값입니다.
# 사용자 입력 처리 전이므로 사이드바 값을 그대로 표시합니다.
display_weather_condition = weather_condition
display_temperature_range = temperature_range
display_wind_level = wind_level
display_style = style

web_search_result = "아직 검색을 실행하지 않았습니다."

# 사용자가 선택한 현재 옵션을 상단 히어로 영역에 표시합니다.
render_hero(
    location=location,
    weather_condition=display_weather_condition,
    temperature_range=display_temperature_range,
    wind_level=display_wind_level,
    situation=situation,
    style=display_style,
    use_web_search=use_web_search,
)

# ──────────────────────────────────────────────────────────────────────────────
# [채팅 기록 초기화 및 복원]
#
# "CHAT_STATE_KEY not in st.session_state" → 앱을 처음 켰을 때 한 번만 실행됩니다.
# 이후 Streamlit이 재실행되더라도 이 키가 이미 있으므로 건너뜁니다.
# ──────────────────────────────────────────────────────────────────────────────
if CHAT_STATE_KEY not in st.session_state:
    st.session_state[CHAT_STATE_KEY] = []

# 채팅 기록이 비어 있으면 예시 질문을 보여줍니다.
if not st.session_state[CHAT_STATE_KEY]:
    render_try_prompt()

# 저장된 채팅 기록을 화면에 다시 그립니다.
# Streamlit은 재실행 시 화면이 비워지기 때문에, session_state에서 꺼내 다시 렌더링합니다.
for message in st.session_state[CHAT_STATE_KEY]:
    if message["role"] == "user":
        render_user_message(message["content"])
    else:
        render_ai_message(message["content"])

# 웹 검색 결과가 있으면 접혀있는 상태로 보여줍니다.
# st.session_state.get(키) → 키가 없으면 None 반환 (KeyError 없음)
last_web_search_result = st.session_state.get("last_web_search_result")
if use_web_search and last_web_search_result:
    with st.expander("DuckDuckGo 검색 참고 정보 보기"):
        st.write(last_web_search_result)

# 채팅 입력창과 마지막 메시지 사이에 공간을 만들어줍니다.
st.markdown('<div class="bottom-safe-space"></div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# [채팅 입력창과 메인 처리 흐름]
#
# st.chat_input()은 화면 하단에 채팅 입력창을 만듭니다.
# 사용자가 텍스트를 입력하고 엔터를 누르면 user_input 변수에 문자열이 들어옵니다.
# 아무것도 입력하지 않았으면 user_input은 None 입니다.
# ──────────────────────────────────────────────────────────────────────────────
user_input = st.chat_input("예: 오늘 비 오고 바람이 불어. 학교 갈 때 뭐 입을까?")

if user_input:
    # ── 1단계: 사용자 입력 정리 및 저장 ─────────────────────────────────────
    cleaned_user_input = clean_text(user_input)
    # session_state 리스트에 새 메시지를 추가합니다.
    # {"role": "user", "content": 텍스트} 형태로 저장합니다.
    st.session_state[CHAT_STATE_KEY].append({"role": "user", "content": cleaned_user_input})
    render_user_message(cleaned_user_input)

    # ── 2단계: 사용자 문장에서 날씨 정보 추출 ────────────────────────────────
    # "오늘 비 와" → weather_condition="비", "덥다" → temperature_range="26~30도" 같은 식으로 추출.
    # 사이드바 값보다 사용자가 직접 쓴 날씨 표현이 우선입니다.
    user_weather = infer_weather_from_user_input(cleaned_user_input)
    final_weather_condition, final_temperature_range, final_wind_level, weather_note = merge_user_weather_with_sidebar(
        user_weather,
        weather_condition,
        temperature_range,
        wind_level,
    )

    # ── 3단계: 사용자 문장에서 스타일 힌트 추출 ──────────────────────────────
    # "스트릿으로"라고 쓰면 사이드바 선택과 관계없이 스트릿 스타일로 처리합니다.
    inferred_style = infer_style_from_user_input(cleaned_user_input, style)
    final_style = inferred_style
    # "자동 추천"이면 날씨와 상황에 따라 어울리는 스타일을 자동으로 골라줍니다.
    if final_style == "자동 추천":
        final_style = choose_auto_style(
            final_weather_condition,
            final_temperature_range,
            final_wind_level,
            situation,
        )

    # 최종으로 결정된 조건을 저장해 두면 디버깅이나 화면 표시에 다시 쓸 수 있습니다.
    st.session_state["last_final_options"] = {
        "weather_condition": final_weather_condition,
        "temperature_range": final_temperature_range,
        "wind_level": final_wind_level,
        "style": final_style,
    }

    # ── 4단계: LLM 프롬프트 재료 준비 ────────────────────────────────────────
    # 각 tools.py 함수가 하나의 "재료"를 만들고, 나중에 prompts.py에서 합칩니다.
    conversation_history = build_conversation_history(st.session_state[CHAT_STATE_KEY])
    weather_keywords = build_weather_keywords(final_weather_condition, final_temperature_range, final_wind_level)
    style_keywords = build_style_keywords(final_style, color_preference)
    context_summary = build_context_summary(
        location,
        final_weather_condition,
        final_temperature_range,
        final_wind_level,
        situation,
        final_style,
        body_type,
        color_preference,
        weather_note,
    )
    warning_keywords = get_weather_warning(final_weather_condition, final_temperature_range, final_wind_level)

    # ── 5단계: 웹 검색 (선택 기능) ───────────────────────────────────────────
    # 체크박스가 켜져 있을 때만 DuckDuckGo를 검색하고 결과를 session_state에 저장합니다.
    if use_web_search:
        search_query = (
            f"{location} 오늘 날씨 옷차림 "
            f"{final_weather_condition} {final_temperature_range} {final_wind_level} "
            f"{situation} {final_style} {cleaned_user_input}"
        )
        web_search_result = search_duckduckgo(search_query, max_results=search_result_count)
        st.session_state["last_web_search_result"] = web_search_result
    else:
        web_search_result = "DuckDuckGo 검색을 사용하지 않았습니다."
        # pop(키, None) → 키가 있으면 삭제, 없어도 None을 반환하며 오류 없음
        st.session_state.pop("last_web_search_result", None)

    # ── 6단계: 최종 프롬프트 조립 ────────────────────────────────────────────
    # prompts.py의 build_weather_fit_prompt() 함수가 모든 재료를 하나의 긴 문자열로 합칩니다.
    prompt = build_weather_fit_prompt(
        user_input=cleaned_user_input,
        conversation_history=conversation_history,
        context_summary=context_summary,
        weather_keywords=weather_keywords,
        style_keywords=style_keywords,
        warning_keywords=warning_keywords,
        web_search_result=web_search_result,
    )

    # ── 7단계: Ollama 호출 및 오류 처리 ─────────────────────────────────────
    # st.spinner()는 처리 중임을 나타내는 로딩 메시지를 화면에 보여줍니다.
    with st.spinner("WEATHER STYLIST가 오늘의 날씨와 코디를 분석하는 중입니다..."):
        try:
            ai_answer = ask_ollama(prompt, model_name)

        except requests.exceptions.ConnectionError:
            # ConnectionError: Ollama 서버 자체에 연결하지 못했을 때 (Ollama가 꺼져 있는 경우)
            ai_answer = f"Ollama가 실행 중이 아닙니다. PowerShell에서 ollama run {DEFAULT_LLM_MODEL} 명령어를 실행한 뒤 다시 시도해주세요."
            st.error("Ollama 연결 실패")

        except requests.exceptions.Timeout:
            # Timeout: 서버에는 연결됐지만 180초 안에 응답이 없을 때
            ai_answer = "답변 시간이 너무 오래 걸렸습니다. 질문을 조금 짧게 입력하거나 다시 시도해주세요."
            st.error(ai_answer)

        except Exception as error:
            # Exception: 위 두 경우 외 모든 예상치 못한 오류를 여기서 잡습니다.
            ai_answer = f"오류가 발생했습니다: {error}"
            st.error(ai_answer)

    # ── 8단계: 답변 화면 출력 및 저장 ───────────────────────────────────────
    ai_answer = clean_text(ai_answer)
    render_ai_message(ai_answer)
    # AI 답변을 채팅 기록에 저장합니다. role을 "assistant"로 표시합니다.
    st.session_state[CHAT_STATE_KEY].append({"role": "assistant", "content": ai_answer})
    # st.rerun()으로 앱을 다시 실행해 새로운 채팅 내용을 화면에 반영합니다.
    st.rerun()
