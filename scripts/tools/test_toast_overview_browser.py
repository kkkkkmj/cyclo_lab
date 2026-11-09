import asyncio,json,subprocess,tempfile,time,base64
from pathlib import Path
import websockets
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'scenario_delivery';checks={}
async def test():
 with tempfile.TemporaryDirectory(prefix='toast-cards-chrome-') as profile:
  log=open('/tmp/toast-cards-chrome.log','w')
  proc=subprocess.Popen(['/usr/bin/google-chrome','--headless=new','--no-sandbox','--disable-crashpad-for-testing','--disable-breakpad','--disable-gpu','--no-zygote','--single-process','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--remote-allow-origins=*','--user-data-dir='+profile,'about:blank'],stdout=log,stderr=log)
  try:
   p=Path(profile)/'DevToolsActivePort'
   for _ in range(100):
    if p.exists():break
    if proc.poll() is not None:raise RuntimeError(Path('/tmp/toast-cards-chrome.log').read_text())
    await asyncio.sleep(.1)
   port,path=p.read_text().splitlines();url='ws://127.0.0.1:'+port+path
   async with websockets.connect(url,max_size=20_000_000) as ws:
    seq=0;session=None
    async def call(method,params={},target=True):
     nonlocal seq
     seq+=1;ident=seq;message={'id':ident,'method':method,'params':params}
     if session and target:message['sessionId']=session
     await ws.send(json.dumps(message))
     while True:
      response=json.loads(await ws.recv())
      if response.get('id')==ident:
       if 'error' in response:raise RuntimeError(response['error'])
       return response.get('result',{})
    tid=(await call('Target.createTarget',{'url':'about:blank'},False))['targetId']
    session=(await call('Target.attachToTarget',{'targetId':tid,'flatten':True},False))['sessionId']
    await call('Page.enable');await call('Runtime.enable')
    await call('Emulation.setDeviceMetricsOverride',{'width':1800,'height':1100,'deviceScaleFactor':1,'mobile':False})
    await call('Page.navigate',{'url':(OUT/'overview_cards.html').as_uri()})
    async def js(expression):return (await call('Runtime.evaluate',{'expression':expression,'returnByValue':True}))['result'].get('value')
    for _ in range(100):
     if await js("document.querySelectorAll('.card').length")==25:break
     await asyncio.sleep(.1)
    checks['default']=await js("({filter:filter.value,count:cards.children.length,columns:cards.dataset.columns,width:cards.firstElementChild.getBoundingClientRect().width,viewBoxes:[...cards.querySelectorAll('svg')].map(x=>x.getAttribute('viewBox'))})")
    assert checks['default']['filter']=='operator_A_1' and checks['default']['count']==25
    assert 450<=checks['default']['width']<=600
    checks['filters']={}
    for group,count in [('all',100),('operator_A',50),('operator_B',50),('operator_A_1',25),('operator_A_2',25),('operator_B_1',25),('operator_B_2',25)]:
     result=await js(f"filter.value='{group}';filter.dispatchEvent(new Event('change'));[...cards.children].map(c=>({{id:c.dataset.id,group:c.dataset.group,index:+c.dataset.index}}))")
     assert len(result)==count and len({x['id'] for x in result})==count
     assert result==sorted(result,key=lambda x:(x['group'],x['index']))
     checks['filters'][group]=count
    await js("filter.value='operator_A_1';filter.dispatchEvent(new Event('change'))")
    checks['columns']=[]
    for n in (1,2,3):
     result=await js(f"document.querySelector('[data-cols=\"{n}\"]').click();getComputedStyle(cards).gridTemplateColumns.split(' ').length")
     assert result==n;checks['columns'].append(n)
    screenshot=await call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(OUT/'overview_cards_desktop.png').write_bytes(base64.b64decode(screenshot['data']))
    await js("cards.firstElementChild.click()")
    assert await js('zoom.open')
    assert await js("document.querySelector('#zoom-body svg').getAttribute('viewBox')===cards.querySelector('svg').getAttribute('viewBox')")
    screenshot=await call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(OUT/'overview_cards_zoom.png').write_bytes(base64.b64decode(screenshot['data']))
    await js("document.getElementById('close').click()");assert not await js('zoom.open')
    await js('cards.firstElementChild.click()');await call('Input.dispatchKeyEvent',{'type':'keyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27});await call('Input.dispatchKeyEvent',{'type':'keyUp','key':'Escape','code':'Escape','windowsVirtualKeyCode':27});assert not await js('zoom.open')
    checks['zoom']={'open':True,'button_close':True,'escape_close':True,'same_viewBox':True}
    checks['unique_embedded_ids']=await js('new Set(scenarios.map(s=>s.id)).size');assert checks['unique_embedded_ids']==100
    checks['same_scale']=len(set(checks['default'].pop('viewBoxes')))==1
    checks['file_scheme']=await js('location.protocol');assert checks['file_scheme']=='file:'
    checks['bread_count_each']=await js("scenarios.every(s=>[0,1,2,3].every(i=>s.shapes['bread_'+i].length>0))")
    checks['no_old_ids']=await js("!document.documentElement.outerHTML.includes('batch02_toast_')")
    await call('Browser.close',{},False)
  finally:
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=5)
   log.close()
 report=ROOT/'logs/toast_overview/overview_cards_checks.json';report.parent.mkdir(parents=True,exist_ok=True)
 report.write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
asyncio.run(test())
