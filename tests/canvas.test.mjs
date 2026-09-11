// DOM integration tests, not a browser or native-touch emulation.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';
import {Gesture} from '../planner/gesture.mjs';

const python=readFileSync(new URL('../planner/canvas.py',import.meta.url),'utf8');
const html=python.split('HTML = """')[1].split('"""')[0];
const source=readFileSync(new URL('../planner/canvas.js',import.meta.url),'utf8').replace('export default function','function render');
function setup(extra={}) {
  const dom=new JSDOM(`<button id="sidebar-button">Sidebar</button><aside data-testid="stSidebar" aria-expanded="false"></aside>${html}`,{url:'https://example.test'});
  const {window:w}=dom, doc=w.document, shell=doc.querySelector('.canvas-shell'), svg=doc.querySelector('svg');
  const events=[], timers=new Map(); let tid=0;
  Object.defineProperty(shell.querySelector('.canvas-viewport'),'clientWidth',{value:640,configurable:true});
  Object.defineProperty(w,'innerHeight',{value:900,writable:true});
  w.setTimeout=fn=>{timers.set(++tid,fn); return tid;}; w.clearTimeout=id=>timers.delete(id);
  svg.createSVGPoint=()=>({x:0,y:0,matrixTransform(){return {x:this.x*10,y:this.y*10};}});
  svg.getScreenCTM=()=>({inverse:()=>({})}); svg.setPointerCapture=()=>{};
  const factory=new Function('Gesture','AbortController','ResizeObserver','MutationObserver',`${source}; return render;`);
  const render=factory(Gesture,w.AbortController,class {observe(){} disconnect(){}},w.MutationObserver);
  const data={room:{width_mm:6000,depth_mm:6000},room_key:'A',room_options:['A','B'],selected_ids:[],
    furniture:[{id:'a',name:'책상',width_mm:1200,depth_mm:600,x_mm:100,y_mm:200,rotation:0,shape:'rectangle',group:'',fill:'green',stroke:'black'}],...extra};
  const cleanup=render({data,parentElement:doc,setTriggerValue:(type,payload)=>events.push({type,...payload})});
  const pointer=(target,type,x=10,y=10,id=1,pointerType='touch')=>{
    const e=new w.Event(type,{bubbles:true,composed:true,cancelable:true});
    Object.assign(e,{clientX:x,clientY:y,pointerId:id,pointerType,button:0,isPrimary:id===1}); target.dispatchEvent(e);
  };
  const shape=shell.querySelector('.furniture'), menu=shell.querySelector('.furniture-menu');
  return {w,doc,shell,svg,shape,menu,events,pointer,timers,cleanup,render,data,dom};
}

