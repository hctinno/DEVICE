"""Bounded stored-body DOCX reader; no files, Office, links or intake writes."""
from hashlib import sha256
from io import BytesIO
import json
import re
import stat
import struct
import zipfile
import zlib
from xml.parsers import expat


_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_REL = 'http://schemas.openxmlformats.org/package/2006/relationships}'
_CT = 'http://schemas.openxmlformats.org/package/2006/content-types}'
_XML = 'http://www.w3.org/XML/1998/namespace}'
_MAIN_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
_DEFAULTS = {
    'max_input_bytes':16777216, 'max_zip_members':1024, 'max_directory_bytes':4194304,
    'max_declared_uncompressed_bytes':67108864, 'max_member_bytes':8388608,
    'max_expanded_bytes':16777216, 'max_compression_ratio':1000,
    'max_xml_depth':64, 'max_xml_elements':200000, 'max_xml_chars':2000000,
    'max_table_depth':8, 'max_blocks':20000, 'max_rows':10000, 'max_cells':50000,
    'max_grid_columns':256, 'max_text_chars':1000000, 'max_output_bytes':8388608,
    'max_issues':128,
}
_META_TYPES = {
    'http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties':'docProps/core.xml',
    _R + '/extended-properties':'docProps/app.xml',
}
_META = set(_META_TYPES.values())
_FIELDS = {_W + name for name in ('fldSimple','fldChar','instrText')}


class _Abort(Exception):
    def __init__(self, status, code, locator=None):
        self.status, self.code, self.locator = status, code, locator


def _stop(status, code, locator=None):
    raise _Abort(status, code, locator)


def _bad(code='malformed_opc', locator=None):
    _stop('malformed_docx', code, locator)


def _hash(raw):
    return sha256(raw).hexdigest()


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _limits(options):
    if options is None:
        return dict(_DEFAULTS)
    if type(options) is not dict:
        raise ValueError('reference_docx_invalid_argument')
    for key, value in options.items():
        if (type(key) is not str or key not in _DEFAULTS or type(value) is not int
                or not (8192 if key == 'max_output_bytes' else 1) <= value <= _DEFAULTS[key]):
            raise ValueError('reference_docx_invalid_argument')
    return {**_DEFAULTS, **options}


def _member(name):
    if (not name or name.startswith('/') or '\\' in name or ':' in name
            or any(ord(c) < 32 or ord(c) == 127 for c in name)):
        _bad()
    if len(name.encode('utf-8')) > 1024:
        _stop('unsupported_format', 'unsupported_package')
    parts = (name[:-1] if name.endswith('/') else name).split('/')
    if any(part in {'', '.', '..'} for part in parts):
        _bad()
    if name != '[Content_Types].xml' and any(re.fullmatch(r'[A-Za-z0-9_.-]+', part) is None for part in parts):
        _stop('unsupported_format', 'unsupported_package')
    return name


def _target(source, target):
    if (type(target) is not str or not target or any(c in target for c in '\\?#')
            or re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target)):
        _stop('unsupported_format', 'unsupported_package')
    value = target[1:] if target.startswith('/') else (source.rpartition('/')[0] + '/' if '/' in source else '') + target
    return _member(value)


