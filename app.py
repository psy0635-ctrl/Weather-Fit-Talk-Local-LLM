import html
import re

import requests
import streamlit as st

from prompts import build_weather_fit_prompt
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


st.set_page_config(
    page_title="WEATHER FIT TALK",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded",
)


CHAT_STATE_KEY = "weather_fit_clean_messages_v4"
DEFAULT_LLM_MODEL = "gemma4:e4b"
BACKUP_LLM_MODELS = ["gemma3:4b", "gemma3:1b"]
LLM_MODEL_OPTIONS = [DEFAULT_LLM_MODEL, *BACKUP_LLM_MODELS]


def load_css(file_name: str) -> None:
    """외부 CSS 파일을 Streamlit 화면에 적용합니다."""
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            css = file.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("style.css 파일을 찾을 수 없습니다. app.py와 같은 폴더에 있는지 확인해주세요.")


def clean_text(text: str) -> str:
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
    """사용자 질문을 오른쪽 말풍선 형태로 출력합니다."""
    safe = html.escape(clean_text(content)).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="user-question-wrap">
            <div class="user-question-card">
                <div class="user-question-label">USER REQUEST</div>
                <div class="user-question-text">{safe}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ai_message(content: str) -> None:
    """AI 답변을 아바타와 함께 출력합니다."""
    cleaned = clean_text(content)
    safe_answer = html.escape(cleaned).replace("\n\n", "<br><br>").replace("\n", "<br>")
    avatar_col, answer_col = st.columns([0.14, 0.86])

    with avatar_col:
        st.markdown(
            """
            <div class="weather-avatar-card">
                <div class="weather-avatar-icon"></div>
                <div class="mini-name">WEATHER<br>STYLIST</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with answer_col:
        st.markdown(
            f"""
            <div class="weather-answer-card">
                <div class="weather-answer-label">WEATHER STYLIST</div>
                <div class="weather-answer-text">{safe_answer}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_try_prompt() -> None:
    """첫 화면에 예시 질문을 보여줍니다."""
    st.markdown(
        """
        <div class="try-box">
            <div class="try-title">01 &middot; TRY THIS PROMPT</div>
            <div class="try-text">
                오늘 비 오고 바람도 좀 불어. 등교 갈 때 춥지 않으면서 깔끔하게 입고 싶어.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_conversation_history(messages: list[dict[str, str]]) -> str:
    """최근 대화 기록을 프롬프트에 넣기 좋은 짧은 문자열로 만듭니다."""
    lines = []
    for message in messages[-6:]:
        role = "사용자" if message["role"] == "user" else "AI"
        lines.append(f"{role}: {clean_text(message['content'])}")
    return "\n".join(lines)


load_css("style.css")


st.sidebar.markdown("## 🌦️ WEATHER FIT SETTINGS")
st.sidebar.caption("날씨와 상황에 맞는 코디 조건을 선택하세요.")

if st.sidebar.button("대화 초기화", use_container_width=True):
    st.session_state[CHAT_STATE_KEY] = []
    st.session_state.pop("last_final_options", None)
    st.rerun()

st.sidebar.markdown("---")

model_name = st.sidebar.selectbox(
    "Local LLM Model",
    LLM_MODEL_OPTIONS,
)

st.sidebar.markdown("### 🌐 WEB SEARCH")

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
    """,
    unsafe_allow_html=True,
)

display_options = st.session_state.get("last_final_options", {})
display_weather_condition = display_options.get("weather_condition", weather_condition)
display_temperature_range = display_options.get("temperature_range", temperature_range)
display_wind_level = display_options.get("wind_level", wind_level)
display_style = display_options.get("style", style)

web_search_result = "아직 검색을 실행하지 않았습니다."

render_hero(
    location=location,
    weather_condition=display_weather_condition,
    temperature_range=display_temperature_range,
    wind_level=display_wind_level,
    situation=situation,
    style=display_style,
    use_web_search=use_web_search,
)

if CHAT_STATE_KEY not in st.session_state:
    st.session_state[CHAT_STATE_KEY] = []

if not st.session_state[CHAT_STATE_KEY]:
    render_try_prompt()

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

user_input = st.chat_input("예: 오늘 비 오고 바람이 불어. 학교 갈 때 뭐 입을까?")

if user_input:
    cleaned_user_input = clean_text(user_input)
    st.session_state[CHAT_STATE_KEY].append({"role": "user", "content": cleaned_user_input})
    render_user_message(cleaned_user_input)

    user_weather = infer_weather_from_user_input(cleaned_user_input)
    final_weather_condition, final_temperature_range, final_wind_level, weather_note = merge_user_weather_with_sidebar(
        user_weather,
        weather_condition,
        temperature_range,
        wind_level,
    )

    inferred_style = infer_style_from_user_input(cleaned_user_input, style)
    final_style = inferred_style
    if final_style == "자동 추천":
        final_style = choose_auto_style(
            final_weather_condition,
            final_temperature_range,
            final_wind_level,
            situation,
        )

    st.session_state["last_final_options"] = {
        "weather_condition": final_weather_condition,
        "temperature_range": final_temperature_range,
        "wind_level": final_wind_level,
        "style": final_style,
    }

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

    prompt = build_weather_fit_prompt(
        user_input=cleaned_user_input,
        conversation_history=conversation_history,
        context_summary=context_summary,
        weather_keywords=weather_keywords,
        style_keywords=style_keywords,
        warning_keywords=warning_keywords,
        web_search_result=web_search_result,
    )

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

    ai_answer = clean_text(ai_answer)
    render_ai_message(ai_answer)
    st.session_state[CHAT_STATE_KEY].append({"role": "assistant", "content": ai_answer})
    st.rerun()
