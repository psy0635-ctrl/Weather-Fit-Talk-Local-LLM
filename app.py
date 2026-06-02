"""WEATHER FIT TALK 메인 실행 파일.

이 파일은 Streamlit 화면을 만들고, 사용자가 입력한 조건을 정리한 뒤,
Ollama 로컬 LLM에 프롬프트를 보내 코디 추천 답변을 화면에 보여줍니다.

처음 읽을 때는 아래 순서로 보면 이해하기 쉽습니다.
1. 기본 설정과 모델 목록
2. 화면을 그리는 함수들
3. 사이드바 입력값
4. 사용자가 질문했을 때 실행되는 처리 흐름
"""

# textwrap: Python 기본 내장 라이브러리.
#           textwrap.dedent()는 여러 줄 문자열에서 공통으로 들여쓰기된 공백을 제거함.
#           사이드바 하단 메타 정보 HTML 블록의 앞쪽 공백을 제거하려고 사용.
import textwrap

# requests: 외부 라이브러리(pip install). HTTP 요청(GET/POST)을 보내는 도구.
#           여기서는 Ollama 서버에 POST 요청으로 프롬프트를 보내고 답변을 받는 데 사용.
import requests

# streamlit: 외부 라이브러리(pip install). Python 코드만으로 웹 앱을 만드는 프레임워크.
#            st.sidebar, st.chat_input, st.markdown 등으로 화면 요소를 쉽게 만들 수 있음.
import streamlit as st

# core/prompts.py는 LLM에 전달할 긴 프롬프트를 조립하는 역할만 담당합니다.
from core.prompts import build_weather_fit_prompt

# core/tools.py에는 날씨/스타일 추론, 검색, 키워드 생성, 텍스트 정제 함수들이 있습니다.
from core.tools import (
    build_context_summary,
    build_style_keywords,
    build_weather_keywords,
    choose_auto_style,
    clean_text,
    get_weather_warning,
    infer_style_from_user_input,
    infer_weather_from_user_input,
    merge_user_weather_with_sidebar,
    search_duckduckgo,
)

# core/ui.py에는 Streamlit 화면을 그리는 render_* 함수들이 있습니다.
from core.ui import (
    build_conversation_history,
    render_ai_message,
    render_hero,
    render_try_prompt,
    render_user_message,
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
    document.querySelectorAll(
        '[data-testid="stChatInput"] textarea'
    ).forEach(el => {
        el.style.setProperty('color', '#F0EBE0', 'important');
        el.style.setProperty('-webkit-text-fill-color', '#F0EBE0', 'important');
        el.style.setProperty('caret-color', '#F0EBE0', 'important');
        el.style.setProperty('background', 'transparent', 'important');
    });

    // 채팅 입력창 배경 고정
    document.querySelectorAll(
        '[data-testid="stChatInput"] > div'
    ).forEach(el => {
        el.style.setProperty('background', 'rgba(240,235,224,0.06)', 'important');
        el.style.setProperty('border', '1px solid rgba(240,235,224,0.20)', 'important');
        el.style.setProperty('border-radius', '10px', 'important');
    });

    // 채팅 하단 컨테이너 배경 고정
    document.querySelectorAll(
        '[data-testid="stBottomBlockContainer"]'
    ).forEach(el => {
        el.style.setProperty('background', '#111113', 'important');
    });

    // 사이드바 텍스트 입력창(지역) 색상 고정
    document.querySelectorAll(
        '[data-testid="stSidebar"] input'
    ).forEach(el => {
        el.style.setProperty('color', '#F0EBE0', 'important');
        el.style.setProperty('-webkit-text-fill-color', '#F0EBE0', 'important');
        el.style.setProperty('caret-color', '#F0EBE0', 'important');
        el.style.setProperty('background', 'rgba(240,235,224,0.08)', 'important');
        el.style.setProperty('border', '1px solid rgba(240,235,224,0.20)', 'important');
    });

    // 전송 버튼 색상
    document.querySelectorAll(
        '[data-testid="stChatInputSubmitButton"], ' +
        '[data-testid="stChatInput"] button'
    ).forEach(el => {
        el.style.setProperty('background', '#C8A96E', 'important');
        el.style.setProperty('color', '#0E0E10', 'important');
        el.style.setProperty('border-radius', '6px', 'important');
    });

    // 사이드바 토글 버튼 색상 고정
    document.querySelectorAll(
        '[data-testid="collapsedControl"] button, ' +
        '[data-testid="stSidebarCollapsedControl"] button, ' +
        '[data-testid="stSidebarCollapseButton"] button, ' +
        'button[aria-label="Open sidebar"], ' +
        'button[aria-label="Close sidebar"]'
    ).forEach(el => {
        el.style.setProperty('background', '#C8A96E', 'important');
        el.style.setProperty('border', '2px solid #C8A96E', 'important');
        el.style.setProperty('border-radius', '50%', 'important');
        el.style.setProperty('min-width', '38px', 'important');
        el.style.setProperty('min-height', '38px', 'important');
        el.style.setProperty('display', 'flex', 'important');
        el.style.setProperty('visibility', 'visible', 'important');
        el.style.setProperty('opacity', '1', 'important');
        el.style.setProperty('z-index', '9999999', 'important');
    });

    // 사이드바 토글 버튼 아이콘 색상 고정
    document.querySelectorAll(
        '[data-testid="collapsedControl"] button svg *, ' +
        '[data-testid="stSidebarCollapsedControl"] button svg *, ' +
        '[data-testid="stSidebarCollapseButton"] button svg *, ' +
        'button[aria-label="Open sidebar"] svg *, ' +
        'button[aria-label="Close sidebar"] svg *'
    ).forEach(el => {
        el.style.setProperty('fill', '#0E0E10', 'important');
        el.style.setProperty('stroke', '#0E0E10', 'important');
        el.style.setProperty('opacity', '1', 'important');
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


# ──────────────────────────────────────────────────────────────────────────────
# [앱 실행 시작 지점]
# 위에서 함수들을 정의했고, 아래부터는 실제로 실행되는 코드입니다.
# Streamlit은 이 파일을 위에서 아래로 순서대로 실행합니다.
# ──────────────────────────────────────────────────────────────────────────────

# 앱 시작 시 CSS를 먼저 적용합니다.
load_css("static/style.css")



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
