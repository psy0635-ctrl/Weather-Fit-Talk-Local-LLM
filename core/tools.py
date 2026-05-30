"""WEATHER FIT TALK에서 쓰는 보조 함수 모음.

app.py가 화면과 실행 흐름을 담당한다면, 이 파일은 실제 판단 로직을 담당합니다.
예를 들어 사용자의 문장에서 "비", "덥다", "바람" 같은 힌트를 찾고,
그 결과를 LLM 프롬프트에 넣기 좋은 키워드 문장으로 바꿉니다.
"""


def contains_any(text: str, keywords: list[str]) -> bool:
    """문장 안에 키워드 중 하나라도 들어 있는지 확인합니다."""
    # ──────────────────────────────────────────────────────────────────────────
    # [any() 함수 설명]
    #
    # any(이터러블) → 이터러블(리스트, 제너레이터 등) 안에 True인 값이 하나라도 있으면 True 반환.
    # 아래 코드를 풀어 쓰면:
    #
    #   for keyword in keywords:
    #       if keyword in text:
    #           return True
    #   return False
    #
    # any()를 쓰면 이걸 한 줄로 표현할 수 있습니다.
    # 또한 any()는 True를 찾자마자 나머지 검사를 멈추는(short-circuit) 최적화도 합니다.
    #
    # 예: contains_any("오늘 비 와", ["비", "우산", "장마"])
    #     → "비" in "오늘 비 와" → True → 즉시 True 반환
    # ──────────────────────────────────────────────────────────────────────────
    return any(keyword in text for keyword in keywords)


def infer_weather_from_user_input(user_input: str) -> dict:
    """사용자 질문에서 날씨, 기온, 바람 힌트를 찾아 dict로 반환합니다."""
    # ──────────────────────────────────────────────────────────────────────────
    # 사용자가 채팅창에 직접 쓴 문장에서 날씨 정보를 추정합니다.
    # 예: "덥다"가 있으면 더운 기온, "비 와"가 있으면 비 오는 날씨로 판단합니다.
    #
    # .lower() → 대소문자 구분 없이 비교하기 위해 소문자로 변환
    # .replace(" ", "") → "비 와" 처럼 공백이 끼어있어도 "비와"로 검색 가능하게 처리
    # ──────────────────────────────────────────────────────────────────────────
    text = str(user_input or "").lower().replace(" ", "")

    # 결과를 담을 딕셔너리입니다.
    # 초기값은 모두 None → "아직 찾지 못했다"는 의미
    # 나중에 merge_user_weather_with_sidebar()에서 None인 값은 사이드바 값으로 채웁니다.
    inferred = {
        "weather_condition": None,
        "temperature_range": None,
        "wind_level": None,
        "weather_note": "",   # 어떤 표현을 감지했는지 기록 (디버깅/프롬프트용)
    }
    notes = []  # 감지된 날씨 표현을 기록하는 리스트

    # ── 기온 추론 ─────────────────────────────────────────────────────────────
    # "덥다", "무더워", "땀" 등이 있으면 더운 날씨로 판단합니다.
    if contains_any(text, ["덥다", "덥고", "더워", "더운", "더움", "무더워", "무더운", "땀", "습해", "습하고", "여름", "반팔"]):
        # 더 강한 더위 표현이 있으면 31도 이상, 그냥 더우면 26~30도
        inferred["temperature_range"] = "31도 이상" if contains_any(text, ["무더워", "폭염", "땀", "너무더워"]) else "26~30도"
        notes.append("더운 날씨 표현")

    # elif: 덥다/춥다는 동시에 성립할 수 없으므로 else if를 사용합니다.
    elif contains_any(text, ["춥다", "추워", "추움", "쌀쌀", "한파", "겨울", "바람차다"]):
        inferred["temperature_range"] = "영하" if contains_any(text, ["한파", "영하", "너무추워"]) else "0~5도"
        notes.append("추운 날씨 표현")

    # ── 강수 추론 ─────────────────────────────────────────────────────────────
    # 비와 눈은 독립적으로 감지합니다 (elif가 아닌 if를 씀 → 기온과 무관하게 항상 확인)
    if contains_any(text, ["비", "비와", "비오", "우산", "장마", "젖"]):
        inferred["weather_condition"] = "비"
        notes.append("비 표현")

    if contains_any(text, ["눈", "눈와", "눈오", "빙판", "미끄러"]):
        inferred["weather_condition"] = "눈"
        notes.append("눈 표현")

    # 비/눈이 없을 때만 흐림으로 판단합니다.
    # (비가 오면서 흐림이라고 중복 판단하는 걸 방지)
    if inferred["weather_condition"] is None and contains_any(text, ["흐림", "흐려", "흐리고", "구름"]):
        inferred["weather_condition"] = "흐림"
        notes.append("흐린 날씨 표현")

    # ── 바람 추론 ─────────────────────────────────────────────────────────────
    # "강풍", "바람 많이" 등이 있으면 강함으로, 그냥 "바람"이면 보통으로 판단합니다.
    if contains_any(text, ["강풍", "바람많이", "바람세", "바람강", "바람이많이"]):
        inferred["wind_level"] = "강함"
        notes.append("강한 바람 표현")
    elif contains_any(text, ["바람"]):
        inferred["wind_level"] = "보통"
        notes.append("바람 표현")

    # 감지된 표현들을 notes 문자열로 정리합니다.
    # ", ".join(리스트) → ["비 표현", "바람 표현"] → "비 표현, 바람 표현"
    if notes:
        inferred["weather_note"] = "사용자 입력에서 " + ", ".join(notes) + "을 감지함"

    return inferred


