from __future__ import annotations

import base64

import streamlit as st

from planner.actions import apply_action
import planner.canvas as canvas_module

from planner.geometry import analyze, occupied_ratio
from planner.models import Furniture, Room
from planner.presets import PRESETS_BY_LABEL
from planner.workspace import Workspace, download_name, export_workspace, import_workspace

# A running Cloud worker can retain the previous imported component after deploy.
if getattr(canvas_module, "CANVAS_VERSION", None) != "0.3.0":
    import importlib

    importlib.reload(canvas_module)
planner_canvas = canvas_module.planner_canvas


VERSION = "0.3.0"
st.set_page_config(page_title="도면 가구 배치", page_icon="📐", layout="wide", initial_sidebar_state="collapsed")
st.html("""<style>
[data-testid="stMainBlockContainer"] { padding: 3.6rem 1.5rem 1rem; max-width: 1600px; }
[data-testid="stVerticalBlock"] { gap: .55rem; }
h1 { font-size: 1.35rem !important; padding: 0 !important; }
[data-testid="stExpander"] { border-radius: 12px; }
@media(max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding: 3.3rem .65rem .75rem; }
  h1 { font-size: 1.15rem !important; }
  button { min-height: 44px; }
  [data-testid="stTextInput"] input { font-size: 16px; }
}
</style>""")


def init_state():
    if "workspace" not in st.session_state:
        work = Workspace()
        work.open_room("1층 · 컴퓨터")
        st.session_state.workspace = work
    st.session_state.project = st.session_state.workspace.project
    st.session_state.setdefault("selected_ids", [])
    st.session_state.setdefault("room_choice", st.session_state.workspace.active)


def change_room():
    st.session_state.project = st.session_state.workspace.open_room(st.session_state.room_choice)
    st.session_state.selected_ids = []


def event_payload(name):
    event = st.session_state.get("planner_canvas")
    payload = getattr(event, name, None) if event else None
    if payload and payload.get("room_key") == st.session_state.workspace.active:
        return payload
    return None


def update_from_canvas():
    payload = event_payload("move")
    if payload:
        moves = {m["id"]: m for m in payload["moves"]}
        for item in st.session_state.project.furniture:
            if item.id in moves:
                item.x_mm = round(float(moves[item.id]["x_mm"]), 1)
                item.y_mm = round(float(moves[item.id]["y_mm"]), 1)
                for axis in ("x", "y"):
                    key = f"{axis}_{item.id}"
                    if key in st.session_state:
                        st.session_state[key] = getattr(item, f"{axis}_mm")
        st.session_state.selected_ids = list(moves)


def select_from_canvas():
    payload = event_payload("select")
    if payload:
        st.session_state.selected_ids = payload["ids"]


def delete_from_canvas():
    payload = event_payload("delete")
    if payload:
        project = st.session_state.project
        project.furniture = [f for f in project.furniture if f.id not in payload["ids"]]
        st.session_state.selected_ids = []


def run_action(action, item_id, name=""):
    try:
        st.session_state.selected_ids = apply_action(st.session_state.project, action, item_id, name)
        key = f"name_{item_id}"
        if action == "rename" and key in st.session_state:
            st.session_state[key] = name.strip()
    except ValueError as exc:
        st.session_state.notice = str(exc)


def action_from_canvas():
    payload = event_payload("action")
    if payload:
        run_action(payload["action"], payload["id"], payload.get("name", ""))


def image_data_url(project):
    if project.plan_image_bytes:
        mime = project.plan_image_mime or "image/png"
        return f"data:{mime};base64,{base64.b64encode(project.plan_image_bytes).decode('ascii')}"
    return None


def status_payload(project):
    palette = {"ok": ("rgba(52,199,89,.35)", "#248a3d"),
               "warning": ("rgba(255,159,10,.4)", "#c93400"),
               "error": ("rgba(255,69,58,.4)", "#d70015")}
    items = []
    for f in project.furniture:
        fill, stroke = palette[analyze(project.room, f, project.furniture).level]
        items.append({"id": f.id, "name": f.name, "width_mm": f.width_mm, "depth_mm": f.depth_mm,
                      "x_mm": f.x_mm, "y_mm": f.y_mm, "rotation": f.rotation,
                      "group": f.group, "shape": f.shape, "fill": fill, "stroke": stroke})
    return items


init_state()
project = st.session_state.project
st.title("도면 가구 배치")

with st.sidebar:
    st.caption(f"v{VERSION} · 성환고 호실 배치")
    st.subheader("저장 / 불러오기")
    imported = st.file_uploader("프로젝트 불러오기", type=["fplan"], key="project_upload")
    if imported and st.button("프로젝트 적용", use_container_width=True):
        try:
            work = import_workspace(imported.getvalue())
            st.session_state.workspace = work
            st.session_state.project = work.project
            st.session_state.room_choice = work.active
            st.session_state.selected_ids = []
            for key in list(st.session_state):
                if key.startswith(("x_", "y_", "w_", "d_", "name_", "g_", "c_")):
                    del st.session_state[key]
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    save_area = st.empty()
    st.caption("모든 호실을 파일 하나에 저장해요. 새로고침·종료 전에 저장해 주세요.")
    st.caption("도면은 공칭치수 기준입니다. 벽 안쪽 유효치수와 차이가 있을 수 있어요.")

