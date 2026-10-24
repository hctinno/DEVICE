/* Contract fixtures for the isolated spectrum component; not Python math evidence. */
function spectrumFixture(variant='complete') {
  const value={schema_version:1,kind:'synthetic_spectrum_view',trace:{
    schema_version:1,kind:'synthetic_frequency_spectrum',capture_id:'capture:bw-1',synthetic:true,
    axis_domain:'frequency_offset_hz',sample_unit:'dB',amplitude_basis:'relative_to_peak',
    selection_policy:'unique_peak_single_lobe_linear_db',frequency_offsets_hz:[-400000,-250000,0,250000,400000],relative_levels_db:[-12,-6,0,-6,-12]},
  bandwidth:{schema_version:1,kind:'synthetic_bandwidth_result',capture_id:'capture:bw-1',input_sha256:'a'.repeat(64),
    algorithm_id:'peak6_linear_db_v1',status:'complete',reason_codes:[],left_offset_hz:-250000,right_offset_hz:250000,
    bandwidth_hz:500000,minimum_bandwidth_hz:500000,margin_hz:0,conditional_comparison:'meets',
    synthetic:true,hardware_verified:false,ai_model_called:false,method_approval:'not_assessed',regulatory_scope_complete:false},
  psd:{schema_version:1,kind:'synthetic_psd_band_result',capture_id:'capture:psd-separate-1',input_sha256:'b'.repeat(64),
    algorithm_id:'declared_3khz_power_v1',input_basis:'band_power_3khz',power_dbm:0,power_mw:1,reference_bandwidth_hz:3000,
    maximum_dbm:8,margin_db:8,conditional_comparison:'meets',source_coverage:'single_declared_band',max_search_complete:false,
    synthetic:true,hardware_verified:false,ai_model_called:false,method_approval:'not_assessed',regulatory_scope_complete:false}};
  if (variant === 'below') {
    value.trace.frequency_offsets_hz=[-200000,-125000,0,125000,200000];
    Object.assign(value.bandwidth,{left_offset_hz:-125000,right_offset_hz:125000,bandwidth_hz:250000,margin_hz:-250000,conditional_comparison:'below'});
  } else if (variant === 'above') Object.assign(value.psd,{power_dbm:9,power_mw:7.943282347242816,margin_db:-1,conditional_comparison:'above'});
  else if (variant === 'incomplete') {
    value.trace.frequency_offsets_hz=[0,100000,200000];value.trace.relative_levels_db=[0,-3,-6];
    Object.assign(value.bandwidth,{status:'incomplete',reason_codes:['left_crossing_missing'],left_offset_hz:null,right_offset_hz:null,bandwidth_hz:null,margin_hz:null,conditional_comparison:null});
  } else if (variant === 'rounded') {
    value.trace.frequency_offsets_hz=[-400000,-249999.99999999997,0,249999.99999999997,400000];
    Object.assign(value.bandwidth,{left_offset_hz:-249999.99999999997,right_offset_hz:249999.99999999997,
      bandwidth_hz:499999.99999999994,margin_hz:-5.820766091346741e-11,conditional_comparison:'below'});
    Object.assign(value.psd,{input_basis:'flat_density_mw_per_hz',power_dbm:8,power_mw:6.309573444801934,
      margin_db:-5.6220036403531095e-16,conditional_comparison:'above'});
  } else if (variant === 'axis-error') {
    value.trace.frequency_offsets_hz=[-1e308,-1,0,1,1e308];
    value.trace.relative_levels_db=[-100,-12,0,-12,-100];
    Object.assign(value.bandwidth,{left_offset_hz:-0.5,right_offset_hz:0.5,bandwidth_hz:1,margin_hz:-499999,conditional_comparison:'below'});
  } else if (variant !== 'complete') throw new Error('unknown_contract_fixture');
  return value;
}
async function main() {
  const assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path');
  const http=require('node:http'), {pathToFileURL}=require('node:url'), {createHash}=require('node:crypto');
  const {chromium}=require('playwright');
  const own=path.resolve(__dirname,'../..'), local=path.join(own,'.local');
  if(!fs.existsSync(local)) fs.mkdirSync(local);
  assert(fs.lstatSync(local).isDirectory() && !fs.lstatSync(local).isSymbolicLink(),'Evidence .local must be a plain directory');
  const evidence=fs.mkdtempSync(path.join(local,'sv-'));
  const checks=[], errors=[], external=[];let browser, server;
  const result={kind:'spectrum_view_contract_browser',contract_fixture:true,python_math_connected:false,
    synthetic:true,hardware_verified:false,ai_model_called:false,checks,passed:false};
  try {
    const view=await import(pathToFileURL(path.join(__dirname,'spectrum_view.mjs')).href);
    const html='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>합성 스펙트럼 계약 검사</title><link rel="stylesheet" href="/spectrum.css"></head><body><main id="mount"></main><script type="module" src="/harness.mjs"></script></body></html>';
    const harness="import {renderSpectrumView} from '/spectrum_view.mjs'; window.spectrumRender=value=>renderSpectrumView(document.getElementById('mount'),value); window.spectrumReady=true;";
    const assets={'/':['text/html; charset=utf-8',html],'/spectrum.css':['text/css; charset=utf-8','body{margin:0;background:#080f1b;padding:20px;color:#e8eff8}#mount{max-width:1100px;margin:auto;min-width:0}'+view.SPECTRUM_VIEW_CSS],
      '/harness.mjs':['text/javascript; charset=utf-8',harness],'/spectrum_view.mjs':['text/javascript; charset=utf-8',fs.readFileSync(path.join(__dirname,'spectrum_view.mjs'))],
      '/spectrum_model.mjs':['text/javascript; charset=utf-8',fs.readFileSync(path.join(__dirname,'spectrum_model.mjs'))]};
    server=http.createServer((request,response)=>{
      const asset=request.method==='GET' && Object.hasOwn(assets,request.url) ? assets[request.url]:null;
      response.writeHead(asset?200:404,{'Content-Type':asset?asset[0]:'text/plain','Cache-Control':'no-store',
        'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'"});
      response.end(asset?asset[1]:'not found');
    });
    await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
    const origin='http://127.0.0.1:'+server.address().port;
    browser=await chromium.launch({headless:true});const context=await browser.newContext({viewport:{width:1440,height:1000}});
    context.setDefaultTimeout(5000);context.on('page',page=>page.on('pageerror',error=>errors.push(error.message)));
    context.on('request',request=>{if(!request.url().startsWith(origin+'/')) external.push(request.url());});
    const page=await context.newPage();await page.goto(origin);await page.waitForFunction(()=>window.spectrumReady);
    const render=async kind=>page.evaluate(value=>{window.spectrumRender(value);},spectrumFixture(kind));
    const check=async(name,action)=>{await action();checks.push(name);console.log('PASS '+name);};
    const dom=async()=>createHash('sha256').update(await page.locator('#mount').innerHTML()).digest('hex');
    await check('complete chart shows source trace -6dB and declared crossings with accessible frequency labels',async()=>{
      await render('complete');assert.equal(await page.locator('svg[role=img]').count(),1);
      await page.getByRole('img',{name:/합성 주파수/}).waitFor();
      assert.equal(await page.locator('[data-spectrum=trace]').getAttribute('points'),'82,252 203.5,140 406,28 608.5,140 730,252');
      assert.equal(await page.locator('[data-spectrum=threshold]').getAttribute('y1'),'140');
      assert.equal(await page.locator('[data-spectrum=crossing-left]').getAttribute('x1'),'203.5');
      assert.equal(await page.locator('[data-spectrum=crossing-right]').getAttribute('x1'),'608.5');
      assert.equal(await page.locator('[data-spectrum=bandwidth]').count(),1);
      assert.match(await page.locator('#mount').innerText(),/주파수 오프셋.*Hz/);
      assert.match(await page.locator('#mount').innerText(),/상대 레벨.*dB/);
    });
    await check('PSD zero dBm is one mW and separate captures hashes limits and scope remain visible',async()=>{
      const text=await page.locator('#mount').innerText();
      for(const expected of ['0 dBm','1 mW','capture:bw-1','capture:psd-separate-1','500000 Hz','3000 Hz','8 dBm','최대 탐색 미실행','합성','실장비 미검증','실제 AI 호출 없음','방법 승인 미평가','전체 규범 범위 미완료']) assert(text.includes(expected),expected);
      assert.equal(await page.locator('#mount button, #mount input, #mount a, #mount select, #mount textarea').count(),0);
    });
    await check('below bandwidth and above PSD keep conditional result meanings',async()=>{
      await render('below');assert.equal(await page.locator('[data-field=bandwidth-comparison]').getAttribute('data-comparison'),'below');
      assert.match(await page.locator('[data-field=bandwidth-comparison]').innerText(),/미만/);
      await render('above');assert.equal(await page.locator('[data-field=psd-comparison]').getAttribute('data-comparison'),'above');
      assert.match(await page.locator('[data-field=psd-comparison]').innerText(),/초과/);
    });
    await check('incomplete shows reasons and never substitutes zero width or crossing marks',async()=>{
      await render('incomplete');assert.equal(await page.locator('[data-spectrum^=crossing-]').count(),0);
      assert.equal(await page.locator('[data-spectrum=bandwidth]').count(),0);
      assert.match(await page.locator('[data-field=bandwidth-value]').innerText(),/계산값 없음/);
      assert.match(await page.locator('#mount').innerText(),/왼쪽 교차가 포함되지 않음/);
      assert.equal(await page.locator('[data-spectrum=trace]').count(),1);
    });
    await check('tiny margins and rounded floats preserve the Python conditional enums',async()=>{
      await render('rounded');assert.match(await page.locator('[data-field=bandwidth-margin]').innerText(),/e-11/);
      assert.match(await page.locator('[data-field=psd-margin]').innerText(),/e-16/);
      assert.equal(await page.locator('[data-field=bandwidth-comparison]').getAttribute('data-comparison'),'below');
      assert.equal(await page.locator('[data-field=psd-comparison]').getAttribute('data-comparison'),'above');
    });
    await check('malformed identity flags private fields XSS and nulls preserve the complete old DOM',async()=>{
      await render('complete');const before=await dom();
      for(const change of [v=>{v.bandwidth.capture_id='other';},v=>{v.psd.hardware_verified=true;},v=>{v.trace.author={seed:1};},
        v=>{v.psd.capture_id='<img src=x onerror="window.spectrumXss=true">';},v=>{v.bandwidth.bandwidth_hz=null;},
        v=>{v.trace.axis_domain='time';},v=>{v.psd.power_mw=NaN;},v=>{v.bandwidth.reason_codes=['unknown'];}]) {
        const value=spectrumFixture();change(value);
        const error=await page.evaluate(value=>{try{window.spectrumRender(value);return null;}catch(error){return error.message;}},value);
        assert.equal(error,'invalid_spectrum_view');assert.equal(await dom(),before);
      }
      assert.equal(await page.locator('#mount img, #mount script').count(),0);assert.equal(await page.evaluate(()=>window.spectrumXss),undefined);
    });
    await check('renderer exceptions are sanitized and leave the previous fragment intact',async()=>{
      const before=await dom();
      const error=await page.evaluate(value=>{
        const original=document.createElementNS.bind(document);
        document.createElementNS=(namespace,tag,...args)=>{if(tag==='polyline'){document.createElementNS=original;throw new Error('PRIVATE_RENDER_CANARY');}return original(namespace,tag,...args);};
        try{window.spectrumRender(value);return null;}catch(error){return error.message;}
      },spectrumFixture());
      assert.equal(error,'spectrum_render_failed');assert.equal(await dom(),before);
      const hostile=await page.evaluate(value=>{
        const original=document.createElementNS.bind(document);
        document.createElementNS=(namespace,tag,...args)=>{if(tag==='polyline'){document.createElementNS=original;throw Object.defineProperty({},'message',{get(){throw new Error('PRIVATE_ERROR_MESSAGE');}});}return original(namespace,tag,...args);};
        try{window.spectrumRender(value);return null;}catch(error){return error.message;}
      },spectrumFixture());
      assert.equal(hostile,'spectrum_render_failed');assert.equal(await dom(),before);await render('complete');
    });
    await check('unrepresentable chart axis is explicit without invented lines while finite report numbers survive',async()=>{
      await render('axis-error');assert.equal(await page.locator('svg').count(),0);
      assert.match(await page.locator('[data-spectrum-chart-error]').innerText(),/차트 표시 불가/);
      assert.match(await page.locator('[data-field=bandwidth-value]').innerText(),/1 Hz/);
    });
    await check('long literal ASCII IDs and a 390px view remain readable without horizontal overflow',async()=>{
      const value=spectrumFixture();value.trace.capture_id='C'.repeat(128);value.bandwidth.capture_id=value.trace.capture_id;value.psd.capture_id='capture:__proto__';
      await page.evaluate(value=>window.spectrumRender(value),value);
      await page.screenshot({path:path.join(evidence,'spectrum-desktop.png'),fullPage:true});
      await page.setViewportSize({width:390,height:844});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      assert((await page.locator('#mount').innerText()).includes('capture:__proto__'));
      await page.screenshot({path:path.join(evidence,'spectrum-mobile.png'),fullPage:true});
    });
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);result.passed=true;
    result.pageErrors=errors;result.externalRequests=external;
    console.log(JSON.stringify({passed:checks.length,evidence,contract_fixture:true,python_math_connected:false}));
  }catch(error){result.error=error.message;throw error;}
  finally{
    try {try{if(browser) await browser.close();}finally{if(server) await new Promise(resolve=>server.close(resolve));}}
    catch(error){result.passed=false;result.cleanup_error='owned_browser_or_server_cleanup_failed';throw error;}
    finally{fs.writeFileSync(path.join(evidence,'result.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});}
  }
}
module.exports={spectrumFixture,main};
if(require.main===module) main().catch(error=>{console.error(error);process.exitCode=1;});
