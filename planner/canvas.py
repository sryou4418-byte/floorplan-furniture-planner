from __future__ import annotations

import streamlit as st

HTML = """
<div class="canvas-shell">
  <div class="canvas-tools">
    <button type="button" data-tool="out" aria-label="도면 축소">−</button>
    <output class="zoom-value" aria-live="polite">100%</output>
    <button type="button" data-tool="in" aria-label="도면 확대">＋</button>
    <button type="button" data-tool="fit">화면 맞춤</button>
    <span class="canvas-help">우클릭 · 길게 눌러 편집</span>
  </div>
  <div class="canvas-viewport"><svg id="planner-svg" role="application" aria-label="가구 배치 작업판" tabindex="0"></svg></div>
  <div class="furniture-menu" role="dialog" aria-label="가구 작업" hidden></div>
</div>
"""

CSS = """
.canvas-shell { width:100%; position:relative; user-select:none; font-family:inherit; }
.canvas-tools { display:flex; gap:6px; align-items:center; margin:0 0 6px; }
.canvas-tools button, .furniture-menu button { min-height:36px; padding:6px 12px; border:1px solid #d5d7db; border-radius:8px; background:#fff; color:#202124; cursor:pointer; font:inherit; }
.canvas-tools button:focus-visible, .furniture-menu button:focus-visible { outline:2px solid #007aff; }
.zoom-value { min-width:44px; text-align:center; font-size:13px; }
.canvas-help { font-size:12px; opacity:.6; margin-left:auto; }
.canvas-viewport { width:100%; overflow:auto; border-radius:8px; background:rgba(128,128,128,.035); }
#planner-svg { display:block; margin:0 auto; background:#fafafa; touch-action:none; }
.room-border { fill:transparent; stroke:#777; stroke-width:2; vector-effect:non-scaling-stroke; }
.furniture { cursor:grab; stroke-width:1; vector-effect:non-scaling-stroke; }
.furniture:active { cursor:grabbing; }
.furniture.selected { stroke:#007aff !important; stroke-width:2; }
.furniture-label { pointer-events:none; text-anchor:middle; dominant-baseline:central; font-weight:700; fill:#1d1d1f; }
.furniture-menu { position:absolute; z-index:20; width:min(230px, calc(100% - 16px)); padding:8px; box-sizing:border-box; background:#fff; color:#202124; border:1px solid #ddd; border-radius:12px; box-shadow:0 8px 28px #0003; }
.furniture-menu[hidden] { display:none; }
.furniture-menu button { display:block; width:100%; text-align:left; margin:3px 0; min-height:44px; }
.furniture-menu button:disabled { opacity:.4; cursor:default; }
.furniture-menu input { box-sizing:border-box; width:100%; padding:10px; font-size:16px; margin:4px 0; }
.furniture-menu .menu-error { color:#b42318; font-size:13px; }
@media(max-width:640px) { .canvas-tools button { min-height:44px; } .canvas-tools { gap:4px; } .canvas-help { display:none; } }
"""

