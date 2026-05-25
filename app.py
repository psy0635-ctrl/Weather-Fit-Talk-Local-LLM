"""WEATHER FIT TALK 메인 실행 파일.

이 파일은 Streamlit 화면을 만들고, 사용자가 입력한 조건을 정리한 뒤,
Ollama 로컬 LLM에 프롬프트를 보내 코디 추천 답변을 화면에 보여줍니다.

처음 읽을 때는 아래 순서로 보면 이해하기 쉽습니다.
1. 기본 설정과 모델 목록
2. 화면을 그리는 함수들
3. 사이드바 입력값
4. 사용자가 질문했을 때 실행되는 처리 흐름
"""

import html
import re
import textwrap

import requests
import streamlit as st

# prompts.py는 LLM에 전달할 긴 프롬프트를 조립하는 역할만 담당합니다.
from prompts import build_weather_fit_prompt

# tools.py에는 날씨/스타일 추론, 검색, 키워드 생성처럼 재사용 가능한 함수들이 있습니다.
from tools import (
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
st.set_page_config(
    page_title="WEATHER FIT TALK",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Streamlit은 화면이 새로 그려질 때마다 코드가 위에서부터 다시 실행됩니다.
# 그래서 이전 채팅 기록은 st.session_state에 저장해 두어야 합니다.
CHAT_STATE_KEY = "weather_fit_clean_messages_v4"

# 앱에서 선택할 수 있는 Ollama 모델 목록입니다.
DEFAULT_LLM_MODEL = "gemma4:e4b"
BACKUP_LLM_MODELS = ["gemma3:4b", "gemma3:1b"]
LLM_MODEL_OPTIONS = [DEFAULT_LLM_MODEL, *BACKUP_LLM_MODELS]


def load_css(file_name: str) -> None:
    # style.css 파일을 읽어서 Streamlit 페이지 안에 <style> 태그로 넣습니다.
    # 이렇게 해야 별도 웹 서버 없이도 CSS가 적용됩니다.
    
    """외부 CSS 파일을 Streamlit 화면에 적용합니다."""
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            css = file.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("style.css 파일을 찾을 수 없습니다. app.py와 같은 폴더에 있는지 확인해주세요.")
# ===== COLOR FIX: JavaScript DOM 직접 조작 =====
# Streamlit 기본 컴포넌트는 CSS만으로 색이 안 바뀌는 경우가 있어
# JavaScript로 입력창/버튼 색상을 한 번 더 강제로 보정합니다.
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
# ===== END COLOR FIX =====

def clean_text(text: str) -> str:
    # LLM이 실수로 HTML, CSS, 코드블록을 답변에 섞어 보내는 경우가 있습니다.
    # 이 함수는 화면에 보여주기 전에 그런 조각을 제거합니다.
    """AI 답변에서 HTML/CSS/코드 조각을 제거하고 일반 텍스트만 남깁니다."""
    text = str(text or "")

    for _ in range(6):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"~~~[\s\S]*?~~~", "", text)
    text = re.sub(r"<\s*(style|script|iframe)\b[^>]*>[\s\S]*?</\s*\1\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"@media\b[^{]*\{[\s\S]*?\}", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?m)^\s*[\w.#:-]+\s*\{[^}]*\}\s*$", "", text)
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</\s*(div|p|li|section|article|h1|h2|h3|h4|h5|h6)\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)

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

    text = text.replace("**", "").replace("__", "").replace("~~", "").replace("`", "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace('="', "").replace("='", "").replace('">', "").replace("'>", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip(" \t")
        lower = line.lower()
        if lower.startswith(("div ", "/div", "class ", "style ", "span ", "/span")):
            continue
        if any(token in lower for token in ["class=", "<div", "</div", "<span", "</span", "{", "}"]):
            continue
        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def ask_ollama(prompt: str, model: str = DEFAULT_LLM_MODEL) -> str:
    # Ollama 서버는 기본적으로 http://localhost:11434 에서 동작합니다.
    # requests.post로 프롬프트를 보내고, 응답 JSON에서 "response"만 꺼냅니다.
    """Ollama 로컬 LLM에 프롬프트를 보내고 답변을 반환합니다."""
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
    response.raise_for_status()
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
    # 앱 상단의 큰 소개 영역을 HTML로 만들어 출력합니다.
    # html.escape는 사용자가 입력한 값이 HTML로 해석되지 않게 막아 줍니다.
    """상단 히어로 영역과 현재 설정 요약을 출력합니다."""
    web_search_status = "ON" if use_web_search else "OFF"

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
    # 사용자가 보낸 메시지를 오른쪽 카드 형태로 보여줍니다.
    """사용자 질문을 오른쪽 말풍선 형태로 출력합니다."""
    safe = html.escape(clean_text(content)).replace("\n", "<br>")
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
    # AI 답변을 아바타 영역과 답변 카드 영역으로 나누어 보여줍니다.
    """AI 답변을 아바타와 함께 출력합니다."""
    cleaned = clean_text(content)
    safe_answer = html.escape(cleaned).replace("\n\n", "<br><br>").replace("\n", "<br>")
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
    # 채팅 기록이 비어 있을 때, 사용자가 바로 따라 해볼 수 있는 예시 질문을 보여줍니다.
    """첫 화면에 예시 질문을 보여줍니다."""
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
    # LLM이 앞 대화를 조금 기억하도록 최근 6개 메시지만 프롬프트에 넣습니다.
    # 너무 많은 대화를 넣으면 프롬프트가 길어져 느려질 수 있습니다.
    """최근 대화 기록을 프롬프트에 넣기 좋은 짧은 문자열로 만듭니다."""
    lines = []
    for message in messages[-6:]:
        role = "사용자" if message["role"] == "user" else "AI"
        lines.append(f"{role}: {clean_text(message['content'])}")
    return "\n".join(lines)


# 앱 시작 시 CSS를 먼저 적용합니다.
load_css("style.css")

# Streamlit이 화면을 다시 그릴 때 색상 스타일이 풀리는 경우가 있어
# MutationObserver로 DOM 변화가 생길 때마다 입력창/버튼 스타일을 다시 적용합니다.
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


# 여기부터는 왼쪽 사이드바에 표시되는 사용자 선택 옵션입니다.
st.sidebar.markdown("## 🌦️ WEATHER FIT SETTINGS")
st.sidebar.caption("날씨와 상황에 맞는 코디 조건을 선택하세요.")

if st.sidebar.button("대화 초기화", use_container_width=True):
    # 대화 기록과 마지막 추천 옵션을 지우고 앱을 새로 그립니다.
    st.session_state[CHAT_STATE_KEY] = []
    st.session_state.pop("last_final_options", None)
    st.rerun()

st.sidebar.markdown("---")

# 어떤 Ollama 모델로 답변을 만들지 선택합니다.
model_name = st.sidebar.selectbox(
    "Local LLM Model",
    LLM_MODEL_OPTIONS,
)

st.sidebar.markdown("### 🌐 WEB SEARCH")

# 체크하면 DuckDuckGo 검색 결과를 프롬프트 참고 정보로 추가합니다.
use_web_search = st.sidebar.checkbox(
    "DuckDuckGo 검색 사용",
    value=False,
    help="체크하면 사용자 질문과 날씨 조건을 바탕으로 DuckDuckGo 검색 결과를 참고합니다.",
)

search_result_count = st.sidebar.selectbox(
    "검색 결과 개수",
    [3, 5, 7],
    index=0,
)

# 아래 값들은 사용자가 직접 채팅에 쓰지 않아도 기본 조건으로 쓰입니다.
location = st.sidebar.text_input("지역", value="서울")

weather_condition = st.sidebar.selectbox(
    "오늘의 날씨",
    ["맑음", "흐림", "비", "눈", "안개", "미세먼지", "폭염", "추위", "일교차 큼"],
)

temperature_range = st.sidebar.selectbox(
    "기온",
    ["영하", "0~5도", "6~10도", "11~15도", "16~20도", "21~25도", "26~30도", "31도 이상"],
    index=4,
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

# 화면 상단에 보여줄 현재 선택값입니다.
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

# 앱을 처음 켰을 때 채팅 기록 저장 공간을 만듭니다.
if CHAT_STATE_KEY not in st.session_state:
    st.session_state[CHAT_STATE_KEY] = []

if not st.session_state[CHAT_STATE_KEY]:
    render_try_prompt()

# 저장된 채팅 기록을 화면에 다시 그립니다.
for message in st.session_state[CHAT_STATE_KEY]:
    if message["role"] == "user":
        render_user_message(message["content"])
    else:
        render_ai_message(message["content"])

last_web_search_result = st.session_state.get("last_web_search_result")
if use_web_search and last_web_search_result:
    with st.expander("DuckDuckGo 검색 참고 정보 보기"):
        st.write(last_web_search_result)

st.markdown('<div class="bottom-safe-space"></div>', unsafe_allow_html=True)

# 하단 채팅 입력창입니다. 사용자가 엔터를 누르면 user_input에 문자열이 들어옵니다.
user_input = st.chat_input("예: 오늘 비 오고 바람이 불어. 학교 갈 때 뭐 입을까?")

if user_input:
    # 1. 사용자가 입력한 문장을 정리하고 채팅 기록에 저장합니다.
    cleaned_user_input = clean_text(user_input)
    st.session_state[CHAT_STATE_KEY].append({"role": "user", "content": cleaned_user_input})
    render_user_message(cleaned_user_input)

    # 2. 사용자의 문장에서 날씨 힌트를 찾아 사이드바 값보다 우선 적용합니다.
    user_weather = infer_weather_from_user_input(cleaned_user_input)
    final_weather_condition, final_temperature_range, final_wind_level, weather_note = merge_user_weather_with_sidebar(
        user_weather,
        weather_condition,
        temperature_range,
        wind_level,
    )

    # 3. 사용자의 문장에서 스타일 힌트를 찾습니다.
    inferred_style = infer_style_from_user_input(cleaned_user_input, style)
    final_style = inferred_style
    if final_style == "자동 추천":
        final_style = choose_auto_style(
            final_weather_condition,
            final_temperature_range,
            final_wind_level,
            situation,
        )

    # 최종으로 결정된 조건을 저장해 두면 디버깅하거나 화면에 다시 쓸 수 있습니다.
    st.session_state["last_final_options"] = {
        "weather_condition": final_weather_condition,
        "temperature_range": final_temperature_range,
        "wind_level": final_wind_level,
        "style": final_style,
    }

    # 4. LLM 프롬프트에 넣을 재료들을 하나씩 만듭니다.
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

    # 5. 검색 옵션이 켜져 있으면 DuckDuckGo 결과를 가져와 참고 자료로 넣습니다.
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
        st.session_state.pop("last_web_search_result", None)

    # 6. prompts.py의 함수로 최종 프롬프트를 조립합니다.
    prompt = build_weather_fit_prompt(
        user_input=cleaned_user_input,
        conversation_history=conversation_history,
        context_summary=context_summary,
        weather_keywords=weather_keywords,
        style_keywords=style_keywords,
        warning_keywords=warning_keywords,
        web_search_result=web_search_result,
    )

    # 7. Ollama에 프롬프트를 보내 답변을 받고, 실패하면 사용자에게 원인을 알려줍니다.
    with st.spinner("WEATHER STYLIST가 오늘의 날씨와 코디를 분석하는 중입니다..."):
        try:
            ai_answer = ask_ollama(prompt, model_name)
        except requests.exceptions.ConnectionError:
            ai_answer = f"Ollama가 실행 중이 아닙니다. PowerShell에서 ollama run {DEFAULT_LLM_MODEL} 명령어를 실행한 뒤 다시 시도해주세요."
            st.error("Ollama 연결 실패")
        except requests.exceptions.Timeout:
            ai_answer = "답변 시간이 너무 오래 걸렸습니다. 질문을 조금 짧게 입력하거나 다시 시도해주세요."
            st.error(ai_answer)
        except Exception as error:
            ai_answer = f"오류가 발생했습니다: {error}"
            st.error(ai_answer)

    # 8. 답변을 정리해서 화면에 보여주고 채팅 기록에 저장합니다.
    ai_answer = clean_text(ai_answer)
    render_ai_message(ai_answer)
    st.session_state[CHAT_STATE_KEY].append({"role": "assistant", "content": ai_answer})
    st.rerun()