test('tap opens editor; drag closes it and sends only a move',()=>{
  const h=setup(); h.pointer(h.shape,'pointerdown'); h.pointer(h.svg,'pointerup');
  assert.equal(h.menu.hidden,false); assert.equal(h.events.length,0);
  h.menu.querySelector('input').value='未適用';
  h.pointer(h.shape,'pointerdown'); assert.equal(h.menu.hidden,false);
  h.pointer(h.svg,'pointermove',30,40); assert.equal(h.menu.hidden,true);
  h.pointer(h.svg,'pointerup',30,40);
  assert.equal(h.events.length,1); assert.equal(h.events[0].type,'move');
  assert.deepEqual(h.events[0].moves,[{id:'a',x_mm:300,y_mm:500}]); h.cleanup(); h.dom.window.close();
});
test('long hold shows x; release does not edit/create; delete triggers once',()=>{
  const h=setup(); h.pointer(h.shape,'pointerdown'); [...h.timers.values()].forEach(fn=>fn());
  assert.equal(h.shell.querySelector('.delete-badge').hidden,false);
  assert.equal(h.shape.parentElement.classList.contains('wiggle'),true);
  h.pointer(h.svg,'pointerup'); assert.equal(h.menu.hidden,true); assert.equal(h.events.length,0);
  const badge=h.shell.querySelector('.delete-badge');
  h.pointer(badge,'pointerdown'); h.pointer(badge,'pointerup'); h.pointer(badge,'pointerdown'); h.pointer(badge,'pointerup');
  assert.equal(h.events.length,1); assert.equal(h.events[0].action,'delete'); h.cleanup(); h.dom.window.close();
});
test('blank tap creates once and busy blocks repeated taps',()=>{
  const h=setup(); const blank=h.shell.querySelector('.room-border');
  for(let n=0;n<2;n++) {h.pointer(blank,'pointerdown'); h.pointer(blank,'pointerup');}
  assert.equal(h.events.length,1); assert.equal(h.events[0].action,'create');
  assert.equal(h.events[0].x_mm,100); h.cleanup(); h.dom.window.close();
});
test('second finger cancels drag and pending hold',()=>{
  const h=setup(); h.pointer(h.shape,'pointerdown'); h.pointer(h.svg,'pointermove',20,20);
  h.pointer(h.svg,'pointerdown',40,40,2); h.pointer(h.svg,'pointerup',20,20);
  assert.equal(h.events.length,0); assert.equal(h.shape.parentElement.getAttribute('transform'),'translate(100,200)');
  assert.equal(h.timers.size,0); h.cleanup(); h.dom.window.close();
});
test('native room selector switches directly and sends only one event',()=>{
  const h=setup(), picker=h.shell.querySelector('[aria-label="호실 선택"]');
  assert.deepEqual([...picker.options].map(option=>option.value),['A','B']);
  picker.value='B'; picker.dispatchEvent(new h.w.Event('change',{bubbles:true}));
  assert.equal(h.events.length,1); assert.equal(h.events[0].type,'room'); assert.equal(h.events[0].label,'B');
  h.cleanup(); h.dom.window.close();
});
test('edit shape normalizes circle payload, Delete inside input is harmless',()=>{
  const h=setup(); h.pointer(h.shape,'pointerdown'); h.pointer(h.svg,'pointerup');
  const shape=h.menu.querySelector('select'); shape.value='circle'; shape.dispatchEvent(new h.w.Event('change'));
  const width=h.menu.querySelector('input[type=number]'); width.value='900';
  width.dispatchEvent(new h.w.KeyboardEvent('keydown',{key:'Delete',bubbles:true,composed:true}));
  assert.equal(h.events.length,0);
  h.menu.querySelector('form').dispatchEvent(new h.w.Event('submit',{cancelable:true}));
  assert.equal(h.events[0].changes.depth_mm,900); assert.equal(h.events[0].changes.shape,'circle');
  h.cleanup(); h.dom.window.close();
});
test('cancelled pointer never moves, repeated render cleans old handlers',()=>{
  const h=setup(); h.pointer(h.shape,'pointerdown'); h.pointer(h.svg,'pointermove',30,30); h.pointer(h.svg,'pointercancel');
  h.pointer(h.svg,'pointerup',30,30); assert.equal(h.events.length,0);
  const cleanup=h.render({data:h.data,parentElement:h.doc,setTriggerValue:(type,payload)=>h.events.push({type,...payload})});
  h.pointer(h.svg,'pointerdown'); h.pointer(h.svg,'pointerup'); assert.equal(h.events.length,1);
  cleanup(); h.dom.window.close();
});
test('furniture-only rerender preserves fitted plan size',()=>{
  const h=setup(), width=h.svg.style.width, height=h.svg.style.height;
  const data={...h.data,furniture:[...h.data.furniture,{...h.data.furniture[0],id:'b',x_mm:1500}]};
  const cleanup=h.render({data,parentElement:h.doc,setTriggerValue:()=>{}});
  assert.equal(h.svg.style.width,width); assert.equal(h.svg.style.height,height);
  cleanup(); h.dom.window.close();
});
test('desktop blank context menu creates one sample at the saved plan point',()=>{
  const h=setup(), blank=h.shell.querySelector('.room-border');
  const event=new h.w.Event('contextmenu',{bubbles:true,cancelable:true});
  Object.assign(event,{clientX:23,clientY:31,pointerType:'mouse'}); blank.dispatchEvent(event);
  assert.equal(h.menu.hidden,false);
  assert.equal(h.menu.querySelector('button').textContent,'샘플 가구 추가');
  h.menu.querySelector('button').click();
  assert.equal(h.events.length,1); assert.equal(h.events[0].action,'create');
  assert.equal(h.events[0].x_mm,230); assert.equal(h.events[0].y_mm,310);
  h.cleanup(); h.dom.window.close();
});
test('desktop double click opens the beside-furniture quick editor without select rerender',()=>{
  const h=setup();
  h.pointer(h.shape,'pointerdown',10,10,1,'mouse'); h.pointer(h.svg,'pointerup',10,10,1,'mouse');
  h.pointer(h.shape,'pointerdown',10,10,1,'mouse'); h.pointer(h.svg,'pointerup',10,10,1,'mouse');
  const event=new h.w.Event('dblclick',{bubbles:true,cancelable:true}); Object.assign(event,{pointerType:'mouse'}); h.shape.dispatchEvent(event);
  assert.equal(h.menu.hidden,false); assert.equal(h.menu.classList.contains('quick-editor'),true);
  assert.equal(h.events.length,0);
  h.cleanup(); h.dom.window.close();
});
test('dropping beyond the room clamps the whole furniture back inside',()=>{
  const h=setup(); h.pointer(h.shape,'pointerdown',10,10); h.pointer(h.svg,'pointermove',700,10); h.pointer(h.svg,'pointerup',700,10);
  assert.equal(h.events.length,1); assert.equal(h.events[0].type,'move');
  assert.equal(h.events[0].moves[0].x_mm,4800); assert.equal(h.events[0].moves[0].y_mm,200);
  h.cleanup(); h.dom.window.close();
});
test('selected desktop furniture shows integer millimeter gap helpers',()=>{
  const h=setup(), data={...h.data,desktop_assists:true,selected_ids:['a']};
  const cleanup=h.render({data,parentElement:h.doc,setTriggerValue:()=>{}});
  const labels=[...h.shell.querySelectorAll('.measure-label')].map(node=>node.textContent);
  assert.ok(labels.includes('100 mm')); assert.ok(labels.includes('200 mm'));
  cleanup(); h.dom.window.close();
});

