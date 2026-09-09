# 도면 가구 배치 (Floorplan Furniture Planner)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://hynx9cgxdvl7xfesmdm3ys.streamlit.app/)

도면 이미지를 배경으로 실제 치수의 사각형 가구를 배치하고, 방 안에 들어가는지와 가구끼리 겹치는지를 확인하는 Streamlit 앱입니다.

- 공개 앱: https://hynx9cgxdvl7xfesmdm3ys.streamlit.app/

## 현재 기능 (v0.1)

- PNG, JPG, PDF 첫 페이지 도면 불러오기
- 직사각형 공간의 실제 가로·세로 입력(mm)
- 가구의 실제 가로·세로 입력 및 도면 위 드래그
- 0°/90° 회전
- 같은 그룹 이름을 가진 가구의 동시 이동
- 벽 이탈, 가구 겹침, 벽 여유 공간 판정
- `.fplan` 프로젝트 저장 및 불러오기

첫 버전에서는 업로드한 도면 전체를 입력한 직사각형 공간에 맞춰 표시합니다. 정확한 비교를 위해 방 또는 공간의 안쪽 경계에 맞춰 자른 도면을 사용하세요.

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