def infer_style_from_user_input(user_input: str, selected_style: str) -> str:
    """사용자 질문의 스타일 표현을 사이드바 선택보다 우선해서 판단합니다."""
    # 사용자가 질문에 스타일을 직접 언급했다면, 사이드바 선택보다 우선합니다.
    # 예: 사이드바가 "캐주얼"이어도 "스트릿으로 입고 싶어"라고 쓰면 "스트릿"을 반환합니다.
    text = str(user_input or "").lower().replace(" ", "")

    if "미니멀" in text:
        return "미니멀"
    if contains_any(text, ["스트릿", "오버핏", "후드", "후디", "카고", "와이드"]):
        return "스트릿"
    if contains_any(text, ["힙", "힙하게", "개성"]):
        return "힙한 스타일"
    if contains_any(text, ["포멀", "발표", "면접", "단정"]):
        return "포멀"
    if contains_any(text, ["캐주얼", "데일리"]):
        return "캐주얼"
    if contains_any(text, ["편하게", "편한", "활동성", "산책"]):
        return "편한 스타일"
    if contains_any(text, ["깔끔하게", "깔끔한", "깔끔"]):
        return "깔끔한 스타일"

    # 스타일 힌트가 없으면 사이드바 선택값을 그대로 반환합니다.
    # "자동 추천"이면 "자동 추천" 문자열을 반환 → 이후 choose_auto_style()이 처리합니다.
    return selected_style if selected_style != "자동 추천" else "자동 추천"


def choose_auto_style(weather_condition: str, temperature_range: str, wind_level: str, situation: str) -> str:
    """자동 추천일 때 날씨와 상황에 맞는 스타일 후보를 고릅니다."""
    # 스타일이 "자동 추천"으로 설정되어 있을 때만 호출됩니다.
    # LLM이 하나의 스타일로 고정하는 게 아니라 2~3가지 후보를 제안하도록 방향을 잡아줍니다.

    # 발표/면접은 상황 특성상 포멀하거나 깔끔한 스타일이 적합합니다.
    if situation in ["발표", "면접"]:
        return "포멀 또는 깔끔한 스타일"
    if situation == "운동/산책":
        return "편한 스타일"
    # 더운 날씨에는 가볍고 통기성 있는 스타일이 적합합니다.
    if temperature_range in ["26~30도", "31도 이상"]:
        return "캐주얼, 편한 스타일, 스트릿 중 하나"
    if situation == "등교" and weather_condition == "비":
        return "캐주얼 또는 스트릿"
    if weather_condition in ["비", "눈"] and wind_level == "강함":
        return "캐주얼, 편한 스타일, 스트릿 중 하나"
    # 특별한 조건이 없으면 가장 일반적인 후보군을 반환합니다.
    return "캐주얼, 스트릿, 깔끔한 스타일 중 하나"


