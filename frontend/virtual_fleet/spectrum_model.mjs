const REASONS=['non_unique_peak','disconnected_lobes','threshold_plateau','left_crossing_missing','right_crossing_missing'];
export const SPECTRUM_REASONS={non_unique_peak:'최대 peak가 유일하지 않음',disconnected_lobes:'-6 dB 이상 lobe가 분리됨',
  threshold_plateau:'-6 dB plateau로 교차가 모호함',left_crossing_missing:'왼쪽 교차가 포함되지 않음',right_crossing_missing:'오른쪽 교차가 포함되지 않음'};
const FLAGS={synthetic:true,hardware_verified:false,ai_model_called:false,method_approval:'not_assessed',regulatory_scope_complete:false};

export function validateSpectrumView(value) {
  const fail=path=>{throw Object.assign(new Error('invalid_spectrum_view'),{path});};
  const object=(item,fields,path)=>{
    if(item===null || typeof item!=='object' || Array.isArray(item) || ![Object.prototype,null].includes(Object.getPrototypeOf(item))) fail(path);
    const keys=Reflect.ownKeys(item), expected=fields.split(' ');
    if(keys.length!==expected.length || keys.some(key=>typeof key!=='string' || !expected.includes(key))) fail(path);
    if(Object.values(Object.getOwnPropertyDescriptors(item)).some(field=>field.get || field.set)) fail(path);
  };
  const number=(item,path)=>{if(typeof item!=='number' || !Number.isFinite(item)) fail(path);};
  const id=(item,path)=>{if(typeof item!=='string' || !/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(item)) fail(path);};
  const digest=(item,path)=>{if(typeof item!=='string' || item.length!==64 || !/^[a-f0-9]{64}$/.test(item)) fail(path);};
  const fixed=(item,values,path)=>{for(const [key,expected] of Object.entries(values)) if(item[key]!==expected) fail(path+'.'+key);};
  const array=(item,path,min,max)=>{
    if(!Array.isArray(item) || item.length<min || item.length>max || Reflect.ownKeys(item).length!==item.length+1) fail(path);
    if(Object.values(Object.getOwnPropertyDescriptors(item)).some(field=>field.get || field.set)) fail(path);
  };
  try {
    object(value,'schema_version kind trace bandwidth psd','view');
    fixed(value,{schema_version:1,kind:'synthetic_spectrum_view'},'view');
    const trace=value.trace, bandwidth=value.bandwidth, psd=value.psd;
    object(trace,'schema_version kind capture_id synthetic axis_domain sample_unit amplitude_basis selection_policy frequency_offsets_hz relative_levels_db','trace');
    fixed(trace,{schema_version:1,kind:'synthetic_frequency_spectrum',synthetic:true,axis_domain:'frequency_offset_hz',sample_unit:'dB',
      amplitude_basis:'relative_to_peak',selection_policy:'unique_peak_single_lobe_linear_db'},'trace');
    id(trace.capture_id,'trace.capture_id');
    const frequencies=trace.frequency_offsets_hz, levels=trace.relative_levels_db;
    array(frequencies,'trace.frequency_offsets_hz',3,65536);array(levels,'trace.relative_levels_db',3,65536);
    if(frequencies.length!==levels.length) fail('trace.length');
    let zero=false;
    for(let index=0;index<frequencies.length;index++) {
      number(frequencies[index],'trace.frequency_offsets_hz');number(levels[index],'trace.relative_levels_db');
      if(index && frequencies[index]<=frequencies[index-1]) fail('trace.order');
      if(levels[index]>0) fail('trace.relative_peak');zero ||= levels[index]===0;
    }
    if(!zero) fail('trace.relative_peak');
    object(bandwidth,'schema_version kind capture_id input_sha256 algorithm_id status reason_codes left_offset_hz right_offset_hz bandwidth_hz minimum_bandwidth_hz margin_hz conditional_comparison synthetic hardware_verified ai_model_called method_approval regulatory_scope_complete','bandwidth');
    fixed(bandwidth,{schema_version:1,kind:'synthetic_bandwidth_result',algorithm_id:'peak6_linear_db_v1',minimum_bandwidth_hz:500000,...FLAGS},'bandwidth');
    id(bandwidth.capture_id,'bandwidth.capture_id');digest(bandwidth.input_sha256,'bandwidth.input_sha256');
    if(bandwidth.capture_id!==trace.capture_id) fail('bandwidth.capture_id');
    array(bandwidth.reason_codes,'bandwidth.reason_codes',0,REASONS.length);
    let previous=-1;
    for(const reason of bandwidth.reason_codes) {
      const index=REASONS.indexOf(reason);if(index<=previous) fail('bandwidth.reason_codes');previous=index;
    }
    const numbers=['left_offset_hz','right_offset_hz','bandwidth_hz','margin_hz'];
    if(bandwidth.status==='incomplete') {
      if(!bandwidth.reason_codes.length || [...numbers,'conditional_comparison'].some(key=>bandwidth[key]!==null)) fail('bandwidth.incomplete');
    } else if(bandwidth.status==='complete') {
      if(bandwidth.reason_codes.length) fail('bandwidth.complete');
      for(const key of numbers) number(bandwidth[key],'bandwidth.'+key);
      if(bandwidth.bandwidth_hz<=0 || bandwidth.left_offset_hz>bandwidth.right_offset_hz
        || bandwidth.left_offset_hz<frequencies[0] || bandwidth.right_offset_hz>frequencies.at(-1)) fail('bandwidth.range');
      if(!['meets','below'].includes(bandwidth.conditional_comparison)) fail('bandwidth.conditional_comparison');
    } else fail('bandwidth.status');
    object(psd,'schema_version kind capture_id input_sha256 algorithm_id input_basis power_dbm power_mw reference_bandwidth_hz maximum_dbm margin_db conditional_comparison source_coverage max_search_complete synthetic hardware_verified ai_model_called method_approval regulatory_scope_complete','psd');
    fixed(psd,{schema_version:1,kind:'synthetic_psd_band_result',algorithm_id:'declared_3khz_power_v1',reference_bandwidth_hz:3000,maximum_dbm:8,
      source_coverage:'single_declared_band',max_search_complete:false,...FLAGS},'psd');
    id(psd.capture_id,'psd.capture_id');digest(psd.input_sha256,'psd.input_sha256');
    if(!['band_power_3khz','flat_density_mw_per_hz'].includes(psd.input_basis)) fail('psd.input_basis');
    for(const key of ['power_dbm','power_mw','margin_db']) number(psd[key],'psd.'+key);
    if(psd.power_mw<=0 || (psd.input_basis==='band_power_3khz' && (psd.power_dbm<-300 || psd.power_dbm>100))) fail('psd.power');
    if(!['meets','above'].includes(psd.conditional_comparison)) fail('psd.conditional_comparison');
    return structuredClone(value);
  } catch {throw new Error('invalid_spectrum_view');}
}

