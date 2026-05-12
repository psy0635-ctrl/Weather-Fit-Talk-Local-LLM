import html
import re

import requests
import streamlit as st
import streamlit.components.v1 as components


# ==============================
# Page setup
# ==============================
st.set_page_config(
    page_title="FIT TALK",
    page_icon="👕",
    layout="wide",
)


# ==============================
# CSS loader
# ==============================
def load_css(file_name: str) -> None:
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            css = f.read()

        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    except FileNotFoundError:
        st.error("style.css 파일을 찾을 수 없습니다. app.py와 같은 폴더에 style.css가 있는지 확인하세요.")


load_css("style.css")

CHAT_STATE_KEY = "messages_v6"


# ==============================
# Text cleanup
# ==============================
def clean_text(text: str) -> str:
    """
    LLM 답변에 HTML/CSS 코드나 HTML 엔티티가 섞여도 화면에는 일반 텍스트만 보이게 정리합니다.
    """
    text = str(text or "")

    # Ollama가 &amp;lt;div&amp;gt;처럼 여러 번 escape한 경우까지 풀어냅니다.
    for _ in range(4):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # fenced code block 안에 들어간 HTML도 버립니다.
    text = re.sub(r"```(?:html|css|python|[a-zA-Z0-9_-]+)?\s*.*?```", "", text, flags=re.DOTALL)

    # style/script 블록과 CSS 조각 제거
    text = re.sub(r"<style\b[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script\b[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\.[\w-]+\s*\{[^{}]*\}", "", text, flags=re.DOTALL)

    # 줄바꿈 성격의 태그는 먼저 줄바꿈으로 바꿉니다.
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</\s*(div|p|li|section|article|h[1-6])\s*>", "\n", text, flags=re.IGNORECASE)

    # 남은 모든 HTML 태그 제거
    text = re.sub(r"<[^>]*>", "", text)

    # 태그 일부가 깨져 남은 경우도 정리
    text = re.sub(r"&lt;[^&\n]*(?:&gt;)?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</?[\w-]+(?:\s+[^>\n]*)?>", "", text)

    remove_patterns = [
        r"NOIR\s*STYLIST\s*TALKING",
        r"USER\s*REQUEST",
        r"ai-message",
        r"ai-bubble",
        r"ai-answer",
        r"bubble-label\s*dark",
        r"chat-row\s*ai-row",
        r"mini-avatar",
        r"mini-head",
        r"mini-hair",
        r"mini-glasses",
        r"mini-mouth",
        r"mini-name",
        r"class\s*=\s*['\"][^'\"]*['\"]",
        r"div\s+class",
    ]

    for pattern in remove_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = text.replace("**", "").replace("__", "").replace("&nbsp;", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = [line.strip(" \t-") for line in text.splitlines()]
    lines = [line for line in lines if line]

    return "\n".join(lines)


# ==============================
# Ollama call
# ==============================
def ask_ollama(prompt: str, model: str = "gemma3:1b") -> str:
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.5,
        },
    }

    response = requests.post(url, json=payload, timeout=180)
    response.raise_for_status()

    data = response.json()
    return clean_text(data.get("response", "답변을 가져오지 못했습니다."))