def merge_user_weather_with_sidebar(
    user_weather: dict,
    sidebar_weather_condition: str,
    sidebar_temperature_range: str,
    sidebar_wind_level: str,
) -> tuple[str, str, str, str]:
    """사용자 입력에서 감지한 날씨 값이 있으면 사이드바 값보다 우선 적용합니다."""
    # ──────────────────────────────────────────────────────────────────────────
    # [tuple 반환 타입 설명]
    #
    # tuple[str, str, str, str] → 문자열 4개를 묶은 튜플을 반환한다는 타입 힌트입니다.
    # 호출하는 쪽에서 이렇게 받습니다:
    #   a, b, c, d = merge_user_weather_with_sidebar(...)
    # 이걸 "언패킹(unpacking)"이라고 합니다.
    #
    # [or 연산자로 기본값 처리]
    # user_weather.get("weather_condition") or sidebar_weather_condition
    #   → user_weather에서 꺼낸 값이 None 또는 빈 문자열("")이면
    #     자동으로 sidebar_weather_condition 값을 사용합니다.
    #
    # 파이썬에서 None, 0, "", [], {} 같은 값은 조건문에서 False로 평가됩니다.
    # 그래서 "A or B" 는 "A가 False(빈값)면 B를 사용하라"는 패턴으로 자주 씁니다.
    # ──────────────────────────────────────────────────────────────────────────
    final_weather_condition = user_weather.get("weather_condition") or sidebar_weather_condition
    final_temperature_range = user_weather.get("temperature_range") or sidebar_temperature_range
    final_wind_level = user_weather.get("wind_level") or sidebar_wind_level
    weather_note = user_weather.get("weather_note") or "사용자 입력에서 별도 날씨 표현이 없어 사이드바 값을 사용함"

    return final_weather_condition, final_temperature_range, final_wind_level, weather_note


def build_weather_keywords(weather_condition: str, temperature_range: str, wind_level: str) -> str:
    """날씨, 기온, 바람 조건을 추천에 참고할 키워드로 정리합니다."""
    # ──────────────────────────────────────────────────────────────────────────
    # LLM은 구체적인 키워드가 많을수록 더 안정적이고 현실적인 답변을 생성합니다.
    # 여기서는 날씨/기온/바람 조건을 실제 옷차림 추천 키워드로 변환합니다.
    #
    # 딕셔너리 매핑 방식을 쓰는 이유:
    #   if/elif 여러 개 대신 딕셔너리로 "조건 → 키워드" 표를 만들면
    #   나중에 항목을 추가/수정하기가 훨씬 쉽습니다.
    # ──────────────────────────────────────────────────────────────────────────
    keywords = []

    # 날씨별로 추천에 참고할 소재, 아이템, 주의점을 모아 둔 표입니다.
    weather_map = {
        "맑음": ["가벼운 레이어드", "자외선 대비", "밝은 포인트"],
        "흐림": ["차분한 색감", "얇은 아우터", "레이어드"],
        "비": ["방수 아우터", "미끄럼 방지 신발", "어두운 하의", "접이식 우산"],
        "눈": ["보온 아우터", "방수 신발", "미끄럼 방지 밑창", "니트 소품"],
        "안개": ["밝은 포인트", "시야 확보", "가벼운 방풍 아우터"],
        "미세먼지": ["세탁 쉬운 겉옷", "마스크", "먼지 덜 붙는 소재"],
        "폭염": ["통기성 좋은 소재", "밝은 색", "얇은 상의", "샌들 또는 가벼운 운동화"],
        "추위": ["두꺼운 아우터", "보온 이너", "머플러", "장갑"],
        "일교차 큼": ["탈착 쉬운 아우터", "얇은 겹옷", "긴팔 이너"],
    }

    # 기온별로 두께감과 계절감을 정하는 키워드입니다.
    temperature_map = {
        "영하": ["패딩", "기모", "히트텍", "목도리"],
        "0~5도": ["코트", "두꺼운 니트", "부츠", "보온 이너"],
        "6~10도": ["자켓", "니트", "긴바지", "가벼운 머플러"],
        "11~15도": ["트렌치코트", "가디건", "셔츠 레이어드"],
        "16~20도": ["얇은 니트", "맨투맨", "데님", "가벼운 자켓"],
        "21~25도": ["셔츠", "반팔 위 얇은 겉옷", "면바지"],
        "26~30도": ["반팔", "린넨", "통 넓은 하의", "얇은 소재"],
        "31도 이상": ["민소매 또는 반팔", "흡습속건", "밝은 색", "모자"],
    }

    # 바람 세기에 따라 날리는 옷, 고정 가능한 모자/우산 등을 조절합니다.
    wind_map = {
        "거의 없음": ["핏이 흐트러지지 않는 코디"],
        "약함": ["얇은 겉옷", "가벼운 레이어드"],
        "보통": ["고정감 있는 아우터", "짧지 않은 하의"],
        "강함": ["방풍 아우터", "펄럭이지 않는 실루엣", "고정 가능한 모자"],
    }

    # .get(키, 기본값) → 키에 해당하는 리스트를 꺼냅니다. 없으면 빈 리스트 [] 반환.
    keywords.extend(weather_map.get(weather_condition, []))
    keywords.extend(temperature_map.get(temperature_range, []))
    keywords.extend(wind_map.get(wind_level, []))

    # ──────────────────────────────────────────────────────────────────────────
    # [dict.fromkeys()를 이용한 중복 제거]
    #
    # 세 개의 map에서 키워드를 합치면 중복이 생길 수 있습니다.
    # 예: "얇은 겉옷"이 weather_map과 wind_map 양쪽에 있을 경우.
    #
    # set()으로도 중복을 제거할 수 있지만, set은 순서를 보장하지 않습니다.
    # dict.fromkeys(리스트)는 딕셔너리의 키 특성(중복 불가)을 이용해
    # 원래 순서를 유지하면서 중복을 제거합니다.
    # 예: dict.fromkeys(["a", "b", "a", "c"]) → {"a": None, "b": None, "c": None}
    #     → 키만 꺼내면 ["a", "b", "c"] (순서 유지, 중복 제거)
    # ──────────────────────────────────────────────────────────────────────────
    return ", ".join(dict.fromkeys(keywords))


