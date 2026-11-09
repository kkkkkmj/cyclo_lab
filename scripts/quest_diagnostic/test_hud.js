/* CPU mocks only; no claim about actual WebGL optics or Meta casting. Run after hud.js. */
function runHUDTests(){
 let count=0;
 const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
 const near=(a,b)=>Math.abs(a-b)<1e-8;
 const normal=hudSettings({});
 assert(normal.scale===.65&&normal.centerX===0&&normal.centerY===0&&!normal.diagnostic,'normal defaults changed');count++;
 assert(hudSettings({mode:'normal',centerX:.4,centerY:.4}).centerX===0,'casting offset leaked into normal');count++;
 const cast=hudSettings({mode:'casting',scale:.6,centerX:.1,centerY:-.1,diagnostic:true});
 const a=hudTransform({width:1200,height:1400},cast);
 assert(near(a.scale[0]*1200,a.scale[1]*1400),'per-eye aspect');count++;
 assert(near(a.center[0],.1)&&near(a.center[1],-.1),'center sign/application');count++;
 for(const [w,h] of [[1200,1400],[1400,1200],[1920,1080]])for(const x of [-.45,.45]){
   const r=hudTransform({width:w,height:h},hudSettings({mode:'casting',scale:.85,centerX:x,centerY:x}));
   assert(r.bounds.every(n=>n>=-.980000001&&n<=.980000001),'panel clipped inside eye');
 }count++;
 let failed=false;try{hudTransform({width:0,height:100},cast);}catch(e){failed=true;}
 assert(failed,'bad viewport accepted');count++;
 const bad=hudSettings({scale:NaN,margin:NaN,mode:'casting',centerX:Infinity});
 assert(bad.scale===.65&&bad.margin===.02&&bad.centerX===0,'invalid settings fallback');count++;
 return count;
}
function runHUDRenderTests(){
 const events=[],texts=[],images=[],uniforms=[],viewports=[];
 let error=0,lost=false;
 const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
 const context={fillRect(){},fillText:(...a)=>texts.push(a),drawImage:(...a)=>images.push(a),
   save(){},restore(){},strokeRect:(...a)=>events.push(['border',...a])};
 const gl=new Proxy({NO_ERROR:0,getError:()=>error,isContextLost:()=>lost,
   getShaderParameter:()=>true,getProgramParameter:()=>true,getUniformLocation:(_,n)=>n,
   uniform2f:(...a)=>uniforms.push(a),viewport:(...a)=>viewports.push(a)},
   {get:(o,k)=>k in o?o[k]:()=>({})});
 const draw=makeHUD(gl,{mode:'casting',scale:.65,centerX:.1,centerY:.1,diagnostic:true});
 const views=[{eye:'left',projectionMatrix:[1]},{eye:'right',projectionMatrix:[2]}];
 const layer={framebufferWidth:3000,framebufferHeight:1700,
   getViewport:v=>v.eye==='left'?{x:0,y:0,width:1400,height:1600}:{x:1500,y:40,width:1450,height:1550}};
 const hands={left:{valid:true,reason:'ok',buttons:[]},right:{valid:true,reason:'ok',buttons:[]}};
 const image={width:960,height:936};
 // The runner installs this document mock before calling makeHUD.
 globalThis.hudTestContext=context;
 // Context is requested at makeHUD time, so runner's getContext returns a forwarding proxy.
 const ack=draw(views,layer,hands,'ACK OK',image,true,200,{stage:'decoded'},'test-build');
 assert(ack,'fresh draw not acknowledged');
 assert(draw.info.status_panel.rendered&&draw.info.status_panel.placement==='above-head','panel was not drawn');
 const panel=draw.info.status_panel;
 const iy=images[0][6];
 assert(panel.y>=0&&panel.y+panel.h<iy&&panel.x>=0&&panel.x+panel.w<=1024,'status overlaps image or leaves panel');
 assert(draw.info.status_panel.lines<=2,'compact status grew beyond two lines');
 assert(texts.some(t=>t[0]==='Left: Checking'),'missing connectivity hides bar');
 draw(views,layer,hands,'ACK OK',image,true,210,{stage:'decoded'},'test-build');
 assert(draw.info.status_panel?.rendered,'panel diagnostics lost between canvas updates');
 assert(viewports[0].join()==='0,0,1400,1600'&&viewports[1].join()==='1500,40,1450,1550','framebuffer/eye mix-up');
 assert(draw.info.framebuffer.width===3000&&draw.info.eyes.length===2,'missing render diagnostics');
 assert(uniforms.filter(a=>a[0]==='panelCenter').every(a=>a[1]===.1&&a[2]===.1),'center uniform missing');
 assert(images.length===3&&images.every(a=>a.length===9&&a[3]===300&&a[4]===300&&a[7]===a[8]),'camera tile cropped or stretched');
 assert(images.map(a=>a[1]).join(',')==='10,330,650'&&images.every(a=>a[2]===612),'wrong camera source');
 assert(images[1][7]===images[2][7]&&images[0][7]>images[1][7],'HEAD not large or wrists unequal');
 assert(['TL','TR','BL','BR'].every(n=>texts.some(t=>t[0]===n))&&events.some(e=>e[0]==='border'),'missing calibration marks');
 assert(!draw(views,layer,hands,'ACK OK',image,false,400,{stage:'stale'},'test-build'),'stale preview acknowledged');
 assert(texts.some(t=>t[0].includes('Waiting for video')),'stale video hidden');
 const nativeStart=images.length;
 assert(draw(views,layer,hands,'ACK OK',{width:768,height:256},true,500,{stage:'decoded'},'test-build',{recording:true,episode_result:{label:'SUCCESS',success:true}},{}),'native preview not acknowledged');
 assert(images.slice(nativeStart).length===3&&images.slice(nativeStart).every(a=>a[3]===244&&a[4]===244),'native draw used legacy crop');
 assert(texts.some(t=>t[0]==='● REC')&&texts.some(t=>t[0]==='SUCCESS'),'record/result not both drawn');
 assert(draw.info.status_panel.resultBox.y+draw.info.status_panel.resultBox.h<144,'result overlaps camera');
 error=1282;let threw=false;try{draw(views,layer,hands,'ACK OK',image,true,600,{stage:'decoded'},'test-build');}catch(e){threw=true;}
 assert(threw,'WebGL error suppressed');
 error=0;lost=true;threw=false;try{draw(views,layer,hands,'ACK OK',image,true,800,{stage:'decoded'},'test-build');}catch(e){threw=true;}
 assert(threw,'context loss suppressed');
 return 19;
}

