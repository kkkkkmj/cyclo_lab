/* Execute after input.js in a JS runtime; no browser/GPU required. */
function runInputTests(){
 let count=0;
 const assert=(ok,message)=>{if(!ok)throw Error(message);};
 const pose={emulatedPosition:false,transform:{position:{x:1,y:2,z:3},orientation:{x:0,y:0,z:0,w:1}}};
 const frame={getPose:space=>space.pose};
 function source(profiles=['meta-quest-touch-plus'],valid=true){return {handedness:'left',profiles,targetRayMode:'tracked-pointer',gripSpace:{pose:valid?pose:null},gamepad:{mapping:'xr-standard',buttons:[{value:1,pressed:true,touched:true}],axes:[0,0]}};}
 const choose=s=>selectControllers(s,frame,{},'visible').left;
 let hand=source(['meta-fixed-hand']);assert(!choose([hand]).valid,'fixed hand allowed');count++;
 let touch=source();assert(choose([hand,touch]).valid&&choose([touch,hand]).valid,'hand overwrites Touch');count++;
 let invalid=source(undefined,false);
 for(const list of [[touch,invalid],[invalid,touch]])assert(choose(list).valid,'invalid overwrites valid');count++;
 const h=choose([invalid]);assert(!h.valid&&!('position' in h)&&h.buttons.length===0,'stale candidate fields');count++;
 let other=source(['generic-trigger-squeeze-thumbstick']);assert(!choose([other]).valid,'unknown allowed');count++;
 let disguised=source();disguised.hand={};assert(!choose([disguised]).valid,'hand property bypass');count++;
 let second=source();const a=choose([touch,second]),b=choose([second,touch]);assert(a.source_id===b.source_id,'order changes identity');count++;
 assert(!selectControllers([touch],frame,{},'hidden').left.valid,'hidden input allowed');count++;
 assert(selectControllers([touch],frame,{},'visible').right.reason==='no_source','missing right hand');count++;
 assert(choose([hand]).reason==='hand_input_excluded','missing rejection reason');count++;
 let right=source();right.handedness='right';
 const both=selectControllers([touch,right],frame,{},'visible');
 assert(both.right.valid&&both.right.handedness==='right'&&both.right.diagnostic.pose_present,'right provenance missing');count++;
 const missing=choose([invalid]);
 assert(!missing.valid&&missing.buttons.length===0&&missing.diagnostic.raw_buttons[0].value===1&&!missing.diagnostic.pose_present,'raw diagnostics changed control validity');count++;
 const unassigned=source();unassigned.handedness='none';
 assert(diagnosticSources([touch,right,unassigned]).map(h=>h.handedness).join(',')==='left,right,none','unassigned sources hidden');count++;
 return count;
}
