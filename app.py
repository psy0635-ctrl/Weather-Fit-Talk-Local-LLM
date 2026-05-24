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
    weather_accent_map = {
        "맑음": ("#f2c94c", "SUNNY"),
        "비": ("#5aa9e6", "RAIN"),
        "눈": ("#9adcf7", "SNOW"),
        "흐림": ("#a8adb7", "CLOUDY"),
        "안개": ("#c8c8bd", "FOG"),
        "미세먼지": ("#c9b18a", "DUST"),
        "폭염": ("#ff8a3d", "HEAT"),
        "추위": ("#82d8d8", "COLD"),
        "일교차 큼": ("#d6c27a", "TEMP SHIFT"),
    }
    weather_accent, weather_badge = weather_accent_map.get(weather_condition, ("#d6c27a", "WEATHER"))
    web_search_status = "ON" if use_web_search else "OFF"

    accent_style = f"<style>:root {{ --hero-accent: {weather_accent}; --hero-accent-muted: {weather_accent}33; }}</style>"

    hero_html = f"""
    <div class="canvas">
        <div class="inner">
            <div class="nav">
                <div class="brand">
                    <div class="brand-symbol"></div>
                    <div>WEATHER FIT TALK</div>
                </div>
            </div>
            <div class="hero">
                <div class="hero-left">
                    <div>
                        <div class="kicker">WEATHER SERVICE × FASHION EDITORIAL × LOCAL LLM</div>
                        <div class="title">WEATHER<br><span class="title-mark">FIT</span> TALK</div>
                        <div class="desc">
                            날씨, 기온, 바람, 상황을 바탕으로 오늘 입기 좋은 옷차림을 추천하는 AI 스타일리스트
                        </div>
                        <div class="concept-row">
                            <div class="concept-pill">TODAY: {html.escape(weather_condition)}</div>
                            <div class="concept-pill">STYLE: {html.escape(style)}</div>
                            <div class="concept-pill">LOCAL MODEL: GEMMA4:E4B</div>
                        </div>
                        <div class="start-note"><span></span>ASK THE WEATHER STYLIST BELOW</div>
                    </div>
                </div>
                <div class="right-stack">
                    <div class="character-card">
                        <div class="character-label">AI WEATHER STYLIST</div>
                        <div class="weather-icon">
                            <div class="sun"></div>
                            <div class="cloud"></div>
                            <div class="rain"></div>
                        </div>
                        <div class="character-name">WEATHER STYLIST</div>
                        <div class="character-desc">
                            패션 에디터처럼 무드를 잡고, 날씨 비서처럼 현실적인 착용감을 챙깁니다.
                        </div>
                    </div>
                    <div class="option-card">
                        <div class="option-heading">
                            <div class="option-title">TODAY WEATHER OPTION</div>
                            <div class="weather-badge">{html.escape(weather_badge)}</div>
                        </div>
                        <div class="option-list">
                            <div><span>지역</span><b>{html.escape(location)}</b></div>
                            <div><span>날씨</span><b>{html.escape(weather_condition)}</b></div>
                            <div><span>기온</span><b>{html.escape(temperature_range)}</b></div>
                            <div><span>바람</span><b>{html.escape(wind_level)}</b></div>
                            <div><span>상황</span><b>{html.escape(situation)}</b></div>
                            <div><span>스타일</span><b>{html.escape(style)}</b></div>
                            <div><span>웹 검색</span><b>{html.escape(web_search_status)}</b></div>
                            <div><span>검색 엔진</span><b>DuckDuckGo</b></div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="info-grid">
                <div class="info-card">
                    <div class="info-title">WHAT IS WEATHER FIT?</div>
                    <div class="info-text">
                        WEATHER FIT TALK는 날씨와 사용자의 상황을 바탕으로 오늘 입기 좋은 옷차림을 추천하는 로컬 LLM 기반 AI 챗봇입니다.
                    </div>
                </div>
                <div class="info-card">
                    <div class="info-title">TODAY FIT SIGNAL</div>
                    <div class="mini-metric">
                        <div><span>MOOD</span><b>{html.escape(style)}</b></div>
                        <div><span>WEATHER</span><b>{html.escape(weather_condition)}</b></div>
                        <div><span>SCENE</span><b>{html.escape(situation)}</b></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(accent_style + hero_html, unsafe_allow_html=True)


def render_user_message(content: str) -> None:
    """사용자 질문을 오른쪽 말풍선 형태로 출력합니다."""
    safe = html.escape(clean_text(content)).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="user-question-wrap">
            <div class="user-question-card">
                <div class="user-question-label">USER WEATHER REQUEST</div>
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
    avatar_col, answer_col = st.columns([0.16, 0.84])

    with avatar_col:
        st.markdown(
            """
            <div class="weather-avatar-card">
                <div class="weather-mini-icon">
                    <div class="mini-cloud"></div>
                    <div class="mini-rain"></div>
                </div>
                <div class="mini-name">WEATHER<br>STYLIST</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with answer_col:
        st.markdown(
            f"""
            <div class="weather-answer-card">
                <div class="weather-answer-label">WEATHER STYLIST TALKING</div>
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
            <div class="try-title">TRY THIS PROMPT</div>
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
    ["gemma4:e4b", "gemma3:4b", "gemma3:1b"],
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
    f"""
    <div class="sidebar-meta">
        <b>Project</b>: Weather Fit Talk<br>
        <b>Local LLM</b>: Ollama + {DEFAULT_LLM_MODEL}<br>
        <b>API Key</b>: 사용하지 않음<br>
        <b>Cost</b>: API 비용 없음<br>
        <b>Topic</b>: 날씨 기반 코디 추천
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
