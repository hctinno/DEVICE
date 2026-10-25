"""Bounded readonly CLI over authored disposable sources; no model or device."""
from contextlib import redirect_stdout,redirect_stderr,ExitStack
import copy
import hashlib
import importlib
import importlib.util
from io import StringIO
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from labflow.intake_current_facts_plan import read_current_conducted_plan_from_facts
from labflow.store import canonical
from test_intake_current_facts_plan import METHOD,completed_fixture


CHILD_OBSERVATIONS=[]


class CurrentFactsPlanCliTests(unittest.TestCase):
    maxDiff=None

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='current-plan-cli-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def api(self):
        name='labflow.intake_current_facts_plan_cli'
        self.assertIsNotNone(importlib.util.find_spec(name),'assigned readonly plan CLI is absent')
        return importlib.import_module(name)

    def arguments(self,fixture):
        path=self.root/'method.json';path.write_text(canonical(METHOD),encoding='utf-8',newline='\n')
        return ['--workspace',str(fixture['store'].root),'--intake-id',fixture['intake_id'],'--method-json',str(path)]

    def invoke(self,module,args,**kwargs):
        output,error=StringIO(),StringIO()
        with redirect_stdout(output),redirect_stderr(error):status=module.main(args,**kwargs)
        return status,output.getvalue(),error.getvalue()

    def dummy_arguments(self,raw=None):
        path=self.root/'method.json'
        path.write_bytes(canonical(METHOD).encode('utf-8') if raw is None else raw)
        return ['--workspace',str(self.root/'unused-state'),'--intake-id','authored-intake','--method-json',str(path)]

    def data(self):
        from test_intake_facts_to_conducted_plan import authored,SUPPORT_BLOCK
        from labflow.intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
        context,analysis,options=authored(SUPPORT_BLOCK)
        context['instructions']='새 합성 PRIVATE-CLI-SECRET 문맥'
        options['expected_context_sha256']=hashlib.sha256(canonical(context).encode('utf-8')).hexdigest()
        wrapper=build_conducted_plan_from_intake_facts(context,analysis,**options)
        return dict(context=context,analysis=analysis,facts_plan=wrapper)

    def test_one_genuine_txt_read_prints_only_the_original_exact3_with_utf8_and_lf(self):
        module=self.api();fixture=completed_fixture(self.root/'txt',kind='text');args=self.arguments(fixture)
        with patch.object(module,'read_current_conducted_plan_from_facts',wraps=read_current_conducted_plan_from_facts) as reader:
            status,out,err=self.invoke(module,args)
        self.assertEqual(status,0);self.assertEqual(err,'');self.assertEqual(reader.call_count,1)
        value=json.loads(out)
        expected=read_current_conducted_plan_from_facts(fixture['store'].root,fixture['intake_id'],method=METHOD)
        self.assertEqual(value,expected);self.assertEqual(set(value),{'context','analysis','facts_plan'})
        self.assertEqual(out,canonical(expected)+'\n')
        self.assertEqual(value['facts_plan']['status'],'ready_for_simulation')
        self.assertIs(value['facts_plan']['plan_input']['verification']['execution_authority'],False)

    def test_genuine_missing_workspace_is_unavailable_without_data_or_private_error_details(self):
        module=self.api();method=self.root/'method.json';method.write_text(canonical(METHOD),encoding='utf-8')
        workspace=self.root/'PRIVATE-SECRET-missing'
        args=['--workspace',str(workspace),'--intake-id','missing-intake','--method-json',str(method)]
        status,out,err=self.invoke(module,args)
        self.assertEqual(status,3);self.assertEqual(out,'')
        self.assertEqual(json.loads(err),{'error':{'code':'store_missing'}})
        self.assertNotIn('PRIVATE-SECRET',err);self.assertFalse(workspace.exists())

    def test_paired_flags_and_expected_pin_lexemes_are_bounded_without_defaults_or_argv_echo(self):
        module=self.api();base=self.dummy_arguments();cases=[[],base[:4],base+base[:2],
            ['--workspace=PRIVATE-SECRET',*base[2:]],base+['--profile','PRIVATE-SECRET'],
            base+['--expected-revision','01'],base+['--expected-revision','0'],
            base+['--expected-revision','9223372036854775808'],base+['--expected-revision','١'],
            base+['--expected-context-sha256','A'*64],base+['--expected-context-sha256','private-secret'],
            ['--workspace','relative',*base[2:]],base[:-1]+['\\\\server\\share\\method.json']]
        for args in cases:
            with self.subTest(args=args):
                with patch.object(module,'read_current_conducted_plan_from_facts') as reader:
                    status,out,err=self.invoke(module,args)
                self.assertEqual(status,1);self.assertEqual(out,'');reader.assert_not_called()
                self.assertEqual(json.loads(err),{'error':{'code':'intake_current_facts_plan_cli_invalid_arguments'}})
                self.assertNotIn('PRIVATE-SECRET',err)
        with patch.object(module,'read_current_conducted_plan_from_facts',return_value=self.data()) as reader:
            status,_,err=self.invoke(module,base+['--expected-revision','7','--expected-context-sha256','a'*64])
        self.assertEqual(status,0);self.assertEqual(err,'')
        self.assertEqual(reader.call_args.kwargs['expected_revision'],7)
        self.assertEqual(reader.call_args.kwargs['expected_context_sha256'],'a'*64)

    def test_strict_method_json_rejects_duplicate_nonfinite_bom_surrogate_depth_and_size_before_api(self):
        module=self.api()
        cases=[b'{"a":1,"a":2}',b'{"x":NaN}',b'{"x":Infinity}',b'{"x":1e999}',
            b'\xef\xbb\xbf{}',b'\xff{}',b'{"x":"\\ud800"}',b'[]',b'{"x":'+b'['*9+b'0'+b']'*9+b'}',
            canonical({str(i):0 for i in range(1100)}).encode('utf-8'),b' '*(65537)]
        for raw in cases:
            with self.subTest(raw_kind=raw[:20]):
                args=self.dummy_arguments(raw)
                with patch.object(module,'read_current_conducted_plan_from_facts') as reader:
                    status,out,err=self.invoke(module,args)
                self.assertEqual(status,1);self.assertEqual(out,'');reader.assert_not_called()
                self.assertEqual(json.loads(err),{'error':{'code':'intake_current_facts_plan_cli_method_invalid'}})
        raw=canonical(METHOD).encode('utf-8');args=self.dummy_arguments(raw+b' '*(65536-len(raw)))
        with patch.object(module,'read_current_conducted_plan_from_facts',return_value=self.data()) as reader:
            status,_,err=self.invoke(module,args)
        self.assertEqual(status,0);self.assertEqual(err,'');self.assertEqual(reader.call_args.kwargs['method'],METHOD)

    def test_native_method_pin_blocks_writers_and_rejects_multiple_links_with_no_method_mutation(self):
        module=self.api();args=self.dummy_arguments();path=Path(args[-1]);before=path.read_bytes()
        def read(*args,**kwargs):
            fd=None;blocked=False
            try:
                try:fd=os.open(path,os.O_WRONLY)
                except PermissionError:blocked=True
            finally:
                if fd is not None:os.close(fd)
            self.assertTrue(blocked);return self.data()
        with patch.object(module,'read_current_conducted_plan_from_facts',side_effect=read):
            self.assertEqual(self.invoke(module,args)[0],0)
        self.assertEqual(path.read_bytes(),before)
        os.link(path,self.root/'method-alias.json')
        with patch.object(module,'read_current_conducted_plan_from_facts') as reader:
            status,out,err=self.invoke(module,args)
        self.assertEqual(status,1);self.assertEqual(out,'');reader.assert_not_called()
        self.assertEqual(json.loads(err)['error']['code'],'intake_current_facts_plan_cli_method_invalid')

    def test_blocked_parent_wrapper_and_original_null_questions_are_data_without_new_envelope(self):
        module=self.api();fixture=completed_fixture(self.root/'blocked',kind='text',duty='40');args=self.arguments(fixture)
        status,out,err=self.invoke(module,args)
        expected=read_current_conducted_plan_from_facts(fixture['store'].root,fixture['intake_id'],method=METHOD)
        self.assertEqual((status,err),(2,''));self.assertEqual(json.loads(out),expected)
        wrapper=json.loads(out)['facts_plan']
        self.assertEqual([q['reason'] for q in wrapper['questions']],['source_unit_missing'])
        self.assertIsNone(wrapper['plan_input']['plan']['source_settings']['duty_cycle'])

    def test_only_fixed_error_codes_are_diagnosed_and_diagnostic_controls_do_not_replace_parent_failure(self):
        from labflow.ui_read_model import ReadModelError
        module=self.api();args=self.dummy_arguments()
        for error,expected in [(ReadModelError('PRIVATE-CLI-SECRET'),'intake_current_facts_plan_cli_parent_unavailable'),
            (RuntimeError('PRIVATE-CLI-SECRET'),'intake_current_facts_plan_cli_internal_error')]:
            with patch.object(module,'read_current_conducted_plan_from_facts',side_effect=error):
                status,out,err=self.invoke(module,args)
            self.assertEqual(status,3 if type(error) is ReadModelError else 1);self.assertEqual(out,'')
            self.assertEqual(json.loads(err)['error']['code'],expected);self.assertNotIn('PRIVATE-CLI-SECRET',err)
        error=ReadModelError('store_missing');original=ReadModelError.__getattribute__
        def access(value,key):
            if key=='code':raise KeyboardInterrupt('diagnostic-secondary')
            return original(value,key)
        with patch.object(ReadModelError,'__getattribute__',access),\
             patch.object(module,'read_current_conducted_plan_from_facts',side_effect=error):
            status,out,err=self.invoke(module,args)
        self.assertEqual((status,out),(3,''))
        self.assertEqual(json.loads(err)['error']['code'],'intake_current_facts_plan_cli_parent_unavailable')
        class BadDiagnostic(StringIO):
            def write(self,value):raise KeyboardInterrupt('second diagnostic control')
        with patch.object(module,'read_current_conducted_plan_from_facts',side_effect=ReadModelError('store_missing')),\
             redirect_stdout(StringIO()),redirect_stderr(BadDiagnostic()):
            self.assertEqual(module.main(args),3)

    def test_original_controls_survive_native_close_and_close_only_failure_emits_no_data(self):
        module=self.api();args=self.dummy_arguments();constructor=module._native._WindowsIO
        for first in (KeyboardInterrupt('first'),MemoryError('first'),SystemExit('first')):
            backends=[];secondary=SystemExit('late native close')
            def create():
                backend=constructor();close=backend.close
                def late():close();raise secondary
                backend.close=late;backends.append(backend);return backend
            with patch.object(module._native,'_WindowsIO',side_effect=create),\
                 patch.object(module,'read_current_conducted_plan_from_facts',side_effect=first),\
                 redirect_stdout(StringIO()),redirect_stderr(StringIO()):
                with self.assertRaises(type(first)) as caught:module.main(args)
            self.assertIs(caught.exception,first);self.assertTrue(all(not b.held for b in backends))
        def create():
            backend=constructor();close=backend.close
            def late():close();raise OSError('PRIVATE-CLI-SECRET close')
            backend.close=late;return backend
        with patch.object(module._native,'_WindowsIO',side_effect=create),\
             patch.object(module,'read_current_conducted_plan_from_facts',return_value=self.data()):
            status,out,err=self.invoke(module,args)
        self.assertEqual((status,out),(1,''));self.assertNotIn('PRIVATE-CLI-SECRET',err)

    def test_parent_output_native_frame_shape_authority_and_new_byte_cap_are_checked_before_stdout(self):
        module=self.api();args=self.dummy_arguments();self.assertEqual(module._FRAME_BYTES,16777216)
        data=self.data();bad=[]
        value=copy.deepcopy(data);value['extra']='PRIVATE-CLI-SECRET';bad.append(value)
        value=copy.deepcopy(data);value['facts_plan']['status']='unknown';bad.append(value)
        value=copy.deepcopy(data);value['facts_plan']['plan_input']['verification']['execution_authority']=True;bad.append(value)
        value=copy.deepcopy(data);value['context']['instructions']='\ud800';bad.append(value)
        for value in bad:
            with patch.object(module,'read_current_conducted_plan_from_facts',return_value=value):
                status,out,err=self.invoke(module,args)
            self.assertEqual((status,out),(1,''));self.assertNotIn('PRIVATE-CLI-SECRET',err)
        with patch.object(module,'_FRAME_BYTES',1024),patch.object(module,'read_current_conducted_plan_from_facts',return_value=data):
            status,out,err=self.invoke(module,args)
        self.assertEqual((status,out),(1,''));self.assertEqual(json.loads(err)['error']['code'],'intake_current_facts_plan_cli_output_limit')
        with patch.object(module,'read_current_conducted_plan_from_facts',return_value=data):status,out,err=self.invoke(module,args)
        self.assertEqual((status,err),(0,''));self.assertIn('PRIVATE-CLI-SECRET',out);self.assertIn('새 합성',out)

    def test_partial_bool_and_failed_stdout_writes_are_not_retried_or_echoed_as_diagnostics(self):
        module=self.api();args=self.dummy_arguments();data=self.data()
        for mode in ('partial','bool','raise'):
            class Sink(StringIO):
                calls=0
                def write(self,text):
                    self.calls+=1
                    if mode=='partial':super().write(text[:5]);return 5
                    if mode=='bool':return True
                    raise OSError('PRIVATE-CLI-SECRET write')
            output,error=Sink(),StringIO()
            with patch.object(module,'read_current_conducted_plan_from_facts',return_value=data),\
                 redirect_stdout(output),redirect_stderr(error):status=module.main(args)
            self.assertEqual(status,1);self.assertEqual(output.calls,1)
            self.assertEqual(json.loads(error.getvalue())['error']['code'],'intake_current_facts_plan_cli_output_failed')
            self.assertNotIn('PRIVATE-CLI-SECRET',error.getvalue());self.assertFalse(output.closed)

    def test_help_has_no_data_or_read_and_help_delivery_failure_is_not_an_argument_error(self):
        module=self.api()
        with patch.object(module,'read_current_conducted_plan_from_facts') as reader:
            status,out,err=self.invoke(module,['--help'])
        self.assertEqual((status,out),(0,''));self.assertIn('--method-json',err);reader.assert_not_called()
        class FailOnce(StringIO):
            calls=0
            def write(self,value):
                self.calls+=1
                if self.calls==1:return 0
                return super().write(value)
        error=FailOnce()
        with redirect_stdout(StringIO()),redirect_stderr(error):status=module.main(['--help'])
        self.assertEqual(status,1)
        self.assertEqual(json.loads(error.getvalue())['error']['code'],'intake_current_facts_plan_cli_output_failed')

    def test_process_route_owns_utf8_lf_but_keeps_first_ki_and_prior_error_during_final_flush(self):
        module=self.api()
        class ProcessStream(StringIO):
            def __init__(self,error=None):super().__init__();self.error=error;self.config=[]
            def reconfigure(self,**kwargs):self.config.append(kwargs)
            def flush(self):
                if self.error is not None:raise self.error
        output,error=ProcessStream(KeyboardInterrupt('first flush')),ProcessStream(OSError('later flush'))
        with patch.object(sys,'argv',['cli','--help']),patch.object(sys,'stdout',output),patch.object(sys,'stderr',error),\
             patch.object(module,'main',return_value=2),patch.object(module,'_quiet') as quiet:
            status=module._process_main()
        self.assertEqual(status,130);self.assertEqual(quiet.call_count,2)
        self.assertTrue(all(call.args[1]==130 for call in quiet.call_args_list))
        self.assertEqual(output.config,[dict(encoding='utf-8',errors='strict',newline='\n')])
        with patch.object(sys,'argv',['cli']),patch.object(sys,'stdout',output),patch.object(sys,'stderr',error),\
             patch.object(module,'main',return_value=3),patch.object(module,'_quiet'):
            self.assertEqual(module._process_main(),3)


