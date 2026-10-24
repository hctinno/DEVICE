import {validateSpectrumView,formatSpectrumNumber,spectrumGeometry,spectrumCoordinatesRepresentable,SPECTRUM_REASONS} from './spectrum_model.mjs';

// Include this constant in the host's self-served stylesheet. Rendering does
// not insert inline styles, load resources, or modify global page state.
export const SPECTRUM_VIEW_CSS=`
.spectrum-view,.spectrum-view *{box-sizing:border-box}
.spectrum-view{width:100%;min-width:0;background:#101b2b;color:#e8eff8;border:1px solid #26364b;border-radius:14px;padding:22px;font-family:Pretendard,"Noto Sans KR","Malgun Gothic",system-ui,sans-serif;letter-spacing:-.02em;line-height:1.55}
.spectrum-view h2,.spectrum-view h3,.spectrum-view p,.spectrum-view figure{margin:0}
.spectrum-view h2{font-size:23px;line-height:1.35}.spectrum-view h3{font-size:15px;margin-bottom:12px}
.spectrum-view .spectrum-kicker{color:#63d9ed;font-size:10px;letter-spacing:.1em;margin-bottom:7px}
.spectrum-view .spectrum-subtitle,.spectrum-view .spectrum-note{font-size:12px;color:#9babbe;margin:9px 0;overflow-wrap:anywhere}
.spectrum-view .spectrum-flags{display:flex;flex-wrap:wrap;gap:7px;margin:16px 0}
.spectrum-view .spectrum-flag{background:#142b3c;color:#b7e9f0;border:1px solid #2c5664;border-radius:5px;padding:4px 8px;font-size:10px}
.spectrum-view .spectrum-chart{padding:16px 0;border-top:1px solid #26364b;border-bottom:1px solid #26364b;margin:18px 0}
.spectrum-view svg{display:block;width:100%;height:auto;max-height:420px;min-width:0}
.spectrum-view svg .tick{font-size:14px;fill:#b9c9dc}.spectrum-view svg .axis-label{font-size:15px;fill:#d3dfee}
.spectrum-view .spectrum-legend{display:flex;flex-wrap:wrap;gap:8px 17px;padding:0;margin:9px 0;list-style:none;font-size:11px;color:#b8c9dc}
.spectrum-view .spectrum-legend li{display:flex;align-items:center;gap:6px}.spectrum-view .spectrum-swatch{width:24px;border-top:2px solid #63d9ed;display:inline-block}
.spectrum-view .spectrum-swatch.threshold{border-color:#668bff;border-top-style:dashed}.spectrum-view .spectrum-swatch.crossing{border-color:#f3c477;border-top-style:dotted}
.spectrum-view figcaption{font-size:12px;color:#b5c6d9;overflow-wrap:anywhere}
.spectrum-view .spectrum-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:18px 0}
.spectrum-view .spectrum-card{background:#0c1626;border:1px solid #26364b;border-radius:9px;padding:17px;min-width:0}
.spectrum-view .spectrum-status{display:inline-block;font-size:11px;color:#abc2ff;background:#1f3154;border:1px solid #384e7b;border-radius:5px;padding:4px 7px;margin-bottom:10px}
.spectrum-view .spectrum-status.warning{color:#f3c477;background:#3a301e;border-color:#5e4d2d}
.spectrum-view dl{margin:0}.spectrum-view dl>div{padding:9px 0;border-bottom:1px solid #223247;min-width:0}
.spectrum-view dt{font-size:11px;color:#9babbe}.spectrum-view dd{font-size:14px;margin:4px 0 0;overflow-wrap:anywhere}
.spectrum-view .spectrum-mono{font-family:"Cascadia Code",Consolas,monospace;letter-spacing:0;font-size:11px;overflow-wrap:anywhere}
.spectrum-view .spectrum-reasons{padding-left:19px;color:#f3c477;font-size:12px}.spectrum-view .spectrum-chart-error{padding:15px;background:#3a301e;border:1px solid #5e4d2d;border-radius:7px;color:#f3c477;font-size:13px}
@media(max-width:600px){.spectrum-view{padding:15px}.spectrum-view h2{font-size:20px}.spectrum-view .spectrum-card{padding:13px}.spectrum-view svg .tick{font-size:22px}.spectrum-view svg .axis-label{font-size:23px}.spectrum-view .spectrum-grid{grid-template-columns:minmax(0,1fr)}}`;

