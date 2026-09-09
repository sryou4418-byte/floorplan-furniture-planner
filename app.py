from __future__ import annotations

import base64

import streamlit as st

from planner.canvas import planner_canvas
from planner.geometry import analyze, occupied_ratio
from planner.image_io import normalize_plan
from planner.models import Furniture, Project, Room
from planner.presets import PRESETS_BY_LABEL
from planner.project_io import export_project, import_project


st.set_page_config(page_title="도면 가구 배치", page_icon="📐", layout="wide")


def init_state() -> None:
    st.session_state.setdefault("project", Project())
    st.session_state.setdefault("selected_ids", [])
    st.session_state.setdefault("image_opacity", 0.55)


def update_from_canvas() -> None:
    event = st.session_state.get("planner_canvas")
    payload = getattr(event, "move", None) if event else None
    if not payload:
        return
    moves = {move["id"]: move for move in payload["moves"]}
    project: Project = st.session_state.project
    for item in project.furniture:
        if item.id in moves:
            item.x_mm = round(float(moves[item.id]["x_mm"]), 1)
            item.y_mm = round(float(moves[item.id]["y_mm"]), 1)


def select_from_canvas() -> None:
    event = st.session_state.get("planner_canvas")
    payload = getattr(event, "select", None) if event else None
    if payload:
        st.session_state.selected_ids = payload["ids"]


def image_data_url(project: Project) -> str | None:
    if not project.plan_image_bytes:
        return None
    mime = project.plan_image_mime or "image/png"
    encoded = base64.b64encode(project.plan_image_bytes).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def status_payload(project: Project) -> list[dict]:
    palette = {
        "ok": ("rgba(52,199,89,.50)", "#248a3d"),
        "warning": ("rgba(255,159,10,.50)", "#c93400"),
        "error": ("rgba(255,69,58,.50)", "#d70015"),
    }
    output = []
    for item in project.furniture:
        status = analyze(project.room, item, project.furniture)
        fill, stroke = palette[status.level]
        output.append({**{
            "id": item.id, "name": item.name, "width_mm": item.width_mm,
            "depth_mm": item.depth_mm, "x_mm": item.x_mm, "y_mm": item.y_mm,
            "rotation": item.rotation, "group": item.group,
        }, "fill": fill, "stroke": stroke})
    return output


init_state()
project: Project = st.session_state.project

st.title("도면 가구 배치")
st.caption("실제 치수를 입력하고 도면 위에서 가구가 들어가는지 확인해 보세요.")

with st.sidebar:
    st.subheader("프로젝트")
    imported = st.file_uploader("프로젝트 불러오기", type=["fplan"], key="project_upload")
    if imported and st.button("프로젝트 적용", use_container_width=True):
        try:
            st.session_state.project = import_project(imported.getvalue())
            st.session_state.selected_ids = []
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.download_button(
        "프로젝트 저장 (.fplan)",
        data=export_project(project),
        file_name="furniture-plan.fplan",
        mime="application/zip",
        use_container_width=True,
    )

    st.divider()
    st.subheader("성환고 호실")
    preset_label = st.selectbox(
        "기본 호실 선택",
        ["직접 설정"] + list(PRESETS_BY_LABEL),
        help="제공된 PDF의 2·3페이지 평면도를 기준으로 만든 호실별 도면입니다.",
    )
    st.caption("표시 치수는 구조 그리드 기준 공칭치수이며, 실제 벽 안쪽 유효치수와 차이가 날 수 있습니다.")
    if preset_label != "직접 설정" and st.button("선택한 호실 열기", use_container_width=True):
        PRESETS_BY_LABEL[preset_label].apply(project)
        st.session_state.selected_ids = []
        st.rerun()

    st.divider()
    st.subheader("사용자 도면")
    plan_file = st.file_uploader("PNG, JPG 또는 PDF", type=["png", "jpg", "jpeg", "pdf"], key="plan_upload")
    if plan_file and st.button("도면 적용", use_container_width=True):
        try:
            image_bytes, mime = normalize_plan(plan_file.getvalue(), plan_file.name)
            project.plan_image_bytes = image_bytes
            project.plan_image_name = plan_file.name
            project.plan_image_mime = mime
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    st.session_state.image_opacity = st.slider("도면 진하기", 0.0, 1.0, st.session_state.image_opacity, 0.05)

    st.divider()
    st.subheader("공간 실제 크기")
    room_name = st.text_input("공간 이름", project.room.name)
    room_width = st.number_input("가로 (mm)", min_value=100.0, max_value=100000.0, value=float(project.room.width_mm), step=100.0)
    room_depth = st.number_input("세로 (mm)", min_value=100.0, max_value=100000.0, value=float(project.room.depth_mm), step=100.0)
    if (room_name, room_width, room_depth) != (project.room.name, project.room.width_mm, project.room.depth_mm):
        project.room = Room(float(room_width), float(room_depth), room_name)

    st.divider()
    with st.form("add_furniture", clear_on_submit=True):
        st.subheader("가구 추가")
        name = st.text_input("가구 이름", placeholder="예: 퀸 침대")
        width = st.number_input("가구 가로 (mm)", min_value=1.0, value=1600.0, step=50.0)
        depth = st.number_input("가구 세로 (mm)", min_value=1.0, value=2000.0, step=50.0)
        group = st.text_input("그룹 이름", placeholder="예: 침실 세트")
        submitted = st.form_submit_button("가구 추가", use_container_width=True)
        if submitted:
            try:
                item = Furniture(name=name, width_mm=float(width), depth_mm=float(depth), group=group.strip())
                item.validate()
                project.furniture.append(item)
                st.session_state.selected_ids = [item.id]
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

