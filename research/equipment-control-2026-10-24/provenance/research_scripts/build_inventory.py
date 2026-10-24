from pathlib import Path
import sqlite3,json,collections,re,csv,hashlib
ROOT=Path('/workspace/research/equipment-control-full-2026-10-24')
(ROOT/'inputs').mkdir(parents=True,exist_ok=True)
(ROOT/'results').mkdir(exist_ok=True)
c=sqlite3.connect('file:/workspace/DEVICE/data/equipment.sqlite3?mode=ro',uri=True);c.row_factory=sqlite3.Row
groups={}
for row in c.execute("""select e.equipment_id,e.model_id,e.name,e.model_name,e.category_id,e.register_no,m.canonical_name manufacturer from equipment e left join manufacturers m using(manufacturer_id) order by e.register_no"""):
 d=dict(row);k=d['model_id'] or 'IDENTITY-'+d['equipment_id']
 g=groups.setdefault(k,dict(item_id=k,model_id=d['model_id'],manufacturer=d['manufacturer'] or '',model=d['model_name'] or '',names=[],categories=[],equipment_ids=[],register_numbers=[]))
 for field,val in [('names',d['name'] or ''),('categories',d['category_id'])]:
  if val and val not in g[field]:g[field].append(val)
 g['equipment_ids'].append(d['equipment_id']);g['register_numbers'].append(d['register_no'])
passive={'antenna','attenuator','rf_coupler','filter','fixture_accessory','passive_electrical','termination'}
electrical={'power_supply','electronic_load','electrical_meter','power_meter','oscilloscope','electrical_safety','daq','calibration'}
rf={'communication_tester','rf_analyzer','network_analyzer','signal_generator','rf_amplifier','emc_transient','emc_network','rf_conversion','sar','power_sensor','broadcast_network'}
environment={'chamber','mechanical_test','fire_ip_test','cooling_heating'}
motion={'motion','motion_controller','interface','switch_system','system_controller','software_computer'}
buckets=collections.defaultdict(list)
for g in groups.values():
 cats=set(g['categories']);text=' '.join(g['names']+[g['model']]).lower()
 activehint=bool(re.search(r'programmable|usb|controller|control unit|switch(ing)? (system|unit|box|matrix)|motor|자동|제어|스위치|마스트|턴테이블',text))
 if cats<=passive and not activehint:
  g['initial_scope']='excluded_passive';g['initial_reason']='기존 분류상 수동 안테나/고정 감쇠기/수동 RF 부품/치구/케이블. 능동 제어 명칭 미검출; 원본 식별자는 보존.';bucket='excluded_passive'
 else:
  g['initial_scope']='candidate_review';g['initial_reason']='설비/계측/인터페이스 또는 혼합 범주: 모델 단위 포함·제외·식별 확인 필요'
  m=g['manufacturer'].lower()
  if any(x in m for x in ['rohde','rodhe','schwarz','keysight','agilent']) and 'schwarzbeck' not in m or m=='hp':bucket='keysight_rs'
  elif cats & environment:bucket='environment'
  elif cats & motion:bucket='motion_switch'
  elif cats & electrical:bucket='electrical'
  elif cats & rf:bucket='rf_emc_sar'
  else:bucket='other_measurement'
 g['assignment']=bucket;g['registration_rows']=len(g['equipment_ids']);buckets[bucket].append(g)
allrows=list(groups.values())
(ROOT/'inventory_items.json').write_text(json.dumps(allrows,ensure_ascii=False,indent=2))
for key,records in buckets.items():
 (ROOT/'inputs'/f'{key}.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
summary={'inventory_rows':sum(r['registration_rows'] for r in allrows),'inventory_items':len(allrows),'identified_models':sum(bool(r['model_id']) for r in allrows),'unidentified_rows':sum(not r['model_id'] for r in allrows),'groups':{k:{'items':len(v),'rows':sum(x['registration_rows'] for x in v),'manufacturers':len(set(x['manufacturer'] for x in v))} for k,v in buckets.items()},'database_sha256':hashlib.sha256(Path('/workspace/DEVICE/data/equipment.sqlite3').read_bytes()).hexdigest()}
(ROOT/'inventory_snapshot.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False))