const unit=(value,label)=>formatSpectrumNumber(value)+' '+label;
function element(doc,tag,className='',text) {
  const node=doc.createElement(tag);if(className) node.className=className;if(text!==undefined) node.textContent=text;return node;
}
function metadata(doc,entries) {
  const list=element(doc,'dl');
  for(const [label,text,field,comparison] of entries) {
    const row=element(doc,'div'), value=element(doc,'dd','',text);
    if(field) value.dataset.field=field;if(comparison!==undefined && comparison!==null) value.dataset.comparison=comparison;
    row.append(element(doc,'dt','',label),value);list.append(row);
  }
  return list;
}
function chart(doc,value) {
  const figure=element(doc,'figure','spectrum-chart');figure.append(element(doc,'h3','','상대 레벨과 -6 dB 교차'));
  const geometry=spectrumGeometry(value);
  const displayError=()=>{
    const error=element(doc,'p','spectrum-chart-error','차트 표시 불가 · 주파수/레벨 범위가 화면 좌표의 표현 한계를 넘었습니다. 게시된 수치와 사유를 확인하세요.');
    error.dataset.spectrumChartError='chart_axis_unrepresentable';error.setAttribute('role','status');figure.append(error);return figure;
  };
  if(geometry.status==='error') return displayError();
  const svg=(tag,attributes={},text)=>{
    const node=doc.createElementNS('http://www.w3.org/2000/svg',tag);
    for(const [key,content] of Object.entries(attributes)) node.setAttribute(key,String(content));
    if(text!==undefined) node.textContent=text;return node;
  };
  const image=svg('svg',{viewBox:`0 0 ${geometry.width} ${geometry.height}`,role:'img','aria-label':'합성 주파수 스펙트럼 · 상대 레벨 dB와 게시된 -6 dB 교차'});
  image.append(svg('title',{},'합성 주파수 오프셋 trace와 -6 dB 선'),svg('desc',{},'시안 실선은 원래 상대 레벨, 파란 파선은 -6 dB, 노란 점선은 계산 결과가 선언한 좌우 교차입니다.'));
  const p=geometry.plot;
  image.append(svg('line',{x1:p.left,x2:p.right,y1:p.bottom,y2:p.bottom,stroke:'#667f9c','data-spectrum':'x-axis'}),
    svg('line',{x1:p.left,x2:p.left,y1:p.top,y2:p.bottom,stroke:'#667f9c'}));
  for(const tick of geometry.y_ticks) {
    image.append(svg('line',{x1:p.left,x2:p.right,y1:tick.y,y2:tick.y,stroke:'#263b53'}),
      svg('text',{x:p.left-10,y:tick.y+5,'text-anchor':'end',class:'tick'},formatSpectrumNumber(tick.value)));
  }
  for(const [index,tick] of geometry.x_ticks.entries()) {
    image.append(svg('line',{x1:tick.x,x2:tick.x,y1:p.bottom,y2:p.bottom+5,stroke:'#667f9c'}),
      svg('text',{x:tick.x,y:p.bottom+27,'text-anchor':index===0?'start':index===geometry.x_ticks.length-1?'end':'middle',class:'tick'},formatSpectrumNumber(tick.value)));
  }
  const polyline=svg('polyline',{points:geometry.points.map(point=>point.x+','+point.y).join(' '),fill:'none',stroke:'#63d9ed','stroke-width':2.5,'vector-effect':'non-scaling-stroke','data-spectrum':'trace'});
  const thresholdLine=svg('line',{x1:p.left,x2:p.right,y1:geometry.threshold_y,y2:geometry.threshold_y,stroke:'#668bff','stroke-width':1.7,'stroke-dasharray':'7 5','vector-effect':'non-scaling-stroke','data-spectrum':'threshold'});
  image.append(svg('text',{x:p.left,y:16,class:'axis-label'},'상대 레벨 (dB)'),
    svg('text',{x:(p.left+p.right)/2,y:310,'text-anchor':'middle',class:'axis-label'},'주파수 오프셋 (Hz)'),polyline,thresholdLine);
  const crossLines=[], markers=[];
  for(const point of geometry.crossings) {
    const line=svg('line',{x1:point.x,x2:point.x,y1:p.top,y2:p.bottom,stroke:'#f3c477','stroke-dasharray':'2 5','stroke-width':1.5,'data-spectrum':'crossing-'+point.side});
    const marker=svg('circle',{cx:point.x,cy:geometry.threshold_y,r:4,fill:'#f3c477'});
    crossLines.push(line);markers.push(marker);image.append(line,marker);
  }
  const bandLine=geometry.crossings.length ? svg('line',{x1:geometry.crossings[0].x,x2:geometry.crossings[1].x,y1:p.bottom-13,y2:p.bottom-13,stroke:'#f3c477','stroke-width':3,'data-spectrum':'bandwidth'}):null;
  if(bandLine) image.append(bandLine);
  // SVG numeric accessors may round more aggressively than JS doubles. Check
  // the staged nodes before publishing any chart into the caller's container.
  try {
    const points=Array.from({length:polyline.points.numberOfItems},(_,index)=>{
      const point=polyline.points.getItem(index);return {x:point.x,y:point.y};
    });
    const threshold=thresholdLine.y1.baseVal.value;
    const crossings=crossLines.map((line,index)=>({...geometry.crossings[index],x:line.x1.baseVal.value}));
    if(!spectrumCoordinatesRepresentable(value,{points,threshold_y:threshold,crossings})
      || thresholdLine.y2.baseVal.value!==threshold || ![thresholdLine.x1.baseVal.value,thresholdLine.x2.baseVal.value].every(Number.isFinite)
      || crossLines.some((line,index)=>line.x2.baseVal.value!==crossings[index].x || ![line.y1.baseVal.value,line.y2.baseVal.value].every(Number.isFinite)
        || markers[index].cx.baseVal.value!==crossings[index].x || markers[index].cy.baseVal.value!==threshold)
      || (bandLine && (!Number.isFinite(bandLine.y1.baseVal.value) || bandLine.y2.baseVal.value!==bandLine.y1.baseVal.value
        || bandLine.x1.baseVal.value!==crossings[0].x || bandLine.x2.baseVal.value!==crossings[1].x || bandLine.x1.baseVal.value>=bandLine.x2.baseVal.value))) return displayError();
  } catch {return displayError();}
  const legend=element(doc,'ul','spectrum-legend');
  for(const [label,type] of [['원래 상대 레벨 · 실선',''],['-6 dB · 파선','threshold'],['게시된 교차/폭 · 점선','crossing']]) {
    const item=element(doc,'li'), swatch=element(doc,'span','spectrum-swatch '+type);swatch.setAttribute('aria-hidden','true');item.append(swatch,doc.createTextNode(label));legend.append(item);
  }
  figure.append(image,legend,element(doc,'figcaption','',`주파수 오프셋 ${unit(value.trace.frequency_offsets_hz[0],'Hz')} ~ ${unit(value.trace.frequency_offsets_hz.at(-1),'Hz')}. 상대 최대는 0 dB입니다. 교차와 폭은 게시된 계산 결과입니다.`));
  return figure;
}

