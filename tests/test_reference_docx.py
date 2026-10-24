"""Synthetic DOCX contracts; no customer documents or Office execution."""
import importlib.util
import hashlib
from io import BytesIO
import json
import struct
import unittest
from unittest import mock
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
TOP = {'schema_version','source','reader','status','complete','scope','limits','blocks','text_sha256','issues','statistics'}
DEFAULTS = {'max_input_bytes':16777216,'max_zip_members':1024,'max_directory_bytes':4194304,
 'max_declared_uncompressed_bytes':67108864,'max_member_bytes':8388608,'max_expanded_bytes':16777216,
 'max_compression_ratio':1000,'max_xml_depth':64,'max_xml_elements':200000,'max_xml_chars':2000000,
 'max_table_depth':8,'max_blocks':20000,'max_rows':10000,'max_cells':50000,'max_grid_columns':256,
 'max_text_chars':1000000,'max_output_bytes':8388608,'max_issues':128}


def paragraph(text):
    return '<w:p><w:r><w:t xml:space="preserve">'+escape(text)+'</w:t></w:r></w:p>'


def package(body='', *, extras=(), main='word/document.xml', relationships='', root_extra='',
            xml=None, namespace=W, compression=zipfile.ZIP_STORED, content_type=MIME):
    types = f'<Types xmlns="{CT}"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/{main}" ContentType="{content_type}"/></Types>'
    rels = f'<Relationships xmlns="{REL}">{root_extra}<Relationship Id="main" Type="{R}/officeDocument" Target="{main}"/></Relationships>'
    document = xml if xml is not None else f'<w:document xmlns:w="{namespace}" xmlns:r="{R}"><w:body>{body}</w:body></w:document>'
    entries = [('[Content_Types].xml',types),('_rels/.rels',rels),(main,document)]
    if relationships:
        parent, _, leaf = main.rpartition('/')
        entries.append(((parent+'/' if parent else '')+'_rels/'+leaf+'.rels',f'<Relationships xmlns="{REL}">{relationships}</Relationships>'))
    entries.extend(extras)
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w',compression=compression) as archive:
        for name,value in entries:
            info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.compress_type=compression
            archive.writestr(info,value.encode('utf-8') if isinstance(value,str) else value)
    return stream.getvalue()


def table(rows, grid=2):
    return '<w:tbl><w:tblGrid>'+('<w:gridCol/>'*grid)+'</w:tblGrid>'+''.join(rows)+'</w:tbl>'


def cell(text='', *, properties='', blocks=None):
    return '<w:tc>'+('<w:tcPr>'+properties+'</w:tcPr>' if properties else '')+(paragraph(text) if blocks is None else blocks)+'</w:tc>'


def flagged(data, *, flag=None, crc=None):
    value=bytearray(data);pos=value.index(b'PK\x01\x02')
    local=struct.unpack_from('<I',value,pos+42)[0]
    if flag is not None:
        struct.pack_into('<H',value,pos+8,flag);struct.pack_into('<H',value,local+6,flag)
    if crc is not None:
        struct.pack_into('<I',value,pos+16,crc);struct.pack_into('<I',value,local+14,crc)
    return bytes(value)


def replace_member(data, part, transform):
    output=BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as source, zipfile.ZipFile(output,'w') as target:
        for info in source.infolist():
            raw=source.read(info)
            target.writestr(info,transform(raw) if info.filename==part else raw)
    return output.getvalue()


class DocxApiTests(unittest.TestCase):
    def test_read_docx_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.reference_docx'))


