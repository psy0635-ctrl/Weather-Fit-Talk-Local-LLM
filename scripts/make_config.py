"""Streamlit 테마 설정 파일을 자동으로 만들어 주는 일회성 스크립트.

이미 .streamlit/config.toml 파일이 있으면 이 스크립트를 다시 실행할 필요는 없습니다.
테마 설정을 처음 만들거나 초기화하고 싶을 때만 실행하면 됩니다.
"""

import os

# .streamlit 폴더가 없으면 새로 만들고, 이미 있으면 그대로 둡니다.
os.makedirs(".streamlit", exist_ok=True)

# Streamlit이 읽을 테마 설정 내용입니다.
config_content = """[theme]
base = "dark"
backgroundColor = "#0E0E10"
secondaryBackgroundColor = "#111113"
textColor = "#F0EBE0"
primaryColor = "#C8A96E"
"""

# config.toml 파일에 위 설정 내용을 저장합니다.
with open(".streamlit/config.toml", "w", encoding="utf-8") as f:
    f.write(config_content)

# 실행 후 사용자가 정상 생성 여부를 확인할 수 있게 터미널에 출력합니다.
print("✅ .streamlit/config.toml 생성 완료")
print("내용 확인:")
print(config_content)
