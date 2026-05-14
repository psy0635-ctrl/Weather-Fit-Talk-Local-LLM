def contains_any(text: str, keywords: list[str]) -> bool:
    """문장 안에 키워드 중 하나라도 들어 있는지 확인합니다."""
    return any(keyword in text for keyword in keywords)


def infer_weather_from_user_input(user_input: str) -> dict:
    """사용자 질문에서 날씨, 기온, 바람 힌트를 찾아 dict로 반환합니다."""
    text = str(user_input or "").lower().replace(" ", "")
    inferred = {
        "weather_condition": None,
        "temperature_range": None,
        "wind_level": None,
        "weather_note": "",
    }
    notes = []

    if contains_any(text, ["덥다", "덥고", "더워", "더운", "더움", "무더워", "무더운", "땀", "습해", "습하고", "여름", "반팔"]):
        inferred["temperature_range"] = "31도 이상" if contains_any(text, ["무더워", "폭염", "땀", "너무더워"]) else "26~30도"
        notes.append("더운 날씨 표현")

    if contains_any(text, ["춥다", "추워", "추움", "쌀쌀", "한파", "겨울", "바람차다", "패딩", "코트"]):
        inferred["temperature_range"] = "영하" if contains_any(text, ["한파", "영하", "너무추워"]) else "0~5도"
        notes.append("추운 날씨 표현")

    if contains_any(text, ["비", "비와", "비오", "우산", "장마", "젖"]):
        inferred["weather_condition"] = "비"
        notes.append("비 표현")

    if contains_any(text, ["눈", "눈와", "눈오", "빙판", "미끄러"]):
        inferred["weather_condition"] = "눈"
        notes.append("눈 표현")

    if inferred["weather_condition"] is None and contains_any(text, ["흐림", "흐려", "흐리고", "구름"]):
        inferred["weather_condition"] = "흐림"
        notes.append("흐린 날씨 표현")

    if contains_any(text, ["강풍", "바람많이", "바람세", "바람강", "바람이많이"]):
        inferred["wind_level"] = "강함"
        notes.append("강한 바람 표현")
    elif contains_any(text, ["바람"]):
        inferred["wind_level"] = "보통"
        notes.append("바람 표현")

    if notes:
        inferred["weather_note"] = "사용자 입력에서 " + ", ".join(notes) + "을 감지함"

    return inferred


def infer_style_from_user_input(user_input: str, selected_style: str) -> str:
    """사용자 질문의 스타일 표현을 사이드바 선택보다 우선해서 판단합니다."""
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

    return selected_style if selected_style != "자동 추천" else "자동 추천"


def choose_auto_style(weather_condition: str, temperature_range: str, wind_level: str, situation: str) -> str:
    """자동 추천일 때 날씨와 상황에 맞는 스타일 후보를 고릅니다."""
    if situation in ["발표", "면접"]:
        return "포멀 또는 깔끔한 스타일"
    if situation == "운동/산책":
        return "편한 스타일"
    if temperature_range in ["26~30도", "31도 이상"]:
        return "캐주얼, 편한 스타일, 스트릿 중 하나"
    if situation == "등교" and weather_condition == "비":
        return "캐주얼 또는 스트릿"
    if weather_condition in ["비", "눈"] and wind_level == "강함":
        return "캐주얼, 편한 스타일, 스트릿 중 하나"
    return "캐주얼, 스트릿, 깔끔한 스타일 중 하나"


def merge_user_weather_with_sidebar(
    user_weather: dict,
    sidebar_weather_condition: str,
    sidebar_temperature_range: str,
    sidebar_wind_level: str,
) -> tuple[str, str, str, str]:
    """사용자 입력에서 감지한 날씨 값이 있으면 사이드바 값보다 우선 적용합니다."""
    final_weather_condition = user_weather.get("weather_condition") or sidebar_weather_condition
    final_temperature_range = user_weather.get("temperature_range") or sidebar_temperature_range
    final_wind_level = user_weather.get("wind_level") or sidebar_wind_level
    weather_note = user_weather.get("weather_note") or "사용자 입력에서 별도 날씨 표현이 없어 사이드바 값을 사용함"

    return final_weather_condition, final_temperature_range, final_wind_level, weather_note