class DocxContractTests(unittest.TestCase):
    def setUp(self):
        self.api=__import__('labflow.reference_docx',fromlist=['read_docx'])

    def read(self, data, limits=None, name='합성.docx'):
        value=self.api.read_docx(data,name,limits=limits)
        self.assertEqual(set(value),TOP);self.assertEqual(value['schema_version'],1)
        self.assertEqual(value['source'],{'filename':name,'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)})
        self.assertEqual(value['reader'],{'name':'reference_docx','version':'1'})
        self.assertEqual(set(value['limits']),set(DEFAULTS));self.assertEqual(value['scope']['page_numbers'],'unavailable')
        self.assertLessEqual(len(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()),value['limits']['max_output_bytes'])
        self.assertEqual(value['complete'],value['status'] in {'ok','empty'})
        return value

    def codes(self, value):
        return {item['code'] for item in value['issues']}

    def test_plain_unicode_hash_exact_DTO_and_repeat(self):
        data=package(paragraph('가나다 & <문서>'))
        first=self.read(data);self.assertEqual(first,self.read(data))
        self.assertEqual(first['status'],'ok');self.assertEqual(first['issues'],[])
        p=first['blocks'][0];self.assertEqual(set(p),{'kind','locator','text','text_sha256','complete','breaks'})
        self.assertEqual(p['text'],'가나다 & <문서>');self.assertTrue(p['complete'])
        self.assertEqual(p['text_sha256'],hashlib.sha256(p['text'].encode()).hexdigest())
        self.assertEqual(first['text_sha256'],p['text_sha256'])
        self.assertEqual(p['locator'],{'part':'/word/document.xml','path':[{'kind':'body','element_index':1},{'kind':'paragraph','element_index':1}]})
        self.assertEqual(first['limits'],DEFAULTS)

    def test_valid_empty_body_blank_paragraph_and_raw_empty_are_distinct(self):
        for body in ['',paragraph(''),paragraph('')+paragraph('')]:self.assertEqual(self.read(package(body))['status'],'empty')
        self.assertEqual(self.read(b'')['status'],'malformed_docx')

    def test_input_types_names_and_limits_are_strict_and_not_mutated(self):
        data=package(paragraph('x'));limits={'max_rows':2};self.read(data,limits);self.assertEqual(limits,{'max_rows':2})
        cases=[(bytearray(data),'x.docx',None),(data,' ',None),(data,'a\x01.docx',None),(data,'x\ud800.docx',None),
               (data,'x.docx',[]),(data,'x.docx',{'bad':1}),(data,'x.docx',{'max_rows':True}),
               (data,'x.docx',{'max_rows':0}),(data,'x.docx',{'max_rows':10001}),(data,'x.docx',{'max_output_bytes':8191})]
        for payload,name,opts in cases:
            with self.subTest(name=repr(name),limits=opts),self.assertRaisesRegex(ValueError,'^reference_docx_invalid_argument$'):
                self.api.read_docx(payload,name,limits=opts)
        self.assertEqual(self.read(data,name='x.DOCX')['status'],'ok')
        self.assertEqual(self.read(data,name='x.docm')['status'],'unsupported_format')

    def test_breaks_tabs_and_spaces_without_fake_pages(self):
        body='<w:p><w:r><w:t xml:space="preserve"> a </w:t><w:tab/><w:br/><w:br w:type="page"/><w:br w:type="column"/><w:cr/></w:r></w:p>'
        value=self.read(package(body));p=value['blocks'][0]
        self.assertEqual(p['text'],' a \t\n\n\n\n')
        self.assertEqual(p['breaks'],[{'offset':4,'kind':'line'},{'offset':5,'kind':'page'},{'offset':6,'kind':'column'},{'offset':7,'kind':'line'}])
        self.assertNotIn('pages',value)

    def test_main_relationship_selects_nonstandard_part(self):
        value=self.read(package(paragraph('x'),main='custom/main.xml'))
        self.assertEqual(value['scope']['part'],'/custom/main.xml');self.assertEqual(value['blocks'][0]['locator']['part'],'/custom/main.xml')

    def test_mixed_blocks_nested_tables_and_element_child_locators(self):
        nested=table(['<w:tr>'+cell('nested')+'</w:tr>'],1)
        body=paragraph('before')+table(['<w:tr>'+cell(blocks=nested+paragraph('after'),properties='<w:gridSpan w:val="1"/>')+cell('')+'</w:tr>'])+paragraph('end')
        value=self.read(package(body));self.assertEqual([b['kind'] for b in value['blocks']],['paragraph','table','paragraph'])
        outer=value['blocks'][1];self.assertEqual(set(outer),{'kind','locator','grid_columns','rows'})
        row=outer['rows'][0];self.assertEqual(set(row),{'locator','grid_before','grid_after','cells'})
        c=row['cells'][0];self.assertEqual(set(c),{'locator','grid_start','grid_span','v_merge','merge_origin','blocks'})
        self.assertEqual([b['kind'] for b in c['blocks']],['table','paragraph'])
        self.assertEqual(c['blocks'][0]['locator']['path'][-1],{'kind':'table','element_index':2})
        self.assertEqual(outer['locator']['path'][-1]['element_index'],2)
        self.assertEqual(value['statistics']['cells'],3)
        self.assertEqual(value['text_sha256'],hashlib.sha256('before\nnested\nafter\n\nend'.encode()).hexdigest())

    def test_grid_span_vertical_merge_and_omitted_val(self):
        props='<w:gridSpan w:val="2"/><w:vMerge w:val="restart"/>'
        rows=['<w:tr>'+cell('origin',properties=props)+'</w:tr>',
              '<w:tr>'+cell('',properties='<w:gridSpan w:val="2"/><w:vMerge/>')+'</w:tr>']
        value=self.read(package(table(rows)));self.assertEqual(value['status'],'ok')
        a,b=[r['cells'][0] for r in value['blocks'][0]['rows']]
        self.assertEqual((a['grid_start'],a['grid_span'],a['v_merge']),(1,2,'restart'))
        self.assertEqual(a['merge_origin'],a['locator']);self.assertEqual(b['merge_origin'],a['locator'])
        self.assertEqual(b['blocks'][0]['text'],'');self.assertEqual(value['statistics']['cells'],2)

    def test_grid_omissions_and_legal_augmentation_or_orphan_are_partial(self):
        row='<w:tr><w:trPr><w:gridBefore w:val="1"/><w:gridAfter w:val="1"/></w:trPr>'+cell('x')+'</w:tr>'
        value=self.read(package(table([row],3)));r=value['blocks'][0]['rows'][0]
        self.assertEqual((r['grid_before'],r['grid_after'],r['cells'][0]['grid_start']),(1,1,2))
        value=self.read(package(table(['<w:tr>'+cell('x',properties='<w:gridSpan w:val="3"/>')+'</w:tr>'],1)))
        self.assertEqual(value['status'],'partial');self.assertIn('unsupported_grid_augmentation',self.codes(value))
        value=self.read(package(table(['<w:tr>'+cell('x',properties='<w:vMerge/>')+'</w:tr>'],1)))
        self.assertEqual(value['status'],'partial');self.assertIsNone(value['blocks'][0]['rows'][0]['cells'][0]['merge_origin'])

    def test_merge_mismatch_is_atomic_malformed(self):
        rows=['<w:tr>'+cell('x',properties='<w:gridSpan w:val="2"/><w:vMerge w:val="restart"/>')+'</w:tr>',
              '<w:tr>'+cell('',properties='<w:vMerge/>')+cell('')+'</w:tr>']
        value=self.read(package(table(rows)));self.assertEqual(value['status'],'malformed_docx')
        self.assertIn('invalid_merge',self.codes(value));self.assertEqual(value['blocks'],[])

    def test_I1_extra_styles_and_unknown_relationship_before_main_keep_body(self):
        extra=f'<Relationship Id="extra" Type="urn:unknown" Target="styles.xml"/>'
        data=package(paragraph('retained'),extras=[('styles.xml','not parsed')],root_extra=extra)
        value=self.read(data);self.assertEqual(value['status'],'partial');self.assertEqual(value['blocks'][0]['text'],'retained')
        self.assertIn('unsupported_part',self.codes(value));self.assertIn('unsupported_relationship',self.codes(value))

    def test_unknown_content_namespace_keeps_known_paragraphs(self):
        value=self.read(package(paragraph('a')+'<x:other xmlns:x="urn:unknown"/>'+paragraph('b')))
        self.assertEqual(value['status'],'partial');self.assertEqual([b['kind'] for b in value['blocks']],['paragraph','unsupported','paragraph'])
        self.assertEqual(value['blocks'][2]['locator']['path'][-1]['element_index'],3)

    def test_nonempty_properties_cached_breaks_and_MC_never_complete(self):
        for body in ['<w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr><w:r><w:t>x</w:t></w:r></w:p>',
                     '<w:p><w:r><w:t>x</w:t><w:lastRenderedPageBreak/></w:r></w:p>',
                     '<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"><mc:Fallback>'+paragraph('not chosen')+'</mc:Fallback></mc:AlternateContent>']:
            self.assertEqual(self.read(package(body))['status'],'partial')

    def test_fields_withhold_whole_paragraph_and_other_text_is_inert(self):
        body=paragraph('DO NOT EXECUTE')+'<w:p><w:r><w:t>prefix</w:t><w:fldChar w:fldCharType="begin"/><w:instrText>COMMAND</w:instrText><w:t>cache</w:t></w:r></w:p>'
        value=self.read(package(body));self.assertEqual(value['status'],'partial')
        self.assertEqual(value['blocks'][0]['text'],'DO NOT EXECUTE');self.assertEqual(value['blocks'][1]['text'],'')
        self.assertFalse(value['blocks'][1]['complete']);self.assertIn('unsupported_field',self.codes(value))

    def test_external_hyperlink_label_only_and_no_URL_in_DTO(self):
        rel=f'<Relationship Id="link" Type="{R}/hyperlink" Target="https://example.invalid/DO_NOT_EMIT" TargetMode="External"/>'
        value=self.read(package('<w:p><w:hyperlink r:id="link"><w:r><w:t>label</w:t></w:r></w:hyperlink></w:p>',relationships=rel))
        self.assertEqual(value['status'],'partial');self.assertEqual(value['blocks'][0]['text'],'label')
        self.assertNotIn('DO_NOT_EMIT',json.dumps(value));self.assertIn('external_relationship',self.codes(value))

    def test_required_hyperlink_target_missing_is_malformed(self):
        value=self.read(package('<w:p><w:hyperlink r:id="missing"><w:r><w:t>x</w:t></w:r></w:hyperlink></w:p>'))
        self.assertEqual(value['status'],'malformed_docx');self.assertIn('malformed_opc',self.codes(value))

    def test_strict_macro_CFB_and_wrong_main_shapes_not_success(self):
        strict=self.read(package(paragraph('x'),namespace='http://purl.oclc.org/ooxml/wordprocessingml/main'))
        self.assertEqual(strict['status'],'unsupported_format')
        self.assertEqual(self.read(package(content_type='application/vnd.ms-word.document.macroEnabled.main+xml'))['status'],'unsupported_format')
        cfb=self.read(bytes.fromhex('d0cf11e0a1b11ae1')+b'\0'*64)
        self.assertEqual(cfb['status'],'unsupported_format');self.assertIn('ole_container_unverified',self.codes(cfb))
        for xml in [f'<w:document xmlns:w="{W}"/>',f'<w:document xmlns:w="{W}"><w:body/><w:body/></w:document>','<broken>']:
            self.assertEqual(self.read(package(xml=xml))['status'],'malformed_docx')

    def test_declared_encryption_is_rejected_before_member_open(self):
        for flag in [1,65]:
            data=flagged(package(paragraph('x')),flag=flag)
            with mock.patch.object(self.api.zipfile.ZipFile,'open',side_effect=AssertionError('must not decrypt')) as opened:
                value=self.read(data)
            self.assertEqual(value['status'],'encrypted');opened.assert_not_called()

    def test_bad_zip_crc_unsafe_names_duplicates_and_symlink_are_not_success(self):
        self.assertEqual(self.read(b'notzip')['status'],'malformed_docx')
        self.assertEqual(self.read(flagged(package(paragraph('x')),crc=1))['status'],'malformed_docx')
        for name in ['../escape.xml','/absolute.xml','a\\b.xml','a/./b.xml','a%20b.xml']:
            value=self.read(package(extras=[(name,b'x')]))
            self.assertFalse(value['complete']);self.assertEqual(value['blocks'],[])
        with self.assertWarns(UserWarning):data=package(extras=[('word/document.xml',b'x')])
        self.assertEqual(self.read(data)['status'],'malformed_docx')
        stream=BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            entry=zipfile.ZipInfo('link');entry.create_system=3;entry.external_attr=0o120777<<16;archive.writestr(entry,b'target')
        self.assertEqual(self.read(stream.getvalue())['status'],'unsupported_format')

    def test_DTD_entities_PI_UTF16_are_rejected_before_expansion(self):
        for prefix in ['<!DOCTYPE w:document [<!ENTITY x "boom">]>', '<?instruction value?>']:
            xml=prefix+f'<w:document xmlns:w="{W}"><w:body>{paragraph("x")}</w:body></w:document>'
            for data in [xml.encode(),xml.encode('utf-16')]:
                value=self.read(package(xml=data));self.assertEqual(value['status'],'malformed_docx');self.assertIn('forbidden_xml',self.codes(value))

    def test_input_directory_member_declared_and_actual_expansion_limits(self):
        data=package(paragraph('x'))
        for opts in [{'max_input_bytes':len(data)-1},{'max_directory_bytes':1},{'max_member_bytes':1},
                     {'max_declared_uncompressed_bytes':1},{'max_expanded_bytes':1}]:
            value=self.read(data,opts);self.assertEqual(value['status'],'limit_exceeded');self.assertEqual(value['blocks'],[])
        self.assertEqual(self.read(data,{'max_input_bytes':len(data)})['status'],'ok')

    def test_member_count_preflight_before_ZipFile_constructor(self):
        data=package(paragraph('x'))
        with mock.patch.object(self.api.zipfile,'ZipFile',side_effect=AssertionError('constructor')) as ctor:
            value=self.read(data,{'max_zip_members':2})
        self.assertEqual(value['status'],'limit_exceeded');ctor.assert_not_called()

    def test_ratio_depth_element_and_character_budgets(self):
        data=package(paragraph('x'*4000),compression=zipfile.ZIP_DEFLATED)
        self.assertEqual(self.read(data,{'max_compression_ratio':1})['status'],'limit_exceeded')
        for opts in [{'max_xml_depth':1},{'max_xml_elements':1},{'max_xml_chars':1}]:
            self.assertEqual(self.read(package(paragraph('abc')),opts)['status'],'limit_exceeded')

    def test_structure_limits_and_lowered_exact_boundaries(self):
        data=package(paragraph('a')+paragraph('b'))
        self.assertEqual(self.read(data,{'max_blocks':2,'max_text_chars':3})['status'],'ok')
        for opts in [{'max_blocks':1},{'max_text_chars':2}]:self.assertEqual(self.read(data,opts)['status'],'limit_exceeded')
        rows=['<w:tr>'+cell('a')+cell('b')+'</w:tr>','<w:tr>'+cell('c')+'</w:tr>']
        data=package(table(rows))
        for opts in [{'max_rows':1},{'max_cells':1},{'max_grid_columns':1}]:self.assertEqual(self.read(data,opts)['status'],'limit_exceeded')
        nested=table(['<w:tr>'+cell(blocks=table(['<w:tr>'+cell('x')+'</w:tr>'],1))+'</w:tr>'],1)
        self.assertEqual(self.read(package(nested),{'max_table_depth':1})['status'],'limit_exceeded')

    def test_output_and_issue_limits_are_atomic_and_inside_themselves(self):
        value=self.read(package(paragraph('x'*8000)),{'max_output_bytes':8192})
        self.assertEqual(value['status'],'limit_exceeded');self.assertEqual(value['blocks'],[])
        self.assertEqual(value['statistics']['paragraphs'],0);self.assertEqual(value['text_sha256'],hashlib.sha256(b'').hexdigest())
        value=self.read(package(paragraph('x'),extras=[('one.xml',b'x'),('two.xml',b'x')]),{'max_issues':1})
        self.assertEqual(value['status'],'limit_exceeded');self.assertEqual(self.codes(value),{'issue_limit'})

    def test_no_files_network_subprocess_or_extraction_and_streams_closed(self):
        data=package(paragraph('inert'));opened=[];original=zipfile.ZipFile.open
        def track(archive,*args,**kwargs):
            stream=original(archive,*args,**kwargs);opened.append(stream);return stream
        with mock.patch('builtins.open',side_effect=AssertionError('filesystem')), \
             mock.patch('socket.create_connection',side_effect=AssertionError('network')), \
             mock.patch('subprocess.Popen',side_effect=AssertionError('process')), \
             mock.patch.object(zipfile.ZipFile,'extractall',side_effect=AssertionError('extract')), \
             mock.patch.object(zipfile.ZipFile,'open',track):
            self.assertEqual(self.read(data)['status'],'ok')
            self.assertEqual(self.read(data,{'max_xml_depth':1})['status'],'limit_exceeded')
        self.assertTrue(opened);self.assertTrue(all(stream.closed for stream in opened))

    def test_unexpected_exception_is_fixed_parser_error(self):
        data=package(paragraph('x'))
        with mock.patch.object(self.api.zipfile,'ZipFile',side_effect=RuntimeError('DO_NOT_EMIT')):
            value=self.read(data)
        self.assertEqual(value['status'],'parser_error');self.assertNotIn('DO_NOT_EMIT',json.dumps(value))

    def test_misplaced_known_text_elements_never_become_complete(self):
        for body in ['<w:p><w:r><w:p><w:r><w:t>x</w:t></w:r></w:p></w:r></w:p>',
                     '<w:p><w:r><w:r><w:t>x</w:t></w:r></w:r></w:p>']:
            value=self.read(package(body));self.assertFalse(value['complete'])

    def test_unknown_metadata_attributes_are_not_silent_complete(self):
        data=package(paragraph('x'));entries=[]
        with zipfile.ZipFile(BytesIO(data)) as archive:
            for info in archive.infolist():
                raw=archive.read(info)
                if info.filename=='_rels/.rels':raw=raw.replace(b'<Relationship Id=',b'<Relationship extra="unverified" Id=')
                entries.append((info.filename,raw))
        stream=BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            for name,raw in entries:archive.writestr(name,raw)
        value=self.read(stream.getvalue());self.assertEqual(value['status'],'partial')
        self.assertEqual(value['blocks'][0]['text'],'x')

    def test_multiple_trailing_slashes_are_not_canonical_directories(self):
        value=self.read(package(paragraph('x'),extras=[('folder///',b'')]))
        self.assertFalse(value['complete']);self.assertEqual(value['blocks'],[])

    def test_unknown_additional_relationship_namespace_keeps_body(self):
        extra='<x:Relationship xmlns:x="urn:unknown" Id="extra" Target="unknown" Type="urn:other"/>'
        value=self.read(package(paragraph('kept'),root_extra=extra))
        self.assertEqual(value['status'],'partial');self.assertEqual(value['blocks'][0]['text'],'kept')

    def test_UTF16_without_DTD_and_exact_XML_limits(self):
        xml=f'<w:document xmlns:w="{W}"><w:body>{paragraph("가")}</w:body></w:document>'.encode('utf-16')
        self.assertEqual(self.read(package(xml=xml))['status'],'ok')
        data=package(paragraph('abc'));base=self.read(data);elements=base['statistics']['xml_elements']
        self.assertEqual(self.read(data,{'max_xml_depth':5,'max_xml_elements':elements,'max_xml_chars':3})['status'],'ok')
        for limits in [{'max_xml_depth':4},{'max_xml_elements':elements-1},{'max_xml_chars':2}]:
            self.assertEqual(self.read(data,limits)['status'],'limit_exceeded')

    def test_exact_ZIP_byte_limits_and_plus_one(self):
        data=package(paragraph('abc'));sizes=[]
        with zipfile.ZipFile(BytesIO(data)) as archive:sizes=[item.file_size for item in archive.infolist()]
        end=data.rfind(b'PK\x05\x06');directory=struct.unpack_from('<I',data,end+12)[0]
        exact={'max_zip_members':3,'max_directory_bytes':directory,'max_member_bytes':max(sizes),
               'max_declared_uncompressed_bytes':sum(sizes),'max_expanded_bytes':sum(sizes),'max_compression_ratio':1}
        self.assertEqual(self.read(data,exact)['status'],'ok')
        for key in ['max_directory_bytes','max_member_bytes','max_declared_uncompressed_bytes','max_expanded_bytes']:
            self.assertEqual(self.read(data,{key:exact[key]-1})['status'],'limit_exceeded')

    def test_optional_metadata_bad_mode_does_not_silently_complete(self):
        kind='http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties'
        extra=f'<Relationship Id="meta" Type="{kind}" Target="docProps/core.xml" TargetMode="Unknown"/>'
        value=self.read(package(paragraph('kept'),root_extra=extra,extras=[('docProps/core.xml',b'unread')]))
        self.assertEqual(value['status'],'partial');self.assertEqual(value['blocks'][0]['text'],'kept')

    def test_unsupported_optional_hyperlink_URI_is_partial_not_main_fatal(self):
        rel=f'<Relationship Id="link" Type="{R}/hyperlink" Target="%6cabel.xml"/>'
        body='<w:p><w:hyperlink r:id="link"><w:r><w:t>kept</w:t></w:r></w:hyperlink></w:p>'
        value=self.read(package(body,relationships=rel))
        self.assertEqual(value['status'],'partial');self.assertEqual(value['blocks'][0]['text'],'kept')
        rel=f'<Relationship Id="link" Type="{R}/hyperlink" Target="missing.xml"/>'
        self.assertEqual(self.read(package(body,relationships=rel))['status'],'malformed_docx')

    def test_every_structure_locator_round_trips_to_original_DOM(self):
        body=paragraph('before')+table(['<w:tr>'+cell(blocks=table(['<w:tr>'+cell('nested')+'</w:tr>'],1),properties='<w:gridSpan w:val="2"/>')+'</w:tr>'])+paragraph('after')
        data=package(body);value=self.read(data)
        with zipfile.ZipFile(BytesIO(data)) as archive:dom=ET.fromstring(archive.read('word/document.xml'))
        expected={'body':'body','paragraph':'p','table':'tbl','row':'tr','cell':'tc'}
        def locate(locator):
            item=dom
            for step in locator['path']:
                item=list(item)[step['element_index']-1]
                self.assertEqual(item.tag,'{'+W+'}'+expected[step['kind']])
        def walk(blocks):
            for block in blocks:
                locate(block['locator'])
                if block['kind']=='table':
                    for row in block['rows']:
                        locate(row['locator'])
                        for c in row['cells']:locate(c['locator']);walk(c['blocks'])
        walk(value['blocks'])

    def test_fixed_seed_corruptions_return_bounded_failure_or_valid_result(self):
        import random
        randomizer=random.Random(20261025);data=package(paragraph('synthetic'))
        statuses={'ok','empty','partial','encrypted','unsupported_format','malformed_docx','limit_exceeded','parser_error'}
        for _ in range(80):
            value=bytearray(data);index=randomizer.randrange(len(value));value[index]^=randomizer.randrange(1,256)
            result=self.read(bytes(value));self.assertIn(result['status'],statuses)

    def test_nontext_container_unknown_content_never_silently_completes(self):
        grid=table(['<w:tr>'+cell('kept')+'</w:tr>'],1).replace('<w:tblGrid>','<w:tblGrid unknown="x">')
        cases=[package(grid),package(paragraph('kept'),root_extra='unknown text')]
        cases.append(replace_member(package(paragraph('kept')),'[Content_Types].xml',
                                    lambda raw: raw.replace(b'</Types>',b'unknown text</Types>')))
        for data in cases:
            with self.subTest(source=hashlib.sha256(data).hexdigest()):
                value=self.read(data);self.assertEqual(value['status'],'partial')
                self.assertIn('unsupported_property',self.codes(value))

    def test_property_containers_require_their_owner_and_unique_occurrence(self):
        bodies=['<w:tcPr/>'+paragraph('kept'),
                table(['<w:tr>'+cell(blocks='<w:sectPr/>'+paragraph('x'))+'</w:tr>'],1),
                '<w:p><w:pPr/><w:pPr/><w:r><w:t>x</w:t></w:r></w:p>',
                '<w:p><w:r><w:rPr/><w:rPr/><w:t>x</w:t></w:r></w:p>']
        for body in bodies:
            with self.subTest(body=body):
                value=self.read(package(body));self.assertEqual(value['status'],'malformed_docx')
                self.assertEqual(value['blocks'],[])

    def test_metadata_target_must_be_known_for_silent_exclusion(self):
        kind='http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties'
        for target in ['docProps/missing.xml','docProps/%63ore.xml']:
            extra=f'<Relationship Id="meta" Type="{kind}" Target="{target}"/>'
            value=self.read(package(paragraph('kept'),root_extra=extra))
            self.assertEqual(value['status'],'partial');self.assertEqual(value['blocks'][0]['text'],'kept')
        extra=f'<Relationship Id="meta" Type="{kind}" Target="docProps/core.xml"/>'
        value=self.read(package(paragraph('kept'),root_extra=extra,extras=[('docProps/core.xml',b'unread')]))
        self.assertEqual(value['status'],'ok');self.assertEqual(value['statistics']['read_members'],3)

    def test_invalid_deflate_payload_is_known_zip_corruption(self):
        data=bytearray(package(paragraph('x'),compression=zipfile.ZIP_DEFLATED))
        with zipfile.ZipFile(BytesIO(data)) as archive:
            info=archive.getinfo('word/document.xml');local=info.header_offset
        name_size,extra_size=struct.unpack_from('<HH',data,local+26)
        data[local+30+name_size+extra_size]=255
        value=self.read(bytes(data));self.assertEqual(value['status'],'malformed_docx')
        self.assertEqual(self.codes(value),{'malformed_zip'})

    def test_process_control_exceptions_are_not_converted_to_success(self):
        data=package(paragraph('x'))
        for failure in (MemoryError,KeyboardInterrupt,SystemExit):
            with mock.patch.object(self.api.zipfile,'ZipFile',side_effect=failure), self.assertRaises(failure):
                self.read(data)


if __name__ == '__main__':
    unittest.main()
