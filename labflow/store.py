from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':'))


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}',value):
        raise ValueError('Invalid identifier')
    return value


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self,root):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        (self.root/'blobs').mkdir(exist_ok=True)
        self.db=self.root/'lab.sqlite3'
        with self.connection() as con:
            con.executescript(Path(__file__).with_name('schema.sql').read_text())

    @contextmanager
    def connection(self):
        con=sqlite3.connect(self.db,timeout=30)
        con.row_factory=sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        try:
            with con:yield con
        finally:con.close()

    def event(self,con,action,subject,details):
        con.execute('INSERT INTO events(created_at,action,subject_id,details_json) VALUES(?,?,?,?)',
                    (utcnow(),action,subject,canonical(details)))

    def blob_path(self,sha):
        if not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha):raise ValueError('Invalid SHA256')
        return self.root/'blobs'/sha

    def verify_blob(self,sha):
        path=self.blob_path(sha)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
            raise ValueError('Missing or corrupted evidence: '+sha)
        return path

    def write_blob(self,payload):
        sha=hashlib.sha256(payload).hexdigest();path=self.blob_path(sha)
        try:
            with path.open('xb') as stream:stream.write(payload)
        except FileExistsError:self.verify_blob(sha)
        return sha

    def import_artifact(self,path,kind='raw'):
        path=Path(path)
        if not path.is_file() or path.stat().st_size>536870912:raise ValueError('Missing or oversized artifact')
        payload=path.read_bytes()
        if not payload:raise ValueError('Empty artifact')
        sha=self.write_blob(payload)
        with self.connection() as con:
            con.execute('INSERT OR IGNORE INTO blobs VALUES(?,?,?)',(sha,len(payload),kind))
            self.event(con,'artifact.import',sha,{'kind':kind})
        return sha

    def document(self,document_id):
        with self.connection() as con:
            row=con.execute('SELECT * FROM documents WHERE document_id=?',(document_id,)).fetchone()
        if row is None:raise ValueError('Unknown document: '+str(document_id))
        return {**json.loads(row['record_json']),'sha256':row['sha256'],'review_status':row['review_status'],'synthetic':bool(row['synthetic'])}

    def documents(self):
        with self.connection() as con:ids=[r[0] for r in con.execute('SELECT document_id FROM documents ORDER BY document_id')]
        return [self.document(i) for i in ids]

    def review_document(self,document_id,reviewer,note):
        if not str(reviewer).strip() or not str(note).strip():raise ValueError('Reviewer and technical review note required')
        doc=self.document(document_id)
        if doc['status']!='downloaded' or doc['representation']!='original' or doc['rights'] not in {'public','licensed_internal'}:
            raise ValueError('Only an acquired original with known usable rights can be reviewed')
        self.verify_blob(doc['sha256'])
        with self.connection() as con:
            con.execute("UPDATE documents SET review_status='reviewed' WHERE document_id=?",(document_id,))
            self.event(con,'document.review',document_id,{'reviewer':reviewer,'note':note})
        return self.document(document_id)

    def row(self,table,key):
        keys={'cases':'case_id','methods':'method_id','plans':'plan_id','runs':'run_id'}
        if table not in keys:raise ValueError('Unknown entity')
        with self.connection() as con:row=con.execute(f'SELECT * FROM {table} WHERE {keys[table]}=?',(key,)).fetchone()
        if row is None:raise ValueError(f'Unknown {table}: {key}')
        return {**dict(row),'data':json.loads(row['data_json'])}