export function formatSpectrumNumber(value) {
  if(typeof value!=='number' || !Number.isFinite(value)) throw new Error('invalid_spectrum_number');
  if(Object.is(value,-0)) return '-0';
  if(value===0) return '0';
  const absolute=Math.abs(value);
  if(absolute<1e-4 || absolute>=1e7) return value.toExponential(6).replace(/\.?0+(?=e)/,'');
  return Number(value.toPrecision(7)).toString();
}

// Screen coordinates only. No bandwidth interpolation, power conversion,
// canonical input hash or conditional engineering comparison is recomputed.
export function spectrumGeometry(value) {
  const {trace,bandwidth}=value, xs=trace.frequency_offsets_hz, ys=trace.relative_levels_db;
  const plot={left:82,right:730,top:28,bottom:252}, span=xs.at(-1)-xs[0];
  let low=-12;for(const level of ys) low=Math.min(low,level);
  const error=()=>({status:'error',code:'chart_axis_unrepresentable'});
  if(!Number.isFinite(span) || span<=0 || !Number.isFinite(-low)) return error();
  const x=offset=>plot.left+((offset-xs[0])/span)*(plot.right-plot.left);
  const y=level=>plot.top+((-level)/(-low))*(plot.bottom-plot.top);
  const points=xs.map((offset,index)=>({x:x(offset),y:y(ys[index])}));
  const threshold=y(-6);
  if(!Number.isFinite(threshold) || threshold===y(0) || points.some((point,index)=>!Number.isFinite(point.x) || !Number.isFinite(point.y) || (index && point.x<=points[index-1].x))) return error();
  const crossings=bandwidth.status==='complete' ? [
    {side:'left',x:x(bandwidth.left_offset_hz),offset_hz:bandwidth.left_offset_hz},
    {side:'right',x:x(bandwidth.right_offset_hz),offset_hz:bandwidth.right_offset_hz},
  ] : [];
  if(crossings.length && (!crossings.every(point=>Number.isFinite(point.x)) || crossings[0].x>=crossings[1].x)) return error();
  const middle=xs[0]+span/2, ticks=[xs[0],...(middle>xs[0] && middle<xs.at(-1) ? [middle]:[]),xs.at(-1)];
  return {status:'ready',width:760,height:320,plot,points,threshold_y:threshold,crossings,
    x_ticks:ticks.map(value=>({x:x(value),value})),y_ticks:[0,-6,low].map(value=>({y:y(value),value}))};
}
