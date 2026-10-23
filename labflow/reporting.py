"""Traceable draft outputs; never issues a certificate or a released test report."""
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import uuid

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from .store import canonical
from .workflow import case_status


def render_report(store,case_id,output_dir):
    payload=case_status(store,case_id)
    payload['report_status']='DRAFT'
    payload['generated_at']=datetime.now(timezone.utc).isoformat()
    payload['release_note']='No official release. Regulatory scope completeness is not reviewed.'
    folder=Path(output_dir).resolve()/case_id/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8])
    folder.mkdir(parents=True,exist_ok=False);(folder/'evidence').mkdir()
    hashes=set()
    for run in payload['runs']:
        if run.get('raw_sha256'):hashes.add(run['raw_sha256'])
        hashes.update(run['setup_artifact_ids']);hashes.update(run['calibration_artifact_ids'])
    payload['evidence_files']={};missing=[]
    for sha in sorted(hashes):
        try:
            data=store.verify_blob(sha).read_bytes()
            if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('Evidence changed during read')
            target=folder/'evidence'/sha;target.write_bytes(data)
            payload['evidence_files'][sha]=str(target.relative_to(folder))
        except ValueError:missing.append(sha)
    if missing:
        payload['blockers'].append('evidence_unavailable_at_report:'+','.join(missing))
        for result in payload['results']:
            result['decision']='blocked';result['blockers'].append('report_evidence_unavailable')
    payload['methods']=[];source_ids=set()
    for method_id in sorted({p['method_id'] for p in payload['plans']}):
        row=store.row('methods',method_id)
        payload['methods'].append({**row['data'],'technical_review_status':row['review_status']})
        source_ids.update(row['data']['source_document_ids'])
    payload['sources']=[]
    for source_id in sorted(source_ids):
        try:doc=store.document(source_id)
        except ValueError:doc={'document_id':source_id,'status':'missing'}
        payload['sources'].append(doc)
    subjects={case_id,*source_ids,*[p['plan_id'] for p in payload['plans']],*[r['run_id'] for r in payload['runs']],*[m['method_id'] for m in payload['methods']]}
    with store.connection() as con:
        payload['audit_events']=[dict(r) for r in con.execute('SELECT * FROM events ORDER BY event_id') if r['subject_id'] in subjects]
    (folder/'report.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

    def display(value):
        if value is None or value=='':return 'Not supplied'
        return json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else str(value)
    product=payload['case']['product']
    result_rows=[]
    for result in payload['results']:
        for point in result['calculations']:
            result_rows.append([result['plan_id'],display(point['value'])+' '+point['unit'],
                result['limit']['operator']+' '+display(result['limit']['value'])+' '+result['limit']['unit'],
                display(point['margin']),result['decision']])
        if not result['calculations']:result_rows.append([result['plan_id'],'No valid result','—','—',result['decision']])
    sections=[
        ('1. Product and document',['Item','Value'],[
            ['Case / report',case_id],['Created (UTC)',payload['generated_at']],
            ['Manufacturer',product.get('manufacturer')],['Model',product.get('model')],
            ['Serial / sample',product.get('serial_number')],['Hardware / firmware',display(product.get('hw_version'))+' / '+display(product.get('fw_version'))],
            ['Authorization route',payload['case']['authorization_route']],['Declared scope',', '.join(payload['case']['scope_ids'])]]),
        ('2. Applicability and configuration',['Plan item','Method','Applicability','Configuration / rationale'],[
            [p['plan_id'],p['method_id'],p['applicability'],display(p['configuration'])+'; '+p['rationale']] for p in payload['plans']]),
        ('3. Measurement results — preliminary',['Plan item','Calculated result','Profile limit','Margin','Decision'],result_rows),
        ('4. Test conditions and equipment',['Run','Date / state','Settings / environment','Equipment'],[
            [r['run_id'],r['started_at']+' / '+r['execution_status'],display(r['settings'])+'; '+display(r['environment']),', '.join(r['equipment_ids'])] for r in payload['runs']]),
        ('5. Methods and editions',['Method','Calculation','Technical review','Source IDs'],[
            [m['method_id'],m['calculator'],m['technical_review_status'],', '.join(m['source_document_ids'])] for m in payload['methods']]),
        ('6. Reference documents',['Document','Title / edition','Acquisition','Review'],[
            [d['document_id'],display(d.get('title'))+' / '+display(d.get('version')),d.get('status'),d.get('review_status')] for d in payload['sources']]),
        ('7. Setup, calibration and raw-data trace',['Run','Raw SHA-256','Setup / calibration references'],[
            [r['run_id'],r.get('raw_sha256'),display(r['setup_artifact_ids'])+' / '+display(r['calibration_artifact_ids'])] for r in payload['runs']]),
        ('8. Unresolved requirements',['Issue'],[[b] for b in payload['blockers']]),
        ('9. Review trail',['Time','Action','Subject'],[[e['created_at'],e['action'],e['subject_id']] for e in payload['audit_events'] if 'review' in e['action']]),
        ('10. Filing and release',['Item','State'],[['Official release','Not available'],['Submitted to FCC/TCB','No'],['Scope completeness','Not reviewed'],['Full calculations / source hashes','See accompanying report.json and evidence files']]),
    ]
    label='SYNTHETIC DATA — ' if payload['synthetic'] else ''
    body=''
    for title,headers,rows in sections:
        body+='<section><h2>'+escape(title)+'</h2><table><thead><tr>'+''.join('<th>'+escape(h)+'</th>' for h in headers)+'</tr></thead><tbody>'
        body+=''.join('<tr>'+''.join('<td>'+escape(display(v))+'</td>' for v in row)+'</tr>' for row in rows)
        if not rows:body+='<tr><td colspan="'+str(len(headers))+'">Not supplied / pending</td></tr>'
        body+='</tbody></table></section>'
    evidence=''.join('<li><a href="'+escape(rel,quote=True)+'">'+escape(sha)+'</a></li>' for sha,rel in payload['evidence_files'].items())
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Draft FCC laboratory report</title>
<style>body{font:14px system-ui,sans-serif;max-width:1000px;margin:36px auto;color:#172b4d}h1{font-size:26px}h2{font-size:18px;margin-top:28px}.banner{border:2px solid #a33;padding:16px;color:#911}table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{border:1px solid #ccd5df;padding:8px;text-align:left;overflow-wrap:anywhere}th{background:#edf2f8}li{overflow-wrap:anywhere}@page{size:A4;margin:18mm}@media print{h2{break-after:avoid}table{font-size:9px}tr{break-inside:avoid}}</style>'''
    html+='<h1>'+escape(label+'DRAFT — FCC workflow report')+'</h1><p class="banner">'+escape(payload['release_note'])+'</p>'+body+'<h2>Retained measurement evidence</h2><ul>'+evidence+'</ul></html>'
    (folder/'report.html').write_text(html)

    # A standard Korean CID font preserves Korean names in addition to Latin FCC content.
    font='HYSMyeongJo-Medium'
    if font not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(UnicodeCIDFont(font))
    style=ParagraphStyle('body',fontName=font,fontSize=8.5,leading=12,spaceAfter=4,wordWrap='CJK')
    title_style=ParagraphStyle('title',parent=style,fontSize=17,leading=22,spaceAfter=14)
    heading_style=ParagraphStyle('heading',parent=style,fontSize=12,leading=17,spaceBefore=12,spaceAfter=8)
    story=[Paragraph(escape(label+'DRAFT — FCC workflow report'),title_style),Paragraph(escape(payload['release_note']),style)]
    for title,headers,rows in sections:
        story.append(Paragraph(escape(title),heading_style))
        values=[headers]+(rows or [['Not supplied / pending']+['']*(len(headers)-1)])
        table=Table([[Paragraph(escape(display(value)),style) for value in row] for row in values],
                    colWidths=[(A4[0]-72)/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf2f8')),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#cbd5e1')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
        story.append(table)
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont(font,8)
        canvas.drawString(36,20,('SYNTHETIC | ' if payload['synthetic'] else '')+'DRAFT — NOT RELEASED | '+case_id)
        canvas.drawRightString(A4[0]-36,20,str(doc.page));canvas.restoreState()
    SimpleDocTemplate(str(folder/'report.pdf'),pagesize=A4,rightMargin=36,leftMargin=36,topMargin=36,bottomMargin=36).build(story,onFirstPage=footer,onLaterPages=footer)
    file_hashes={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
    (folder/'files.sha256.json').write_text(json.dumps(file_hashes,indent=2)+'\n')
    return {'html':str(folder/'report.html'),'pdf':str(folder/'report.pdf'),'json':str(folder/'report.json'),'manifest':str(folder/'files.sha256.json'),'status':'DRAFT','synthetic':payload['synthetic']}
