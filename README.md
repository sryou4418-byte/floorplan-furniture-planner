# 도면 가구 배치 (Floorplan Furniture Planner)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://hynx9cgxdvl7xfesmdm3ys.streamlit.app/)

도면 이미지를 배경으로 실제 치수의 사각형 가구를 배치하고, 방 안에 들어가는지와 가구끼리 겹치는지를 확인하는 Streamlit 앱입니다.

- 공개 앱: https://hynx9cgxdvl7xfesmdm3ys.streamlit.app/

## 현재 기능 (v0.1)

- PNG, JPG, PDF 첫 페이지 도면 불러오기
- 제공된 PDF 2·3페이지를 기준으로 한 1층·2층 호실 23개 선택
- 데스크톱 화면에서 방 전체가 보이는 작업판 자동 맞춤
- 직사각형 공간의 실제 가로·세로 입력(mm)
- 가구의 실제 가로·세로 입력 및 도면 위 드래그
- 도면 드래그 좌표와 숫자 입력 좌표의 실시간 동기화
- 선택 가구의 `Delete` 또는 `Backspace` 키 삭제
- 0°/90° 회전
- 같은 그룹 이름을 가진 가구의 동시 이동
- 벽 이탈, 가구 겹침, 벽 여유 공간 판정
- `.fplan` 프로젝트 저장 및 불러오기

기본 호실은 원본 문서의 1페이지 배치도를 포함하지 않고, 2페이지(1층)와 3페이지(2층)의 각 실 내부만 분리해 사용합니다. 사용자가 직접 올린 도면은 전체를 입력한 직사각형 공간에 맞춰 표시하므로 정확한 비교를 위해 방 안쪽 경계에 맞춰 자른 도면을 사용하세요.

기본 호실의 가로·세로는 도면의 구조 그리드를 기준으로 한 공칭치수입니다. 벽 두께와 마감 등을 제외한 실제 내부 유효치수는 현장 또는 상세 도면으로 별도 확인해야 합니다.

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## 테스트

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

## 다음 단계

- 도면의 두 점과 실제 길이를 이용한 축척 보정
- 다각형 방과 여러 방 지원
- 문, 창문, 기둥 및 문 열림 반경
- 다중 선택 그룹 생성/해제 UI
- 가구 간 권장 통로 폭 검사
- 실행 취소/다시 실행과 여러 배치안 비교
