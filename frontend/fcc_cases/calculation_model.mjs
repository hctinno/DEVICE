/*039 independent typed boundary. No PDF, client arithmetic, aliases or authority. */
export const FCC_CASE_CALCULATION_REQUEST_MAX_BYTES=32768;
export const FCC_CASE_CALCULATION_WIRE_REQUEST_MAX_BYTES=65536;
export const FCC_CASE_CALCULATION_RESULT_MAX_BYTES=131072;
export const FCC_CASE_CALCULATION_RESPONSE_MAX_BYTES=163840;
const CASE_CAP=8*1024*1024;
const COMMON='schema_version kind corpus_id execution_mode synthetic validation_scope verification';
const VERIFICATION='hardware_verified physical_verified model_execution_verified normative_compliance_verified coverage_complete';
const PREVIEW='case_id report_group_id report_number revision issuer_class issue_date scope_status fcc_ids product_family manufacturer models rules methods equipment_models review_status document_ids evaluation_group';
const COUNT_KEYS='candidate_count acquired_unique_pdfs parsed_unique_pdfs complete_text_pdfs partial_text_pdfs no_citable_text_pdfs exhibit_relations case_count reviewed_claim_count gap_or_unreviewed_claim_count scope_counts independent_group_eligible_cases normative_comparison_completed_cases development_integrated_cases model_evaluated_cases';
const SCOPE_STATUSES=['in_scope','pending','out_of_range','future'];
const MISSING=['product_family','fcc_ids','report_group_id','reuse_group_ids','issuer_class','scope_status','review_status'];