def _directory(data, limits):
    """Count bounded central records before ZipFile can construct ZipInfo objects."""
    if data[:4] not in {b'PK\x03\x04', b'PK\x05\x06'}:
        _bad('malformed_zip')
    found = None
    position = len(data)
    while True:
        position = data.rfind(b'PK\x05\x06', max(0, len(data)-65557), position)
        if position < 0:
            break
        if position+22 <= len(data):
            fields = struct.unpack_from('<4s4H2IH', data, position)
            if position+22+fields[7] == len(data):
                found = fields
                break
    if found is None:
        _bad('malformed_zip')
    _, disk, central_disk, on_disk, count, size, offset, _ = found
    if (disk or central_disk or on_disk != count or count == 65535
            or size == 0xffffffff or offset == 0xffffffff
            or data[max(0,position-20):position-16] == b'PK\x06\x07'):
        _stop('unsupported_format', 'unsupported_package')
    if count > limits['max_zip_members'] or size > limits['max_directory_bytes']:
        _stop('limit_exceeded', 'zip_limit')
    if offset+size != position or offset > len(data):
        _bad('malformed_zip')
    entries, folded, expanded = {}, set(), 0
    cursor = offset
    encrypted = False
    while cursor < position:
        if len(entries) >= limits['max_zip_members']:
            _stop('limit_exceeded', 'zip_limit')
        if cursor+46 > position:
            _bad('malformed_zip')
        item = struct.unpack_from('<4s6H3I5H2I', data, cursor)
        if item[0] != b'PK\x01\x02':
            _bad('malformed_zip')
        flags, method, crc, compressed, length = item[3], item[4], item[7], item[8], item[9]
        name_size, extra_size, comment_size = item[10:13]
        end = cursor+46+name_size+extra_size+comment_size
        if end > position or not name_size:
            _bad('malformed_zip')
        raw_name = data[cursor+46:cursor+46+name_size]
        try:
            name = raw_name.decode('utf-8' if flags & 2048 else 'cp437')
        except UnicodeError:
            _bad('malformed_zip')
        _member(name)
        if name in entries:
            _bad()
        if name.casefold() in folded:
            _stop('unsupported_format', 'unsupported_package')
        folded.add(name.casefold())
        if (item[13] or compressed == 0xffffffff or length == 0xffffffff
                or item[16] == 0xffffffff or method not in {0, 8}
                or flags & ~0x084f or flags & 64 and not flags & 1
                or stat.S_IFMT(item[15] >> 16) == stat.S_IFLNK):
            _stop('unsupported_format', 'unsupported_package')
        extra = cursor+46+name_size
        while extra < cursor+46+name_size+extra_size:
            if extra+4 > cursor+46+name_size+extra_size:
                _bad('malformed_zip')
            kind, amount = struct.unpack_from('<HH', data, extra)
            if kind == 1:
                _stop('unsupported_format', 'unsupported_package')
            extra += 4+amount
            if extra > cursor+46+name_size+extra_size:
                _bad('malformed_zip')
        expanded += length
        if name.endswith('/') and length:
            _bad('malformed_zip')
        if (length > limits['max_member_bytes'] or expanded > limits['max_declared_uncompressed_bytes']
                or length > limits['max_compression_ratio'] * max(1, compressed)):
            _stop('limit_exceeded', 'zip_limit')
        local = item[16]
        if local+30 > offset or data[local:local+4] != b'PK\x03\x04':
            _bad('malformed_zip')
        header = struct.unpack_from('<4s5H3I2H', data, local)
        begin = local+30+header[9]+header[10]
        if (header[2] != flags or header[3] != method or begin+compressed > offset
                or data[local+30:local+30+header[9]] != raw_name):
            _bad('malformed_zip')
        if not flags & 8 and header[6:9] != (crc, compressed, length):
            _bad('malformed_zip')
        entries[name] = (length, compressed, flags, method)
        encrypted |= bool(flags & 1)
        cursor = end
    if len(entries) != count:
        _bad('malformed_zip')
    if encrypted:
        _stop('encrypted', 'encrypted_zip')
    return entries


class _Node:
    __slots__ = ('tag', 'attrs', 'children', 'text', 'index')

    def __init__(self, tag, attrs, index):
        self.tag, self.attrs, self.index = tag, attrs, index
        self.children, self.text = [], []