options = list(PRESETS_BY_LABEL)
if st.session_state.workspace.active == "직접 설정":
    options.insert(0, "직접 설정")
st.selectbox("호실", options, key="room_choice", on_change=change_room, label_visibility="collapsed")
if "notice" in st.session_state:
    st.warning(st.session_state.pop("notice"))

# Place the work area first, render its current data after the editing forms.
canvas_area = st.empty()
status_area = st.empty()
add_column, edit_column = st.columns(2, gap="medium")
with add_column, st.expander("＋ 가구 추가", expanded=False):
    shape_label = st.radio("가구 모양", ["사각형", "원형"], horizontal=True)
    with st.form("add_furniture", clear_on_submit=True):
        name = st.text_input("가구 이름", max_chars=80, placeholder="예: 책상")
        width = st.number_input("지름 (mm)" if shape_label == "원형" else "가구 가로 (mm)", min_value=1.0, value=1200.0, step=50.0)
        depth = width if shape_label == "원형" else st.number_input("가구 세로 (mm)", min_value=1.0, value=600.0, step=50.0)
        group = st.text_input("그룹 이름", help="같은 그룹은 함께 움직여요.")
        if st.form_submit_button("가구 추가", use_container_width=True):
            try:
                item = Furniture(name=name.strip(), width_mm=width, depth_mm=depth, group=group.strip(),
                                 shape="circle" if shape_label == "원형" else "rectangle")
                item.validate()
                project.furniture.append(item)
                st.session_state.selected_ids = [item.id]
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

selected = next((f for f in project.furniture if f.id in st.session_state.selected_ids), None)
with edit_column, st.expander("선택 가구 편집", expanded=False):
    if selected:
        st.caption("우클릭 또는 길게 누르기로 이름 변경·회전·복사·삭제할 수 있어요.")
        with st.form(f"edit_{selected.id}"):
            edit_name = st.text_input("선택 가구 이름", selected.name, max_chars=80, key=f"name_{selected.id}")
            x = st.number_input("왼쪽 위치 X", value=float(selected.x_mm), step=50.0, key=f"x_{selected.id}")
            y = st.number_input("위쪽 위치 Y", value=float(selected.y_mm), step=50.0, key=f"y_{selected.id}")
            w = st.number_input("지름" if selected.shape == "circle" else "가로", min_value=1.0, value=float(selected.width_mm), step=50.0, key=f"w_{selected.id}")
            d = w if selected.shape == "circle" else st.number_input("세로", min_value=1.0, value=float(selected.depth_mm), step=50.0, key=f"d_{selected.id}")
            clearance = st.number_input("벽 여유 공간 (mm)", min_value=0.0, value=float(selected.clearance_mm), step=50.0, key=f"c_{selected.id}")
            group = st.text_input("그룹 이름", selected.group, key=f"g_{selected.id}")
            if st.form_submit_button("변경 적용", use_container_width=True):
                if not edit_name.strip():
                    st.error("가구 이름을 입력해 주세요.")
                else:
                    selected.name = edit_name.strip()
                    selected.x_mm, selected.y_mm = x, y
                    selected.width_mm, selected.depth_mm = w, d
                    selected.clearance_mm, selected.group = clearance, group.strip()
                    st.rerun()
        action = st.selectbox("작업", ["복사", "90° 회전", "삭제"] if selected.shape != "circle" else ["복사", "삭제"])
        if st.button("작업 실행", use_container_width=True):
            run_action({"복사": "copy", "90° 회전": "rotate", "삭제": "delete"}[action], selected.id)
            st.rerun()
    else:
        st.caption("도면에서 가구를 선택해 주세요.")

with st.expander("호실 치수 확인 / 보정"):
    st.caption("실측한 벽 안쪽 치수가 있을 때 보정하세요. 모든 수치는 mm 단위입니다.")
    with st.form(f"room_dimensions_{st.session_state.workspace.active}"):
        rw = st.number_input("호실 가로 (mm)", min_value=100.0, max_value=100000.0, value=float(project.room.width_mm))
        rd = st.number_input("호실 세로 (mm)", min_value=100.0, max_value=100000.0, value=float(project.room.depth_mm))
        if st.form_submit_button("치수 적용"):
            project.room = Room(rw, rd, project.room.name)
            st.rerun()

with canvas_area.container():
    planner_canvas(data={"room": {"width_mm": project.room.width_mm, "depth_mm": project.room.depth_mm},
                         "room_key": st.session_state.workspace.active, "furniture": status_payload(project),
                         "selected_ids": st.session_state.selected_ids, "image_data_url": image_data_url(project)},
                   key="planner_canvas", on_move_change=update_from_canvas,
                   on_select_change=select_from_canvas, on_delete_change=delete_from_canvas,
                   on_action_change=action_from_canvas)

ratio = occupied_ratio(project.room, project.furniture)
status_text = "가구를 우클릭하거나 길게 눌러 편집하세요."
if selected:
    status = analyze(project.room, selected, project.furniture)
    status_text = "배치 가능" if status.level == "ok" else "여유 공간 부족" if status.level == "warning" else "벽 이탈 또는 가구 겹침"
status_area.caption(f"가구 {len(project.furniture)}개 · 면적 점유 {ratio:.1%} · {status_text}")
save_area.download_button("프로젝트 저장 (.fplan)", data=export_workspace(st.session_state.workspace),
                          file_name=download_name(st.session_state.workspace), mime="application/zip",
                          use_container_width=True)