const fail=()=>{throw Error('invalid_fcc_case_calculation');};
const need=value=>{if(!value)fail();};
const checked=action=>{try{return action();}catch{fail();}};
const strip=value=>value.replace(/^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g,'');
const exact=(value,keys)=>need(value && typeof value==='object' && !Array.isArray(value) && Object.keys(value).sort().join(' ')===keys.split(' ').sort().join(' '));
const list=(value,max=50000,min=0)=>need(Array.isArray(value) && value.length>=min && value.length<=max);
const integer=(value,max=Number.MAX_SAFE_INTEGER,min=0)=>need(Number.isSafeInteger(value) && value>=min && value<=max);
const bool=value=>need(typeof value==='boolean');
const text=(value,max=16384)=>need(typeof value==='string' && [...value].length<=max && strip(value).length>0);
const nullable=(value,check)=>{if(value!==null)check(value);};
const id=value=>need(typeof value==='string' && value.length>0 && value.length<=128 && /^[A-Za-z0-9]/.test(value) && !/[^A-Za-z0-9_.-]/.test(value));
const sha=value=>need(typeof value==='string' && value.length===64 && !/[^a-f0-9]/.test(value));
const oneOf=(value,values)=>need(values.includes(value));
const unique=values=>need(new Set(values).size===values.length);
const strings=(values,max=50000,length=16384)=>{list(values,max);values.forEach(value=>text(value,length));unique(values);};
const ids=(values,max,min=0)=>{list(values,max,min);values.forEach(id);unique(values);};
const safeFccCaseHref=value=>{try{if(typeof value!=='string' || !/^https?:\/\//i.test(value) || /[\s\u0000-\u001F\u007F\\]/.test(value))return null;const url=new URL(value);return ['http:','https:'].includes(url.protocol) && !url.username && !url.password?url.href:null;}catch{return null;}};
function boundary(value){
 need(!/[\uD800-\uDFFF]/u.test(value));
 need(!/(?:^|[\s"'(<])(?:[A-Za-z]:[\\/]|\\\\[^\\\s]+\\|file:\/\/|\.local[\\/])|(?:^|[\s"'(<])\/(?:Users|home|private|tmp|var|mnt|Volumes)\//i.test(value));
}
function clone(input,cap=CASE_CAP,maxDepth=20,maxNodes=200000){
 let nodes=0;const copy=(value,depth=0)=>{
  need(++nodes<=maxNodes && depth<=maxDepth);
  if(value===null || typeof value==='boolean')return value;
  if(typeof value==='number'){need(Number.isFinite(value) && (!Number.isInteger(value) || Number.isSafeInteger(value)));return value;}
  if(typeof value==='string'){need([...value].length<=32768);boundary(value);return value;}
  need(value && typeof value==='object');const array=Array.isArray(value),prototype=Object.getPrototypeOf(value);
  need(array?prototype===Array.prototype:prototype===Object.prototype || prototype===null);
  const output=array?[]:{},keys=Reflect.ownKeys(value);
  if(array){need(value.length<=maxNodes && keys.length===value.length+1);for(let i=0;i<value.length;i++)need(Object.hasOwn(value,i));}
  for(const key of keys){if(array && key==='length')continue;const d=Object.getOwnPropertyDescriptor(value,key);
   need(typeof key==='string' && d.enumerable && Object.hasOwn(d,'value'));boundary(key);
   if(!array){need(++nodes<=maxNodes && depth+1<=maxDepth);need([...key].length<=32768);}
   Object.defineProperty(output,key,{value:copy(d.value,depth+1),enumerable:true,writable:true,configurable:true});}
  return output;
 };const output=copy(input);need(new TextEncoder().encode(JSON.stringify(output)).length<=cap);return output;
}
function parse(input,cap,maxDepth=20,maxNodes=200000){
 need(typeof input==='string' && new TextEncoder().encode(input).length<=cap);let position=0,nodes=0;
 const space=()=>{while(position<input.length && /[ \t\r\n]/.test(input[position]))position++;};
 const string=()=>{const start=position++;let escaped=false;while(position<input.length){const ch=input[position++];if(!escaped && ch==='"'){const result=JSON.parse(input.slice(start,position));boundary(result);return result;}if(!escaped && ch==='\\')escaped=true;else escaped=false;}fail();};
 const value=depth=>{
  need(depth<=maxDepth && ++nodes<=maxNodes);space();const ch=input[position];
  if(ch==='"')return string();
  if(ch==='{' || ch==='['){position++;const object=ch==='{',output=object?{}:[],end=object?'}':']';space();if(input[position]===end){position++;return output;}
   while(true){space();let key;if(object){need(input[position]==='"');need(++nodes<=maxNodes && depth+1<=maxDepth);key=string();need(!Object.hasOwn(output,key));space();need(input[position++]===':');}const item=value(depth+1);if(object)Object.defineProperty(output,key,{value:item,enumerable:true,writable:true,configurable:true});else output.push(item);space();const next=input[position++];if(next===end)break;need(next===',');}return output;}
  for(const [token,result] of [['true',true],['false',false],['null',null]])if(input.slice(position,position+token.length)===token){position+=token.length;return result;}
  const regex=/-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/y;regex.lastIndex=position;const match=regex.exec(input);need(match);position=regex.lastIndex;
  // Check the original integer token before any rounding by Number.
  if(!/[.eE]/.test(match[0])){const exact=BigInt(match[0]);need(exact<=BigInt(Number.MAX_SAFE_INTEGER) && exact>=BigInt(Number.MIN_SAFE_INTEGER));}
  const result=Number(match[0]);need(Number.isFinite(result) && (!Number.isInteger(result) || Number.isSafeInteger(result)));return result;
 };const result=value(0);space();need(position===input.length);return clone(result,cap,maxDepth,maxNodes);
}
const url=value=>need(safeFccCaseHref(value)!==null);
const fccUrl=value=>{url(value);const host=new URL(value).hostname.toLowerCase();need(host==='fcc.gov' || host.endsWith('.fcc.gov'));};
function date(value){
 need(typeof value==='string' && value.length===10 && /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value));const [year,month,day]=value.split('-').map(Number);need(year>=1 && month>=1 && month<=12);const days=[31,year%4===0 && (year%100!==0 || year%400===0)?29:28,31,30,31,30,31,31,30,31,30,31];need(day>=1 && day<=days[month-1]);
}
function timestamp(value){
 text(value,128);need(/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?\+09:00$/.test(value));date(value.slice(0,10));need(Number(value.slice(11,13))<24 && Number(value.slice(14,16))<60 && Number(value.slice(17,19))<60);return value.slice(0,19)+(value.slice(19,-6).replace('.','')).padEnd(128,'0');
}
function common(value,kind){need(value.schema_version===1 && value.kind===kind && value.execution_mode==='report_derived' && value.validation_scope==='source_bytes_and_retained_page_literals_only');id(value.corpus_id);bool(value.synthetic);exact(value.verification,VERIFICATION);Object.values(value.verification).forEach(flag=>need(flag===false));}
function scope(value,synthetic){exact(value,'issue_date_from cutoff_at timezone population_status search_scope_notes unverified_ranges synthetic');need(value.issue_date_from==='2025-01-01' && value.timezone==='Asia/Seoul' && value.population_status==='unconfirmed' && value.synthetic===synthetic);need(timestamp(value.cutoff_at)>=timestamp('2025-01-01T00:00:00+09:00'));list(value.search_scope_notes,32);value.search_scope_notes.forEach(note=>text(note,2048));list(value.unverified_ranges,32);value.unverified_ranges.forEach(note=>text(note,2048));}
function searches(values,cutoff){
 list(values,128);const seen=new Set();for(const value of values){exact(value,'search_id institution_scope query url searched_at status page_start page_end result_limit candidate_count unverified_ranges notes');id(value.search_id);need(!seen.has(value.search_id));seen.add(value.search_id);oneOf(value.institution_scope,['hct_korea','hct_america','mixed','unresolved']);text(value.query,4096);url(value.url);need(timestamp(value.searched_at)<=timestamp(cutoff));oneOf(value.status,['ok','partial','blocked','failed']);for(const key of ['page_start','page_end','result_limit'])nullable(value[key],v=>integer(v,Number.MAX_SAFE_INTEGER,1));nullable(value.candidate_count,v=>integer(v));need((value.page_start===null && value.page_end===null) || (value.page_start!==null && value.page_end!==null && value.page_start<=value.page_end));list(value.unverified_ranges,32);value.unverified_ranges.forEach(note=>text(note,2048));nullable(value.notes,v=>text(v,2048));}return seen;
}
function documents(values,context=null){
 list(values,16);const byId=new Map(),hashes=new Set();let bytes=0,relations=0,pages=0;
 for(const value of values){exact(value,'document_id sha256 size_bytes physical_pages exhibits rights extraction page_index');id(value.document_id);sha(value.sha256);need(!byId.has(value.document_id) && !hashes.has(value.sha256));byId.set(value.document_id,value);hashes.add(value.sha256);integer(value.size_bytes,16*1024*1024,1);bytes+=value.size_bytes;integer(value.physical_pages,100000,1);list(value.exhibits,64,1);relations+=value.exhibits.length;const links=new Set();
  for(const exhibit of value.exhibits){exact(exhibit,'exhibit_id fcc_id application_id exhibit_type url source_kind accessed_at official_match_status official_url search_ids');text(exhibit.exhibit_id,128);nullable(exhibit.fcc_id,v=>text(v,128));nullable(exhibit.application_id,v=>text(v,256));nullable(exhibit.exhibit_type,v=>text(v,256));nullable(exhibit.url,url);oneOf(exhibit.source_kind,['official','mirror','existing_user']);timestamp(exhibit.accessed_at);oneOf(exhibit.official_match_status,['unverified','listing_only','pdf_hash_matched','blocked']);nullable(exhibit.official_url,fccUrl);if(exhibit.source_kind!=='existing_user')need(exhibit.url!==null);if(exhibit.source_kind==='official')fccUrl(exhibit.url);if(['listing_only','pdf_hash_matched'].includes(exhibit.official_match_status))need(exhibit.official_url!==null);ids(exhibit.search_ids,32);if(context)exhibit.search_ids.forEach(key=>need(context.searchIds.has(key)));const link=JSON.stringify([exhibit.exhibit_id,exhibit.url]);need(!links.has(link));links.add(link);}
  exact(value.rights,'status notes public_redistribution_allowed external_model_use_allowed');oneOf(value.rights.status,['private_only','permission_recorded','unresolved']);nullable(value.rights.notes,v=>text(v,2048));need(value.rights.public_redistribution_allowed===false && value.rights.external_model_use_allowed===false);
  const extraction=value.extraction;exact(extraction,'status complete total_pages processed_pages parser issues');oneOf(extraction.status,['ok','empty','partial','image_only','no_text','limit_exceeded','parser_error']);bool(extraction.complete);need(extraction.complete===['ok','empty'].includes(extraction.status));integer(extraction.total_pages,100000,1);need(extraction.total_pages===value.physical_pages);integer(extraction.processed_pages,200);need(extraction.processed_pages<=extraction.total_pages);pages+=extraction.processed_pages;exact(extraction.parser,'name version');text(extraction.parser.name);nullable(extraction.parser.version,text);list(extraction.issues);for(const issue of extraction.issues){exact(issue,'code file_page');text(issue.code);nullable(issue.file_page,v=>integer(v,value.physical_pages,1));}
  list(value.page_index,200);need(value.page_index.length===extraction.processed_pages);const seen=new Set();for(const page of value.page_index){exact(page,'file_page status text_sha256 line_count citable');integer(page.file_page,value.physical_pages,1);need(!seen.has(page.file_page));seen.add(page.file_page);oneOf(page.status,['ok','empty','truncated','image_only','no_text','limit_exceeded','error']);sha(page.text_sha256);integer(page.line_count);bool(page.citable);if(page.citable)need(page.status==='ok' && page.line_count>0);}
 }need(bytes<=64*1024*1024 && relations<=256 && pages<=800);return byId;
}
function preview(value,byDocument){
 exact(value,PREVIEW);id(value.case_id);nullable(value.report_group_id,id);for(const key of ['report_number','revision','product_family','manufacturer'])nullable(value[key],text);nullable(value.issue_date,date);oneOf(value.issuer_class,['hct_korea','hct_america','unknown']);oneOf(value.scope_status,SCOPE_STATUSES);oneOf(value.review_status,['reviewed','partial','unreviewed','conflicting']);for(const key of ['fcc_ids','models','rules','methods','equipment_models'])strings(value[key]);ids(value.document_ids,16,1);value.document_ids.forEach(key=>need(byDocument.has(key)));
 const group=value.evaluation_group;exact(group,'eligible keys missing');bool(group.eligible);strings(group.keys,50000,32768);strings(group.missing,7,128);group.missing.forEach(reason=>oneOf(reason,MISSING));need(group.eligible===(group.missing.length===0));for(const key of group.keys)need(/^(?:family|fcc|report|source|reuse):.+/s.test(key));if(group.eligible)need(value.product_family!==null && value.fcc_ids.length>0 && value.report_group_id!==null && value.issuer_class!=='unknown' && value.scope_status==='in_scope' && value.review_status==='reviewed' && group.keys.some(key=>key.startsWith('reuse:')));
}
function summary(value){
 exact(value,COMMON+' scope searches counts documents case_previews');common(value,'fcc_report_case_summary');scope(value.scope,value.synthetic);const searchIds=searches(value.searches,value.scope.cutoff_at),byDocument=documents(value.documents,{scope:value.scope,searchIds});list(value.case_previews,128);const seen=new Set();for(const item of value.case_previews){preview(item,byDocument);need(!seen.has(item.case_id));seen.add(item.case_id);}
 const counts=value.counts;exact(counts,COUNT_KEYS);need(counts.candidate_count===null && counts.normative_comparison_completed_cases===null && counts.development_integrated_cases===null && counts.model_evaluated_cases===0);for(const key of COUNT_KEYS.split(' ').filter(key=>!['candidate_count','normative_comparison_completed_cases','development_integrated_cases','scope_counts'].includes(key)))integer(counts[key]);need(counts.acquired_unique_pdfs===value.documents.length && counts.parsed_unique_pdfs===value.documents.length && counts.case_count===value.case_previews.length && counts.exhibit_relations===value.documents.reduce((sum,row)=>sum+row.exhibits.length,0));for(const key of ['complete_text_pdfs','partial_text_pdfs','no_citable_text_pdfs'])need(counts[key]<=counts.parsed_unique_pdfs);exact(counts.scope_counts,SCOPE_STATUSES.join(' '));for(const key of SCOPE_STATUSES){integer(counts.scope_counts[key]);need(counts.scope_counts[key]===value.case_previews.filter(row=>row.scope_status===key).length);}need(counts.independent_group_eligible_cases===value.case_previews.filter(row=>row.evaluation_group.eligible).length);return value;
}
function same(left,right){if(left===right)return true;if(!left || !right || typeof left!=='object' || typeof right!=='object' || Array.isArray(left)!==Array.isArray(right))return false;const keys=Object.keys(left).sort();return JSON.stringify(keys)===JSON.stringify(Object.keys(right).sort()) && keys.every(key=>same(left[key],right[key]));}
function claimValue(value,depth=0){need(depth<=6);if(typeof value==='string')need([...value].length<=16384);else if(value && typeof value==='object'){if(!Array.isArray(value))for(const key of Object.keys(value))need([...key].length<=16384);Object.values(value).forEach(child=>claimValue(child,depth+1));}}
function detail(value,expectedId,index=null){
 id(expectedId);exact(value,COMMON+' case documents');common(value,'fcc_report_case');const byDocument=documents(value.documents);const item=value.case;exact(item,'case_id report_group_id document_ids claims relations reuse_group_ids preview');need(item.case_id===expectedId);id(item.case_id);nullable(item.report_group_id,id);ids(item.document_ids,16,1);need(item.document_ids.length===value.documents.length);item.document_ids.forEach(key=>need(byDocument.has(key)));preview(item.preview,byDocument);need(item.preview.case_id===expectedId && item.preview.report_group_id===item.report_group_id && same(item.preview.document_ids,item.document_ids));ids(item.reuse_group_ids,32);list(item.relations,32);const relationIds=new Set();for(const relation of item.relations){exact(relation,'relation_id kind target_case_id external_target status');id(relation.relation_id);need(!relationIds.has(relation.relation_id));relationIds.add(relation.relation_id);oneOf(relation.kind,['revision_of','part_of','appendix_of','exhibit_of']);oneOf(relation.status,['resolved','unresolved']);if(relation.status==='resolved'){id(relation.target_case_id);need(relation.target_case_id!==expectedId && relation.external_target===null);if(index)need(index.case_previews.some(row=>row.case_id===relation.target_case_id));}else{need(relation.target_case_id===null);text(relation.external_target,256);}}
 list(item.claims,64);const claimIds=new Set();let evidenceCount=0;
 for(const claim of item.claims){exact(claim,'claim_id field value unit status basis evidence');id(claim.claim_id);need(!claimIds.has(claim.claim_id));claimIds.add(claim.claim_id);text(claim.field,128);need(/^(?:report|issuer|product|method|setting|equipment|correction|result|normative)(?:\.[a-z0-9_]+){1,3}$/.test(claim.field) && !/[\r\n]/.test(claim.field));nullable(claim.unit,v=>text(v,64));oneOf(claim.status,['reviewed','extracted','not_reported','extraction_failed','ambiguous','conflicting']);oneOf(claim.basis,['report_fact','government_rule','guidance','standard_reference_only','developer_inference','synthetic_policy']);claimValue(claim.value);list(claim.evidence,8);evidenceCount+=claim.evidence.length;
  if(['not_reported','extraction_failed'].includes(claim.status))need(claim.value===null && claim.evidence.length===0);
  if(['reviewed','extracted'].includes(claim.status)){need(claim.value!==null && claim.evidence.length>0);if(typeof claim.value==='string')text(claim.value);if(claim.value && typeof claim.value==='object')need(Object.keys(claim.value).length>0);}
  for(const evidence of claim.evidence){exact(evidence,'document_id source_sha256 file_page printed_page table row column footnotes text_sha256 line_start line_end quote literal_verified');id(evidence.document_id);need(byDocument.has(evidence.document_id));const doc=byDocument.get(evidence.document_id);sha(evidence.source_sha256);need(evidence.source_sha256===doc.sha256 && evidence.literal_verified===true);integer(evidence.file_page,doc.physical_pages,1);for(const key of ['printed_page','table','row','column'])nullable(evidence[key],v=>text(v,128));list(evidence.footnotes,16);evidence.footnotes.forEach(note=>text(note,512));sha(evidence.text_sha256);integer(evidence.line_start,Number.MAX_SAFE_INTEGER,1);integer(evidence.line_end,Number.MAX_SAFE_INTEGER,1);need(evidence.line_end>=evidence.line_start && evidence.line_end-evidence.line_start<40);text(evidence.quote,8192);const page=doc.page_index.find(page=>page.file_page===evidence.file_page);need(page?.citable===true && page.status==='ok' && page.text_sha256===evidence.text_sha256 && evidence.line_end<=page.line_count);}
 }need(evidenceCount<=4096);
 if(item.preview.issuer_class!=='unknown')for(const field of ['issuer.classification','issuer.legal_name','issuer.address'])need(item.claims.some(claim=>claim.field===field && claim.status==='reviewed' && (claim.basis==='report_fact' || field==='issuer.classification' && claim.basis==='developer_inference') && typeof claim.value==='string' && strip(claim.value) && (field!=='issuer.classification' || claim.value===item.preview.issuer_class)));
 if(index){need(value.corpus_id===index.corpus_id && value.synthetic===index.synthetic);const original=index.case_previews.find(row=>row.case_id===expectedId);need(original && same(original,item.preview));for(const doc of value.documents)need(same(index.documents.find(row=>row.document_id===doc.document_id),doc));}
 return value;
}
const RESULT_KEYS='schema_version kind corpus_id case_id calculator status reason_codes execution_mode synthetic validation_scope verification context source_page inputs reported_result calculation unit_conversion comparison_policy comparison interpretation_scope';
const VERIFY8=VERIFICATION+' source_bytes_reverified issuer_authenticity_verified native_raw_observed';
const CASE_CODES=['fcc_case_invalid_packet','fcc_case_invalid_sources','fcc_case_limit_exceeded','fcc_case_pdf_invalid','fcc_case_extraction_unavailable','fcc_case_invalid_evidence','fcc_case_invalid_query','fcc_case_not_found','fcc_case_invalid_intake'];
const ERROR_CODES=[...CASE_CODES,'fcc_calc_invalid_case','fcc_calc_invalid_request','fcc_calc_limit_exceeded','fcc_case_catalog_unconfigured','fcc_case_catalog_invalid','fcc_case_calculation_invalid_request','fcc_case_calculation_limit_exceeded','fcc_case_catalog_unavailable','fcc_case_calculation_unavailable'];
const REASONS='case_context_unconfirmed case_context_conflicting rule_mismatch method_mismatch claim_missing claim_unreviewed claim_basis_unconfirmed claim_role_mismatch claim_type_mismatch unit_mismatch evidence_unconfirmed source_page_mismatch source_row_mismatch row_evidence_unconfirmed context_source_mismatch corrections_already_applied numeric_representation_unavailable calculation_unavailable'.split(' ');
const LOCATORS='document_id source_sha256 file_page text_sha256 line_start line_end table row'.split(' ');
const ANCHORS=['document_id','source_sha256','file_page','text_sha256'];
const unsafe=value=>/[\u0000-\u001f\u007f\\]/.test(value) || value.startsWith('/') || /^[A-Za-z]:[\/\\]/.test(value) || /^(?:https?|file):/i.test(value);
const requestText=value=>{text(value,256);need(!unsafe(value));};
function request(input){
 const value=clone(input,FCC_CASE_CALCULATION_REQUEST_MAX_BYTES,10,512);
 exact(value,'schema_version case_id calculation_request');need(value.schema_version===1);id(value.case_id);
 const command=clone(value.calculation_request,16384,8,256);
 exact(command,'calculator rule method input_claim_ids reported_result_claim_id comparison_policy');
 need(command.calculator==='rf_power');requestText(command.rule);requestText(command.method);
 exact(command.input_claim_ids,'reading');id(command.input_claim_ids.reading);
 need(command.reported_result_claim_id===null && command.comparison_policy===null);return value;
}
function projection(value,sourceDetail,command){
 exact(value,'role claim_id field value unit sources');
 need(value.role==='reading' && value.claim_id===command.input_claim_ids.reading && value.field==='result.rf_power_reading' && value.unit==='dBm');
 const claim=sourceDetail.case.claims.find(item=>item.claim_id===value.claim_id);
 need(claim && claim.status==='reviewed' && claim.basis==='report_fact' && claim.field===value.field && claim.unit===value.unit && same(claim.value,value.value));
 need(typeof value.value==='number' && Number.isFinite(value.value));list(value.sources,8,1);
 const expected=claim.evidence.filter(item=>item.literal_verified===true).map(item=>Object.fromEntries(LOCATORS.map(key=>[key,item[key]])));
 const compare=(left,right)=>{
  for(const key of ['document_id','file_page','line_start','line_end','table','row']){
   const a=left[key]??'',b=right[key]??'';
   if(a!==b)return a<b?-1:1;
  }return 0;
 };
 expected.sort(compare);need(same(value.sources,expected));
 for(const source of value.sources){
  exact(source,LOCATORS.join(' '));id(source.document_id);sha(source.source_sha256);sha(source.text_sha256);
  for(const name of ['file_page','line_start','line_end'])integer(source[name],Number.MAX_SAFE_INTEGER,1);
  need(source.line_start<=source.line_end);
  for(const name of ['table','row'])nullable(source[name],value=>{text(value,128);need(!unsafe(value));});
 }
}
function rowWitness(binding,source){
 exact(binding,'basis table row line_start line_end');
 const label=value=>value===null || ['unknown','unconfirmed','not_reported','n/a','미확인','불명','-','–','—'].includes(strip(value).toLowerCase())?null:value;
 for(const name of ['table','row'])nullable(binding[name],value=>{text(value,128);need(!unsafe(value) && label(value)===value);});
 if(binding.basis==='explicit_table_row'){
  return binding.table!==null && binding.row!==null && binding.line_start===null && binding.line_end===null && binding.table===label(source.table) && binding.row===label(source.row);
 }
 need(binding.basis==='common_line_range');integer(binding.line_start,Number.MAX_SAFE_INTEGER,1);integer(binding.line_end,Number.MAX_SAFE_INTEGER,binding.line_start);
 return source.line_start<=binding.line_start && binding.line_end<=source.line_end && binding.table===label(source.table) && binding.row===label(source.row);
}
function response(input,expectedRequest,inputDetail){
 const expected=request(expectedRequest),sourceDetail=detail(clone(inputDetail),expected.case_id);
 const value=clone(input,FCC_CASE_CALCULATION_RESPONSE_MAX_BYTES,20,10000);
 exact(value,'schema_version kind corpus_id case_id status request_context result error_code execution_authorized');
 need(value.schema_version===1 && value.kind==='fcc_case_calculation' && value.execution_authorized===false);
 oneOf(value.status,['calculated','insufficient_evidence','rejected']);nullable(value.case_id,id);nullable(value.corpus_id,id);
 if(value.request_context!==null){const context=request(value.request_context);need(same(context,expected) && value.case_id===context.case_id);}
 if(value.status==='rejected'){
  need(value.result===null);oneOf(value.error_code,ERROR_CODES);
  if(['fcc_case_calculation_invalid_request','fcc_calc_invalid_request','fcc_case_invalid_query'].includes(value.error_code))need(value.request_context===null && value.case_id===null);
  else if(value.request_context===null)need(value.case_id===null);
  if(value.corpus_id!==null)need(value.corpus_id===sourceDetail.corpus_id);
  return value;
 }
 need(value.request_context!==null && value.corpus_id===sourceDetail.corpus_id && value.case_id===expected.case_id && value.error_code===null);
 const result=clone(value.result,FCC_CASE_CALCULATION_RESULT_MAX_BYTES,16,8192),command=expected.calculation_request,p=sourceDetail.case.preview;
 exact(result,RESULT_KEYS);
 need(result.schema_version===1 && result.kind==='fcc_report_calculation_check' && result.corpus_id===value.corpus_id && result.case_id===value.case_id && result.calculator==='rf_power' && result.status===value.status);
 need(result.execution_mode==='report_derived' && result.synthetic===sourceDetail.synthetic && result.validation_scope==='provided_case_dto_and_claim_source_consistency_only' && result.interpretation_scope==='reviewer_structured_values_not_literal_semantic_certification');
 exact(result.verification,VERIFY8);Object.values(result.verification).forEach(value=>need(value===false));
 list(result.reason_codes,1);
 if(result.status==='calculated')need(result.reason_codes.length===0);
 else{need(result.reason_codes.length===1);oneOf(result.reason_codes[0],REASONS);}
 exact(result.context,'rule method issuer_class product_family');
 const fullContext={rule:strip(command.rule),method:strip(command.method),issuer_class:p.issuer_class,product_family:p.product_family};
 const emptyContext={rule:null,method:null,issuer_class:null,product_family:null};
 need(same(result.context,fullContext) || same(result.context,emptyContext));
 if(!same(result.context,emptyContext)){oneOf(p.issuer_class,['hct_korea','hct_america']);text(p.product_family);}
 list(result.inputs,1);result.inputs.forEach(item=>projection(item,sourceDetail,command));
 if(result.source_page!==null){
  const page=result.source_page;exact(page,'document_id source_sha256 file_page text_sha256 row_binding');need(result.inputs.length===1);
  const sources=result.inputs[0].sources.filter(source=>ANCHORS.every(key=>same(page[key],source[key])));
  need(sources.length>0 && sources.some(source=>rowWitness(page.row_binding,source)));
 }
 for(const name of ['reported_result','unit_conversion','comparison_policy','comparison'])need(result[name]===null);
 if(result.status==='insufficient_evidence')need(result.calculation===null);
 else{
  need(same(result.context,fullContext) && result.source_page!==null && result.inputs.length===1);
  exact(result.calculation,'value unit native_result');exact(result.calculation.native_result,'value unit');
  need(typeof result.calculation.value==='number' && Number.isFinite(result.calculation.value) && result.calculation.value>0 && result.calculation.unit==='W' && same(result.calculation.value,result.calculation.native_result.value) && result.calculation.native_result.unit==='W');
 }
 return value;
}
export const validateFccCaseCalculationRequest=input=>checked(()=>request(input));
export const parseFccCaseCalculationSummaryJson=input=>checked(()=>summary(parse(input,CASE_CAP)));
export const parseFccCaseCalculationCaseJson=(input,caseId,index)=>checked(()=>detail(parse(input,CASE_CAP),caseId,summary(clone(index))));
export const validateFccCaseCalculationResponse=(input,command,sourceDetail)=>checked(()=>response(input,command,sourceDetail));
export const parseFccCaseCalculationJson=(input,command,sourceDetail)=>checked(()=>response(parse(input,FCC_CASE_CALCULATION_RESPONSE_MAX_BYTES,20,10000),command,sourceDetail));
export function createFccCaseCalculationGate(){let current=null;return {begin(){current=Object.freeze({});return current;},clear(){current=null;},current(ticket){return current!==null && ticket===current;}};}
