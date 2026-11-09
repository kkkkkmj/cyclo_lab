/* Display-only settings; never change control coordinates or camera observations. */
const HUD_REVISION='practice-interruption-9';
function hudSettings(input={}) {
  const number=(v,fallback,lo,hi)=>Number.isFinite(Number(v))?Math.max(lo,Math.min(hi,Number(v))):fallback;
  const casting=input.mode==='casting';
  return {mode:casting?'casting':'normal',scale:number(input.scale,.65,.35,.85),
    margin:number(input.margin,.02,0,.18),
    centerX:casting?number(input.centerX,0,-.45,.45):0,
    centerY:casting?number(input.centerY,0,-.45,.45):0,diagnostic:!!input.diagnostic};
}
// Estimated casting preset: left-eye forward-axis NDC is -P[8] = +0.24251257.
// Meta eye/crop mapping is unverified. Round to +0.24 and apply to the whole HUD.
const HUD_STORAGE_KEY='cyclo.quest.display.v2';
function hudDefaults(mode='casting') {
  return hudSettings(mode==='normal'?{mode:'normal',scale:.65,margin:.02,diagnostic:false}:
    {mode:'casting',scale:.50,margin:.02,centerX:.24,centerY:.10,diagnostic:true});
}
function defaultHUDPreferences(){return {schema:2,mode:'casting',profiles:{normal:hudDefaults('normal'),casting:hudDefaults('casting')}};}
function loadHUDPreferences(storage){
  const fallback=defaultHUDPreferences();
  try{
    if(storage===undefined)storage=globalThis.localStorage;
    const raw=storage.getItem(HUD_STORAGE_KEY);
    if(!raw){
      // A new key applies the requested preset once. Subsequent loads restore edits.
      // Retain the old v1 key untouched; it must not override this migration.
      return {state:fallback,status:'New default layout (v2) applied once — '+saveHUDPreferences(fallback,storage)};
    }
    const data=JSON.parse(raw);
    if(data.schema!==2||!['normal','casting'].includes(data.mode)||!data.profiles)throw Error('invalid saved settings');
    for(const mode of ['normal','casting']){
      const v=data.profiles[mode];
      if(!v||['scale','margin','centerX','centerY'].some(k=>typeof v[k]!=='number'||!Number.isFinite(v[k]))||typeof v.diagnostic!=='boolean')throw Error('invalid saved profile');
      fallback.profiles[mode]=hudSettings({...v,mode});
    }
    fallback.mode=data.mode;
    return {state:fallback,status:'Saved display settings restored'};
  }catch(error){return {state:fallback,status:'Failed to load saved settings; using defaults: '+String(error)};}
}
function saveHUDPreferences(state,storage){
  try{
    if(storage===undefined)storage=globalThis.localStorage;
    storage.setItem(HUD_STORAGE_KEY,JSON.stringify(state));
    return 'Display settings saved — retained across reloads/VR sessions at this address';
  }catch(error){return 'Failed to save display settings (usable in the current VR session): '+String(error);}
}
function hudTransform(viewport,settings) {
  const {width:w,height:h}=viewport;
  if(!(w>0&&h>0))throw Error('Invalid XR viewport');
  const sx=settings.scale*Math.min(1,h/w),sy=settings.scale*Math.min(1,w/h);
  // Keep the complete panel within each eye. Meta's downstream crop is unknown.
  const clamp=(v,s)=>Math.max(-.98+s,Math.min(.98-s,v));
  const x=clamp(settings.centerX,sx),y=clamp(settings.centerY,sy);
  return {scale:[sx,sy],center:[x,y],bounds:[x-sx,y-sy,x+sx,y+sy]};
}
// Pure presentation of the simulator's verdict; button state never implies control activation.
function teleopStatusLines(status,fresh){
  if(!fresh)return ['Status unavailable — stale/interrupted video', 'Previous arm-active indication is invalid', 'After input/video recovery, release squeeze → press again'];
  if(!status||status.version!==1)return ['No control status received — check teleop launcher/server versions', 'Valid input or a pressed button alone does not establish active arm control'];
  const reasons={ready:'Ready',active:'Arm active',anchored:'Anchored',waiting:'Waiting',episode_waiting:'Waiting',
    release_then_squeeze:'Release squeeze, then press again',input_not_live:'Input lost',preview_not_live:'Video unconfirmed',
    loop_gap:'Control loop delayed',new_reference_release_buttons:'New reference: release squeeze',
    look_forward_release_both_squeezes:'Look forward; release both squeezes',controller_jump_release:'Input jump: release squeeze'};
  const rows=[`${status.episode_state} ${status.preview_only?'Preview only':''} | X start / A stop·wait | Control verdict`];
  const number=v=>Number.isFinite(v)?v.toFixed(2):'--';
  for(const side of ['left','right']){
    const h=status.hands[side];
    const control=!status.live?'Input lost':!h.valid?'Invalid input':status.preview_only?'Control disabled':status.episode_state==='WAITING'?'Waiting':
      h.active?'Arm active':(reasons[h.control_reason]||h.control_reason);
    const sq=h.raw_squeeze||{pressed:h.squeeze_pressed,value:h.squeeze},tr=h.raw_trigger||{value:h.trigger};
    rows.push(`${side==='left'?'L':'R'} Input ${h.valid?'Valid':'Invalid'} | ${control} | SQ ${sq.pressed?'ON':'OFF'} ${number(sq.value)} / TR ${number(tr.value)}`);
  }
  const age=v=>Number.isFinite(v)?Math.round(v)+'ms':'--';
  rows.push(`Input ${age(status.input_age_ms)} | focus ${status.visibility||'--'} | Video ${age(status.preview?.frame_age_ms)} | ACK ${status.preview_ok?'OK':status.compatibility==='reload_required'?'Version mismatch':'Unconfirmed'}`);
  if(status.preview_only){
    rows.push('Preview only: robot control disabled / X can start');
  }else if(status.episode_state==='WAITING'){
    const labels={input_stale:'Stale/missing input',quest_not_visible:'Quest not focused',input_not_live:'Invalid connection',
      preview_unconfirmed:'Fresh video display unconfirmed (stale/not displayed)',invalid:'Invalid input',not_touch_plus:'Not Touch Plus',
      buttons_invalid:'Invalid buttons/mapping',squeeze_held:'Release squeeze'};
    const blocks=status.start_blockers.map(code=>{const parts=code.split(':');return parts.length===2?
      (parts[0]==='left'?'L ':'R ')+(labels[parts[1]]||parts[1]):(labels[code]||code);});
    const message=blocks.length?(status.start_blocked?'START_BLOCKED: ':'Start conditions: ')+blocks.join(' · '):'Ready to start — press X again';
    // Wrap, never truncate a blocking condition. The common two-hand case fits two lines.
    for(let i=0;i<message.length;i+=56)rows.push(message.slice(i,i+56));
  }else rows.push('SQ: squeeze state/value / TR: trigger value — button ON ≠ active arm control');
  return rows;
}
// Compact view has at most two lines; full reasons remain in the page's details view.
function compactStatusLines(status,fresh){
  if(!fresh)return ['Status unavailable — stale video', 'After input/video recovery, release squeeze → press again'];
  if(!status||status.version!==1)return ['No control status received', 'Check launcher/server connection / see details'];
  const names={ready:'Ready',active:'Active',anchored:'Anchored',waiting:'Waiting',episode_waiting:'Waiting',
    release_then_squeeze:'Release again',input_not_live:'Input lost',preview_not_live:'Waiting for video',
    loop_gap:'Loop delayed',new_reference_release_buttons:'Release again',
    look_forward_release_both_squeezes:'Awaiting reference',controller_jump_release:'Input jump'};
  const value=v=>Number.isFinite(v)?v.toFixed(1):'--';
  const sides=['left','right'].map(side=>{
    const h=status.hands[side];
    const state=!status.live?'Input lost':!h.valid?'Invalid input':status.preview_only?'Disabled':
      status.episode_state==='WAITING'?'Waiting':h.active?'Active':names[h.control_reason]||'Blocked';
    return `${side==='left'?'L':'R'} ${state} SQ${value(h.raw_squeeze?.value??h.squeeze)}/TR${value(h.raw_trigger?.value??h.trigger)}`;
  });
  const rows=[`${status.episode_state} | ${sides.join(' | ')}`];
  if(status.episode_state==='WAITING'&&!status.preview_only&&status.start_blockers?.length){
    const blocks=status.start_blockers;
    let reason;
    if(status.compatibility==='reload_required')reason='Reload page';
    else if(blocks.includes('input_stale'))reason='Stale input';
    else if(blocks.includes('quest_not_visible'))reason='Quest not focused';
    else if(blocks.includes('preview_unconfirmed'))reason='Confirm fresh video';
    else if(blocks.some(b=>b.endsWith(':squeeze_held')))reason='Release squeeze: '+['left','right'].filter(s=>blocks.includes(s+':squeeze_held')).map(s=>s==='left'?'Left hand':'Right hand').join('·');
    else reason='Check both Touch Plus inputs';
    rows.push('Start blocked: '+reason+' · See page for details');
  }
  return rows;
}
// Display-only extraction of COMPLETE square camera tiles from compose_live's 960x936 mosaic.
// No camera pixels are cropped: the overview, labels and old footer simply are not drawn.
function cameraTiles(native=false){
  // Fixed inner safe area: no scaling of the whole XR panel or camera pixels.
  // Labels use empty space / the 24px inter-row gap, never the camera area.
  return [
    {name:'HEAD',source:native?[6,6,244,244]:[10,612,300,300],destination:[272,144,480,480],label:[80,168]},
    {name:'LEFT WRIST',source:native?[262,6,244,244]:[330,612,300,300],destination:[108,648,328,328],label:[108,643]},
    {name:'RIGHT WRIST',source:native?[518,6,244,244]:[650,612,300,300],destination:[588,648,328,328],label:[588,643]}
  ];
}
function controllerConnected(hand,received,network){
  const touch=h=>!!h&&!!h.source_id&&h.profiles?.includes('meta-quest-touch-plus')&&
    !h.profiles.some(p=>/hand/i.test(p))&&h.reason!=='hand_input_excluded'&&h.mapping==='xr-standard';
  // A pose can temporarily be invalid while the physical controller is still connected.
  // SQ/TR, WAITING and video freshness intentionally do not participate in connectivity.
  return network==='ACK OK'&&touch(hand)&&touch(received)&&hand.source_id===received.source_id;
}
function recordingBadge(status,fresh){
  if(!fresh||typeof status?.recording!=='boolean')return {text:'Checking',color:'#a3aab3'};
  return status.recording?{text:'● REC',color:'#ff6565'}:{text:'NO REC',color:'#a3aab3'};
}
/* A small, head-fixed diagnostic panel, not immersive simulation streaming. */
function makeHUD(gl, options={}) {
  options=hudSettings(options);
  const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=1024;
  const c=canvas.getContext('2d');
  function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
  const program=gl.createProgram();
  gl.attachShader(program,shader(gl.VERTEX_SHADER,'attribute vec2 p; uniform vec2 panelScale; uniform vec2 panelCenter; varying vec2 uv; void main(){uv=vec2((p.x+1.0)/2.0,(1.0-p.y)/2.0);gl_Position=vec4(p.x*panelScale.x+panelCenter.x,p.y*panelScale.y+panelCenter.y,0.,1.);}'));
  gl.attachShader(program,shader(gl.FRAGMENT_SHADER,'precision mediump float; varying vec2 uv; uniform sampler2D tex; void main(){gl_FragColor=texture2D(tex,uv);}'));
  gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
  const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
  gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
  const texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
  let last=-Infinity,lastImage=null,lastPanel=null;
  const draw=(views,layer,hands,network,image,previewFresh,t,previewStatus,build,teleop=null,receivedHands=null)=>{
    const eyeViews=views.map(view=>{
      const v=layer.getViewport(view);
      return {eye:view.eye,viewport:{x:v.x,y:v.y,width:v.width,height:v.height},
        transform:hudTransform(v,options),projectionMatrix:Array.from(view.projectionMatrix||[])};
    });
    draw.info={revision:HUD_REVISION,build,settings:options,status_panel:lastPanel,
      camera_tiles:cameraTiles(image?.width===768&&image?.height===256),
      framebuffer:{width:layer.framebufferWidth,height:layer.framebufferHeight},
      projection:'screen-fixed clip-space HUD; XR projection not applied',eyes:eyeViews};
    gl.useProgram(program);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    const location=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,2,gl.FLOAT,false,0,0);
    gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,texture);gl.uniform1i(gl.getUniformLocation(program,'tex'),0);
    if(t-last>100||image!==lastImage){last=t;lastImage=image;
      c.fillStyle='#101c2b';c.fillRect(0,0,1024,1024);c.font='20px sans-serif';
      const native=image?.width===768&&image?.height===256;
      const supported=native||(image?.width===960&&image?.height===936);
      const tiles=cameraTiles(native);
      c.font='18px sans-serif';c.fillStyle='white';
      for(const tile of tiles){
        c.fillText(tile.name,...tile.label);
        if(image&&previewFresh&&supported)
          c.drawImage(image,...tile.source,...tile.destination);
      }
      if(!image||!previewFresh||!supported){
        c.fillStyle='#adbecd';c.fillText('Waiting for video',300,360);
      }
      const panel={x:108,y:96,w:808,h:40};
      const connections={left:receivedHands===null?null:controllerConnected(hands.left,receivedHands.left,network),
                         right:receivedHands===null?null:controllerConnected(hands.right,receivedHands.right,network)};
      draw.info.status_panel=lastPanel={...panel,placement:'above-head',rendered:true,lines:1,connections};
      c.fillStyle='#06121f';c.fillRect(panel.x,panel.y,panel.w,panel.h);
      c.font='26px sans-serif';
      ['left','right'].forEach((side,i)=>{
        c.fillStyle=connections[side]?'#61e993':'#a3aab3';
        c.fillText(`${i===0?'Left':'Right'}: ${connections[side]===null?'Checking':connections[side]?'Connected':'Disconnected'}`,panel.x+16+i*300,panel.y+29);
      });
      const recording=recordingBadge(teleop,previewFresh);
      c.fillStyle=recording.color;c.fillText(recording.text,panel.x+634,panel.y+29);
      if(options.diagnostic){
        c.save();c.strokeStyle='#00ffff';c.lineWidth=6;c.strokeRect(4,4,1016,1016);
        c.font='bold 24px sans-serif';
        for(const [label,x,y,color] of [['TL',8,8,'#00ffff'],['TR',944,8,'#ffe45c'],['BL',8,978,'#65ff85'],['BR',944,978,'#ff85e5']]){
          c.fillStyle='#000';c.fillRect(x,y,72,38);c.fillStyle=color;c.fillText(label,x+12,y+28);
        }
        c.restore();
      }
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,canvas);
    }
    if(gl.isContextLost())throw Error('WebGL context lost');
    for(const eye of eyeViews){const v=eye.viewport,transform=eye.transform;
      gl.viewport(v.x,v.y,v.width,v.height);
      gl.uniform2f(gl.getUniformLocation(program,'panelScale'),...transform.scale);
      gl.uniform2f(gl.getUniformLocation(program,'panelCenter'),...transform.center);
      gl.drawArrays(gl.TRIANGLE_STRIP,0,4);}
    const error=gl.getError();if(error!==gl.NO_ERROR)throw Error('WebGL draw/upload error '+error);
    return !!image&&previewFresh&&((image.width===960&&image.height===936)||(image.width===768&&image.height===256))&&views.length>0;
  };
  draw.info=null;
  return draw;
}
