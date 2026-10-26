# 자기주도학습 AI 시연 앱

교과목 및 학습 어려움에 따른 **학습전략 추천 → 학생의 직접 수행 → 학습일지 AI 브리핑 → 학생이 선택하는 다음 목표**를 보여주는 독립 기능 시연 앱입니다.

이 저장소는 **공개 저장소**입니다. 기존 비공개 연구용 앱, 평가용 계정, 데이터베이스, 학생 정보 및 API 키를 복사하지 않았습니다.

## Streamlit Cloud 배포 설정

- Repository: \`seulyi2332/sdl-ai-preview\`
- Branch: \`main\`
- Main file path: \`ai_preview_app.py\`
- App URL: 사용 가능한 이름을 선택

Cloud에서 새 앱을 만든 후 해당 **새 앱의 Advanced settings → Secrets**에만 아래 항목을 직접 지정합니다.

\`\`\`toml
OPENAI_API_KEY = "새 앱에 설정할 본인의 OpenAI API 키"
OPENAI_MODEL = "gpt-4o-mini"
\`\`\`

실제 키를 코드, GitHub 이슈, 채팅 또는 스크린샷에 노출하지 마세요. 평가 앱의 기존 API 키 값은 공개 저장소로 복사하지 마세요. API 사용에는 요금이 발생할 수 있습니다.

## 로컬 실행

\`\`\`bash
pip install -r requirements.txt
streamlit run ai_preview_app.py
\`\`\`

## 구현된 기능

- 24개 카탈로그 학습전략을 활용한 과목 및 어려움 기반 추천; 키가 있는 경우 OpenAI가 이유와 실행 과제 구성
- 비교표, 풀이, 회상, 설명, 글쓰기 등의 학습자 직접 수행 기록
- 학습일지 자유 작성 및 원문 근거가 있는 학습경험 추출
- AI가 작성하는 수정 가능한 학습 브리핑 초안
- 확인 전에는 저장되지 않는 목표 제안과 학생의 직접 선택
- 시연 전용 목표 및 할 일 표

## 구현 범위 및 주의사항

- **원본 연구용 프로토타입과 DB가 연동되지 않는 시연 버전**입니다. 아직 17개 설계원리 39개 세부지침 전체를 지원하지 않습니다.
- Streamlit Community Cloud 서버의 로컬 SQLite는 **재시작 시 삭제될 수 있습니다.** 영구 연구자료로 사용하지 마세요.
- \`DEMO01\` 같은 공개 시연 코드는 안전한 사용자 인증이 아닙니다. **실제 학생 정보, 비공개 강의자료, 개인적인 일기를 입력하지 마세요.**
- AI API 키가 없을 때는 카탈로그 추천만 제공하며, AI 브리핑을 실제로 생성한 척하지 않습니다.
- 사용자 평가에 사용하는 기존 앱을 변경하지 않았습니다.

## 자동 테스트

\`\`\`bash
python -m unittest discover -s tests -p 'test_ai_upgrade.py' -v
python -m py_compile ai_preview_app.py sdl_upgrade/*.py
\`\`\`