left, right = st.columns([2.15, 1], gap="large")

with right:
    st.subheader("배치 상태")
    ratio = occupied_ratio(project.room, project.furniture)
    metric_a, metric_b = st.columns(2)
    metric_a.metric("가구 수", f"{len(project.furniture)}개")
    metric_b.metric("면적 점유", f"{ratio * 100:.1f}%")

    selected = next((item for item in project.furniture if item.id in st.session_state.selected_ids), None)
    if selected:
        status = analyze(project.room, selected, project.furniture)
        if status.level == "ok":
            st.success("배치 가능")
        elif status.level == "warning":
            st.warning("들어가지만 설정한 여유 공간이 부족합니다.")
        elif not status.inside_room:
            st.error(f"벽 밖으로 최대 {status.overflow_mm:.0f}mm 나갑니다.")
        else:
            st.error("다른 가구와 겹칩니다: " + ", ".join(status.overlaps))

        st.markdown(f"**{selected.name}** · {selected.width_mm:.0f} × {selected.depth_mm:.0f}mm")
        edit_name = st.text_input("선택 가구 이름", selected.name, key=f"name_{selected.id}")
        col_x, col_y = st.columns(2)
        new_x = col_x.number_input("왼쪽 위치 X", value=float(selected.x_mm), step=50.0, key=f"x_{selected.id}")
        new_y = col_y.number_input("위쪽 위치 Y", value=float(selected.y_mm), step=50.0, key=f"y_{selected.id}")
        col_w, col_d = st.columns(2)
        new_w = col_w.number_input("가로", min_value=1.0, value=float(selected.width_mm), step=50.0, key=f"w_{selected.id}")
        new_d = col_d.number_input("세로", min_value=1.0, value=float(selected.depth_mm), step=50.0, key=f"d_{selected.id}")
        new_clearance = st.number_input("벽 여유 공간 (mm)", min_value=0.0, value=float(selected.clearance_mm), step=50.0, key=f"c_{selected.id}")
        new_group = st.text_input("그룹 이름", selected.group, key=f"g_{selected.id}", help="같은 그룹 이름의 가구는 함께 이동합니다.")
        selected.name = edit_name
        selected.x_mm, selected.y_mm = float(new_x), float(new_y)
        selected.width_mm, selected.depth_mm = float(new_w), float(new_d)
        selected.clearance_mm = float(new_clearance)
        selected.group = new_group.strip()

        action_a, action_b = st.columns(2)
        if action_a.button("90° 회전", use_container_width=True):
            selected.rotation = 90 if selected.rotation == 0 else 0
            st.rerun()
        if action_b.button("삭제", use_container_width=True, type="secondary"):
            project.furniture = [item for item in project.furniture if item.id != selected.id]
            st.session_state.selected_ids = []
            st.rerun()
    else:
        st.info("가구를 추가하거나 작업판에서 선택하면 상세 정보가 표시됩니다.")

    st.divider()
    st.caption("좌표의 기준점은 공간 왼쪽 위이며 모든 계산은 mm 단위입니다.")

with left:
    planner_canvas(
        data={
            "room": {"width_mm": project.room.width_mm, "depth_mm": project.room.depth_mm},
            "furniture": status_payload(project),
            "selected_ids": st.session_state.selected_ids,
            "image_data_url": image_data_url(project),
            "image_opacity": st.session_state.image_opacity,
        },
        key="planner_canvas",
        on_move_change=update_from_canvas,
        on_select_change=select_from_canvas,
    )
