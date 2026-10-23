import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from labflow.active_intake import register_source, scan_source
from labflow.store import Store


class IntakeCLITests(unittest.TestCase):
    def test_cli_discovers_unicode_upload_and_records_generic_user_instruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            inbox=root/'inbox'
            (inbox/'request').mkdir(parents=True)
            (inbox/'request'/'details.txt').write_text('제품 설명 — 요청 시장 미기재',encoding='utf-8')
            def call(*args):
                result=subprocess.run([sys.executable,'-m','labflow','--workspace',str(root/'state'),*args],
                                      capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(result.returncode,0,result.stderr)
                return json.loads(result.stdout)
            call('intake-add-source','INBOX',str(inbox),'--synthetic','--settle-seconds','0.001')
            self.assertEqual(call('intake-scan','INBOX')['accepted'],[])
            self.assertEqual(len(call('intake-scan','INBOX')['accepted']),1)
            self.assertEqual(call('intake-respond','E1','proceed')['status'],'recorded')
            self.assertTrue(call('intake-status')[0]['delegated'])
            job=call('intake-claim','worker')
            self.assertEqual(job['documents'][0]['text'],'제품 설명 — 요청 시장 미기재')


class IntakeMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_intake_analysis_preserves_evidence_and_cannot_grant_authority(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            inbox=root/'inbox'
            (inbox/'one').mkdir(parents=True)
            (inbox/'one'/'product.txt').write_text('Handheld infrared control.\n',encoding='utf-8')
            store=Store(root/'state')
            register_source(store,'INBOX',inbox,synthetic=True,settle_seconds=1)
            scan_source(store,'INBOX',now=100)
            scan_source(store,'INBOX',now=101)
            parameters=StdioServerParameters(command=sys.executable,
                args=['-m','labflow','--workspace',str(root/'state'),'mcp'],cwd=str(Path(__file__).resolve().parents[1]))
            async with stdio_client(parameters) as (read,write):
                async with ClientSession(read,write) as session:
                    await session.initialize()
                    names={tool.name for tool in (await session.list_tools()).tools}
                    self.assertIn('lab_intake_claim',names)
                    self.assertNotIn('lab_intake_respond',names)
                    self.assertNotIn('lab_intake_add_source',names)
                    async def call(name,args=None):
                        result=await session.call_tool(name,args or {})
                        self.assertFalse(result.isError,result.content)
                        return result.structuredContent
                    claimed=await call('lab_intake_claim',{'worker_id':'mcp-worker'})
                    job=claimed['job']
                    doc=job['documents'][0]
                    result=await call('lab_intake_complete',{'job_id':job['job_id'],'token':job['token'],
                        'analysis':{'schema_version':1,'producer':{'kind':'fixture','name':'mcp-contract'},
                        'identity':'single','missing_fields':[],
                        'facts':[{'field':'product_type','value':'remote_control','status':'inferred',
                            'evidence':[{'path':doc['path'],'sha256':doc['sha256'],'line_start':1,'line_end':1,
                                         'quote':'Handheld infrared control.','role':'product'}]}]}})
                    self.assertEqual(result['facts']['product_type']['value'],'remote_control')
                    self.assertIn('missing_market',{q['key'] for q in result['questions']})
                    status=await call('lab_intake_status',{'intake_id':job['intake_id']})
                    self.assertFalse(status['intakes'][0]['delegated'])
                    caps=await call('lab_capabilities')
                    self.assertFalse(caps['autonomous_model_service'])
                    self.assertFalse(caps['live_hardware'])


if __name__=='__main__':
    unittest.main()