class CurrentFactsPlanCliChildTests(unittest.TestCase):
    maxDiff=None

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='plan-cli-child-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=Path(__file__).resolve().parents[1]

    def arguments(self,fixture,name='method'):
        path=self.root/(name+'.json');path.write_text(canonical(METHOD),encoding='utf-8',newline='\n')
        return ['--workspace',str(fixture['store'].root),'--intake-id',fixture['intake_id'],'--method-json',str(path)]

    def command(self,args):
        return [sys.executable,'-X','utf8','-B','-m','labflow.intake_current_facts_plan_cli',*args]

    def run_cli(self,args):
        command=self.command(args)
        result=subprocess.run(command,cwd=self.repo,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        self.assertLessEqual(len(result.stdout),16777216);self.assertLessEqual(len(result.stderr),4096)
        CHILD_OBSERVATIONS.append(dict(argv=command,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,
            source='actual Python module child, not a model process'))
        return result

    def files(self,fixture):
        from test_intake_current_facts_plan import CurrentFactsPlanTests
        return CurrentFactsPlanTests.files(self,fixture)

    def test_actual_module_pdf_and_txt_ready_preserve_original_exact3_and_native_source_files(self):
        for kind in ('pdf','text'):
            with self.subTest(kind=kind):
                fixture=completed_fixture(self.root/kind,kind=kind);args=self.arguments(fixture,kind)
                before=self.files(fixture);method=Path(args[-1]).read_bytes()
                result=self.run_cli(args)
                expected=read_current_conducted_plan_from_facts(fixture['store'].root,fixture['intake_id'],method=METHOD)
                self.assertEqual(result.returncode,0);self.assertEqual(result.stderr,b'')
                self.assertEqual(result.stdout,canonical(expected).encode('utf-8')+b'\n')
                self.assertNotIn(b'\r',result.stdout);self.assertEqual(json.loads(result.stdout),expected)
                self.assertEqual(self.files(fixture),before);self.assertEqual(Path(args[-1]).read_bytes(),method)

    def test_actual_module_blocked_unit_and_unsupported_method_keep_parent_gaps_without_approval(self):
        fixture=completed_fixture(self.root/'blocked',kind='text',duty='40');args=self.arguments(fixture)
        result=self.run_cli(args);value=json.loads(result.stdout)
        self.assertEqual((result.returncode,result.stderr),(2,b''))
        self.assertEqual([q['reason'] for q in value['facts_plan']['questions']],['source_unit_missing'])
        self.assertIsNone(value['facts_plan']['plan_input']['plan']['source_settings']['duty_cycle'])
        unsupported=dict(METHOD,method_id='unverified-authored-method')
        Path(args[-1]).write_text(canonical(unsupported),encoding='utf-8')
        result=self.run_cli(args);value=json.loads(result.stdout)
        self.assertEqual((result.returncode,result.stderr),(2,b''))
        self.assertTrue(any(g['code']=='unsupported_method_field' for g in value['facts_plan']['plan_input']['gaps']))
        self.assertIs(value['facts_plan']['plan_input']['verification']['execution_authority'],False)

    def test_actual_module_malformed_method_and_parent_unavailable_have_no_data_or_secret_echo(self):
        method=self.root/'PRIVATE-CLI-SECRET.json';method.write_bytes(b'{"PRIVATE-CLI-SECRET":NaN}')
        workspace=self.root/'PRIVATE-CLI-SECRET-state'
        args=['--workspace',str(workspace),'--intake-id','authored-intake','--method-json',str(method)]
        result=self.run_cli(args)
        self.assertEqual((result.returncode,result.stdout),(1,b''))
        self.assertEqual(json.loads(result.stderr),{'error':{'code':'intake_current_facts_plan_cli_method_invalid'}})
        self.assertNotIn(b'PRIVATE-CLI-SECRET',result.stderr)
        method.write_text(canonical(METHOD),encoding='utf-8')
        result=self.run_cli(args)
        self.assertEqual((result.returncode,result.stdout),(3,b''))
        self.assertEqual(json.loads(result.stderr),{'error':{'code':'store_missing'}})
        self.assertFalse(workspace.exists())

    def test_actual_module_closed_stdout_is_non_success_not_interpreter_exit120_and_preserves_sources(self):
        fixture=completed_fixture(self.root/'stdout',kind='text');args=self.arguments(fixture);before=self.files(fixture)
        command=self.command(args);process=subprocess.Popen(command,cwd=self.repo,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            process.stdout.close();process.stdout=None
            try:out,err=process.communicate(timeout=30)
            except BaseException:
                process.kill();process.communicate(timeout=5);raise
        finally:
            if process.stderr is not None:process.stderr.close()
        CHILD_OBSERVATIONS.append(dict(argv=command,returncode=process.returncode,stdout=b'',stderr=err,
            source='actual Python child with parent read end closed; no model',stdout_route='closed before delivery'))
        self.assertEqual(process.returncode,1);self.assertNotEqual(process.returncode,120)
        self.assertEqual(json.loads(err),{'error':{'code':'intake_current_facts_plan_cli_output_failed'}})
        self.assertEqual(self.files(fixture),before)


if __name__=='__main__':unittest.main()
