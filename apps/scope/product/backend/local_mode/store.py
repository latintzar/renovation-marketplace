"""SQLite-backed legacy REST row contract, scoped to a verified local visitor.

This is a new local adapter, not an export of the historical Supabase schema.
Only the original route modules call its private ASGI application.
"""
from __future__ import annotations
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, re, secrets, sqlite3, time, uuid
from fastapi import FastAPI, Request, HTTPException
from .seed import starter
VISITOR = ContextVar('marketplace_local_visitor', default=None)
TABLES = frozenset(['contractors', 'quotes', 'jobs', 'job_messages', 'milestone_updates', 'variation_orders', 'notifications', 'reviews'])

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:

    def __init__(self, state):
        self.state = Path(state)
        self.state.mkdir(parents=True, exist_ok=True, mode=448)
        self.state.chmod(0o700)
        self.path = self.state / 'workspace.sqlite'
        with self.connect() as db:
            db.executescript('PRAGMA journal_mode=WAL; PRAGMA max_page_count=32768; CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, identity TEXT NOT NULL, expires INTEGER NOT NULL, touched INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS records (guest TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(guest,kind,id)); CREATE INDEX IF NOT EXISTS records_scope ON records(guest,kind);')
        self.path.chmod(0o600)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=10000')
        db.execute('PRAGMA max_page_count=32768')
        return db

    def admit(self, secret=None, role=None):
        fresh = False
        stamp = int(time.time())
        touched = time.time_ns()
        digest = hashlib.sha256((secret or '').encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT identity,expires FROM sessions WHERE id=?', (digest,)).fetchone()
            if prior is None or prior['expires'] < stamp:
                secret = secrets.token_urlsafe(32)
                digest = hashlib.sha256(secret.encode()).hexdigest()
                fresh = True
                identity = {'contractor_id': str(uuid.uuid4()), 'contractor_auth_id': str(uuid.uuid4()), 'homeowner_id': str(uuid.uuid4()), 'role': 'contractor', 'preferred_language': 'en'}
                db.execute('INSERT INTO sessions(id,identity,expires,touched) VALUES(?,?,?,?)', (digest, json.dumps(identity), stamp + 43200, touched))
                for table, rows in starter(identity).items():
                    for row in rows:
                        db.execute('INSERT INTO records VALUES(?,?,?,?)', (digest, table, str(row['id']), json.dumps(row)))
            else:
                identity = json.loads(prior['identity'])
            if role in {'contractor', 'homeowner'}:
                identity['role'] = role
            db.execute('UPDATE sessions SET identity=?,touched=? WHERE id=?', (json.dumps(identity), touched, digest))
            expired = [r[0] for r in db.execute('SELECT id FROM sessions WHERE expires<? UNION SELECT id FROM (SELECT id FROM sessions ORDER BY touched DESC LIMIT -1 OFFSET 256)', (stamp,))]
            for key in expired:
                db.execute('DELETE FROM records WHERE guest=?', (key,))
                db.execute('DELETE FROM sessions WHERE id=?', (key,))
        return (secret, {'key': digest, **identity}, fresh)

    def user(self, identity):
        homeowner = identity['role'] == 'homeowner'
        return {'id': identity['homeowner_id'] if homeowner else identity['contractor_auth_id'], 'email': 'homeowner@example.invalid' if homeowner else 'contractor@example.invalid', 'user_metadata': {'preferred_language': identity.get('preferred_language', 'en')}, 'app_metadata': {}, 'aud': 'local-workspace', 'created_at': '2026-01-01T00:00:00Z'}

    def reset(self, identity):
        with self.connect() as db:
            db.execute('DELETE FROM records WHERE guest=?', (identity['key'],))
            db.execute('DELETE FROM sessions WHERE id=?', (identity['key'],))

    def language(self, identity, language):
        if language not in {'en', 'es'}:
            raise HTTPException(400, 'Choose English or Spanish.')
        identity = {**identity, 'preferred_language': language}
        saved = {k: v for k, v in identity.items() if k != 'key'}
        with self.connect() as db:
            db.execute('UPDATE sessions SET identity=? WHERE id=?', (json.dumps(saved), identity['key']))
        return self.user(identity)

    def rows(self, db, guest, table):
        return [json.loads(r[0]) for r in db.execute('SELECT document FROM records WHERE guest=? AND kind=?', (guest, table))]

    def operation(self, identity, table, method, params, payload=None):
        if table not in TABLES:
            raise HTTPException(404, 'Choose a local workspace record.')
        if method not in {'GET', 'POST', 'PATCH', 'DELETE'}:
            raise HTTPException(405, 'Choose a supported record operation.')

        def matches(row):
            for key, value in params.multi_items():
                if key in {'select', 'order', 'limit', 'offset', 'on_conflict'}:
                    continue
                if not re.fullmatch('[a-z][a-z0-9_]*', key):
                    raise HTTPException(400, 'Choose a supported record filter.')
                operator, sep, expected = value.partition('.')
                if not sep:
                    raise HTTPException(400, 'Choose an exact record filter.')
                actual = row.get(key)
                if operator == 'eq':
                    comparable = str(actual).lower() if isinstance(actual, bool) else str(actual)
                    if comparable != expected:
                        return False
                elif operator == 'in':
                    if not (expected.startswith('(') and expected.endswith(')')) or str(actual) not in expected[1:-1].split(','):
                        return False
                elif operator == 'is':
                    if not (expected == 'null' and actual is None or (expected == 'true' and actual is True) or (expected == 'false' and actual is False)):
                        return False
                else:
                    raise HTTPException(400, 'Choose a supported record filter.')
            return True
        guest = identity['key']
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = self.rows(db, guest, table)
            selected = [r for r in rows if matches(r)]
            if method == 'POST':
                values = payload if isinstance(payload, list) else [payload]
                if not values or len(values) > 20:
                    raise HTTPException(413, 'Choose up to twenty records.')
                selected = []
                for value in values:
                    if not isinstance(value, dict) or len(json.dumps(value)) > 48000:
                        raise HTTPException(400, 'Choose a smaller record.')
                    row = {**value, 'id': str(value.get('id') or uuid.uuid4()), 'created_at': value.get('created_at') or now()}
                    if any((r['id'] == row['id'] for r in rows)):
                        raise HTTPException(409, 'This record already exists.')
                    rows.append(row)
                    selected.append(row)
            elif method == 'PATCH':
                if not isinstance(payload, dict) or len(json.dumps(payload)) > 48000:
                    raise HTTPException(400, 'Choose a smaller record.')
                for row in selected:
                    row.update({k: v for k, v in payload.items() if k not in {'id', 'created_at'}})
            elif method == 'DELETE':
                rows = [r for r in rows if r not in selected]
            if method != 'GET':
                if len(rows) > 128 or sum((len(json.dumps(r)) for r in rows)) > 256000:
                    raise HTTPException(413, 'Local workspace record limit reached.')
                other_bytes = db.execute('SELECT coalesce(sum(length(document)),0) FROM records WHERE guest=? AND kind<>?', (guest, table)).fetchone()[0]
                if other_bytes + sum(len(json.dumps(row)) for row in rows) > 256000:
                    raise HTTPException(413, 'Local workspace storage limit reached.')
                db.execute('DELETE FROM records WHERE guest=? AND kind=?', (guest, table))
                db.executemany('INSERT INTO records VALUES(?,?,?,?)', [(guest, table, str(r['id']), json.dumps(r)) for r in rows])
            order = params.get('order', '')
            if order:
                key, _, direction = order.partition('.')
                selected.sort(key=lambda r: str(r.get(key) or ''), reverse=direction == 'desc')
            limit = max(0, min(200, int(params.get('limit', '200'))))
            offset = max(0, min(1000, int(params.get('offset', '0'))))
            selected = selected[offset:offset + limit]
            fields = params.get('select', '*')
            if fields != '*':
                names = fields.split(',')
                if any((not re.fullmatch('[a-z][a-z0-9_]*', name) for name in names)):
                    raise HTTPException(400, 'Choose supported record fields.')
                selected = [{k: r.get(k) for k in names} for r in selected]
            return selected

    def rest_app(self):
        app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

        @app.api_route('/rest/v1/{table}', methods=['GET', 'POST', 'PATCH', 'DELETE'])
        async def records(table: str, request: Request):
            identity = VISITOR.get()
            if identity is None or request.url.hostname != 'local.marketplace.invalid':
                raise HTTPException(403, 'Local workspace authority required.')
            payload = await request.json() if request.method in {'POST', 'PATCH'} else None
            return self.operation(identity, table, request.method, request.query_params, payload)
        return app
