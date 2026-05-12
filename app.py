import streamlit as st
import requests

# ==============================
# 페이지 기본 설정
# ==============================
st.set_page_config(
    page_title="FIT TALK Local LLM",
    page_icon="👕",
    layout="centered"
)

# ==============================
# 제목 영역
# ==============================
st.title("👕 FIT TALK")
st.subheader("AI Personal Styling Chatbot with Local LLM")

st.write(
    """
    이 챗봇은 OpenAI/Gemini API를 사용하지 않고,  
    내 컴퓨터에서 실행되는 로컬 LLM(Ollama)을 이용해 코디를 추천합니다.
    """
)

# ==============================
# 사이드바 옵션
# ==============================
st.sidebar.title("스타일 옵션")

model_name = st.sidebar.selectbox(
    "사용할 로컬 모델",
    ["gemma3:1b"]
)

situation = st.sidebar.selectbox(
    "오늘의 상황",
    ["학교", "발표", "데이트", "카페", "면접", "여행", "친구 모임", "기타"]
)

style = st.sidebar.selectbox(
    "원하는 스타일",
    ["미니멀", "캐주얼", "스트릿", "포멀", "깔끔한 스타일", "힙한 스타일", "편한 스타일"]
)

body_type = st.sidebar.selectbox(
    "체형",
    ["마른 체형", "보통 체형", "큰 체형", "키가 작은 편", "키가 큰 편", "직접 입력"]
)

color_preference = st.sidebar.selectbox(
    "선호 색상",
    ["무채색", "블랙", "화이트", "네이비", "베이지", "밝은 색", "상관없음"]
)

# ==============================
# 사용자 입력
# ==============================
user_input = st.text_area(
    "오늘 어떤 스타일이 필요하세요?",
    placeholder="예: 키 175cm, 마른 체형이고 오늘 발표가 있어서 깔끔하게 입고 싶어."
)

# ==============================
# Ollama 호출 함수
# ==============================
def ask_ollama(prompt: str, model: str) -> str:
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=payload, timeout=180)
    response.raise_for_status()

    data = response.json()
    return data.get("response", "답변을 가져오지 못했습니다.")


# ==============================
# 추천 버튼
# ==============================
if st.button("추천 받기"):
    if not user_input:
        st.warning("먼저 내용을 입력해주세요.")
    else:
        prompt = f"""
너는 대학생을 위한 친절한 AI 패션 스타일리스트야.

사용자의 체형, 상황, 원하는 분위기를 바탕으로
상의, 하의, 신발, 액세서리 조합을 추천해줘.

너무 비싼 브랜드명보다는 일반적인 옷 종류 중심으로 추천해줘.
초보자도 이해할 수 있게 쉽게 설명해줘.
답변은 반드시 한국어로 해줘.

반드시 아래 형식으로 답변해줘.

1. 추천 스타일 이름
2. 상의 추천
3. 하의 추천
4. 신발 추천
5. 액세서리 추천
6. 추천 이유
7. 피하면 좋은 조합

[선택 옵션]
- 상황: {situation}
- 원하는 스타일: {style}
- 체형: {body_type}
- 선호 색상: {color_preference}

[사용자 입력]
{user_input}
"""

        with st.spinner("로컬 LLM이 스타일을 추천하는 중입니다..."):
            try:
                ai_answer = ask_ollama(prompt, model_name)

                st.success("추천이 완료되었습니다!")
                st.markdown(ai_answer)

            except requests.exceptions.ConnectionError:
                st.error("Ollama가 실행 중이 아닙니다.")
                st.write("먼저 PowerShell에서 아래 명령어를 실행해 주세요.")
                st.code("ollama run gemma3:1b", language="powershell")

            except requests.exceptions.Timeout:
                st.error("답변 시간이 너무 오래 걸렸습니다.")
                st.write("잠시 후 다시 시도하거나 더 짧게 질문해 주세요.")

            except Exception as e:
                st.error("오류가 발생했습니다.")
                st.write(e)