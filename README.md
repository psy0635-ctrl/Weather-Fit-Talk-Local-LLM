# FIT TALK — Local LLM Personal Styling Chatbot

## 1. 프로젝트 소개

FIT TALK는 사용자의 체형, 상황, 원하는 스타일을 입력받아  
AI가 개인 맞춤형 코디를 추천해주는 웹 기반 스타일링 챗봇입니다.

이 프로젝트는 OpenAI나 Gemini API를 사용하지 않고,  
Ollama를 이용해 로컬 LLM을 실행하여 AI 답변을 생성합니다.

## 2. 제작 배경

많은 사람들이 발표, 데이트, 학교, 친구 모임 등 다양한 상황에서  
어떤 옷을 입어야 할지 고민합니다.

FIT TALK는 이러한 고민을 해결하기 위해  
사용자의 상황, 체형, 선호 스타일을 바탕으로  
상의, 하의, 신발, 액세서리 조합을 추천하는 챗봇입니다.

## 3. 주요 기능

- 상황별 코디 추천
- 체형 기반 핏 추천
- 선호 스타일 반영
- 선호 색상 반영
- 추천 이유 설명
- 피하면 좋은 조합 안내
- OpenAI/Gemini API 없이 로컬 LLM으로 답변 생성

## 4. 사용 기술

| 구분 | 사용 기술 |
|---|---|
| Language | Python |
| Web Framework | Streamlit |
| Local LLM Tool | Ollama |
| LLM Model | gemma3:1b |
| HTTP Request | requests |
| Version Control | GitHub |

## 5. 실행 방법

### 1. Ollama 모델 실행

```bash
ollama run gemma3:1b