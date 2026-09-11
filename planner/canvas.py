from pathlib import Path

import streamlit as st

CANVAS_VERSION = "0.8.0-1"
ROOT = Path(__file__).parent
HTML = """
<div class="canvas-shell">
  <h1>도면 가구 배치</h1>
  <label class="room-picker"><span class="visually-hidden">호실 선택</span><select aria-label="호실 선택"></select></label>
  <div class="canvas-tools">
    <button type="button" data-tool="out" aria-label="도면 축소">−</button>
    <output class="zoom-value" aria-live="polite">100%</output>
    <button type="button" data-tool="in" aria-label="도면 확대">＋</button>
    <button type="button" data-tool="fit">화면 맞춤</button>
    <button type="button" class="assist-toggle" aria-pressed="true">정렬 보조 켬</button>
    <span class="canvas-help">빈 도면 탭: 가구 추가</span>
  </div>
  <div class="utility-tools" role="group" aria-label="설비 표시 도구">
    <button type="button" data-utility="" aria-pressed="true">가구 조작</button>
    <button type="button" data-utility="water" aria-pressed="false"><span class="utility-dot water"></span>수도</button>
    <button type="button" data-utility="electric" aria-pressed="false"><span class="utility-dot electric"></span>전기</button>
    <button type="button" data-utility="three_phase" aria-pressed="false"><span class="utility-dot three-phase"></span>전기 3상</button>
  </div>
  <p class="utility-help">종류 선택 후 도면을 눌러 점 표시 · 점을 누르면 삭제 메뉴</p>
  <div class="canvas-viewport"><svg id="planner-svg" role="application" aria-label="가구 배치 작업판" tabindex="0"></svg></div>
  <button class="delete-badge" type="button" aria-label="선택 가구 삭제" hidden>×</button>
  <button class="delete-done" type="button" hidden>삭제 모드 완료</button>
  <div class="furniture-menu" role="region" aria-label="가구 편집" hidden></div>
  <p class="canvas-message" role="status"></p>
</div>
"""
CSS = (ROOT / "canvas.css").read_text(encoding="utf-8")
JS = (ROOT / "gesture.mjs").read_text(encoding="utf-8").replace("export class", "class") + "\n" + (ROOT / "canvas.js").read_text(encoding="utf-8")
planner_canvas = st.components.v2.component("floorplan_furniture_canvas_v08_1", html=HTML, css=CSS, js=JS)