def build_weather_keywords(weather_condition: str, temperature_range: str, wind_level: str) -> str:
    """날씨, 기온, 바람 조건을 추천에 참고할 키워드로 정리합니다."""
    keywords = []

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

    wind_map = {
        "거의 없음": ["핏이 흐트러지지 않는 코디"],
        "약함": ["얇은 겉옷", "가벼운 레이어드"],
        "보통": ["고정감 있는 아우터", "짧지 않은 하의"],
        "강함": ["방풍 아우터", "펄럭이지 않는 실루엣", "고정 가능한 모자"],
    }

    keywords.extend(weather_map.get(weather_condition, []))
    keywords.extend(temperature_map.get(temperature_range, []))
    keywords.extend(wind_map.get(wind_level, []))

    return ", ".join(dict.fromkeys(keywords))


def build_style_keywords(style: str, color_preference: str) -> str:
    """선택한 스타일과 선호 색상을 추천 방향 키워드로 구체화합니다."""
    if "또는" in style or "," in style or "중 하나" in style:
        auto_keywords = [
            style,
            "2~3가지 스타일 옵션",
            "날씨와 상황에 맞는 선택지",
            "미니멀 고정 금지",
        ]
        color_keywords = {
            "관계없음": ["각 스타일에 어울리는 색감"],
            "무채색": ["무채색 팔레트", "블랙", "그레이", "화이트"],
            "블랙": ["블랙 중심", "선명한 대비", "시크한 분위기"],
            "화이트": ["화이트 포인트", "깨끗한 인상", "밝은 톤"],
            "네이비": ["네이비", "단정한 분위기", "화이트 또는 그레이 매치"],
            "베이지": ["베이지", "따뜻한 톤", "브라운 또는 아이보리 매치"],
            "밝은 색": ["밝은 포인트", "산뜻한 톤", "가벼운 무드"],
        }.get(color_preference, [])
        return ", ".join(dict.fromkeys(auto_keywords + color_keywords))

    style_map = {
        "자동 추천": ["날씨와 상황에 맞는 2~3가지 스타일 후보", "미니멀 고정 금지", "다양한 선택지"],
        "미니멀": ["간결한 실루엣", "무채색", "과하지 않은 포인트", "깔끔한 핏", "기본 아이템 중심"],
        "캐주얼": ["데일리룩", "편안한 핏", "기본 티셔츠", "데님", "스니커즈", "자연스러운 분위기"],
        "스트릿": ["오버핏", "후디", "카고팬츠", "와이드 팬츠", "볼캡", "스니커즈", "레이어드"],
        "포멀": ["셔츠", "슬랙스", "재킷", "로퍼", "단정한 실루엣", "발표/면접에 어울리는 분위기"],
        "깔끔한 스타일": ["단정한 니트", "셔츠", "슬랙스", "정돈된 색 조합", "과하지 않은 코디"],
        "힙한 스타일": ["와이드 팬츠", "레이어드", "포인트 액세서리", "개성 있는 실루엣", "스트릿 감성"],
        "편한 스타일": ["스웨트셔츠", "조거팬츠", "편한 스니커즈", "활동성", "부드러운 소재"],
        "러블리": ["부드러운 색감", "니트", "스커트", "작은 포인트", "따뜻한 분위기"],
    }

    color_map = {
        "관계없음": ["선택한 스타일에 어울리는 색감"],
        "무채색": ["무채색 팔레트", "블랙", "그레이", "화이트"],
        "블랙": ["블랙 중심", "선명한 대비", "시크한 분위기"],
        "화이트": ["화이트 포인트", "깨끗한 인상", "밝은 톤"],
        "네이비": ["네이비", "단정한 분위기", "화이트 또는 그레이 매치"],
        "베이지": ["베이지", "따뜻한 톤", "브라운 또는 아이보리 매치"],
        "밝은 색": ["밝은 포인트", "산뜻한 톤", "가벼운 무드"],
    }

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
    weather_note: str = "",
) -> str:
    """최종 보정된 조건을 프롬프트용 문장으로 정리합니다."""
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
    if weather_note:
        lines.append(f"- 날씨 판단 근거: {weather_note}")
    return "\n".join(lines)


def get_weather_warning(weather_condition: str, temperature_range: str, wind_level: str) -> str:
    """오늘 조건에서 피하면 좋은 옷차림 힌트를 만듭니다."""
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

    if temperature_range in ["영하", "0~5도"]:
        warnings.extend(["얇은 반팔 단독 착용", "보온 없는 하의"])
    elif temperature_range in ["26~30도", "31도 이상"]:
        warnings.extend(["두꺼운 레이어드", "열이 갇히는 합성 소재", "패딩이나 두꺼운 코트"])

    if wind_level == "강함":
        warnings.extend(["펄럭이는 긴 스커트", "날아가기 쉬운 모자", "고정 안 되는 우산"])

    if not warnings:
        warnings.append("날씨와 상황에 맞지 않는 과한 레이어드")

    return ", ".join(dict.fromkeys(warnings))
