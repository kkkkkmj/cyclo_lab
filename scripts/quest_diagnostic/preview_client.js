/* Errors and decode/draw acknowledgements are deliberately separate. */
function createPreviewClient(){
 const state={stage:'waiting',http_status:null,error:null,received:0,decoded:0,drawn:0,
              frame_id:null,run_id:null,drawn_frame_id:null};
 let image=null,expires=0,capturedClock=null,busy=false,drawnImage=null,teleop=null;
 return {
  state,
  teleop:()=>teleop,
  diagnostics:()=>({frame_age_ms:capturedClock===null?null:performance.now()-capturedClock}),
  image:()=>image,
  fresh:()=>!!image&&performance.now()<expires,
  confirmed:()=>!!image&&drawnImage===image&&performance.now()<expires,
  invalidateDraw:()=>{drawnImage=null;},
  markDrawn:()=>{if(image&&performance.now()<expires){
    drawnImage=image;state.drawn_frame_id=state.frame_id;state.drawn++;state.stage='draw_submitted';state.error=null;
  }},
  drawError:error=>{drawnImage=null;state.stage='draw_error';state.error=String(error);},
  poll:async function(){
    if(busy)return;busy=true;
    try{
      const requested=performance.now();
      const response=await fetch('/preview.jpg',{cache:'no-store',signal:AbortSignal.timeout(800)});
      state.http_status=response.status;
      state.server_build=response.headers.get('X-Quest-Server-Build');
      if(response.status!==200){
        state.stage='http_error';expires=0;drawnImage=null;
        const body=await response.text();state.producer_reason=null;
        try{state.producer_reason=JSON.parse(body).reason||null;}catch(_){}
        state.error=body.slice(0,240);return;
      }
      state.producer_reason=null;state.received++;
      const age=Number(response.headers.get('X-Preview-Age-Ms'));
      if(!response.headers.has('X-Preview-Age-Ms')||!Number.isFinite(age)||age<0)throw Error('missing/invalid preview age header');
      state.stage='decoding';
      const blob=await response.blob(),decodeStarted=performance.now();
      const next=await createImageBitmap(blob);
      state.bytes=blob.size;state.decode_ms=performance.now()-decodeStarted;
      state.fetch_decode_ms=performance.now()-requested;
      if(image)image.close();image=next;drawnImage=null;capturedClock=requested-age;expires=capturedClock+1000;
      state.frame_id=response.headers.get('X-Preview-Frame');
      state.run_id=response.headers.get('X-Preview-Run');
      // Optional, display-only metadata tied to this decoded frame. Old producers are explicit unknown.
      teleop=null;
      try{const value=JSON.parse(response.headers.get('X-Teleop-Status'));if(value?.version===1)teleop=value;}catch(_){/* Display unavailable; preview safety is unchanged. */}
      state.decoded++;state.stage=performance.now()<expires?'decoded':'decoded_but_stale';state.error=null;
    }catch(error){expires=0;drawnImage=null;state.stage='fetch_or_decode_error';state.error=String(error);}
    finally{busy=false;}
  }
 };
}
