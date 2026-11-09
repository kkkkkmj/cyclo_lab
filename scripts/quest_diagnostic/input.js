/* Strict Touch Plus selection. Each candidate owns fresh fields; hands are never merged. */
const sourceIds = new WeakMap();
let nextSourceId = 1;
const emptyHand = (reason='no_source') => ({valid:false, reason, profiles:[], buttons:[], axes:[]});
function controllerCandidate(source, frame, reference, visibility) {
  const h=emptyHand();
  if(!sourceIds.has(source))sourceIds.set(source, String(nextSourceId++));
  h.source_id=sourceIds.get(source);
  // Raw diagnostic fields are never consumed by control or used to grant validity.
  h.handedness=source.handedness;
  h.diagnostic={handedness:source.handedness,target_ray_mode:source.targetRayMode,
    grip_space:!!source.gripSpace,pose_checked:false,pose_present:null,
    raw_buttons:Array.from(source.gamepad?.buttons||[],b=>({value:b.value,pressed:b.pressed,touched:b.touched}))};
  h.profiles=Array.from(source.profiles||[]);
  if(source.hand || h.profiles.some(p=>/hand/i.test(p))) {h.reason='hand_input_excluded';return h;}
  if(!h.profiles.includes('meta-quest-touch-plus')) {h.reason='controller_profile_not_allowed';return h;}
  if(source.targetRayMode!=='tracked-pointer') {h.reason='not_tracked_pointer';return h;}
  const gp=source.gamepad;h.mapping=gp?.mapping||'';
  if(!gp) {h.reason='no_gamepad';return h;}
  if(gp.mapping!=='xr-standard') {h.reason='unsupported_mapping';return h;}
  if(visibility!=='visible') {h.reason='session_not_visible';return h;}
  if(!source.gripSpace) {h.reason='no_grip_space';return h;}
  const pose=frame.getPose(source.gripSpace,reference);
  h.diagnostic.pose_checked=true;h.diagnostic.pose_present=!!pose;
  if(!pose) {h.reason='no_grip_pose';return h;}
  h.emulated_position=pose.emulatedPosition;
  if(pose.emulatedPosition) {h.reason='emulated_position';return h;}
  const p=pose.transform.position,q=pose.transform.orientation;
  h.position=[p.x,p.y,p.z];h.quaternion_xyzw=[q.x,q.y,q.z,q.w];
  h.buttons=Array.from(gp.buttons,b=>({value:b.value,pressed:b.pressed,touched:b.touched}));
  h.axes=Array.from(gp.axes);h.valid=true;h.reason='ok';
  return h;
}
function selectControllers(sources, frame, reference, visibility) {
  const result={left:emptyHand(),right:emptyHand()};
  for(const side of ['left','right']) {
    const candidates=Array.from(sources).filter(s=>s.handedness===side)
      .map(s=>controllerCandidate(s,frame,reference,visibility));
    const allowed=h=>h.profiles.includes('meta-quest-touch-plus')&&!h.profiles.some(p=>/hand/i.test(p))&&h.reason!=='hand_input_excluded';
    const valid=candidates.filter(h=>allowed(h)&&h.valid);
    // Stable identity prevents inputSources order changes from switching controllers.
    valid.sort((a,b)=>Number(a.source_id)-Number(b.source_id));
    result[side]=valid[0]||candidates.find(allowed)||candidates[0]||emptyHand();
    result[side].candidates=candidates.map(h=>({source_id:h.source_id,profiles:h.profiles,valid:h.valid,reason:h.reason,diagnostic:h.diagnostic}));
  }
  return result;
}

// Include unassigned sources too, so missing right handedness can be distinguished from filtering.
function diagnosticSources(sources){
  return Array.from(sources,s=>({source_id:sourceIds.get(s)||null,handedness:s.handedness,
    profiles:Array.from(s.profiles||[]),hand:!!s.hand,target_ray_mode:s.targetRayMode,
    grip_space:!!s.gripSpace,mapping:s.gamepad?.mapping||'',
    raw_buttons:Array.from(s.gamepad?.buttons||[],b=>({value:b.value,pressed:b.pressed,touched:b.touched}))}));
}
