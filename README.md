# 🌦️ WEATHER FIT TALK

> **날씨 × 패션 AI 스타일링 챗봇** — Ollama 로컬 LLM 기반

[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-웹UI-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Ollama](https://img.shields.io/badge/Ollama-LocalLLM-black)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📌 프로젝트 소개

**WEATHER FIT TALK**는 날씨·기온·바람·상황·스타일을 종합 분석하여  
오늘 입기 좋은 코디를 추천해주는 **로컬 LLM 기반 AI 스타일링 챗봇**입니다.

OpenAI / Gemini **API Key 없이** Ollama 로컬 모델만으로 실행됩니다.

```
💬 사용자: "오늘 비 오고 바람이 불어. 학교 갈 때 뭐 입을까?"

🤖 AI:  날씨·상황·스타일 분석
        → 상의 / 하의 / 아우터 / 신발 / 소품까지 구체적으로 추천
```

---

## 🎯 제작 목적

| # | 목표 |
|---|------|
| 1 | 로컬 LLM을 활용한 챗봇 직접 구현 |
| 2 | **API Key 없이 실행 가능한** AI 서비스 설계 |
| 3 | Streamlit 웹 UI 제작 |
| 4 | 사용자 입력 기반 조건 추론 기능 구현 |
| 5 | DuckDuckGo 검색 결과를 활용한 확장 기능 추가 |
| 6 | 날씨 + 스타일을 결합한 코디 추천 시스템 구현 |

---

## ✨ 핵심 기능

| 기능 | 설명 |
|------|------|
| 🌤️ **날씨 기반 코디 추천** | 날씨·기온·바람 조건에 맞는 옷차림 추천 |
| 🏫 **상황별 추천** | 등교, 발표, 면접, 데이트, 여행 등 상황 반영 |
| 👗 **스타일 선택** | 자동 추천 / 미니멀 / 캐주얼 / 스트릿 / 포멀 선택 가능 |
| 🧠 **사용자 입력 우선** | 사이드바 조건보다 **사용자가 직접 입력한 표현을 우선** 반영 |
| 🖥️ **로컬 LLM 사용** | Ollama 기반 로컬 모델로 답변 생성 |
| 🔍 **DuckDuckGo 검색** | 선택 시 검색 결과를 참고하여 더 풍부한 답변 생성 |
| 💸 **API 비용 없음** | OpenAI / Gemini API Key **불필요** |
| 🌐 **웹 UI 제공** | Streamlit 기반 웹 페이지로 실행 |

---

## 🛠️ 사용 기술

| 구분 | 기술 |
|------|------|
| 언어 | Python |
| 웹 프레임워크 | Streamlit |
| LLM 실행 환경 | **Ollama** |
| 사용 모델 | `gemma4:e4b` / `gemma3:4b` / `gemma3:1b` |
| 웹 검색 | DuckDuckGo Search (`ddgs`) |
| HTTP 요청 | requests |
| 스타일링 | CSS |

---

## 📁 프로젝트 구조

```
Weather-Fit-Talk-Local-LLM/
│
├── app.py              # Streamlit 메인 실행 파일
├── prompts.py          # LLM 프롬프트 레이어 정의
├── tools.py            # 날씨·스타일 추론 및 DuckDuckGo 검색 기능
├── style.css           # 웹 UI 디자인
├── requirements.txt    # 필요한 Python 라이브러리 목록
└── README.md           # 프로젝트 설명 문서
```

### 📄 파일 역할

**`app.py`** — 웹 페이지 구성, 사이드바 옵션, 사용자 입력 처리, Ollama LLM 호출, CSS 로드

**`prompts.py`** — 시스템 역할 정의, HTML/CSS 출력 금지 규칙, 사용자 입력 우선 규칙, 최종 답변 형식 지정

**`tools.py`** — 날씨·스타일 추론, 자동 스타일 추천, 키워드 생성, DuckDuckGo 검색 실행 및 결과 요약

**`style.css`** — 블랙 기반 에디토리얼 스타일, 아이보리 카드 UI, Streamlit 기본 UI 커스터마이징

---

## ⚙️ 설치 및 실행

### 1. 프로젝트 클론

```bash
git clone https://github.com/psy0635-ctrl/Weather-Fit-Talk-Local-LLM.git
cd 레포지토리이름
```

### 2. 가상환경 생성 및 활성화

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\activate
```

> ⚠️ PowerShell 보안 오류 발생 시 먼저 실행:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

### 3. 라이브러리 설치

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Ollama 설치 확인

```bash
ollama --version
```

> Ollama가 없다면 [공식 사이트](https://ollama.com)에서 설치하세요.

### 5. 모델 다운로드

```bash
# 권장 모델
ollama pull gemma3:4b

# 저사양 환경용 경량 모델
ollama pull gemma3:1b

# 고성능 모델
ollama pull gemma4:e4b
```

### 6. Ollama 모델 실행 (터미널 1)

```bash
ollama run gemma3:4b
```

### 7. Streamlit 실행 (터미널 2)

```bash
python -m streamlit run app.py
```

브라우저에서 접속: **http://localhost:8501**

---

## 💬 사용 방법

1. **왼쪽 사이드바**에서 조건 선택
   - 지역 / 오늘의 날씨 / 기온 / 바람
   - 오늘의 상황 / 원하는 스타일 / 체형 / 선호 색상

2. 필요 시 **DuckDuckGo 검색 사용** 체크

3. **하단 입력창**에 질문 입력

```
💬 예시 질문

"오늘 비 오고 바람이 불어. 학교 갈 때 뭐 입을까?"
"오늘 30도이고 발표하러 가. 스트릿으로 밝은 색 추천해줘."
"날씨가 쌀쌀한데 데이트 갈 때 깔끔하게 입고 싶어."
```

---

## 🔄 로직 흐름

```
사용자 입력
    ↓
Streamlit 웹 앱
    ↓
날씨 / 스타일 자동 추론
    ↓
사이드바 조건 + 사용자 입력 병합
    ↓
DuckDuckGo 검색 여부 확인 (선택)
    ↓
프롬프트 생성 (멀티 레이어)
    ↓
Ollama 로컬 LLM 호출
    ↓
HTML/CSS 코드 제거 → 웹 화면에 답변 출력
```

---

## 🧠 프롬프트 설계

프롬프트는 **8개 레이어**로 구성됩니다.

| 레이어 | 역할 |
|--------|------|
| `SYSTEM_LAYER` | AI 역할 정의 |
| `SAFETY_LAYER` | HTML/CSS 출력 금지 |
| `USER_INPUT_PRIORITY_LAYER` | **사용자 입력 우선 규칙** |
| `STYLE_PRIORITY_LAYER` | 스타일 우선 규칙 |
| `WEB_SEARCH_LAYER` | 검색 결과 활용 규칙 |
| `RULE_LAYER` | 답변 작성 규칙 |
| `RECOMMENDATION_LAYER` | 코디 추천 기준 |
| `OUTPUT_FORMAT_LAYER` | **최종 답변 형식 지정** |

---

## ✅ 답변 형식 예시

```
오늘의 결론:
오늘처럼 비가 오고 바람이 부는 날에는 방수성과 활동성을 모두 고려한 캐주얼 코디가 좋습니다.

오늘의 무드:
비 오는 날의 깔끔한 캐주얼룩

추천 코디:
- 상의: 얇은 니트 또는 맨투맨
- 하의: 어두운 색 데님 또는 면바지
- 아우터: 방수 가능한 바람막이
- 신발: 미끄럼 방지 스니커즈
- 소품: 작은 우산 또는 크로스백

날씨 대응 포인트:
- 기온: 얇은 레이어드로 체온 조절
- 비/눈/습도: 젖어도 티가 덜 나는 색상 추천
- 바람: 펄럭이지 않는 아우터 추천
- 활동성: 등교 상황에 맞게 편안한 신발 추천

피하면 좋은 조합:
- 밝은색 긴 바지 / 미끄러운 구두

한 줄 요약:
비 오는 날에는 방수 아우터와 편한 신발을 중심으로 깔끔하게 입는 것이 좋습니다.

스타일 키워드:
#비오는날코디 #캐주얼룩 #등교룩
```

---

## ⚠️ 주의 사항

> **앱 실행 전 반드시 Ollama 모델이 실행 중이어야 합니다.**

```bash
# 모델 목록 확인
ollama list
```

- `app.py`에서 선택한 **모델명이 설치된 모델명과 일치**해야 합니다.
- DuckDuckGo 검색을 사용하려면 `ddgs` 설치가 필요합니다: `pip install ddgs`
- 답변에 HTML 코드가 섞이는 경우 → `prompts.py` UTF-8 저장 여부 확인 → `clean_text` 함수 적용 확인 → Streamlit 재실행 → `Ctrl + F5`

---

## 🚀 향후 개선 방향

- [ ] 실제 날씨 API 연동
- [ ] 지역 자동 감지 기능
- [ ] 스타일 이미지 추천 기능
- [ ] 사용자 옷장 데이터 저장
- [ ] 모바일 반응형 UI 개선
- [ ] 추천 코디 저장 기능
- [ ] GitHub Pages / Render 배포
- [ ] 발표용 모드 추가

---

## 👨‍💻 제작자

**박수용**

> WEATHER FIT TALK는 날씨와 상황에 맞는 옷차림을 추천하는 로컬 LLM 기반 AI 스타일링 챗봇입니다.
