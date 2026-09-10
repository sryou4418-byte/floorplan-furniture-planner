export default function(component) {
  const {data,parentElement,setTriggerValue}=component;
  const shell=parentElement.querySelector('.canvas-shell'); shell._cleanup?.();
  const doc=shell.ownerDocument, win=doc.defaultView;
  const controller=new AbortController(), signal=controller.signal;
  const listen=(target,event,fn,options={})=>target.addEventListener(event,fn,{...options,signal});
  const svg=shell.querySelector('svg'), viewport=shell.querySelector('.canvas-viewport');
  const menu=shell.querySelector('.furniture-menu'), roomSelect=shell.querySelector('.room-picker select');
  const assistToggle=shell.querySelector('.assist-toggle');
  const badge=shell.querySelector('.delete-badge'), done=shell.querySelector('.delete-done');
  const message=shell.querySelector('.canvas-message'); message.textContent='';
  const items=new Map(data.furniture.map(f=>[f.id,{...f}])), groups=new Map();
  const selected=new Set(data.selected_ids||[]), gesture=new Gesture(), pointers=new Set();
  let drag=null, timer=null, clickTimer=null, deleteId=null, deletePointer=null, busy=false, lastTouch=-Infinity;
  let assistEnabled=shell._assistEnabled!==false;
  let zoom=shell._room===data.room_key ? (shell._zoom||1) : 1;
  shell._room=data.room_key;
  let baseWidth=1;
  const send=(type,payload)=>{
    if(busy) return;
    busy=true;
    setTriggerValue(type,{...payload,room_key:data.room_key,nonce:win.crypto.randomUUID()});
  };
  const closeMenu=()=>{menu.hidden=true; const active=menu.getRootNode().activeElement; if(active&&menu.contains(active)) active.blur();};
  const mark=ids=>{
    selected.clear(); ids.forEach(id=>selected.add(id));
    for(const [id,g] of groups) g.querySelector('.furniture').classList.toggle('selected',selected.has(id));
  };
  const stopDelete=()=>{deleteId=null; deletePointer=null; badge.hidden=true; done.hidden=true; groups.forEach(g=>g.classList.remove('wiggle'));};
  const cancel=()=>{
    win.clearTimeout(timer); gesture.reset();
    if(drag) for(const id of drag.ids) {const f=items.get(id); groups.get(id)?.setAttribute('transform',`translate(${f.x_mm},${f.y_mm})`);}
    drag=null;
  };
  const closeAll=()=>{closeMenu(); stopDelete(); cancel();};
  closeAll();
  const placeBadge=()=>{
    if(!deleteId) return;
    const r=groups.get(deleteId).getBoundingClientRect(), s=shell.getBoundingClientRect(), v=viewport.getBoundingClientRect();
    badge.style.left=`${Math.max(0,Math.min(r.right-s.left-22,s.width-44))}px`;
    badge.style.top=`${Math.max(v.top-s.top,Math.min(r.top-s.top-22,v.bottom-s.top-44))}px`;
  };
  const fit=()=>{
    if(drag) return;
    const ratio=data.room.width_mm/data.room.depth_mm;
    svg.style.width=`${baseWidth*zoom}px`; svg.style.height=`${baseWidth*zoom/ratio}px`;
    viewport.style.maxHeight=`${baseWidth/ratio+2}px`;
    shell.querySelector('.zoom-value').textContent=`${Math.round(zoom*100)}%`; shell._zoom=zoom; placeBadge();
  };
  const measure=(force=false)=>{
    if(!menu.hidden) return;
    const h=win.visualViewport?.height||win.innerHeight;
    const containerWidth=Math.max(1,viewport.clientWidth-4), previous=shell._fitBasis;
    if(force||!previous||previous.room!==data.room_key||Math.abs(previous.containerWidth-containerWidth)>2) {
      const ratio=data.room.width_mm/data.room.depth_mm;
      baseWidth=Math.min(containerWidth,Math.max(220,h*.7)*ratio);
      shell._fitBasis={room:data.room_key,containerWidth,screenHeight:h,baseWidth};
    } else baseWidth=previous.baseWidth;
    fit();
  };
  const observer=new ResizeObserver(()=>measure()); observer.observe(viewport);
  listen(win,'resize',()=>measure()); if(win.visualViewport) listen(win.visualViewport,'resize',()=>measure());
  listen(viewport,'scroll',placeBadge,{passive:true});
  for(const b of shell.querySelectorAll('[data-tool]')) listen(b,'click',()=>{
    const refit=b.dataset.tool==='fit'; closeAll(); zoom=refit?1:Math.min(2,Math.max(.5,zoom+(b.dataset.tool==='in'?.1:-.1))); measure(refit);
  });
  const updateAssistToggle=()=>{
    assistToggle.setAttribute('aria-pressed',String(assistEnabled));
    assistToggle.textContent=`정렬 보조 ${assistEnabled?'켬':'끔'}`;
  };
  updateAssistToggle();
  listen(assistToggle,'click',()=>{assistEnabled=!assistEnabled; shell._assistEnabled=assistEnabled; updateAssistToggle();});
  roomSelect.replaceChildren();
  for(const label of data.room_options||[]) {
    const option=doc.createElement('option'); option.value=label; option.textContent=label; option.selected=label===data.room_key; roomSelect.append(option);
  }
  listen(roomSelect,'pointerdown',()=>{closeMenu(); stopDelete(); cancel();});
  listen(roomSelect,'change',()=>{const label=roomSelect.value; closeAll(); if(label!==data.room_key) send('room',{label});});
  listen(doc,'pointerdown',event=>{
    const path=event.composedPath();
    if(!path.includes(shell)) closeAll();
    else if(!path.includes(menu)&&!path.includes(svg)&&!path.includes(badge)&&!path.includes(done)) {closeMenu(); stopDelete();}
  },{capture:true});
  listen(doc,'click',event=>{if(!event.composedPath().includes(shell)) closeAll();});
  listen(doc,'focusin',event=>{if(!event.composedPath().includes(shell)) closeAll();});
  svg.replaceChildren(); svg.setAttribute('viewBox',`0 0 ${data.room.width_mm} ${data.room.depth_mm}`);
  const node=(tag,attrs={})=>{const e=doc.createElementNS('http://www.w3.org/2000/svg',tag); for(const [k,v] of Object.entries(attrs)) e.setAttribute(k,v); return e;};
  if(data.image_data_url) svg.append(node('image',{href:data.image_data_url,width:data.room.width_mm,height:data.room.depth_mm,preserveAspectRatio:'none',opacity:.65}));
  svg.append(node('rect',{width:data.room.width_mm,height:data.room.depth_mm,class:'room-border'}));
  const assistLayer=node('g',{class:'assist-layer'}); svg.append(assistLayer);
  const point=event=>{const p=svg.createSVGPoint(); p.x=event.clientX; p.y=event.clientY; return p.matrixTransform(svg.getScreenCTM().inverse());};
  const button=(label,fn,parent=menu)=>{const b=doc.createElement('button'); b.type='button'; b.textContent=label; listen(b,'click',fn); parent.append(b); return b;};
  const command=(action,id)=>{closeMenu(); stopDelete(); send('action',{action,id});};
  const boxOf=(item,dx=0,dy=0)=>{
    const [width,depth]=item.rotation===90?[item.depth_mm,item.width_mm]:[item.width_mm,item.depth_mm];
    return {left:item.x_mm+dx,top:item.y_mm+dy,right:item.x_mm+dx+width,bottom:item.y_mm+dy+depth,width,depth};
  };
  const selectionBox=(ids,dx=0,dy=0)=>{
    const boxes=ids.map(id=>boxOf(items.get(id),dx,dy));
    return {left:Math.min(...boxes.map(b=>b.left)),top:Math.min(...boxes.map(b=>b.top)),right:Math.max(...boxes.map(b=>b.right)),bottom:Math.max(...boxes.map(b=>b.bottom))};
  };
  const clampDelta=(ids,dx,dy)=>{
    const box=selectionBox(ids,dx,dy), width=box.right-box.left, depth=box.bottom-box.top;
    if(width>data.room.width_mm) dx-=box.left;
    else if(box.left<0) dx-=box.left; else if(box.right>data.room.width_mm) dx+=data.room.width_mm-box.right;
    if(depth>data.room.depth_mm) dy-=box.top;
    else if(box.top<0) dy-=box.top; else if(box.bottom>data.room.depth_mm) dy+=data.room.depth_mm-box.bottom;
    return {dx,dy};
  };
  const snapDelta=(ids,dx,dy,disabled)=>{
    if(disabled||!assistEnabled||!data.desktop_assists) return {...clampDelta(ids,dx,dy),guides:{}};
    const moving=selectionBox(ids,dx,dy), movingSet=new Set(ids);
    const xTargets=[0,data.room.width_mm], yTargets=[0,data.room.depth_mm];
    for(const [id,item] of items) if(!movingSet.has(id)) {
      const b=boxOf(item); xTargets.push(b.left,(b.left+b.right)/2,b.right); yTargets.push(b.top,(b.top+b.bottom)/2,b.bottom);
    }
    const xAnchors=[moving.left,(moving.left+moving.right)/2,moving.right];
    const yAnchors=[moving.top,(moving.top+moving.bottom)/2,moving.bottom];
    const rect=svg.getBoundingClientRect();
    const threshold=10*data.room.width_mm/Math.max(rect.width,1);
    let bestX={distance:Infinity,adjust:0,target:null}, bestY={distance:Infinity,adjust:0,target:null};
    for(const anchor of xAnchors) for(const target of xTargets) {const adjust=target-anchor,distance=Math.abs(adjust); if(distance<bestX.distance) bestX={distance,adjust,target};}
    for(const anchor of yAnchors) for(const target of yTargets) {const adjust=target-anchor,distance=Math.abs(adjust); if(distance<bestY.distance) bestY={distance,adjust,target};}
    const guides={};
    if(bestX.distance<=threshold) {dx+=bestX.adjust; guides.x=bestX.target;}
    if(bestY.distance<=threshold) {dy+=bestY.adjust; guides.y=bestY.target;}
    return {...clampDelta(ids,dx,dy),guides};
  };
  const line=(x1,y1,x2,y2,label,className='measure-line')=>{
    const g=node('g',{class:className}); g.append(node('line',{x1,y1,x2,y2}));
    if(label!==undefined) {const t=node('text',{x:(x1+x2)/2,y:(y1+y2)/2,class:'measure-label'}); t.textContent=label; g.append(t);}
    assistLayer.append(g);
  };
  const renderAssists=(ids,dx=0,dy=0,guides={})=>{
    assistLayer.replaceChildren();
    if(!ids.length||!data.desktop_assists) return;
    if(guides.x!==undefined) line(guides.x,0,guides.x,data.room.depth_mm,undefined,'alignment-guide');
    if(guides.y!==undefined) line(0,guides.y,data.room.width_mm,guides.y,undefined,'alignment-guide');
    const box=selectionBox(ids,dx,dy), cx=(box.left+box.right)/2, cy=(box.top+box.bottom)/2;
    const horizontal=[{gap:box.left,x1:0,x2:box.left,y:cy},{gap:data.room.width_mm-box.right,x1:box.right,x2:data.room.width_mm,y:cy}];
    const vertical=[{gap:box.top,y1:0,y2:box.top,x:cx},{gap:data.room.depth_mm-box.bottom,y1:box.bottom,y2:data.room.depth_mm,x:cx}];
    const movingSet=new Set(ids);
    for(const [id,item] of items) if(!movingSet.has(id)) {
      const other=boxOf(item);
      const yOverlap=Math.min(box.bottom,other.bottom)-Math.max(box.top,other.top);
      const xOverlap=Math.min(box.right,other.right)-Math.max(box.left,other.left);
      if(yOverlap>0&&other.right<=box.left) horizontal.push({gap:box.left-other.right,x1:other.right,x2:box.left,y:(Math.max(box.top,other.top)+Math.min(box.bottom,other.bottom))/2});
      if(yOverlap>0&&other.left>=box.right) horizontal.push({gap:other.left-box.right,x1:box.right,x2:other.left,y:(Math.max(box.top,other.top)+Math.min(box.bottom,other.bottom))/2});
      if(xOverlap>0&&other.bottom<=box.top) vertical.push({gap:box.top-other.bottom,y1:other.bottom,y2:box.top,x:(Math.max(box.left,other.left)+Math.min(box.right,other.right))/2});
      if(xOverlap>0&&other.top>=box.bottom) vertical.push({gap:other.top-box.bottom,y1:box.bottom,y2:other.top,x:(Math.max(box.left,other.left)+Math.min(box.right,other.right))/2});
    }
    const h=horizontal.filter(v=>v.gap>=0).sort((a,b)=>a.gap-b.gap)[0];
    const v=vertical.filter(value=>value.gap>=0).sort((a,b)=>a.gap-b.gap)[0];
    if(h) line(h.x1,h.y,h.x2,h.y,`${Math.round(h.gap)} mm`);
    if(v) line(v.x,v.y1,v.x,v.y2,`${Math.round(v.gap)} mm`);
  };
  const editor=item=>{
    closeAll(); mark([item.id]); renderAssists([item.id]); menu.classList.remove('floating'); menu.classList.add('quick-editor'); menu.replaceChildren(); menu.hidden=false;
    const target=groups.get(item.id).getBoundingClientRect(), shellRect=shell.getBoundingClientRect();
    const width=Math.min(310,Math.max(240,shellRect.width-16));
    const right=target.right-shellRect.left+10, left=target.left-shellRect.left-width-10;
    menu.style.width=`${width}px`; menu.style.left=`${right+width<=shellRect.width-4?right:Math.max(4,left)}px`;
    menu.style.top=`${Math.max(4,Math.min(target.top-shellRect.top,shellRect.height-330))}px`;
    const form=doc.createElement('form'); menu.append(form);
    const field=(label,value,type='text')=>{
      const wrap=doc.createElement('label'); wrap.textContent=label;
      const input=doc.createElement('input'); input.type=type; input.value=value; input.setAttribute('aria-label',label);
      if(type==='number') {input.min='1'; input.step='1'; input.inputMode='numeric';} else input.maxLength=80;
      input.required=true; wrap.append(input); form.append(wrap); return input;
    };
    const name=field('가구 이름',item.name); name.parentElement.className='menu-wide';
    const wrap=doc.createElement('label'); wrap.textContent='모양';
    const shape=doc.createElement('select'); shape.setAttribute('aria-label','모양');
    for(const [value,label] of [['rectangle','사각형'],['circle','원형']]) {const o=doc.createElement('option'); o.value=value; o.textContent=label; shape.append(o);}
    shape.value=item.shape; wrap.append(shape); form.append(wrap);
    const w=field(item.shape==='circle'?'지름 (mm)':'가로 (mm)',Math.round(item.width_mm),'number');
    const d=field('세로 (mm)',Math.round(item.depth_mm),'number');
    const updateShape=()=>{
      w.parentElement.firstChild.textContent=shape.value==='circle'?'지름 (mm)':'가로 (mm)';
      w.setAttribute('aria-label',shape.value==='circle'?'지름 (mm)':'가로 (mm)');
      d.parentElement.hidden=shape.value==='circle'; d.disabled=shape.value==='circle';
    };
    listen(shape,'change',updateShape); updateShape();
    const error=doc.createElement('div'); error.className='menu-error menu-wide'; error.setAttribute('role','alert'); form.append(error);
    const apply=doc.createElement('button'); apply.type='submit'; apply.textContent='적용'; form.append(apply);
    button('취소',closeMenu,form);
    listen(form,'submit',event=>{
      event.preventDefault(); const width=Number(w.value), depth=shape.value==='circle'?width:Number(d.value);
      if(!name.value.trim()||![width,depth].every(v=>Number.isFinite(v)&&v>0)) {error.textContent='이름과 0보다 큰 치수를 입력해 주세요.'; return;}
      closeMenu(); send('action',{action:'edit',id:item.id,changes:{name:name.value.trim(),shape:shape.value,width_mm:width,depth_mm:depth}});
    });
    const actions=doc.createElement('div'); actions.className='menu-actions'; menu.append(actions);
    button('90° 회전',()=>command('rotate',item.id),actions).disabled=item.shape==='circle';
    button('복사',()=>command('copy',item.id),actions);
    const hint=doc.createElement('p'); hint.className='canvas-message'; hint.textContent='변경 후 적용 · 가구를 끌면 미적용 입력은 취소돼요.'; menu.append(hint);
  };
  const context=(item,event)=>{
    closeAll(); mark([item.id]); renderAssists([item.id]); menu.replaceChildren(); menu.hidden=false; menu.classList.remove('quick-editor'); menu.classList.add('floating');
    const r=shell.getBoundingClientRect(); menu.style.left=`${Math.max(4,Math.min(event.clientX-r.left,r.width-258))}px`;
    menu.style.top=`${Math.max(0,Math.min(event.clientY-r.top,r.height-260))}px`;
    button('가구 편집',()=>editor(item));
    button('90° 회전',()=>command('rotate',item.id)).disabled=item.shape==='circle';
    button('복사',()=>command('copy',item.id)); button('삭제',()=>command('delete',item.id)); button('닫기',closeMenu);
  };
  const blankContext=event=>{
    const p=point(event), r=shell.getBoundingClientRect(); closeAll(); menu.replaceChildren();
    menu.hidden=false; menu.classList.remove('quick-editor'); menu.classList.add('floating');
    menu.style.width='220px'; menu.style.left=`${Math.max(4,Math.min(event.clientX-r.left,r.width-228))}px`;
    menu.style.top=`${Math.max(0,Math.min(event.clientY-r.top,r.height-110))}px`;
    button('샘플 가구 추가',()=>{closeMenu(); send('action',{action:'create',x_mm:p.x,y_mm:p.y});});
    button('닫기',closeMenu);
  };
  const startDelete=id=>{
    cancel(); closeMenu(); stopDelete(); deleteId=id; mark([id]); groups.get(id).classList.add('wiggle'); badge.hidden=false; done.hidden=false; placeBadge();
  };
  listen(badge,'pointerdown',event=>{event.preventDefault(); event.stopPropagation(); deletePointer=event.pointerId;});
  listen(badge,'pointerup',event=>{
    event.preventDefault(); event.stopPropagation();
    if(deletePointer!==event.pointerId) return;
    const id=deleteId; deletePointer=null; if(id) command('delete',id);
  });
  listen(badge,'pointercancel',()=>{deletePointer=null;});
  listen(badge,'click',event=>{event.preventDefault(); event.stopPropagation(); if(event.detail===0&&deleteId) command('delete',deleteId);});
  listen(done,'click',stopDelete);
  listen(doc,'keydown',event=>{
    if(event.key==='Escape') {closeAll(); return;}
    if(event.composedPath().some(e=>e.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(e.tagName))) return;
    if(event.ctrlKey||event.altKey||event.metaKey||event.repeat||!menu.hidden) return;
    if(['Delete','Backspace'].includes(event.key)&&selected.size) {event.preventDefault(); send('delete',{ids:[...selected]});}
  });
  for(const item of items.values()) {
    const [w,d]=item.rotation===90?[item.depth_mm,item.width_mm]:[item.width_mm,item.depth_mm];
    const g=node('g',{transform:`translate(${item.x_mm},${item.y_mm})`}); g.dataset.id=item.id;
    const s=item.shape==='circle'?node('circle',{cx:w/2,cy:w/2,r:w/2}):node('rect',{width:w,height:d,rx:Math.min(w,d)*.035});
    s.setAttribute('fill',item.fill); s.setAttribute('stroke',item.stroke); s.setAttribute('class',`furniture${selected.has(item.id)?' selected':''}`);
    const size=item.shape==='circle'?`Ø ${Math.round(w)} mm`:`${Math.round(item.width_mm)} × ${Math.round(item.depth_mm)} mm`;
    const font=Math.min(Math.min(w,d)*.14,w*.8/Math.max([...item.name].length,size.length*.6,1));
    const label=node('text',{x:w/2,y:d/2,'font-size':font,class:'furniture-label'});
    const title=node('tspan',{x:w/2,dy:'-.65em'}); title.textContent=item.name;
    const sub=node('tspan',{x:w/2,dy:'1.5em','font-weight':400}); sub.textContent=size;
    label.append(title,sub); g.append(s,label); svg.append(g); groups.set(item.id,g);
    listen(s,'contextmenu',event=>{event.preventDefault(); if(event.pointerType==='touch'||event.pointerType==='pen'||win.performance.now()-lastTouch<1200) return; context(items.get(item.id),event);});
    listen(s,'dblclick',event=>{
      if(event.pointerType==='touch'||event.pointerType==='pen'||win.performance.now()-lastTouch<1200) return;
      event.preventDefault(); event.stopPropagation(); win.clearTimeout(clickTimer); editor(items.get(item.id));
    });
  }
  listen(svg,'contextmenu',event=>{
    if(event.target.closest?.('.furniture')||event.pointerType==='touch'||event.pointerType==='pen'||win.performance.now()-lastTouch<1200) return;
    event.preventDefault(); blankContext(event);
  });
  listen(svg,'pointerdown',event=>{
    pointers.add(event.pointerId);
    if(pointers.size>1) {cancel(); return;}
    if(busy||event.button!==0||event.isPrimary===false) return;
    const target=event.target.closest?.('.furniture')?.parentElement.dataset.id||null;
    if(deleteId) {stopDelete(); if(!target) return;}
    const touch=event.pointerType==='touch'||event.pointerType==='pen';
    if(touch) lastTouch=win.performance.now();
    gesture.start(event.pointerId,event.clientX,event.clientY,event.timeStamp,touch,target);
    if(!target) {if(!menu.hidden) {closeMenu(); gesture.reset();} return;}
    event.preventDefault(); svg.setPointerCapture(event.pointerId);
    const item=items.get(target), ids=item.group?[...items.values()].filter(f=>f.group===item.group).map(f=>f.id):selected.has(target)&&selected.size>1?[...selected]:[target];
    drag={ids,start:point(event),target,touch};
    if(touch) timer=win.setTimeout(()=>{if(gesture.hold(event.pointerId,event.timeStamp+550)) startDelete(target);},550);
  });
  listen(svg,'pointermove',event=>{
    if(!gesture.move(event.pointerId,event.clientX,event.clientY)) return;
    win.clearTimeout(timer);
    if(!drag) return;
    closeMenu(); stopDelete(); const p=point(event);
    const snapped=snapDelta(drag.ids,p.x-drag.start.x,p.y-drag.start.y,event.altKey||drag.touch);
    drag.preview=snapped;
    for(const id of drag.ids) {const f=items.get(id); groups.get(id).setAttribute('transform',`translate(${f.x_mm+snapped.dx},${f.y_mm+snapped.dy})`);}
    renderAssists(drag.ids,snapped.dx,snapped.dy,snapped.guides);
  });
  listen(svg,'pointerup',event=>{
    pointers.delete(event.pointerId); win.clearTimeout(timer);
    const current=drag, outcome=gesture.end(event.pointerId,event.clientX,event.clientY,event.timeStamp); drag=null;
    if(outcome==='drag'&&current) {
      closeMenu(); const p=point(event);
      const final=current.preview||snapDelta(current.ids,p.x-current.start.x,p.y-current.start.y,event.altKey||current.touch);
      const moves=current.ids.map(id=>({id,x_mm:items.get(id).x_mm+final.dx,y_mm:items.get(id).y_mm+final.dy}));
      moves.forEach(m=>Object.assign(items.get(m.id),m)); mark(current.ids); send('move',{moves});
    } else if(outcome==='tap'&&current) {
      if(current.touch) editor(items.get(current.target));
      else {
        const ids=event.shiftKey?new Set(selected):new Set(); event.shiftKey&&ids.has(current.target)?ids.delete(current.target):ids.add(current.target);
        mark([...ids]); renderAssists([...ids]); win.clearTimeout(clickTimer);
        clickTimer=win.setTimeout(()=>send('select',{ids:[...ids]}),240);
      }
    } else if(outcome==='create') {const p=point(event); send('action',{action:'create',x_mm:p.x,y_mm:p.y});}
  });
  listen(svg,'pointercancel',event=>{pointers.delete(event.pointerId); cancel();});
  listen(svg,'lostpointercapture',()=>{if(drag) cancel();});
  listen(doc,'pointerup',event=>pointers.delete(event.pointerId));
  listen(win,'blur',()=>{pointers.clear(); closeAll();});
  renderAssists([...selected]); measure();
  shell._cleanup=()=>{win.clearTimeout(clickTimer); closeAll(); controller.abort(); observer.disconnect();};
  return shell._cleanup;
}