JS = r"""
export default function(component) {
  const {data, parentElement, setTriggerValue} = component;
  const shell = parentElement.querySelector('.canvas-shell');
  shell._cleanup?.();
  const controller = new AbortController();
  const signal = controller.signal;
  const svg = shell.querySelector('svg');
  const viewport = shell.querySelector('.canvas-viewport');
  const menu = shell.querySelector('.furniture-menu');
  const doc = svg.ownerDocument;
  const win = doc.defaultView;
  const room = data.room;
  const selected = new Set(data.selected_ids || []);
  const ns = 'http://www.w3.org/2000/svg';
  let drag = null, pressTimer = null;
  let zoom = shell._room === data.room_key ? (shell._zoom || 1) : 1;
  shell._room = data.room_key;
  let maxHeight = 500;
  const send = (type, payload) => setTriggerValue(type, {...payload, room_key:data.room_key, nonce:Date.now()});
  const closeMenu = () => {menu.hidden = true;};
  closeMenu();
  const listen = (target, name, fn, options={}) => target.addEventListener(name, fn, {...options, signal});
  const fit = () => {
    const width = Math.max(1, viewport.clientWidth - 4);
    const ratio = room.width_mm / room.depth_mm;
    const baseWidth = Math.min(width, maxHeight * ratio);
    svg.style.width = `${baseWidth * zoom}px`;
    svg.style.height = `${baseWidth * zoom / ratio}px`;
    viewport.style.maxHeight = `${maxHeight + 2}px`;
    shell.querySelector('.zoom-value').textContent = `${Math.round(zoom*100)}%`;
    shell._zoom = zoom;
  };
  const measure = () => {
    maxHeight = Math.max(220, win.innerHeight - Math.max(100, shell.getBoundingClientRect().top) - 145);
    fit();
  };
  const observer = new ResizeObserver(fit);
  observer.observe(viewport);
  listen(win, 'resize', measure);
  for (const button of shell.querySelectorAll('[data-tool]')) {
    listen(button, 'click', () => {
      zoom = button.dataset.tool === 'fit' ? 1 : Math.min(2, Math.max(.5, zoom + (button.dataset.tool === 'in' ? .1 : -.1)));
      closeMenu(); measure();
    });
  }
  svg.replaceChildren();
  svg.setAttribute('viewBox', `0 0 ${room.width_mm} ${room.depth_mm}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  const node = (tag, attrs={}) => {
    const e = doc.createElementNS(ns, tag);
    for (const [key,value] of Object.entries(attrs)) e.setAttribute(key, value);
    return e;
  };
  if (data.image_data_url) svg.append(node('image', {href:data.image_data_url, width:room.width_mm, height:room.depth_mm, preserveAspectRatio:'none', opacity:.65}));
  svg.append(node('rect', {width:room.width_mm, height:room.depth_mm, class:'room-border'}));
  const localItems = new Map(data.furniture.map(item => [item.id, {...item}]));
  const groups = new Map();
  const pointAt = event => {
    const point = svg.createSVGPoint(); point.x = event.clientX; point.y = event.clientY;
    return point.matrixTransform(svg.getScreenCTM().inverse());
  };
  const mark = ids => {
    selected.clear(); ids.forEach(id=>selected.add(id));
    for (const [id, group] of groups) group.firstElementChild.classList.toggle('selected', selected.has(id));
  };
  const clearPress = () => {win.clearTimeout(pressTimer); pressTimer=null;};
  const cancelDrag = () => {
    clearPress();
    if (drag) for (const id of drag.ids) {
      const f = localItems.get(id); groups.get(id)?.setAttribute('transform', `translate(${f.x_mm},${f.y_mm})`);
    }
    drag=null;
  };
  const button = (text, fn, disabled=false) => {
    const b=doc.createElement('button'); b.type='button'; b.textContent=text; b.disabled=disabled;
    b.addEventListener('click',fn); menu.append(b); return b;
  };
  const openMenu = (item, x, y) => {
    cancelDrag(); mark([item.id]); menu.replaceChildren(); menu.hidden=false;
    const rect=shell.getBoundingClientRect();
    menu.style.left=`${Math.max(4,Math.min(x-rect.left,rect.width-246))}px`;
    menu.style.top=`${Math.max(0,Math.min(y-rect.top,Math.min(rect.height,win.innerHeight-rect.top)-290))}px`;
    button('이름 변경', () => {
      menu.replaceChildren();
      const form=doc.createElement('form');
      const input=doc.createElement('input'); input.value=item.name; input.maxLength=80; input.setAttribute('aria-label','새 가구 이름');
      const error=doc.createElement('div'); error.className='menu-error'; error.setAttribute('role','alert');
      form.append(input,error); menu.append(form);
      const save=doc.createElement('button'); save.type='submit'; save.textContent='확인'; form.append(save);
      form.addEventListener('submit',event=>{
        event.preventDefault(); const name=input.value.trim();
        if (!name) {error.textContent='이름을 입력해 주세요.'; return;}
        closeMenu(); send('action',{action:'rename',id:item.id,name});
      });
      button('취소',()=>{closeMenu(); svg.focus({preventScroll:true});}); input.focus(); input.select();
    });
    button('90° 회전',()=>{closeMenu(); send('action',{action:'rotate',id:item.id});},item.shape==='circle');
    button('복사',()=>{closeMenu(); send('action',{action:'copy',id:item.id});});
    button('삭제',()=>{closeMenu(); send('action',{action:'delete',id:item.id});});
    button('닫기',()=>{closeMenu(); svg.focus({preventScroll:true});});
    menu.querySelector('button').focus({preventScroll:true});
  };
  listen(doc,'pointerdown',event=>{if(!event.composedPath().includes(menu)) closeMenu();});
  listen(doc,'keydown',event=>{
    if(event.key==='Escape') {closeMenu(); cancelDrag(); return;}
    if(event.composedPath().some(e=>e.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(e.tagName))) return;
    if(event.ctrlKey || event.altKey || event.metaKey || event.repeat || !menu.hidden) return;
    if((event.key==='Delete' || event.key==='Backspace') && selected.size) {event.preventDefault(); send('delete',{ids:[...selected]});}
  });
  for (const item of data.furniture) {
    const [width,depth]=item.rotation===90 ? [item.depth_mm,item.width_mm] : [item.width_mm,item.depth_mm];
    const group=node('g',{transform:`translate(${item.x_mm},${item.y_mm})`}); group.dataset.id=item.id;
    const shape=item.shape==='circle' ? node('circle',{cx:width/2,cy:width/2,r:width/2}) : node('rect',{width,height:depth,rx:Math.min(width,depth)*.035});
    shape.setAttribute('fill',item.fill); shape.setAttribute('stroke',item.stroke);
    shape.setAttribute('class',`furniture${selected.has(item.id)?' selected':''}`);
    const sizeText=item.shape==='circle' ? `Ø ${Math.round(item.width_mm)} mm` : `${Math.round(item.width_mm)} × ${Math.round(item.depth_mm)} mm`;
    const font=Math.min(Math.min(width,depth)*.14,width*.8/Math.max([...item.name].length,sizeText.length*.6,1));
    const label=node('text',{x:width/2,y:depth/2,'font-size':font,class:'furniture-label'});
    const title=node('tspan',{x:width/2,dy:'-.65em'}); title.textContent=item.name;
    const size=node('tspan',{x:width/2,dy:'1.5em','font-weight':400}); size.textContent=sizeText;
    label.append(title,size); group.append(shape,label); svg.append(group); groups.set(item.id,group);
    listen(shape,'contextmenu',event=>{event.preventDefault(); openMenu(localItems.get(item.id),event.clientX,event.clientY);});
    listen(shape,'pointerdown',event=>{
      if(event.button!==0 || event.isPrimary===false) return;
      event.preventDefault(); closeMenu(); svg.focus({preventScroll:true}); shape.setPointerCapture(event.pointerId); clearPress();
      const ids=item.group ? data.furniture.filter(f=>f.group===item.group).map(f=>f.id) : selected.has(item.id)&&selected.size>1 ? [...selected] : [item.id];
      drag={pointerId:event.pointerId,start:pointAt(event),cx:event.clientX,cy:event.clientY,ids,moved:false,
        origins:Object.fromEntries(ids.map(id=>[id,[localItems.get(id).x_mm,localItems.get(id).y_mm]]))};
      if(event.pointerType==='touch' || event.pointerType==='pen') pressTimer=win.setTimeout(()=>openMenu(localItems.get(item.id),event.clientX,event.clientY),550);
    });
    listen(shape,'pointermove',event=>{
      if(!drag || drag.pointerId!==event.pointerId) return;
      if(Math.hypot(event.clientX-drag.cx,event.clientY-drag.cy)<6 && !drag.moved) return;
      clearPress(); drag.moved=true;
      const p=pointAt(event),dx=p.x-drag.start.x,dy=p.y-drag.start.y;
      for(const id of drag.ids) {const [x,y]=drag.origins[id]; groups.get(id).setAttribute('transform',`translate(${x+dx},${y+dy})`);}
    });
    listen(shape,'pointerup',event=>{
      clearPress(); if(!drag || drag.pointerId!==event.pointerId) return;
      const current=drag; drag=null;
      if(current.moved) {
        const p=pointAt(event),dx=p.x-current.start.x,dy=p.y-current.start.y;
        const moves=current.ids.map(id=>({id,x_mm:current.origins[id][0]+dx,y_mm:current.origins[id][1]+dy}));
        moves.forEach(m=>Object.assign(localItems.get(m.id),m)); mark(current.ids); send('move',{moves});
      } else {
        const ids=event.shiftKey ? new Set(selected) : new Set();
        event.shiftKey && ids.has(item.id) ? ids.delete(item.id) : ids.add(item.id);
        mark([...ids]); send('select',{ids:[...ids]});
      }
    });
    listen(shape,'pointercancel',cancelDrag);
    listen(shape,'lostpointercapture',()=>{if(drag)cancelDrag();});
  }
  measure();
  shell._cleanup=()=>{cancelDrag(); controller.abort(); observer.disconnect(); closeMenu();};
  const cleanup=shell._cleanup;
  return cleanup;
}
"""

planner_canvas = st.components.v2.component("floorplan_furniture_canvas", html=HTML, css=CSS, js=JS)
