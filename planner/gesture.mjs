// Pure gesture classifier; handlers own timers and pointer capture.
export class Gesture {
  constructor(threshold=6, holdMs=550) { this.threshold=threshold; this.holdMs=holdMs; this.reset(); }
  reset() { this.current=null; }
  start(id,x,y,time,touch,target) { this.current={id,x,y,time,touch,target,moved:false}; }
  move(id,x,y) {
    const g=this.current;
    if (!g || g.id!==id) return false;
    if (Math.hypot(x-g.x,y-g.y)>=this.threshold) g.moved=true;
    return g.moved;
  }
  hold(id,time) {
    const g=this.current;
    if (!g || g.id!==id || !g.touch || !g.target || g.moved || time-g.time<this.holdMs) return false;
    this.reset(); return true;
  }
  end(id,x,y,time) {
    const g=this.current;
    if (!g || g.id!==id) return null;
    this.move(id,x,y); this.reset();
    if(g.moved) return g.target ? 'drag' : null;
    if(time-g.time>=this.holdMs && g.touch) return null;
    return g.target ? 'tap' : g.touch ? 'create' : null;
  }
}