def build_style_keywords(style: str, color_preference: str) -> str:
    """선택한 스타일과 선호 색상을 추천 방향 키워드로 구체화합니다."""
    # ──────────────────────────────────────────────────────────────────────────
    # "자동 추천" 또는 여러 스타일 후보(예: "캐주얼, 스트릿 중 하나")인 경우:
    # 하나의 스타일로 고정하지 않고 여러 방향을 열어두는 키워드를 만듭니다.
    #
    # "또는", ","(쉼표), "중 하나" 가 style 문자열에 있으면 자동 추천 경우입니다.
    # ──────────────────────────────────────────────────────────────────────────
    if "또는" in style or "," in style or "중 하나" in style:
        auto_keywords = [
            style,
            "2~3가지 스타일 옵션",
            "날씨와 상황에 맞는 선택지",
            "미니멀 고정 금지",
        ]
        # 색상 선호에 따른 키워드를 color_keywords 변수에 저장합니다.
        color_keywords = {
            "관계없음": ["각 스타일에 어울리는 색감"],
            "무채색": ["무채색 팔레트", "블랙", "그레이", "화이트"],
            "블랙": ["블랙 중심", "선명한 대비", "시크한 분위기"],
            "화이트": ["화이트 포인트", "깨끗한 인상", "밝은 톤"],
            "네이비": ["네이비", "단정한 분위기", "화이트 또는 그레이 매치"],
            "베이지": ["베이지", "따뜻한 톤", "브라운 또는 아이보리 매치"],
            "밝은 색": ["밝은 포인트", "산뜻한 톤", "가벼운 무드"],
        }.get(color_preference, [])   # .get(키, []) → 없는 색상이면 빈 리스트 반환
        return ", ".join(dict.fromkeys(auto_keywords + color_keywords))

    # 특정 스타일이 선택된 경우: 그 스타일에 맞는 아이템/실루엣 키워드를 정의합니다.
    style_map = {
        "자동 추천": ["날씨와 상황에 맞는 2~3가지 스타일 후보", "미니멀 고정 금지", "다양한 선택지"],
        "미니멀": ["간결한 실루엣", "무채색", "과하지 않은 포인트", "깔끔한 핏", "기본 아이템 중심"],
        "캐주얼": ["데일리룩", "편안한 핏", "기본 티셔츠", "데님", "스니커즈", "자연스러운 분위기"],
        "스트릿": ["오버핏", "후디", "카고팬츠", "와이드 팬츠", "볼캡", "스니커즈", "레이어드"],
        "포멀": ["셔츠", "슬랙스", "재킷", "로퍼", "단정한 실루엣", "발표/면접에 어울리는 분위기"],
        "깔끔한 스타일": ["단정한 니트", "셔츠", "슬랙스", "정돈된 색 조합", "과하지 않은 코디"],
        "힙한 스타일": ["와이드 팬츠", "레이어드", "포인트 액세서리", "개성 있는 실루엣", "스트릿 감성"],
        "편한 스타일": ["스웨트셔츠", "조거팬츠", "편한 스니커즈", "활동성", "부드러운 소재"],
    }

    # 색상 선호에 따른 키워드 매핑입니다.
    color_map = {
        "관계없음": ["선택한 스타일에 어울리는 색감"],
        "무채색": ["무채색 팔레트", "블랙", "그레이", "화이트"],
        "블랙": ["블랙 중심", "선명한 대비", "시크한 분위기"],
        "화이트": ["화이트 포인트", "깨끗한 인상", "밝은 톤"],
        "네이비": ["네이비", "단정한 분위기", "화이트 또는 그레이 매치"],
        "베이지": ["베이지", "따뜻한 톤", "브라운 또는 아이보리 매치"],
        "밝은 색": ["밝은 포인트", "산뜻한 톤", "가벼운 무드"],
    }

    # style_map.get(style, [style]) → style이 딕셔너리에 없으면 [style] 자체를 키워드로 사용
    keywords = style_map.get(style, [style]) + color_map.get(color_preference, [])
    return ", ".join(dict.fromkeys(keywords))