function runHUDPersistenceTests(){
 let raw=null,count=0;
 const assert=(v,msg)=>{if(!v)throw Error(msg);};
 const storage={getItem:()=>raw,setItem:(_,v)=>{raw=v;}};
 let loaded=loadHUDPreferences(storage),state=loaded.state;
 assert(state.mode==='casting'&&state.profiles.casting.scale===.50&&state.profiles.casting.centerX===.24&&state.profiles.casting.centerY===.10,'estimated preset');count++;
 assert(state.profiles.normal.scale===.65&&state.profiles.normal.centerX===0,'normal changed');count++;
 state.profiles.casting.scale=.62;state.profiles.casting.centerX=.14;state.profiles.casting.centerY=.08;
 saveHUDPreferences(state,storage);loaded=loadHUDPreferences(storage);
 assert(loaded.state.profiles.casting.scale===.62&&loaded.state.profiles.casting.centerX===.14&&loaded.state.profiles.casting.centerY===.08,'refresh persistence');count++;
 state.mode='normal';saveHUDPreferences(state,storage);loaded=loadHUDPreferences(storage);
 assert(loaded.state.mode==='normal'&&loaded.state.profiles.casting.scale===.62,'mode/profile retention');count++;
 state.profiles.casting=hudDefaults('casting');state.mode='casting';saveHUDPreferences(state,storage);
 assert(loadHUDPreferences(storage).state.profiles.casting.scale===.50,'persisted reset');count++;
 raw='{broken';assert(loadHUDPreferences(storage).state.mode==='casting','bad JSON fallback');count++;
 raw=JSON.stringify({schema:99});assert(loadHUDPreferences(storage).state.profiles.casting.centerX===.24,'schema fallback');count++;
 const denied={getItem(){throw Error('blocked');},setItem(){throw Error('quota');}};
 assert(loadHUDPreferences(denied).status.includes('Failed')&&saveHUDPreferences(state,denied).includes('Failed'),'storage denial hidden');count++;
 return count;
}

