# 개발 인수인계와 배포 절차

## 역할 분리

- app.py: UI와 Streamlit 세션 상태. workspace.project와 project는 동일 객체여야 한다.
- planner/workspace.py: 호실별 객체 소유, 호실 전환, v2 파일 입출력, 한국 시간 파일명.
- planner/models.py: 단일 호실과 가구. circle은 width_mm == depth_mm인 지름.
- planner/geometry.py: 실제 mm 단위 판정. 화면 배율과 독립.
- planner/canvas.py: SVG 표시와 이벤트. 비율 변환은 getScreenCTM().inverse() 사용.
- planner/project_io.py: v1 단일 호실 입출력. 기존 파일 호환을 유지한다.
- planner/presets.py: 처음 여는 호실의 기본값에만 apply. 재방문 시 apply 금지.

## 다음 개발자가 지켜야 할 사항

1. 사용자 요구사항과 CHANGELOG를 먼저 대조한다. 완료를 알리기 전 누락 여부 확인.
2. 호실 전환·저장·불러오기·드래그 입력값 동기화에 회귀 테스트를 추가한다.
3. 파일 읽기 크기 제한과 스키마 검증 유지. 업로드 파일 내용을 실행하지 않는다.
4. 공유 저장/외부 데이터베이스는 사용자 승인 없이 추가하지 않는다.
5. PDF 원본, 배치도, 층 전체 도면을 추가 공개하지 않는다.
6. 매 빌드 CHANGELOG에 버전·변경·검증·미해결 항목을 기록하고 UI 버전과 맞춘다.
7. python -m pytest -q, python -m ruff check ., git diff --check 실행.
8. 상호 의존 파일은 가능한 한 한 커밋으로 배포. main 최신 상태를 확인하고 강제 갱신 금지.
9. 공개 앱에서 호실 왕복, 배율, 원형, 숫자 편집, 드래그, 텍스트 편집 중 Delete 보호를 확인.
10. 확인하지 못한 검증은 통과라고 기록하지 말고 명시한다.