# ==============================
# Hero
# ==============================
def render_hero(situation: str, style: str, body_type: str, color_preference: str) -> None:
    hero_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        * {{
            box-sizing: border-box;
        }}

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

        .inner {{
            position: relative;
            z-index: 2;
        }}

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

        .brand-symbol::before {{
            left: -10px;
        }}

        .brand-symbol::after {{
            right: -10px;
        }}

        .menu {{
            display: flex;
            gap: 28px;
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 0.08em;
        }}

        .menu span {{
            border-bottom: 1px solid transparent;
            padding-bottom: 4px;
        }}

        .menu .active {{
            border-bottom: 1px solid #050505;
        }}

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
            font-size: 145px;
            line-height: 0.78;
            font-weight: 950;
            letter-spacing: -0.1em;
        }}

        .black-block {{
            display: inline-block;
            width: 210px;
            height: 82px;
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

        .character {{
            height: 245px;
            position: relative;
        }}

        .hair {{
            position: absolute;
            left: 50%;
            top: 15px;
            transform: translateX(-50%);
            width: 132px;
            height: 86px;
            background: #e8e8e4;
            border-radius: 70px 70px 20px 20px;
        }}

        .hair::before {{
            content: "";
            position: absolute;
            left: -20px;
            top: 18px;
            width: 52px;
            height: 92px;
            background: #e8e8e4;
            border-radius: 40px 12px 24px 34px;
            transform: rotate(12deg);
        }}

        .hair::after {{
            content: "";
            position: absolute;
            right: -20px;
            top: 18px;
            width: 52px;
            height: 92px;
            background: #e8e8e4;
            border-radius: 12px 40px 34px 24px;
            transform: rotate(-12deg);
        }}

        .face {{
            position: absolute;
            left: 50%;
            top: 60px;
            transform: translateX(-50%);
            width: 112px;
            height: 128px;
            background: #d6d6d1;
            border: 2px solid #e8e8e4;
            border-radius: 48% 48% 42% 42%;
        }}

        .glasses {{
            position: absolute;
            left: 17px;
            top: 43px;
            width: 78px;
            height: 22px;
            background: #050505;
        }}

        .nose {{
            position: absolute;
            left: 54px;
            top: 70px;
            width: 2px;
            height: 18px;
            background: #050505;
            opacity: 0.55;
        }}

        .mouth {{
            position: absolute;
            left: 41px;
            top: 97px;
            width: 32px;
            height: 7px;
            border-bottom: 2px solid #050505;
            border-radius: 0 0 22px 22px;
        }}

        .neck {{
            position: absolute;
            left: 50%;
            top: 180px;
            transform: translateX(-50%);
            width: 36px;
            height: 36px;
            background: #d6d6d1;
        }}

        .jacket {{
            position: absolute;
            left: 50%;
            bottom: 0;
            transform: translateX(-50%);
            width: 195px;
            height: 78px;
            background: #111;
            border: 2px solid #e8e8e4;
            border-bottom: none;
            clip-path: polygon(18% 0, 82% 0, 100% 100%, 0 100%);
        }}

        .character-name {{
            font-size: 26px;
            font-weight: 950;
            letter-spacing: -0.05em;
            margin-top: 16px;
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

        .option-list {{
            display: grid;
            gap: 8px;
        }}

        .option-list div {{
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid rgba(0,0,0,0.18);
            padding-bottom: 6px;
            font-size: 13px;
        }}

        .option-list span {{
            color: #555;
        }}

        .option-list b {{
            color: #050505;
        }}
    </style>
    </head>

    <body>
        <div class="canvas">
            <div class="inner">
                <div class="nav">
                    <div class="brand">
                        <div class="brand-symbol"></div>
                        <div>FIT TALK</div>
                    </div>

                    <div class="menu">
                        <span class="active">HOME</span>
                        <span>STYLING</span>
                        <span>LOCAL LLM</span>
                        <span>NOIR</span>
                        <span>ARCHIVE</span>
                    </div>
                </div>

                <div class="hero">
                    <div>
                        <div class="kicker">LOCAL LLM × CHARACTER STYLING × NO API KEY</div>

                        <div class="title">
                            <span class="black-block"></span>FIT<br>TALK
                        </div>

                        <div class="desc">
                            API Key 없이 로컬 LLM으로 실행되는<br>
                            AI Personal Styling Chatbot
                        </div>
                    </div>

                    <div class="character-card">
                        <div class="character-label">AI FASHION EDITOR</div>

                        <div class="character">
                            <div class="hair"></div>
                            <div class="face">
                                <div class="glasses"></div>
                                <div class="nose"></div>
                                <div class="mouth"></div>
                            </div>
                            <div class="neck"></div>
                            <div class="jacket"></div>
                        </div>

                        <div class="character-name">NOIR STYLIST</div>
                        <div class="character-desc">
                            당신의 상황과 분위기를 읽고<br>
                            오늘의 핏을 편집합니다.
                        </div>
                    </div>
                </div>

                <div class="info-grid">
                    <div class="info-card">
                        <div class="info-title">WHAT IS FIT TALK?</div>
                        <div class="info-text">
                            FIT TALK는 사용자의 체형, 상황, 원하는 분위기를 바탕으로
                            상의·하의·신발·액세서리 조합을 추천하는 AI 스타일링 챗봇입니다.
                            OpenAI나 Gemini API를 사용하지 않고 Ollama 로컬 LLM으로 답변을 생성합니다.
                        </div>
                    </div>

                    <div class="info-card">
                        <div class="info-title">CURRENT OPTION</div>
                        <div class="option-list">
                            <div><span>Situation</span><b>{html.escape(situation)}</b></div>
                            <div><span>Style</span><b>{html.escape(style)}</b></div>
                            <div><span>Body Type</span><b>{html.escape(body_type)}</b></div>
                            <div><span>Color</span><b>{html.escape(color_preference)}</b></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    components.html(hero_html, height=760, scrolling=False)


# ==============================
# Message renderers
# ==============================
def render_user_message(content: str) -> None:
    safe = html.escape(clean_text(content)).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="user-message-wrap">
            <div class="user-message">
                <div class="message-label">USER REQUEST</div>
                {safe}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ai_message(content: str) -> None:
    safe = html.escape(clean_text(content)).replace("\n", "<br>")

    st.markdown(
        f"""
        <div class="ai-message-wrap">
            <div class="ai-avatar-box">
                <div class="mini-head">
                    <div class="mini-hair"></div>
                    <div class="mini-glasses"></div>
                    <div class="mini-mouth"></div>
                </div>
                <div class="mini-name">NOIR<br>STYLIST</div>
            </div>

            <div class="ai-message">
                <div class="message-label dark">NOIR STYLIST TALKING</div>
                {safe}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_try_prompt() -> None:
    st.markdown(
        """
        <div class="try-box">
            <div class="try-title">TRY THIS PROMPT</div>
            <div class="try-text">
                키 175cm, 마른 체형이고 오늘 발표가 있어.
                너무 정장 같지는 않고 깔끔하게 입고 싶어.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==============================
# Sidebar
# ==============================
st.sidebar.markdown("## ⚙ FIT SETTINGS")
st.sidebar.caption("스타일 추천 조건을 선택하세요.")

if st.sidebar.button("🧹 대화 초기화", use_container_width=True):
    st.session_state[CHAT_STATE_KEY] = []
    st.session_state.pop("messages_v5", None)
    st.rerun()

st.sidebar.markdown("---")

model_name = st.sidebar.selectbox(
    "Local LLM Model",
    ["gemma3:1b"],
)

situation = st.sidebar.selectbox(
    "오늘의 상황",
    ["학교", "발표", "데이트", "카페", "면접", "여행", "친구 모임", "기타"],
)

style = st.sidebar.selectbox(
    "원하는 스타일",
    ["미니멀", "캐주얼", "스트릿", "포멀", "깔끔한 스타일", "힙한 스타일", "편한 스타일"],
)

body_type = st.sidebar.selectbox(
    "체형",
    ["마른 체형", "보통 체형", "큰 체형", "키가 작은 편", "키가 큰 편", "직접 입력"],
)

color_preference = st.sidebar.selectbox(
    "선호 색상",
    ["무채색", "블랙", "화이트", "네이비", "베이지", "밝은 색", "상관없음"],
)

st.sidebar.markdown("---")

st.sidebar.markdown(
    """
    <div class="sidebar-meta">
        <b>Local LLM</b>: Ollama + gemma3:1b<br>
        <b>API Key</b>: 사용하지 않음<br>
        <b>Cost</b>: API 비용 없음<br>
        <b>UI</b>: Character Chat Interface
    </div>
    """,
    unsafe_allow_html=True,
)


# ==============================
# Main view
# ==============================
render_hero(
    situation=situation,
    style=style,
    body_type=body_type,
    color_preference=color_preference,
)


# ==============================
# Chat history
# ==============================
if CHAT_STATE_KEY not in st.session_state:
    st.session_state[CHAT_STATE_KEY] = []


if len(st.session_state[CHAT_STATE_KEY]) == 0:
    render_try_prompt()


for message in st.session_state[CHAT_STATE_KEY]:
    if message["role"] == "user":
        render_user_message(message["content"])
    else:
        render_ai_message(message["content"])


# ==============================
# Chat input
# ==============================
user_input = st.chat_input(
    "오늘 어떤 스타일이 필요하세요? 예: 발표룩, 데이트룩, 스트릿룩"
)


# ==============================
# Input handling
# ==============================
if user_input:
    cleaned_user_input = clean_text(user_input)

    st.session_state[CHAT_STATE_KEY].append({
        "role": "user",
        "content": cleaned_user_input,
    })

    render_user_message(cleaned_user_input)

    conversation_history = ""

    for message in st.session_state[CHAT_STATE_KEY][-6:]:
        if message["role"] == "user":
            conversation_history += f"사용자: {clean_text(message['content'])}\n"
        else:
            conversation_history += f"AI: {clean_text(message['content'])}\n"

    prompt = f"""
너는 대학생을 위한 감각적인 AI 패션 스타일리스트야.
너의 이름은 NOIR STYLIST야.

중요:
- HTML, CSS, JavaScript, XML, Markdown 코드블록을 절대 출력하지 마.
- div, span, class, style 같은 코드 단어를 출력하지 마.
- 화면 구성이나 UI 코드를 설명하지 말고, 오직 패션 추천 문장만 출력해.

답변 규칙:
- 반드시 한국어로 답변해.
- 첫 문장은 반드시 "오늘의 무드는 ...입니다." 형식으로 시작해.
- 너무 비싼 브랜드명보다는 일반적인 옷 종류 중심으로 추천해.
- 사용자가 추가 질문을 하면 이전 대화 흐름을 반영해.
- 초보자도 이해할 수 있게 쉽게 설명해.
- 패션 잡지 에디터처럼 감각적이지만, 과하지 않게 말해.
- 사용자의 체형, 상황, 선호 색상을 반드시 반영해.
- 답변은 짧게 끊어서 보기 좋게 정리해.
- 마지막에 스타일 해시태그를 넣어.

현재 선택 옵션:
- 상황: {situation}
- 원하는 스타일: {style}
- 체형: {body_type}
- 선호 색상: {color_preference}

최근 대화 기록:
{conversation_history}

이번 사용자 질문:
{cleaned_user_input}

답변 형식:
오늘의 무드는 [스타일 이름]입니다.

[추천 코디]
- 상의:
- 하의:
- 신발:
- 액세서리:

[추천 이유]
왜 이 조합이 좋은지 설명해줘.

[피하면 좋은 조합]
상황이나 체형에 맞지 않을 수 있는 조합을 알려줘.

[Style Keywords]
#키워드 #키워드 #키워드
"""

    with st.spinner("NOIR STYLIST가 스타일을 분석하는 중입니다..."):
        try:
            ai_answer = ask_ollama(prompt, model_name)
            ai_answer = clean_text(ai_answer)

        except requests.exceptions.ConnectionError:
            ai_answer = "Ollama가 실행 중이 아닙니다. PowerShell에서 ollama run gemma3:1b 명령어를 실행해 주세요."
            st.error("Ollama 연결 실패")

        except requests.exceptions.Timeout:
            ai_answer = "답변 시간이 너무 오래 걸렸습니다. 질문을 조금 짧게 입력하거나 다시 시도해 주세요."
            st.error(ai_answer)

        except Exception as e:
            ai_answer = f"오류가 발생했습니다: {e}"
            st.error(ai_answer)

    render_ai_message(ai_answer)

    st.session_state[CHAT_STATE_KEY].append({
        "role": "assistant",
        "content": clean_text(ai_answer),
    })