class _Reader:
    def __init__(self, data, name, limits):
        self.data, self.limits = data, limits
        self.result = {
            'schema_version':1,
            'source':{'filename':name, 'sha256':_hash(data), 'size_bytes':len(data)},
            'reader':{'name':'reference_docx', 'version':'1'},
            'status':'parser_error', 'complete':False,
            'scope':{'profile':'wordprocessingml-transitional-body-v1', 'part':None,
                     'page_numbers':'unavailable'},
            'limits':dict(limits), 'blocks':[], 'text_sha256':_hash(b''), 'issues':[],
            'statistics':{'zip_members':None, 'read_members':0, 'expanded_bytes':0,
                          'xml_elements':0, 'blocks':0, 'paragraphs':0, 'tables':0,
                          'rows':0, 'cells':0, 'text_chars':0},
        }
        self.stats = self.result['statistics']
        self.xml_chars = 0
        self.texts = []
        self.issue_map, self.pending = {}, {}
        self.problems = 0
        self.main = None
        self.rels, self.rels_known = {}, True

    def issue(self, code, locator=None, *, part=None, occurrences=1):
        part = part if part is not None else locator['part'] if locator is not None else self.result['scope']['part']
        key = code, part
        if key not in self.issue_map:
            if len(self.issue_map) >= self.limits['max_issues']:
                _stop('limit_exceeded', 'issue_limit')
            item = {'code':code, 'locator':locator, 'occurrences':0}
            self.issue_map[key] = item
            self.result['issues'].append(item)
        self.issue_map[key]['occurrences'] += occurrences
        self.problems += occurrences

    def defer(self, code, part):
        key = part, code
        self.pending[key] = self.pending.get(key, 0)+1

    def tick(self, name, amount=1):
        # Paragraph/table counts share the already-enforced block budget.
        if name in {'paragraphs', 'tables'}:
            self.stats[name] += amount
            return
        if self.stats[name]+amount > self.limits['max_'+name]:
            _stop('limit_exceeded', 'structure_limit')
        self.stats[name] += amount

    def read_xml(self, part):
        if part not in self.entries or part.endswith('/'):
            _bad()
        self.stats['read_members'] += 1
        chunks, count = [], 0
        with self.archive.open(part, 'r') as stream:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                count += len(chunk)
                self.stats['expanded_bytes'] += len(chunk)
                if count > self.limits['max_member_bytes'] or self.stats['expanded_bytes'] > self.limits['max_expanded_bytes']:
                    _stop('limit_exceeded', 'zip_limit')
                chunks.append(chunk)
        if count != self.entries[part][0]:
            _bad('malformed_zip')
        return self.xml(b''.join(chunks))

    def xml(self, raw):
        parser = expat.ParserCreate(namespace_separator='}')
        stack, roots = [], []
        def forbidden(*args):
            _bad('forbidden_xml')
        def start(tag, attrs):
            if len(stack)+1 > self.limits['max_xml_depth'] or self.stats['xml_elements']+1 > self.limits['max_xml_elements']:
                _stop('limit_exceeded', 'xml_limit')
            self.stats['xml_elements'] += 1
            node = _Node(tag, attrs, len(stack[-1].children)+1 if stack else 1)
            (stack[-1].children if stack else roots).append(node)
            stack.append(node)
        def characters(value):
            self.xml_chars += len(value)
            if self.xml_chars > self.limits['max_xml_chars']:
                _stop('limit_exceeded', 'xml_limit')
            if stack:
                stack[-1].text.append(value)
        parser.StartElementHandler, parser.EndElementHandler = start, lambda tag: stack.pop()
        parser.CharacterDataHandler = characters
        parser.StartDoctypeDeclHandler = forbidden
        parser.EntityDeclHandler = forbidden
        parser.ExternalEntityRefHandler = forbidden
        parser.ProcessingInstructionHandler = forbidden
        parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
        try:
            parser.Parse(raw, True)
        except expat.ExpatError:
            _bad('malformed_xml')
        if len(roots) != 1:
            _bad('malformed_xml')
        return roots[0]

    def content_types(self):
        node = self.read_xml('[Content_Types].xml')
        if node.tag != _CT+'Types':
            _stop('unsupported_format', 'unsupported_namespace')
        if node.attrs or any(text.strip() for text in node.text):
            self.defer('unsupported_property','[Content_Types].xml')
        defaults, overrides = {}, {}
        for child in node.children:
            if child.tag == _CT+'Default':
                if set(child.attrs)-{'Extension','ContentType'} or child.children or any(t.strip() for t in child.text):
                    self.defer('unsupported_property','[Content_Types].xml')
                ext, kind = child.attrs.get('Extension'), child.attrs.get('ContentType')
                if not ext or not kind or ext.casefold() in defaults:
                    _bad()
                defaults[ext.casefold()] = kind
            elif child.tag == _CT+'Override':
                if set(child.attrs)-{'PartName','ContentType'} or child.children or any(t.strip() for t in child.text):
                    self.defer('unsupported_property','[Content_Types].xml')
                part, kind = child.attrs.get('PartName'), child.attrs.get('ContentType')
                if not part or not part.startswith('/') or not kind:
                    _bad()
                part = _target('', part)
                if part in overrides:
                    _bad()
                overrides[part] = kind
            else:
                self.defer('unsupported_property', '[Content_Types].xml')
        return defaults, overrides

    def relationships(self, part, *, required=False):
        node = self.read_xml(part)
        if node.tag != _REL+'Relationships':
            if required:
                _stop('unsupported_format', 'unsupported_namespace')
            self.defer('unsupported_relationship', part)
            return {}, False
        if node.attrs or any(text.strip() for text in node.text):
            self.defer('unsupported_property',part)
        result = {}
        for child in node.children:
            if child.tag != _REL+'Relationship':
                self.defer('unsupported_relationship', part)
                continue
            if set(child.attrs)-{'Id','Type','Target','TargetMode'} or child.children or any(t.strip() for t in child.text):
                self.defer('unsupported_property',part)
            identity, kind, target = (child.attrs.get(key) for key in ('Id','Type','Target'))
            if not identity or not kind or not target or identity in result:
                _bad()
            result[identity] = (kind, target, child.attrs.get('TargetMode', 'Internal'))
        return result, True

    def location(self, node, kind, parent=None):
        return {'part':'/'+self.main, 'path':([] if parent is None else parent['path'])+
                [{'kind':kind, 'element_index':node.index}]}

    def properties(self, node, loc, *, attrs=(), children=()):
        if any(key not in attrs for key in node.attrs) or any(text.strip() for text in node.text):
            self.issue('unsupported_property', loc)
        for child in node.children:
            if child.tag not in children:
                self.issue('unsupported_merge' if child.tag in {_W+'hMerge',_W+'bidiVisual'} else 'unsupported_property', loc)

    def one(self, node, local, *, code='malformed_xml'):
        values = [child for child in node.children if child.tag == _W+local]
        if len(values) > 1:
            _bad(code)
        return values[0] if values else None

    def number(self, node, loc, *, default=0, minimum=0, code='malformed_xml'):
        if node is None:
            return default
        self.properties(node, loc, attrs=(_W+'val',))
        value = node.attrs.get(_W+'val')
        if value is None or re.fullmatch(r'\+?[0-9]+', value) is None:
            _bad(code, loc)
        literal = value.lstrip('+').lstrip('0') or '0'
        cap = self.limits['max_grid_columns']
        if len(literal) > len(str(cap)) or int(literal) > cap:
            _stop('limit_exceeded', 'structure_limit', loc)
        number = int(literal)
        if number < minimum:
            _bad(code, loc)
        return number

    def paragraph(self, node, parent):
        self.tick('blocks'); self.tick('paragraphs')
        loc = self.location(node, 'paragraph', parent)
        initial = self.problems
        stack, field = [node], False
        while stack:
            item = stack.pop()
            field |= item.tag in _FIELDS
            stack.extend(item.children)
        parts, breaks = [], []
        length = 0
        def append(value, kind=None):
            nonlocal length
            if kind is not None:
                breaks.append({'offset':length, 'kind':kind})
            parts.append(value); length += len(value)
            if self.stats['text_chars']+length+(1 if self.texts else 0) > self.limits['max_text_chars']:
                _stop('limit_exceeded', 'text_limit', loc)
        def visit(item):
            if item.tag in {_W+'p',_W+'r'}:
                if item.tag == _W+'p' and item is not node:
                    _bad('malformed_xml',loc)
                self.one(item,'pPr' if item.tag == _W+'p' else 'rPr')
                self.properties(item, loc, children=tuple(child.tag for child in item.children))
                allowed = ({_W+'pPr',_W+'r',_W+'hyperlink'} if item.tag == _W+'p' else
                           {_W+'rPr',_W+'t',_W+'tab',_W+'cr',_W+'br'})
                for child in item.children:
                    if child.tag in allowed:
                        visit(child)
                    elif child.tag in {_W+'p',_W+'r',_W+'t',_W+'tab',_W+'cr',_W+'br',_W+'pPr',_W+'rPr',_W+'hyperlink'}:
                        _bad('malformed_xml',loc)
                    else:
                        self.issue('unsupported_markup',loc)
            elif item.tag in {_W+'pPr',_W+'rPr'}:
                self.properties(item, loc)
            elif item.tag == _W+'hyperlink':
                self.properties(item, loc, attrs=(_R+'}id',_W+'anchor'), children=tuple(child.tag for child in item.children))
                identity = item.attrs.get(_R+'}id')
                if identity is not None:
                    if not self.rels_known:
                        self.issue('unsupported_relationship', loc)
                    elif identity not in self.rels:
                        _bad('malformed_opc', loc)
                    else:
                        kind, target, mode = self.rels[identity]
                        if kind != _R+'/hyperlink' or mode not in {'Internal','External'}:
                            self.issue('unsupported_relationship', loc)
                        elif mode == 'Internal':
                            try:
                                part = _target(self.main,target)
                            except _Abort as failure:
                                if failure.status != 'unsupported_format':
                                    raise
                                self.issue('unsupported_relationship', loc)
                            else:
                                if part not in self.entries:
                                    _bad('malformed_opc', loc)
                for child in item.children:
                    if child.tag == _W+'r':
                        visit(child)
                    else:
                        self.issue('unsupported_markup',loc)
            elif item.tag == _W+'t':
                if item.children:
                    _bad('malformed_xml', loc)
                if any(key != _XML+'space' for key in item.attrs):
                    self.issue('unsupported_property', loc)
                if item.attrs.get(_XML+'space','default') not in {'default','preserve'}:
                    _bad('malformed_xml', loc)
                append(''.join(item.text))
            elif item.tag in {_W+'tab',_W+'cr',_W+'br'}:
                self.properties(item, loc, attrs=(_W+'type',) if item.tag == _W+'br' else ())
                if item.tag == _W+'tab':
                    append('\t')
                else:
                    kind = item.attrs.get(_W+'type','textWrapping')
                    if kind not in {'textWrapping','page','column'}:
                        _bad('malformed_xml', loc)
                    append('\n', 'line' if kind == 'textWrapping' else kind)
            else:
                self.issue('unsupported_markup', loc)
        if field:
            self.issue('unsupported_field', loc)
        else:
            visit(node)
        text = ''.join(parts)
        self.stats['text_chars'] += len(text)+(1 if self.texts else 0)
        if self.stats['text_chars'] > self.limits['max_text_chars']:
            _stop('limit_exceeded', 'text_limit', loc)
        self.texts.append(text)
        return {'kind':'paragraph','locator':loc,'text':text,'text_sha256':_hash(text.encode('utf-8')),
                'complete':self.problems == initial,'breaks':breaks}

    def blocks(self, node, parent, depth):
        result = []
        for child in node.children:
            if child.tag == _W+'p':
                result.append(self.paragraph(child, parent))
            elif child.tag == _W+'tbl':
                result.append(self.table(child, parent, depth+1))
            elif child.tag in {_W+'tcPr',_W+'sectPr'}:
                if (child.tag == _W+'tcPr' and node.tag != _W+'tc'
                        or child.tag == _W+'sectPr' and node.tag != _W+'body'):
                    _bad('malformed_xml', self.location(child,'unsupported',parent))
                if child.tag == _W+'sectPr':
                    self.properties(child, self.location(child,'unsupported',parent))
            else:
                self.tick('blocks')
                loc = self.location(child,'unsupported',parent)
                self.issue('unsupported_markup', loc)
                result.append({'kind':'unsupported','locator':loc,'reason':'unsupported_markup'})
        return result

    def table(self, node, parent, depth):
        if depth > self.limits['max_table_depth']:
            _stop('limit_exceeded', 'structure_limit')
        self.tick('blocks'); self.tick('tables')
        loc = self.location(node,'table',parent)
        self.properties(node,loc,children=tuple(child.tag for child in node.children))
        props, grid = self.one(node,'tblPr'), self.one(node,'tblGrid')
        if props is not None:
            self.properties(props,loc)
        columns = None
        if grid is None:
            self.issue('unsupported_merge',loc)
        else:
            columns = 0
            self.properties(grid,loc,children=tuple(child.tag for child in grid.children))
            for child in grid.children:
                if child.tag == _W+'gridCol':
                    columns += 1; self.properties(child,loc)
                else:
                    self.issue('unsupported_property',loc)
            if columns > self.limits['max_grid_columns']:
                _stop('limit_exceeded', 'structure_limit',loc)
        rows, active = [], {}
        for row in node.children:
            if row.tag in {_W+'tblPr',_W+'tblGrid'}:
                continue
            if row.tag != _W+'tr':
                self.issue('unsupported_markup',self.location(row,'unsupported',loc)); continue
            self.tick('rows'); rowloc = self.location(row,'row',loc)
            self.properties(row,rowloc,children=tuple(child.tag for child in row.children))
            rowprops = self.one(row,'trPr')
            if rowprops is not None:
                self.properties(rowprops,rowloc,children=(_W+'gridBefore',_W+'gridAfter'))
            before = self.number(self.one(rowprops,'gridBefore') if rowprops is not None else None,rowloc)
            after = self.number(self.one(rowprops,'gridAfter') if rowprops is not None else None,rowloc)
            cells, following, start = [], {}, before+1
            for child in row.children:
                if child.tag == _W+'trPr':
                    continue
                if child.tag != _W+'tc':
                    self.issue('unsupported_markup',self.location(child,'unsupported',rowloc)); continue
                self.tick('cells'); cellloc = self.location(child,'cell',rowloc)
                self.properties(child,cellloc,children=tuple(item.tag for item in child.children))
                cp = self.one(child,'tcPr',code='invalid_merge')
                if cp is not None:
                    self.properties(cp,cellloc,children=(_W+'gridSpan',_W+'vMerge'))
                span = self.number(self.one(cp,'gridSpan',code='invalid_merge') if cp is not None else None,
                                   cellloc,default=1,minimum=1,code='invalid_merge')
                if start+span-1 > self.limits['max_grid_columns']:
                    _stop('limit_exceeded','structure_limit',cellloc)
                merge = self.one(cp,'vMerge',code='invalid_merge') if cp is not None else None
                mode, origin = 'none', None
                key = start, span
                if merge is not None:
                    self.properties(merge,cellloc,attrs=(_W+'val',))
                    mode = merge.attrs.get(_W+'val','continue')
                    if mode not in {'restart','continue'}:
                        _bad('invalid_merge',cellloc)
                    if mode == 'restart':
                        origin = cellloc
                    elif key in active:
                        origin = active[key]
                    elif any(start < other+amount and other < start+span for other,amount in active):
                        _bad('invalid_merge',cellloc)
                    else:
                        self.issue('unsupported_merge',cellloc)
                    if origin is not None:
                        following[key] = origin
                blocks = self.blocks(child,cellloc,depth)
                cells.append({'locator':cellloc,'grid_start':start,'grid_span':span,
                              'v_merge':mode,'merge_origin':origin,'blocks':blocks})
                start += span
            used = start-1+after
            if used > self.limits['max_grid_columns']:
                _stop('limit_exceeded','structure_limit',rowloc)
            if columns is not None and used > columns:
                self.issue('unsupported_grid_augmentation',rowloc)
            rows.append({'locator':rowloc,'grid_before':before,'grid_after':after,'cells':cells})
            active = following
        return {'kind':'table','locator':loc,'grid_columns':columns,'rows':rows}

    def run(self):
        if len(self.data) > self.limits['max_input_bytes']:
            _stop('limit_exceeded','input_limit')
        if not self.result['source']['filename'].lower().endswith('.docx'):
            _stop('unsupported_format','unsupported_format')
        if self.data.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
            _stop('unsupported_format','ole_container_unverified')
        self.entries = _directory(self.data,self.limits)
        self.stats['zip_members'] = len(self.entries)
        with BytesIO(self.data) as buffer, zipfile.ZipFile(buffer) as archive:
            self.archive = archive
            if len(archive.infolist()) != len(self.entries):
                _bad('malformed_zip')
            defaults, overrides = self.content_types()
            roots, _ = self.relationships('_rels/.rels',required=True)
            candidates = [rel for rel in roots.values() if rel[0] == _R+'/officeDocument']
            if len(candidates) != 1:
                if not candidates and any(rel[0] not in _META_TYPES for rel in roots.values()):
                    _stop('unsupported_format','unsupported_package')
                _bad()
            _, target, mode = candidates[0]
            if mode != 'Internal':
                _bad()
            self.main = _target('',target)
            if self.main not in self.entries:
                _bad()
            self.result['scope']['part'] = '/'+self.main
            kind = overrides.get(self.main,defaults.get(self.main.rpartition('.')[2].casefold()))
            if kind != _MAIN_TYPE:
                _stop('unsupported_format','unsupported_package')
            document = self.read_xml(self.main)
            if document.tag != _W+'document':
                if not document.tag.startswith(_W):
                    _stop('unsupported_format','unsupported_namespace')
                _bad('malformed_xml')
            bodies = [child for child in document.children if child.tag == _W+'body']
            if len(bodies) != 1:
                _bad()
            body = bodies[0]
            parent, _, leaf = self.main.rpartition('/')
            relpart = (parent+'/' if parent else '')+'_rels/'+leaf+'.rels'
            if relpart in self.entries:
                self.rels, self.rels_known = self.relationships(relpart)
            allowed = {'[Content_Types].xml','_rels/.rels',self.main,relpart} | _META
            for part in sorted(self.entries):
                if part not in allowed and not part.endswith('/'):
                    self.defer('unsupported_part',part)
            for identity, (kind,target,mode) in roots.items():
                if kind == _R+'/officeDocument':
                    continue
                if mode == 'External':
                    self.defer('external_relationship','_rels/.rels')
                elif mode != 'Internal' or kind not in _META_TYPES:
                    self.defer('unsupported_relationship','_rels/.rels')
                else:
                    try:
                        metadata = _target('',target)
                    except _Abort as failure:
                        if failure.status != 'unsupported_format':
                            raise
                        self.defer('unsupported_relationship','_rels/.rels')
                    else:
                        if metadata != _META_TYPES[kind] or metadata not in self.entries:
                            self.defer('unsupported_relationship','_rels/.rels')
            for kind,target,mode in self.rels.values():
                if mode == 'External':
                    self.defer('external_relationship',relpart)
                elif mode != 'Internal' or kind != _R+'/hyperlink':
                    self.defer('unsupported_relationship',relpart)
            for (part,code), count in sorted(self.pending.items()):
                self.issue(code,part=part,occurrences=count)
            bodyloc = self.location(body,'body')
            self.properties(document,bodyloc,children=(_W+'body',))
            self.properties(body,bodyloc,children=tuple(child.tag for child in body.children))
            self.result['blocks'] = self.blocks(body,bodyloc,0)
        self.result['text_sha256'] = _hash('\n'.join(self.texts).encode('utf-8'))
        self.result['status'] = 'partial' if self.result['issues'] else 'ok' if any(self.texts) else 'empty'
        self.result['complete'] = self.result['status'] in {'ok','empty'}
        if len(_encoded(self.result)) > self.limits['max_output_bytes']:
            _stop('limit_exceeded','output_limit')
        return self.result

    def failure(self, failure):
        self.result.update(status=failure.status,complete=False,blocks=[],text_sha256=_hash(b''),
                           issues=[{'code':failure.code,'locator':failure.locator,'occurrences':1}])
        for key in ('blocks','paragraphs','tables','rows','cells','text_chars'):
            self.stats[key] = 0
        if len(_encoded(self.result)) > self.limits['max_output_bytes']:
            self.result['issues'] = [{'code':'output_limit','locator':None,'occurrences':1}]
            self.result['status'] = 'limit_exceeded'
        return self.result


def read_docx(data: bytes, name: str, *, limits=None) -> dict:
    """Return bounded stored text/table evidence; source bytes remain caller-owned."""
    if (type(data) is not bytes or type(name) is not str or not name.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in name)):
        raise ValueError('reference_docx_invalid_argument')
    try:
        if len(name.encode('utf-8')) > 1024:
            raise ValueError('reference_docx_invalid_argument')
    except UnicodeError:
        raise ValueError('reference_docx_invalid_argument') from None
    reader = _Reader(data,name,_limits(limits))
    try:
        return reader.run()
    except _Abort as failure:
        return reader.failure(failure)
    except (MemoryError,KeyboardInterrupt,SystemExit):
        raise
    except (zipfile.BadZipFile,EOFError,struct.error,UnicodeError,zlib.error):
        return reader.failure(_Abort('malformed_docx','malformed_zip'))
    except Exception:
        return reader.failure(_Abort('parser_error','parser_error'))