for(const kind of ['water','electric','three_phase']) for(const device of ['mouse','touch']) {
  test(`${device} places ${kind} once at the plan point without adding furniture`,()=>{
    const h=setup(); h.shell.querySelector(`[data-utility="${kind}"]`).click();
    h.pointer(h.shape,'pointerdown',25,35,1,device); h.pointer(h.svg,'pointerup',25,35,1,device);
    h.pointer(h.svg,'pointerdown',25,35,1,device); h.pointer(h.svg,'pointerup',25,35,1,device);
    assert.equal(h.events.length,1); assert.equal(h.events[0].action,'utility_create');
    assert.equal(h.events[0].kind,kind); assert.equal(h.events[0].x_mm,250); assert.equal(h.events[0].y_mm,350);
    h.cleanup(); h.dom.window.close();
  });
}

test('utility drag, multitouch and cancellation do not place points',()=>{
  const h=setup(); h.shell.querySelector('[data-utility="water"]').click();
  h.pointer(h.svg,'pointerdown',20,20); h.pointer(h.svg,'pointermove',60,60); h.pointer(h.svg,'pointerup',60,60);
  h.pointer(h.svg,'pointerdown'); h.pointer(h.svg,'pointerdown',40,40,2); h.pointer(h.svg,'pointerup'); h.pointer(h.svg,'pointerup',40,40,2);
  h.pointer(h.svg,'pointerdown'); h.pointer(h.svg,'pointercancel'); h.pointer(h.svg,'pointerup');
  assert.equal(h.events.length,0); h.cleanup(); h.dom.window.close();
});

test('utility points render specified colors above furniture and delete only through their menu',()=>{
  const h=setup({utility_points:[{id:'u1',kind:'water',x_mm:100,y_mm:200},{id:'u2',kind:'electric',x_mm:300,y_mm:400},{id:'u3',kind:'three_phase',x_mm:500,y_mm:600}]});
  assert.deepEqual([...h.svg.querySelectorAll('.utility-mark')].map(e=>e.getAttribute('fill')),['#2563eb','#facc15','#ef4444']);
  const point=h.svg.querySelector('.utility-hit');
  h.pointer(point,'pointerdown'); h.pointer(h.svg,'pointerup');
  assert.equal(h.events.length,0); assert.equal(h.menu.querySelector('button').textContent,'수도 표시 삭제');
  h.menu.querySelector('button').click();
  assert.equal(h.events.length,1); assert.equal(h.events[0].action,'utility_delete'); assert.equal(h.events[0].id,'u1');
  h.cleanup(); h.dom.window.close();
});

test('Escape exits point mode and furniture editor keeps shape above the dimension pair',()=>{
  const h=setup(); h.shell.querySelector('[data-utility="electric"]').click();
  h.doc.dispatchEvent(new h.w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
  assert.equal(h.shell.querySelector('[data-utility=""]').getAttribute('aria-pressed'),'true');
  h.pointer(h.shape,'pointerdown'); h.pointer(h.svg,'pointerup');
  assert.equal(h.menu.querySelector('select').parentElement.className,'menu-wide');
  assert.equal(h.menu.querySelectorAll('input[type="number"]').length,2);
  h.cleanup(); h.dom.window.close();
});