def build_context_summary(
    location: str,
    weather_condition: str,
    temperature_range: str,
    wind_level: str,
    situation: str,
    style: str,
    body_type: str,
    color_preference: str,
    weather_note: str = "",  # 기본값이 ""이므로 이 인자를 생략해도 됩니다.
) -> str:
    """최종 보정된 조건을 프롬프트용 문장으로 정리합니다."""
    # 최종 결정된 조건을 사람이 읽기 쉬운 목록 형태의 문자열로 만듭니다.
    # 이 문자열은 prompts.py에서 LLM 프롬프트의 CONTEXT_LAYER로 들어갑니다.
    lines = [
        f"- 지역: {location}",
        f"- 최종 날씨: {weather_condition}",
        f"- 최종 기온: {temperature_range}",
        f"- 최종 바람: {wind_level}",
        f"- 상황: {situation}",
        f"- 최종 스타일: {style}",
        f"- 체형: {body_type}",
        f"- 선호 색상: {color_preference}",
    ]
    # weather_note가 있을 때만(빈 문자열이 아닐 때만) 추가합니다.
    if weather_note:
        lines.append(f"- 날씨 판단 근거: {weather_note}")
    # "\n".join(리스트) → 리스트의 항목들을 줄바꿈으로 연결해 하나의 문자열로 만듭니다.
    return "\n".join(lines)


