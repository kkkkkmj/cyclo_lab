/* Run after preview_client.js with mocked fetch/createImageBitmap/performance. */
async function runPreviewClientTests(mock){
 let count=0;
 const assert=(ok,text)=>{if(!ok)throw Error(text);};
 let c=createPreviewClient();
 mock.code=503;await c.poll();assert(c.state.stage==='http_error'&&!c.confirmed(),'503 must fail closed');count++;
 mock.code=200;mock.decodeError=true;await c.poll();assert(c.state.stage==='fetch_or_decode_error'&&!c.confirmed(),'decode failure hidden');count++;
 mock.decodeError=false;await c.poll();assert(c.fresh()&&!c.confirmed(),'decode incorrectly confirms draw');count++;
 c.markDrawn();assert(c.confirmed()&&c.state.stage==='draw_submitted','draw acknowledgement missing');count++;
 mock.now+=1001;assert(!c.confirmed(),'stale frame accepted');count++;
 mock.now=0;await c.poll();c.markDrawn();c.drawError('GPU error');assert(!c.confirmed()&&c.state.error==='GPU error','draw failure allowed');count++;
 mock.age=2000;await c.poll();assert(!c.fresh()&&c.state.stage==='decoded_but_stale','stale decode accepted');count++;
 mock.age=null;await c.poll();assert(c.state.stage==='fetch_or_decode_error','missing header accepted');count++;
 mock.now=50000;mock.age=100;await c.poll();c.markDrawn();
 mock.now+=50;mock.code=503;await c.poll();
 assert(!c.confirmed()&&c.diagnostics().frame_age_ms===150,'error must not replace frame age with browser uptime');count++;
 mock.code=200;mock.decodeError=true;mock.now+=50;await c.poll();
 assert(!c.confirmed()&&c.diagnostics().frame_age_ms===200,'decode failure must retain actual frame age');count++;
 return count;
}