function runHUDMigrationTests(){
 const values=new Map([['cyclo.quest.display.v1',JSON.stringify({schema:1,mode:'normal',profiles:{casting:{scale:.7}}})]]);
 const storage={getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v)};
 const old=values.get('cyclo.quest.display.v1');
 const assert=(v,m)=>{if(!v)throw Error(m);};
 let result=loadHUDPreferences(storage);
 assert(HUD_STORAGE_KEY==='cyclo.quest.display.v2'&&result.state.schema===2,'version not advanced');
 assert(result.state.mode==='casting'&&result.state.profiles.casting.scale===.5&&result.state.profiles.casting.centerX===.24&&result.state.profiles.casting.centerY===.1&&result.state.profiles.casting.diagnostic,'old values overrode new preset');
 assert(values.has(HUD_STORAGE_KEY)&&values.get('cyclo.quest.display.v1')===old,'first load not saved or old data modified');
 result.state.profiles.casting.centerX=.31;result.state.profiles.casting.scale=.53;saveHUDPreferences(result.state,storage);
 result=loadHUDPreferences(storage);
 assert(result.state.profiles.casting.centerX===.31&&result.state.profiles.casting.scale===.53,'preset reapplied over user edits');
 const transform=hudTransform({width:1680,height:1760},hudDefaults('casting'));
 assert(transform.center[0]===.24&&transform.center[1]===.1&&transform.scale[0]===.5,'measured viewport clamps preset');
 assert(Math.abs((transform.center[0]-.12)*1680/2-100.8)<1e-8,'horizontal displacement');
 return 6;
}

function runControlStatusTests(){
 const assert=(v,m)=>{if(!v)throw Error(m);};
 const h={valid:true,active:false,control_reason:'ready',squeeze_pressed:true,squeeze:1,trigger:.4};
 const status={version:1,episode_state:'WAITING',live:true,hands:{left:h,right:{...h}},start_blocked:true,
   start_blockers:['input_stale','preview_unconfirmed','left:squeeze_held','right:squeeze_held']};
 let lines=teleopStatusLines(status,true).join('');
 assert(lines.includes('WAITING')&&lines.includes('SQ ON 1.00')&&!lines.includes('Arm active'),'button misrepresented as control');
 assert(['START_BLOCKED','Stale/missing input','Fresh video display unconfirmed','L Release squeeze','R Release squeeze'].every(s=>lines.includes(s)),'lost blocking condition');
 status.episode_state='RUNNING';h.active=true;h.control_reason='active';
 assert(teleopStatusLines(status,true).join('').includes('L Input Valid | Arm active'),'actual verdict missing');
 assert(!teleopStatusLines(status,false).join('').includes('L Input Valid | Arm active'),'stale active verdict');
 assert(teleopStatusLines(null,true)[0].includes('received'),'old producer invents state');
 status.live=false;
 assert(teleopStatusLines(status,true)[1].includes('Input lost'),'input loss hidden by button');
 return 6;
}

function runCompactStatusTests(){
 const assert=(v,m)=>{if(!v)throw Error(m);};
 const h={valid:true,active:false,control_reason:'ready',squeeze:1,trigger:.7};
 const s={version:1,episode_state:'WAITING',live:true,hands:{left:h,right:{...h}},
   start_blockers:['left:squeeze_held','right:squeeze_held','left:invalid']};
 let rows=compactStatusLines(s,true);
 assert(rows.length===2&&rows[0].includes('L Waiting SQ1.0/TR0.7')&&!rows[0].includes('Active'),'buttons imply movement');
 assert(rows[1].includes('Left hand·Right hand')&&!rows[1].includes('invalid'),'blocking summary');
 s.episode_state='RUNNING';h.active=true;
 rows=compactStatusLines(s,true);
 assert(rows.length===1&&rows[0].includes('L Active')&&rows[0].includes('R Ready'),'actual control not shown');
 assert(compactStatusLines(s,false).length<=2&&!compactStatusLines(s,false).join('').includes('L Active'),'stale active status');
 assert(compactStatusLines(null,true).length<=2,'missing status too long');
 assert(!rows.join('').match(/build|revision|ms|focus/),'detail leaked into compact view');
 return 6;
}

