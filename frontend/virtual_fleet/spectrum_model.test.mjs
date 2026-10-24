import test from 'node:test';
import assert from 'node:assert/strict';
import fixture from './spectrum_browser_check.cjs';
import {validateSpectrumView, formatSpectrumNumber, spectrumGeometry} from './spectrum_model.mjs';
const {spectrumFixture}=fixture;

test('exact contract accepts complete below above incomplete rounded and separate PSD captures',()=>{
  for(const kind of ['complete','below','above','incomplete','rounded','axis-error']) {
    const value=spectrumFixture(kind), actual=validateSpectrumView(value);
    assert.deepEqual(actual,value);assert.notEqual(actual,value);assert.notEqual(actual.trace,value.trace);
    assert.notEqual(actual.psd.capture_id,actual.trace.capture_id);
  }
});

test('validated values are detached JSON copies in both directions',()=>{
  const value=spectrumFixture(), actual=validateSpectrumView(value);
  value.trace.relative_levels_db[0]=-50;value.psd.capture_id='changed';
  assert.equal(actual.trace.relative_levels_db[0],-12);assert.equal(actual.psd.capture_id,'capture:psd-separate-1');
  actual.bandwidth.reason_codes.push('left_crossing_missing');assert.deepEqual(value.bandwidth.reason_codes,[]);
});

test('capture IDs follow the fixed ASCII 128 character rule with literal safe IDs',()=>{
  const value=spectrumFixture();value.trace.capture_id='C'.repeat(128);value.bandwidth.capture_id=value.trace.capture_id;
  assert.equal(validateSpectrumView(value).trace.capture_id.length,128);
  for(const id of ['C'.repeat(129),'한글','<img src=x onerror=alert(1)>','bad\n','']) {
    const changed=spectrumFixture();changed.psd.capture_id=id;assert.throws(()=>validateSpectrumView(changed),/invalid_spectrum_view/);
  }
  const safe=spectrumFixture();safe.psd.capture_id='capture:__proto__';assert.equal(validateSpectrumView(safe).psd.capture_id,'capture:__proto__');
});

test('rejects every missing or extra top trace and result key rather than filtering private data',()=>{
  const paths=[[],['trace'],['bandwidth'],['psd']];
  for(const keys of paths) {
    const value=spectrumFixture(), item=keys.reduce((node,key)=>node[key],value);
    for(const key of Object.keys(item)) {
      const changed=structuredClone(value), record=keys.reduce((node,name)=>node[name],changed);delete record[key];
      assert.throws(()=>validateSpectrumView(changed),/invalid_spectrum_view/);
    }
    item.author={seed:17};assert.throws(()=>validateSpectrumView(value),/invalid_spectrum_view/);
  }
});

test('rejects wrong identity flags constants hash types and unsupported enum strings',()=>{
  for(const change of [v=>{v.schema_version=true;},v=>{v.bandwidth.capture_id='other';},v=>{v.trace.axis_domain='time';},
    v=>{v.trace.sample_unit='dBm';},v=>{v.trace.amplitude_basis='absolute';},v=>{v.trace.selection_policy='sort';},
    v=>{v.bandwidth.algorithm_id='future';},v=>{v.psd.algorithm_id='future';},v=>{v.psd.reference_bandwidth_hz=3001;},
    v=>{v.bandwidth.minimum_bandwidth_hz=0;},v=>{v.psd.maximum_dbm=10;},v=>{v.psd.input_basis='unknown_rbw';},
    v=>{v.psd.source_coverage='full_band';},v=>{v.psd.max_search_complete=true;},v=>{v.psd.conditional_comparison='below';},
    v=>{v.bandwidth.conditional_comparison='above';},v=>{v.bandwidth.input_sha256='not-a-hash';},
    v=>{v.psd.input_sha256='a'.repeat(64)+'\n';},v=>{v.psd.power_mw=0;},v=>{v.bandwidth.status=['complete'];}]) {
    const value=spectrumFixture();change(value);assert.throws(()=>validateSpectrumView(value),/invalid_spectrum_view/);
  }
  for(const part of ['bandwidth','psd']) for(const [key,value] of Object.entries({synthetic:false,hardware_verified:true,ai_model_called:true,
    method_approval:'approved',regulatory_scope_complete:true})) {
    const data=spectrumFixture();data[part][key]=value;assert.throws(()=>validateSpectrumView(data),/invalid_spectrum_view/);
  }
});

