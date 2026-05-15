import html
import re

import requests
import streamlit as st
import streamlit.components.v1 as components

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
    page_icon="☁️",
    layout="wide",
)


CHAT_STATE_KEY = "weather_fit_clean_messages_v4"


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


def ask_ollama(prompt: str, model: str = "gemma4:e4b") -> str:
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
) -> None:
    """상단 히어로 영역과 현재 설정 요약을 출력합니다."""
    hero_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            padding: 0;
            background: #050505;
            font-family: Arial, Helvetica, sans-serif;
        }}
        .canvas {{
            width: 100%;
            min-height: 720px;
            background: #e8e8e4;
            color: #050505;
            padding: 34px 38px;
            position: relative;
            overflow: hidden;
        }}
        .canvas::before {{
            content: "";
            position: absolute;
            inset: 0;
            background-image:
                linear-gradient(rgba(0,0,0,0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0,0,0,0.035) 1px, transparent 1px);
            background-size: 22px 22px;
            opacity: 0.5;
            pointer-events: none;
        }}
        .inner {{ position: relative; z-index: 2; }}
        .nav {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(0,0,0,0.25);
            padding-bottom: 14px;
            margin-bottom: 58px;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 22px;
            font-weight: 900;
            letter-spacing: 0.04em;
        }}
        .brand-symbol {{
            width: 30px;
            height: 30px;
            border: 2px solid #050505;
            border-radius: 50%;
            position: relative;
        }}
        .brand-symbol::before,
        .brand-symbol::after {{
            content: "";
            position: absolute;
            width: 9px;
            height: 2px;
            background: #050505;
            top: 12px;
        }}
        .brand-symbol::before {{ left: -10px; }}
        .brand-symbol::after {{ right: -10px; }}
        .menu {{
            display: flex;
            gap: 28px;
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 0.08em;
        }}
        .menu span {{ border-bottom: 1px solid transparent; padding-bottom: 4px; }}
        .menu .active {{ border-bottom: 1px solid #050505; }}
        .hero {{
            display: grid;
            grid-template-columns: 1.25fr 0.75fr;
            gap: 36px;
            align-items: end;
        }}
        .kicker {{
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 0.1em;
            margin-bottom: 18px;
        }}
        .title {{
            font-size: 128px;
            line-height: 0.78;
            font-weight: 950;
            letter-spacing: -0.08em;
        }}
        .black-block {{
            display: inline-block;
            width: 190px;
            height: 76px;
            background: #050505;
            margin-right: 20px;
            vertical-align: middle;
        }}
        .desc {{
            margin-top: 28px;
            padding-top: 14px;
            border-top: 1px solid rgba(0,0,0,0.25);
            font-size: 14px;
            line-height: 1.7;
        }}
        .character-card {{
            width: 330px;
            min-height: 445px;
            background: #050505;
            color: #e8e8e4;
            padding: 22px;
            margin-left: auto;
        }}
        .character-label {{
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 0.1em;
            color: #bdbdbd;
            border-bottom: 1px solid rgba(255,255,255,0.2);
            padding-bottom: 12px;
            margin-bottom: 26px;
        }}
        .weather-icon {{
            width: 150px;
            height: 150px;
            margin: 18px auto 28px auto;
            position: relative;
        }}
        .cloud {{
            position: absolute;
            left: 20px;
            top: 40px;
            width: 112px;
            height: 58px;
            background: #e8e8e4;
            border-radius: 40px;
        }}
        .cloud::before {{
            content: "";
            position: absolute;
            left: 20px;
            top: -28px;
            width: 58px;
            height: 58px;
            background: #e8e8e4;
            border-radius: 50%;
        }}
        .cloud::after {{
            content: "";
            position: absolute;
            right: 16px;
            top: -18px;
            width: 48px;
            height: 48px;
            background: #e8e8e4;
            border-radius: 50%;
        }}
        .rain {{
            position: absolute;
            left: 38px;
            top: 112px;
            width: 6px;
            height: 32px;
            background: #e8e8e4;
            transform: rotate(18deg);
            box-shadow: 38px 0 0 #e8e8e4, 76px 0 0 #e8e8e4;
        }}
        .character-name {{
            font-size: 25px;
            font-weight: 950;
            letter-spacing: -0.03em;
            margin-top: 18px;
        }}
        .character-desc {{
            margin-top: 8px;
            font-size: 13px;
            color: #c8c8c8;
            line-height: 1.6;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 1.35fr 0.85fr;
            gap: 18px;
            margin-top: 34px;
        }}
        .info-card {{
            background: rgba(255,255,255,0.36);
            border: 1px solid rgba(0,0,0,0.2);
            padding: 18px;
        }}
        .info-title {{
            font-size: 13px;
            font-weight: 950;
            letter-spacing: 0.06em;
            margin-bottom: 12px;
        }}
        .info-text {{
            font-size: 13px;
            line-height: 1.8;
            color: #252525;
        }}
        .option-list {{ display: grid; gap: 8px; }}
        .option-list div {{
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid rgba(0,0,0,0.18);
            padding-bottom: 6px;
            font-size: 13px;
        }}
        .option-list span {{ color: #555; }}
        .option-list b {{ color: #050505; }}
    </style>
    </head>
    <body>
        <div class="canvas">
            <div class="inner">
                <div class="nav">
                    <div class="brand">
                        <div class="brand-symbol"></div>
                        <div>WEATHER FIT</div>
                    </div>
                    <div class="menu">
                        <span class="active">HOME</span>
                        <span>WEATHER</span>
                        <span>STYLING</span>
                        <span>LOCAL LLM</span>
                        <span>ARCHIVE</span>
                    </div>
                </div>
                <div class="hero">
                    <div>
                        <div class="kicker">LOCAL LLM × WEATHER STYLING × NO API KEY</div>
                        <div class="title"><span class="black-block"></span>WEATHER<br>FIT</div>
                        <div class="desc">
                            날씨, 기온, 바람, 상황을 바탕으로<br>
                            오늘 입기 좋은 옷차림을 추천하는 AI 챗봇
                        </div>
                    </div>
                    <div class="character-card">
                        <div class="character-label">AI WEATHER STYLIST</div>
                        <div class="weather-icon">
                            <div class="cloud"></div>
                            <div class="rain"></div>
                        </div>
                        <div class="character-name">WEATHER STYLIST</div>
                        <div class="character-desc">
                            오늘의 날씨와 상황을 읽고<br>
                            가장 현실적인 코디를 추천합니다.
                        </div>
                    </div>
                </div>
                <div class="info-grid">
                    <div class="info-card">
                        <div class="info-title">WHAT IS WEATHER FIT?</div>
                        <div class="info-text">
                            WEATHER FIT은 사용자가 선택한 날씨, 기온, 바람, 상황을 바탕으로
                            상의, 하의, 아우터, 신발, 소품을 추천하는 날씨 기반 AI 코디 챗봇입니다.
                            OpenAI나 Gemini API 없이 Ollama 로컬 LLM으로 답변을 생성합니다.
                        </div>
                    </div>
                    <div class="info-card">
                        <div class="info-title">CURRENT WEATHER OPTION</div>
                        <div class="option-list">
                            <div><span>Location</span><b>{html.escape(location)}</b></div>
                            <div><span>Weather</span><b>{html.escape(weather_condition)}</b></div>
                            <div><span>Temp</span><b>{html.escape(temperature_range)}</b></div>
                            <div><span>Wind</span><b>{html.escape(wind_level)}</b></div>
                            <div><span>Situation</span><b>{html.escape(situation)}</b></div>
                            <div><span>Style</span><b>{html.escape(style)}</b></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    components.html(hero_html, height=760, scrolling=False)


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
        st.markdown("###### WEATHER STYLIST TALKING")
        st.markdown(cleaned)


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


st.sidebar.markdown("## ☁️ WEATHER FIT SETTINGS")
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

use_web_search = st.sidebar.checkbox(
    "DuckDuckGo 검색 사용",
    value=False,
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
        <b>Project</b>: Weather Fit Talk<br>
        <b>Local LLM</b>: Ollama + gemma4:e4b<br>
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

render_hero(
    location=location,
    weather_condition=display_weather_condition,
    temperature_range=display_temperature_range,
    wind_level=display_wind_level,
    situation=situation,
    style=display_style,
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

user_input = st.chat_input("오늘 날씨와 상황을 입력해보세요. 예: 비 오는데 등교 갈 때 뭐 입을까?")

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
            f"{final_weather_condition} {final_temperature_range} {cleaned_user_input}"
        )
        web_search_result = search_duckduckgo(search_query, max_results=3)
        with st.expander("DuckDuckGo 검색 참고 정보 보기"):
            st.write(web_search_result)
    else:
        web_search_result = "웹 검색을 사용하지 않았습니다."

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
            ai_answer = "Ollama가 실행 중이 아닙니다. PowerShell에서 ollama run gemma4:e4b 명령어를 실행한 뒤 다시 시도해주세요."
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