def search_duckduckgo(query: str, max_results: int = 5) -> str:
    """DuckDuckGo 검색 결과를 LLM 프롬프트에 넣기 좋은 짧은 문자열로 정리합니다."""
    # ──────────────────────────────────────────────────────────────────────────
    # [선택적 라이브러리 import 패턴]
    #
    # 검색 기능(ddgs)은 선택적 기능이어서 일부 환경에는 설치되지 않을 수 있습니다.
    # 함수 맨 위에서 import하면 라이브러리가 없을 때 앱 자체가 시작부터 죽어버립니다.
    #
    # 해결책: 함수 안에서 try/except ImportError로 import를 감쌉니다.
    #   라이브러리가 없으면 ImportError가 발생하고,
    #   except 블록에서 사용자에게 안내 문자열을 반환합니다.
    #   → 앱 전체가 멈추지 않고 이 기능만 비활성화됩니다.
    # ──────────────────────────────────────────────────────────────────────────
    if not query or not query.strip():
        return "검색어가 비어 있어 DuckDuckGo 검색을 실행하지 않았습니다."

    try:
        from ddgs import DDGS
    except ImportError:
        return "ddgs 패키지가 설치되어 있지 않습니다. requirements.txt 설치 후 검색을 사용할 수 있습니다."

    try:
        results = []

        # ──────────────────────────────────────────────────────────────────────
        # [with 문(컨텍스트 매니저) 사용 이유]
        #
        # with DDGS() as ddgs: 는 "DDGS 객체를 만들고, 블록이 끝나면 자동으로 닫아라"는 뜻입니다.
        # 네트워크 연결처럼 열고 닫아야 하는 자원을 사용할 때,
        # with 문을 쓰면 오류가 나도 자원이 자동으로 해제되어 메모리 누수를 방지합니다.
        # ──────────────────────────────────────────────────────────────────────
        with DDGS() as ddgs:
            for item in ddgs.text(query.strip(), max_results=max_results):
                title = str(item.get("title", "")).strip()
                body = str(item.get("body", "")).strip()
                href = str(item.get("href", "")).strip()

                # 제목도 내용도 없는 결과는 건너뜁니다.
                if not title and not body:
                    continue

                # 각 검색 결과를 LLM이 읽기 좋은 형식으로 만듭니다.
                # [:120] → 문자열을 최대 120자로 자름 (프롬프트 길이 최적화)
                results.append(
                    "\n".join(
                        [
                            f"- 제목: {title[:120]}",
                            f"  요약: {body[:240]}",
                            f"  링크: {href[:200]}",
                        ]
                    )
                )

        if not results:
            return "검색 결과를 찾지 못했습니다."

        # "\n".join(results) → 각 검색 결과를 줄바꿈으로 이어붙인 하나의 문자열로 반환
        return "\n".join(results)

    except Exception as error:
        # 네트워크 오류, 서비스 차단 등 예상치 못한 오류도 문자열로 반환합니다.
        # 앱이 멈추는 것보다 안내 메시지를 보여주는 것이 낫기 때문입니다.
        return f"검색 중 오류가 발생했습니다: {error}"


def get_weather_warning(weather_condition: str, temperature_range: str, wind_level: str) -> str:
    """오늘 조건에서 피하면 좋은 옷차림 힌트를 만듭니다."""
    # ──────────────────────────────────────────────────────────────────────────
    # 이 함수는 "하지 말아야 할 조합"을 미리 정리해 LLM 프롬프트에 넣어줍니다.
    # 예: 비 오는 날 스웨이드 신발 → 젖어서 망가짐
    #     폭염에 패딩 → 너무 더움
    #
    # LLM은 이 경고 키워드를 보고 부적절한 추천을 피할 수 있게 됩니다.
    # ──────────────────────────────────────────────────────────────────────────
    warnings = []

    if weather_condition == "비":
        warnings.extend(["밝은 바지", "밑창이 미끄러운 신발", "젖기 쉬운 스웨이드 소재"])
    elif weather_condition == "눈":
        warnings.extend(["얇은 단화", "바닥 접지력이 약한 신발", "발목이 드러나는 코디"])
    elif weather_condition == "폭염":
        warnings.extend(["두꺼운 니트", "검정색 두꺼운 아우터", "통풍 안 되는 소재"])
    elif weather_condition == "추위":
        warnings.extend(["얇은 외투 하나만 입기", "짧은 양말", "목이 드러나는 상의"])
    elif weather_condition == "미세먼지":
        warnings.extend(["먼지가 잘 붙는 니트 겉옷", "세탁 어려운 아우터"])

    # 기온이 낮거나 높을 때도 피해야 할 조합을 추가합니다.
    # in 연산자로 여러 조건을 한번에 확인합니다: "영하" in ["영하", "0~5도"]
    if temperature_range in ["영하", "0~5도"]:
        warnings.extend(["얇은 반팔 단독 착용", "보온 없는 하의"])
    elif temperature_range in ["26~30도", "31도 이상"]:
        warnings.extend(["두꺼운 레이어드", "열이 갇히는 합성 소재", "패딩이나 두꺼운 코트"])

    if wind_level == "강함":
        warnings.extend(["펄럭이는 긴 스커트", "날아가기 쉬운 모자", "고정 안 되는 우산"])

    # 경고 항목이 하나도 없으면 일반적인 주의 사항을 추가합니다.
    if not warnings:
        warnings.append("날씨와 상황에 맞지 않는 과한 레이어드")

    # dict.fromkeys()로 혹시 있을 중복을 제거하고 쉼표로 이어붙입니다.
    return ", ".join(dict.fromkeys(warnings))