test('trace numeric arrays keep the original order and relative peak definition',()=>{
  for(const change of [v=>{v.trace.frequency_offsets_hz[1]=true;},v=>{v.trace.relative_levels_db[1]=NaN;},
    v=>{v.trace.frequency_offsets_hz[0]=-Infinity;},v=>{v.trace.frequency_offsets_hz.reverse();},
    v=>{v.trace.frequency_offsets_hz[1]=v.trace.frequency_offsets_hz[0];},v=>{v.trace.relative_levels_db.pop();},
    v=>{v.trace.relative_levels_db=v.trace.relative_levels_db.map(x=>x-1);},v=>{v.trace.relative_levels_db[0]=1;},
    v=>{v.trace.frequency_offsets_hz=[0,1];v.trace.relative_levels_db=[0,-6];}]) {
    const value=spectrumFixture();change(value);assert.throws(()=>validateSpectrumView(value),/invalid_spectrum_view/);
  }
  const tooLong=spectrumFixture();tooLong.trace.frequency_offsets_hz=Array.from({length:65537},(_,index)=>index);
  tooLong.trace.relative_levels_db=Array(65537).fill(-12);tooLong.trace.relative_levels_db[32768]=0;
  assert.throws(()=>validateSpectrumView(tooLong),/invalid_spectrum_view/);
});

test('the declared 65536 point limit is accepted without sorting or losing bins',()=>{
  const value=spectrumFixture();value.trace.frequency_offsets_hz=Array.from({length:65536},(_,index)=>index);
  value.trace.relative_levels_db=Array(65536).fill(-12);value.trace.relative_levels_db[32768]=0;
  Object.assign(value.bandwidth,{left_offset_hz:32767.5,right_offset_hz:32768.5,bandwidth_hz:1,margin_hz:-499999,conditional_comparison:'below'});
  const actual=validateSpectrumView(value);assert.equal(actual.trace.frequency_offsets_hz.length,65536);
  assert.equal(spectrumGeometry(actual).points.length,65536);assert.deepEqual(actual.trace.frequency_offsets_hz,value.trace.frequency_offsets_hz);
});

test('JSON boundary rejects array extras accessors sparse arrays and non-JSON records with sanitized errors',()=>{
  for(const change of [v=>{v.trace.frequency_offsets_hz.seed=1;},v=>{delete v.trace.frequency_offsets_hz[1];},
    v=>{Object.defineProperty(v.trace.relative_levels_db,0,{get(){throw new Error('PRIVATE_GETTER');}});},
    v=>{v.bandwidth=new Date();},v=>{v.trace[Symbol('private')]=1;}]) {
    const value=spectrumFixture();change(value);
    assert.throws(()=>validateSpectrumView(value),error=>error.message==='invalid_spectrum_view' && !error.message.includes('PRIVATE'));
  }
});

test('array accessors are not evaluated and hostile exception messages never escape validation',()=>{
  const value=spectrumFixture();let reads=0;
  Object.defineProperty(value.trace.relative_levels_db,0,{enumerable:true,get(){reads++;return -12;}});
  assert.throws(()=>validateSpectrumView(value),/invalid_spectrum_view/);assert.equal(reads,0);
  const hostile=new Proxy({},{getPrototypeOf(){throw Object.defineProperty({},'message',{get(){throw new Error('PRIVATE_ERROR_MESSAGE');}});}});
  assert.throws(()=>validateSpectrumView(hostile),error=>error.message==='invalid_spectrum_view');
});

test('complete requires finite values and incomplete requires null values and ordered reasons',()=>{
  for(const key of ['left_offset_hz','right_offset_hz','bandwidth_hz','margin_hz']) for(const bad of [null,true,NaN,Infinity]) {
    const value=spectrumFixture();value.bandwidth[key]=bad;assert.throws(()=>validateSpectrumView(value),/invalid_spectrum_view/);
  }
  for(const key of ['power_dbm','power_mw','margin_db']) for(const bad of [null,false,NaN,Infinity]) {
    const value=spectrumFixture();value.psd[key]=bad;assert.throws(()=>validateSpectrumView(value),/invalid_spectrum_view/);
  }
  for(const key of ['left_offset_hz','right_offset_hz','bandwidth_hz','margin_hz','conditional_comparison']) {
    const value=spectrumFixture('incomplete');value.bandwidth[key]=0;assert.throws(()=>validateSpectrumView(value),/invalid_spectrum_view/);
  }
  for(const reasons of [[],['unknown'],['left_crossing_missing','non_unique_peak'],['non_unique_peak','non_unique_peak']]) {
    const value=spectrumFixture('incomplete');value.bandwidth.reason_codes=reasons;assert.throws(()=>validateSpectrumView(value),/invalid_spectrum_view/);
  }
});