export function renderSpectrumView(container,value) {
  const validated=validateSpectrumView(value);
  try {
    const {trace,bandwidth:bw,psd}=validated;
    const doc=container?.ownerDocument;if(!doc || typeof container.replaceChildren!=='function') throw new Error('invalid_container');
    const root=element(doc,'section','spectrum-view');root.dataset.spectrumView='';root.setAttribute('aria-label','합성 스펙트럼 계산 결과');
    root.append(element(doc,'p','spectrum-kicker','SYNTHETIC FREQUENCY · BW6 / PSD'),element(doc,'h2','','합성 주파수 계산'),
      element(doc,'p','spectrum-subtitle','명시한 주파수 trace와 단일 3kHz 구간의 조건부 계산입니다.'));
    const flags=element(doc,'div','spectrum-flags');
    for(const label of ['합성','실장비 미검증','실제 AI 호출 없음','방법 승인 미평가','전체 규범 범위 미완료']) flags.append(element(doc,'span','spectrum-flag',label));
    root.append(flags,chart(doc,validated));
    const grid=element(doc,'div','spectrum-grid'), band=element(doc,'section','spectrum-card'), power=element(doc,'section','spectrum-card');
    const complete=bw.status==='complete', bandComparison=complete ? (bw.conditional_comparison==='meets'?'선언 경계 이상 (조건부)':'선언 경계 미만 (조건부)'):'비교 보류 · 미완료';
    band.append(element(doc,'h3','','-6 dB 폭'),element(doc,'p','spectrum-status'+(complete?'':' warning'),complete?'교차/폭 계산 완료':'교차 미완료'),metadata(doc,[
      ['게시된 폭',complete?unit(bw.bandwidth_hz,'Hz'):'계산값 없음','bandwidth-value'],['선언 최소',unit(bw.minimum_bandwidth_hz,'Hz')],
      ['왼쪽 교차 오프셋',complete?unit(bw.left_offset_hz,'Hz'):'계산값 없음'],['오른쪽 교차 오프셋',complete?unit(bw.right_offset_hz,'Hz'):'계산값 없음'],
      ['게시된 margin',complete?unit(bw.margin_hz,'Hz'):'계산값 없음','bandwidth-margin'],['게시된 조건부 비교',bandComparison,'bandwidth-comparison',bw.conditional_comparison],
    ]));
    if(!complete) {
      const list=element(doc,'ul','spectrum-reasons');for(const reason of bw.reason_codes) list.append(element(doc,'li','',SPECTRUM_REASONS[reason]));band.append(list);
    }
    const basis=psd.input_basis==='band_power_3khz'?'선언된 3kHz 구간 전력':'일정한 mW/Hz 밀도의 3kHz 적분 선언';
    power.append(element(doc,'h3','','단일 3kHz PSD'),element(doc,'p','spectrum-status'+(psd.conditional_comparison==='above'?' warning':''),'한 구간의 계산'),metadata(doc,[
      ['게시된 구간 전력',unit(psd.power_dbm,'dBm')+' · '+unit(psd.power_mw,'mW'),'psd-power'],['선언 구간',unit(psd.reference_bandwidth_hz,'Hz')],
      ['선언 최대',unit(psd.maximum_dbm,'dBm')],['게시된 margin',unit(psd.margin_db,'dB'),'psd-margin'],
      ['게시된 조건부 비교',psd.conditional_comparison==='meets'?'선언 경계 이하 (조건부)':'선언 경계 초과 (조건부)','psd-comparison',psd.conditional_comparison],['입력 기준',basis],
    ]),element(doc,'p','spectrum-note','전대역 최대 탐색 미실행 · 전체 PSD 최대값으로 간주하지 않습니다.'));
    grid.append(band,power);root.append(grid,element(doc,'p','spectrum-note','화면 수치가 반올림되어 경계와 같아 보여도 원래 계산된 비교를 표시합니다.'));
    const identity=element(doc,'section','spectrum-card');identity.append(element(doc,'h3','','입력 식별과 범위'));
    const list=metadata(doc,[['BW trace capture',trace.capture_id],['BW 게시자 제공 입력 SHA-256',bw.input_sha256],['PSD 입력 capture',psd.capture_id],['PSD 게시자 제공 입력 SHA-256',psd.input_sha256]]);
    for(const node of list.querySelectorAll('dd')) node.classList.add('spectrum-mono');identity.append(list,element(doc,'p','spectrum-note','PSD capture는 별도로 선언된 입력입니다. 같은 취득으로 임의 연결하지 않습니다. 입력 SHA-256은 계산 결과에 포함된 식별자입니다.'));
    root.append(identity,element(doc,'p','spectrum-note','이 결과는 합성 계산 범위의 읽기 화면입니다. 실제 RF 취득·현행 방법 승인·기관 적합성을 입증하지 않습니다.'));
    container.replaceChildren(root);return root;
  } catch {throw new Error('spectrum_render_failed');}
}
