import test from 'node:test';
import assert from 'node:assert/strict';
import {Gesture} from '../planner/gesture.mjs';

test('blank touch tap creates once; mouse click does not',()=>{
  const g=new Gesture(); g.start(1,10,10,0,true,null);
  assert.equal(g.end(1,12,12,100),'create'); assert.equal(g.end(1,12,12,120),null);
  g.start(2,10,10,0,false,null); assert.equal(g.end(2,10,10,100),null);
});
test('scroll, long blank press and cancellation never create',()=>{
  const g=new Gesture(); g.start(1,10,10,0,true,null); g.move(1,10,30);
  assert.equal(g.end(1,10,10,100),null);
  g.start(1,10,10,0,true,null); assert.equal(g.end(1,10,10,600),null);
  g.start(1,10,10,0,true,null); g.reset(); assert.equal(g.end(1,10,10,50),null);
});
test('furniture tap vs drag vs hold are exclusive',()=>{
  const g=new Gesture(); g.start(1,10,10,0,true,'a'); assert.equal(g.end(1,11,10,100),'tap');
  g.start(1,10,10,0,true,'a'); g.move(1,30,10); assert.equal(g.hold(1,600),false);
  assert.equal(g.end(1,30,10,650),'drag');
  g.start(1,10,10,0,true,'a'); assert.equal(g.hold(1,549),false);
  assert.equal(g.hold(1,550),true); assert.equal(g.end(1,10,10,600),null);
});
test('wrong pointer and cancelled multi-touch cannot finish gesture',()=>{
  const g=new Gesture(); g.start(1,0,0,0,true,'a');
  assert.equal(g.end(2,0,0,10),null); g.reset();
  assert.equal(g.hold(1,600),false); assert.equal(g.end(1,0,0,50),null);
});