test('rounding does not cause JavaScript to replace the declared conditional comparison',()=>{
  const value=validateSpectrumView(spectrumFixture('rounded'));
  assert.equal(formatSpectrumNumber(value.bandwidth.bandwidth_hz),'500000');assert.equal(value.bandwidth.conditional_comparison,'below');
  assert.equal(value.psd.power_dbm,8);assert.equal(value.psd.conditional_comparison,'above');
  for(const number of [1e-16,-1e-12,Number.MIN_VALUE]) {
    const displayed=formatSpectrumNumber(number);assert.notEqual(Number(displayed),0);assert(Number.isFinite(Number(displayed)));
  }
});

test('chart geometry uses declared crossings and reports an unrepresentable axis explicitly',()=>{
  const value=validateSpectrumView(spectrumFixture());
  const geometry=spectrumGeometry(value);assert.equal(geometry.status,'ready');assert.equal(geometry.points.length,5);
  assert.equal(geometry.crossings.length,2);assert(geometry.crossings[0].x<geometry.crossings[1].x);
  assert.equal(spectrumGeometry(validateSpectrumView(spectrumFixture('incomplete'))).crossings.length,0);
  const error=spectrumGeometry(validateSpectrumView(spectrumFixture('axis-error')));assert.equal(error.status,'error');assert.equal(error.code,'chart_axis_unrepresentable');
  const collapsed=spectrumFixture();collapsed.bandwidth.left_offset_hz=0;collapsed.bandwidth.right_offset_hz=0;
  assert.equal(spectrumGeometry(validateSpectrumView(collapsed)).status,'error');
});

test('SVG float coordinate precision preserves distinctions before publishing chart geometry',()=>{
  assert.equal(spectrumGeometry(validateSpectrumView(spectrumFixture('svg-precision'))).status,'error');
  const value=spectrumFixture();value.trace.relative_levels_db[0]=-6.00000000001;
  assert.equal(spectrumGeometry(validateSpectrumView(value)).status,'error');
});

test('non-enumerable object and array data fields cannot disappear from the validated JSON copy',()=>{
  for(const change of [v=>Object.defineProperty(v,'schema_version',{enumerable:false}),
    v=>Object.defineProperty(v.psd,'conditional_comparison',{enumerable:false}),
    v=>Object.defineProperty(v.trace.frequency_offsets_hz,0,{enumerable:false}),
    v=>{Object.assign(v,spectrumFixture('incomplete'));Object.defineProperty(v.bandwidth.reason_codes,0,{enumerable:false});}]) {
    const value=spectrumFixture();change(value);assert.throws(()=>validateSpectrumView(value),/invalid_spectrum_view/);
  }
  const normal=spectrumFixture();Object.freeze(normal.psd);assert.deepEqual(validateSpectrumView(normal),normal);
  const nullPrototype=Object.assign(Object.create(null),spectrumFixture());
  nullPrototype.trace=Object.assign(Object.create(null),nullPrototype.trace);
  nullPrototype.psd=Object.assign(Object.create(null),nullPrototype.psd);
  const copy=validateSpectrumView(nullPrototype);assert.equal(copy.psd.conditional_comparison,'meets');
  assert.deepEqual(validateSpectrumView(copy),copy);
});

test('JSON values are checked by their own indices rather than inherited array hooks',()=>{
  const value=spectrumFixture();
  Object.setPrototypeOf(value.trace.frequency_offsets_hz,Object.assign(Object.create(Array.prototype),{at(){return Infinity;}}));
  value.bandwidth.right_offset_hz=1e9;
  assert.throws(()=>validateSpectrumView(value),/invalid_spectrum_view/);
  const reasons=spectrumFixture('incomplete');reasons.bandwidth.reason_codes=['unknown'];
  Object.setPrototypeOf(reasons.bandwidth.reason_codes,Object.assign(Object.create(Array.prototype),{*[Symbol.iterator](){yield 'left_crossing_missing';}}));
  assert.throws(()=>validateSpectrumView(reasons),/invalid_spectrum_view/);
  const dense=spectrumFixture('incomplete');
  for(const array of [dense.trace.frequency_offsets_hz,dense.trace.relative_levels_db,dense.bandwidth.reason_codes]) Object.setPrototypeOf(array,null);
  assert.equal(validateSpectrumView(dense).bandwidth.reason_codes[0],'left_crossing_missing');
});