function runCameraConnectionTests(){
 const assert=(v,m)=>{if(!v)throw Error(m);};
 const h={source_id:'2',profiles:['meta-quest-touch-plus'],mapping:'xr-standard',valid:false,reason:'no_grip_pose'};
 assert(controllerConnected(h,{...h},'ACK OK'),'temporary pose loss incorrectly disconnects controller');
 assert(!controllerConnected(h,h,'stale'),'stale reception allowed');
 assert(!controllerConnected(h,{...h,source_id:'3'},'ACK OK'),'old source ACK accepted');
 assert(!controllerConnected({...h,profiles:['meta-fixed-hand']},h,'ACK OK'),'hand tracking connected');
 assert(!controllerConnected({...h,reason:'hand_input_excluded'},h,'ACK OK'),'disguised hand connected');
 assert(!controllerConnected(h,{},'ACK OK'),'missing received input connected');
 for(const margin of [0,.02,.18]){
   const box={x:24+margin*1024,y:84+margin*1024,w:976-2*margin*1024,h:842-2*margin*1024};
   const r=Math.min(box.w/960,box.h/936);
   const rect={x:box.x+(box.w-960*r)/2,y:box.y+(box.h-936*r)/2,w:960*r,h:936*r};
   const tiles=cameraTiles(rect);
   for(const tile of tiles){const [x,y,w,h]=tile.destination;
     assert(x>=0&&y>=0&&x+w<=1024&&y+h<=1024&&w===h,'tile outside canvas / distorted');}
   assert(tiles[0].destination[1]+tiles[0].destination[3]<tiles[1].destination[1],'camera overlap');
 }
 return 8;
}

function runDenseLayoutTests(){
 const tiles=cameraTiles();const assert=(v,m)=>{if(!v)throw Error(m);};
 assert(tiles[0].destination[2]===480&&tiles[1].destination[2]===328,'unexpected sizes');
 assert(tiles[1].destination[2]===tiles[2].destination[2],'unequal wrists');
 assert(136<tiles[0].destination[1],'bar overlaps head');
 assert(tiles.every(t=>t.destination[0]>=48&&t.destination[1]>=144&&t.destination[0]+t.destination[2]<=976&&t.destination[1]+t.destination[3]<=976),'safe area overflow');
 assert(tiles.every(t=>t.source[2]===300&&t.source[3]===300&&t.destination[2]===t.destination[3]),'crop/stretch');
 return 5;
}

function runNativeRecordingTests(){
 const assert=(v,m)=>{if(!v)throw Error(m);};
 const old=cameraTiles(false),native=cameraTiles(true);
 assert(native.every((t,i)=>t.destination.join()===old[i].destination.join()),'layout changed');
 assert(native.every(t=>t.source[2]===244&&t.source[3]===244)&&native[2].source[0]===518,'native ROI cropped');
 assert(recordingBadge({episode_state:'RUNNING'},true).text==='Checking','RUNNING inferred recording');
 assert(recordingBadge({episode_state:'RUNNING',recording:false},true).text==='NO REC','disabled recorder shows REC');
 assert(recordingBadge({episode_state:'WAITING',recording:true},true).text==='● REC','recorder verdict overridden');
 assert(recordingBadge({recording:true},false).text==='Checking','stale REC retained');
 assert(recordingBadge(null,true).text==='Checking','missing status not explicit');
 return 7;
}

function runEpisodeResultTests(){
 const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
 const status={episode_state:'WAITING',recording:false,live:false,
   episode_result:{reason:'success',label:'SUCCESS',success:true}};
 assert(episodeResultBadge(status).color==='#61e993','success must be green');
 const calls=[],rects=[],images=[];
 const c={fillRect:(...x)=>rects.push(x),fillText:function(text,x,y,maxWidth){calls.push({text,x,y,maxWidth,color:this.fillStyle,font:this.font});},
   drawImage:(...x)=>images.push(x)};
 const canvas={getContext:()=>c};
 const panel=drawPCPreview(canvas,{width:768,height:256},status,true);
 assert(panel.recording==='NO REC'&&panel.result==='SUCCESS','practice result hidden by recorder state');
 const result=calls.find(x=>x.text==='SUCCESS');
 assert(result.color==='#61e993'&&result.font==='bold 32px sans-serif','success styling');
 assert(result.x+result.maxWidth<=916&&result.y<144,'result clips or overlaps camera');
 assert(images.every(x=>x[6]>=144),'camera overlaps status');
 assert(drawPCPreview(canvas,null,status,false).result==='SUCCESS','historical result erased by stale input');
 for(const label of ['STOPPED','TRACKING STALL','TIMEOUT','BREAD DROPPED']){
   status.episode_result={label,success:false};
   assert(drawPCPreview(canvas,null,status,true).result===label,'wrong stop reason');
 }
 status.episode_result=null;assert(drawPCPreview(canvas,null,status,true).result==='','approved start did not clear');
 return 10;
}
