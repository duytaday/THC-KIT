"""Content-addressed originals and independent lifecycle facts, outside Git."""
import contextlib,hashlib,json,sqlite3,threading,time,uuid
from pathlib import Path

STATES=('downloaded','verified','indexed','edit_ready','training_example_ready','human_approved')

class Store:
    def __init__(self,root):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        for name in ('originals','partial','quarantine','derived','http-cache','datasets','models'): (self.root/name).mkdir(exist_ok=True)
        self.lock=threading.RLock();self.db=sqlite3.connect(self.root/'assets.sqlite3',timeout=60,check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, provider TEXT NOT NULL, provider_id TEXT NOT NULL, cluster TEXT, verified INTEGER NOT NULL DEFAULT0, indexed INTEGER NOT NULL DEFAULT0, updated REAL NOT NULL, document TEXT NOT NULL, UNIQUE(provider,provider_id));
CREATE TABLE IF NOT EXISTS discovery(query TEXT NOT NULL,category TEXT NOT NULL,offset INTEGER NOT NULL,finished INTEGER NOT NULL,updated REAL NOT NULL,PRIMARY KEY(query,category));
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,time REAL NOT NULL,asset TEXT,kind TEXT NOT NULL,document TEXT NOT NULL);'''.replace('DEFAULT0','DEFAULT 0'))
        self.db.commit()

    def close(self):self.db.close()

    def get(self,key):
        with self.lock:
            row=self.db.execute('SELECT document FROM assets WHERE id=?',(key,)).fetchone()
            return json.loads(row[0]) if row else None

    def rows(self):
        with self.lock:return [json.loads(r[0]) for r in self.db.execute('SELECT document FROM assets ORDER BY id')]

    def put(self,record,commit=True):
        with self.lock:
            record=dict(record,updated_at=time.time());st=record.get('states',{})
            self.db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET cluster=excluded.cluster,verified=excluded.verified,indexed=excluded.indexed,updated=excluded.updated,document=excluded.document',(record['asset_id'],record['provider'],record['provider_id'],record.get('duplicate_cluster_id'),int(st.get('verified',False)),int(st.get('indexed',False)),record['updated_at'],json.dumps(record,ensure_ascii=False)))
            if commit:self.db.commit()
        return record

    def discover(self,record):
        key=hashlib.sha256((record['provider']+':'+record['provider_id']).encode()).hexdigest()[:32]
        with self.lock:
            old=self.get(key)
            if old:
                old['discovery_categories']=sorted(set(old.get('discovery_categories',[old['category']])+[record['category']]))
                self.put(old);return old,False
            record={**record,'asset_id':key,'discovered_at':time.time(),'downloaded_at':None,'states':dict.fromkeys(STATES,False),'stage':'discovered','attempts':0,'quality_flags':[],'split':'unassigned','derivatives':{},'duplicate_cluster_id':key,'local_path':None,'sha256':None,'usable_windows':[]}
            self.inherit_split(record);self.put(record);return record,True

    def inherit_split(self,record):
        path=self.root/'split-groups.json'
        if not path.exists():return
        from revisions import digest
        creator=digest(record.get('creator') or 'unknown-'+record['provider'])
        groups=json.loads(path.read_text(encoding='utf-8'))['groups']
        matches={g['partition'] for g in groups if creator in g['creator_keys'] or record['source_family_id'] in g['source_families'] or record.get('sha256') in g['sha256']}
        if len(matches)>1:raise ValueError('Split registry contains conflicting source groups')
        if matches:record['split']=next(iter(matches))

    def checkpoint(self,query,category,offset,finished=False):
        with self.lock:
            self.db.execute('INSERT OR REPLACE INTO discovery VALUES(?,?,?,?,?)',(query,category,offset,int(finished),time.time()));self.db.commit()

    def cursor(self,query,category):
        with self.lock:
            row=self.db.execute('SELECT offset,finished FROM discovery WHERE query=? AND category=?',(query,category)).fetchone()
            return (row[0],bool(row[1])) if row else (0,False)

    def event(self,kind,document,asset=None):
        with self.lock:
            self.db.execute('INSERT INTO events(time,asset,kind,document) VALUES(?,?,?,?)',(time.time(),asset,kind,json.dumps(document,ensure_ascii=False)));self.db.commit()

    def merge(self,record,other,reason):
        with self.lock:
            clusters={record['duplicate_cluster_id'],other['duplicate_cluster_id']};canonical=min(clusters)
            members=[r for r in self.rows() if r['duplicate_cluster_id'] in clusters]+[record]
            splits={r.get('split','unassigned') for r in members}-{'unassigned'}
            if len(splits)>1:
                # Freeze training rather than silently admitting an alias across a split.
                (self.root/'datasets'/'split-invalidated.json').write_text(json.dumps(dict(reason='Duplicate crossed frozen partitions',assets=[r['asset_id'] for r in members],splits=sorted(splits))),encoding='utf-8')
            split='sealed_final' if len(splits)>1 or 'sealed_final' in splits else next(iter(splits),'unassigned')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                for item in self.rows():
                    if item['duplicate_cluster_id'] in clusters:
                        item['duplicate_cluster_id']=canonical;item['source_family_id']=other['source_family_id'];item['split']=split;self.put(item,False)
                record['duplicate_cluster_id']=canonical;record['source_family_id']=other['source_family_id'];record['split']=split;record['duplicate_of']=other['asset_id'];record['duplicate_reason']=reason;self.put(record,False);self.db.commit()
            except BaseException:self.db.rollback();raise
        return record

    def stats(self):
        rows=self.rows();verified=[r for r in rows if r['states']['verified'] and not r.get('parent_asset_ids')]
        representatives={}
        for r in verified:
            old=representatives.get(r['duplicate_cluster_id'])
            if old is None or (r['states']['edit_ready'],r['states']['indexed'])>(old['states']['edit_ready'],old['states']['indexed']):representatives[r['duplicate_cluster_id']]=r
        result=dict(discovered=len(rows),downloaded=sum(r['states']['downloaded'] for r in rows),verified=len(verified),unique=len(representatives),indexed=sum(r['states']['indexed'] for r in rows),edit_ready=sum(r['states']['edit_ready'] for r in representatives.values()),training_example_ready=sum(r['states']['training_example_ready'] for r in rows),human_approved=sum(r['states']['human_approved'] for r in rows),failed=sum(r['stage']=='quarantined' for r in rows),deferred=sum(r['stage']=='deferred' for r in rows),duplicates=len(verified)-len(representatives),original_bytes=sum(r.get('file_bytes',0) for r in {r.get('sha256'):r for r in rows if r['states']['downloaded']}.values()),categories={k:sum(r['category']==k for r in representatives.values()) for k in sorted({r['category'] for r in rows})},failure_reasons={reason:sum(r.get('last_error')==reason for r in rows) for reason in sorted({r['last_error'] for r in rows if r.get('last_error')})})

        usable=[r for r in representatives.values() if r['states']['edit_ready'] and r['states']['indexed'] and r.get('split') not in ('sealed_final','test')]
        result.update(indexed_unique=sum(r['states']['indexed'] for r in representatives.values()),retrievable=len(usable),usable_categories={k:sum(r['category']==k for r in usable) for k in result['categories']})
        return result

    def export(self):
        with self.lock:
            path=self.root/'manifest.jsonl';temp=path.with_suffix('.'+uuid.uuid4().hex+'.tmp')
            with temp.open('w',encoding='utf-8') as out:
                for row in self.rows():out.write(json.dumps(row,ensure_ascii=False)+'\n')
            temp.replace(path);stats=self.stats();temp=self.root/('progress.'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(self.root/'progress.json')
        return stats
