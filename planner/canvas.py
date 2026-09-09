from __future__ import annotations

import streamlit as st


HTML = """
<div class="canvas-shell">
  <div class="canvas-help">가구를 끌어서 이동 · Shift+클릭으로 여러 개 선택</div>
  <svg id="planner-svg" role="application" aria-label="가구 배치 작업판"></svg>
</div>
"""

CSS = """
.canvas-shell { width: 100%; user-select: none; }
.canvas-help { color: var(--st-text-color); opacity: .62; font-size: 12px; margin: 0 0 8px; }
#planner-svg { display: block; max-width: 100%; margin: 0 auto; background: #f7f7f9; border: 1px solid rgba(128,128,128,.22); border-radius: 18px; touch-action: none; }
.room-border { fill: transparent; stroke: rgba(60,60,67,.72); stroke-width: 18; vector-effect: non-scaling-stroke; }
.furniture { cursor: grab; stroke-width: 10; vector-effect: non-scaling-stroke; }
.furniture:active { cursor: grabbing; }
.furniture.selected { stroke: #007aff !important; stroke-width: 18; }
.furniture-label { pointer-events: none; text-anchor: middle; dominant-baseline: central; font-weight: 700; fill: #1d1d1f; }
"""

JS = r"""
export default function(component) {
  const { data, parentElement, setTriggerValue } = component;
  const svg = parentElement.querySelector('#planner-svg');
  const room = data.room;
  const ns = 'http://www.w3.org/2000/svg';
  const selected = new Set(data.selected_ids || []);
  svg.replaceChildren();
  svg.setAttribute('viewBox', `0 0 ${room.width_mm} ${room.depth_mm}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  svg.setAttribute('tabindex', '0');
  svg.onkeydown = event => {
    if ((event.key === 'Delete' || event.key === 'Backspace') && selected.size) {
      event.preventDefault();
      setTriggerValue('delete', {nonce: Date.now(), ids: [...selected]});
    }
  };

  // Keep the complete room visible on a desktop screen while preserving scale.
  const maxCanvasHeight = 500;
  const availableWidth = parentElement.getBoundingClientRect().width || 760;
  const roomRatio = room.width_mm / room.depth_mm;
  const displayWidth = Math.min(availableWidth, maxCanvasHeight * roomRatio);
  const displayHeight = displayWidth / roomRatio;
  svg.style.width = `${displayWidth}px`;
  svg.style.height = `${displayHeight}px`;

  if (data.image_data_url) {
    const image = document.createElementNS(ns, 'image');
    image.setAttribute('href', data.image_data_url);
    image.setAttribute('x', '0'); image.setAttribute('y', '0');
    image.setAttribute('width', room.width_mm); image.setAttribute('height', room.depth_mm);
    image.setAttribute('preserveAspectRatio', 'none');
    image.setAttribute('opacity', data.image_opacity ?? 0.58);
    svg.appendChild(image);
  }

  const border = document.createElementNS(ns, 'rect');
  border.setAttribute('x', '0'); border.setAttribute('y', '0');
  border.setAttribute('width', room.width_mm); border.setAttribute('height', room.depth_mm);
  border.setAttribute('class', 'room-border');
  svg.appendChild(border);

  const localItems = new Map(data.furniture.map(item => [item.id, {...item}]));
  let drag = null;
  const svgPoint = (event) => {
    const point = svg.createSVGPoint(); point.x = event.clientX; point.y = event.clientY;
    return point.matrixTransform(svg.getScreenCTM().inverse());
  };
  const dimensions = item => item.rotation === 90
    ? [item.depth_mm, item.width_mm] : [item.width_mm, item.depth_mm];
  const targetIds = item => item.group
    ? data.furniture.filter(x => x.group === item.group).map(x => x.id)
    : (selected.has(item.id) && selected.size > 1 ? [...selected] : [item.id]);

  for (const item of data.furniture) {
    const [width, depth] = dimensions(item);
    const group = document.createElementNS(ns, 'g');
    group.dataset.id = item.id;
    group.setAttribute('transform', `translate(${item.x_mm},${item.y_mm})`);
    const rect = document.createElementNS(ns, 'rect');
    rect.setAttribute('width', width); rect.setAttribute('height', depth);
    rect.setAttribute('rx', Math.min(width, depth) * .045);
    rect.setAttribute('fill', item.fill); rect.setAttribute('stroke', item.stroke);
    rect.setAttribute('class', `furniture${selected.has(item.id) ? ' selected' : ''}`);
    const label = document.createElementNS(ns, 'text');
    label.setAttribute('x', width / 2); label.setAttribute('y', depth / 2);
    label.setAttribute('font-size', Math.max(65, Math.min(width, depth) * .12));
    label.setAttribute('class', 'furniture-label');
    label.textContent = `${item.name}  ${Math.round(item.width_mm)}×${Math.round(item.depth_mm)}`;
    group.append(rect, label); svg.appendChild(group);

    rect.addEventListener('pointerdown', event => {
      event.preventDefault(); svg.focus({preventScroll: true}); rect.setPointerCapture(event.pointerId);
      const point = svgPoint(event);
      const ids = targetIds(item);
      drag = { pointerId: event.pointerId, start: point, ids,
        origins: Object.fromEntries(ids.map(id => [id, [localItems.get(id).x_mm, localItems.get(id).y_mm]])) };
    });
    rect.addEventListener('pointermove', event => {
      if (!drag || drag.pointerId !== event.pointerId) return;
      const point = svgPoint(event); const dx = point.x - drag.start.x; const dy = point.y - drag.start.y;
      for (const id of drag.ids) {
        const node = svg.querySelector(`g[data-id="${id}"]`);
        const [ox, oy] = drag.origins[id];
        node?.setAttribute('transform', `translate(${ox + dx},${oy + dy})`);
      }
    });
    rect.addEventListener('pointerup', event => {
      if (!drag || drag.pointerId !== event.pointerId) return;
      const point = svgPoint(event); const dx = point.x - drag.start.x; const dy = point.y - drag.start.y;
      const moves = drag.ids.map(id => ({id, x_mm: drag.origins[id][0] + dx, y_mm: drag.origins[id][1] + dy}));
      drag = null;
      setTriggerValue('move', {nonce: Date.now(), moves});
    });
    rect.addEventListener('click', event => {
      if (event.detail === 0) return;
      let ids;
      if (event.shiftKey) {
        ids = new Set(selected); ids.has(item.id) ? ids.delete(item.id) : ids.add(item.id);
        ids = [...ids];
      } else { ids = [item.id]; }
      setTriggerValue('select', {nonce: Date.now(), ids});
    });
  }
}
"""


planner_canvas = st.components.v2.component(
    "floorplan_furniture_canvas",
    html=HTML,
    css=CSS,
    js=JS,
)
