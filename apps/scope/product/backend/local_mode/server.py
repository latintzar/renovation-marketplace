"""Original marketplace routers with recipient-owned local auth and SQLite storage."""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit
import json, re, secrets
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from core import CurrentUser, require_auth, optional_auth, require_contractor, require_homeowner
from core.errors import AppError
from core.http import local_http_transport
from payments import SandboxContext, resolve_sandbox
from .store import Store, VISITOR
COOKIE = 'renovation_workspace_session'
READS = ['/v1/canvas/[^/]+', '/v1/quotes', '/v1/homeowner/quotes', '/v1/contractor/by-auth-user/[^/]+', '/v1/projects/[^/]+', '/v1/milestone-updates/[^/]+', '/v1/variation-orders/[^/]+', '/v1/messages/[^/]+', '/v1/notifications', '/v1/documents/[^/]+/(?:agreement|invoice)']
WRITES = ['/v1/milestone/submit-proof', '/v1/variation/create', '/v1/quote/(?:update|finalize)', '/v1/messages/send', '/v1/projects/[^/]+/milestones/[0-9]+/proof', '/v1/projects/[^/]+/variations', '/v1/projects/[^/]+/variations/[^/]+/decline', '/v1/notifications/mark-read']

def create_app(state, *, prefix='', public_origin='', build=None):
    if prefix and (not re.fullmatch('(?:/[A-Za-z0-9_-]+)+', prefix)):
        raise ValueError('Choose a portable application prefix.')
    if public_origin:
        parsed = urlsplit(public_origin)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or (parsed.path not in {'', '/'}) or parsed.query or parsed.fragment:
            raise ValueError('Choose the recipient HTTPS origin.')
        public_origin = public_origin.rstrip('/')
    from core.db import sb_url, sb_key
    if sb_url() != 'http://local.marketplace.invalid/rest/v1' or sb_key() != 'local-internal-transport-only':
        raise ValueError('Start local mode through tools/native.py with its owned environment.')
    store = Store(state)
    transport = httpx.ASGITransport(store.rest_app())
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store

    def identity():
        value = VISITOR.get()
        if value is None:
            raise HTTPException(401, 'Open your local workspace.')
        return value

    async def current_user():
        actor = identity()
        u = store.user(actor)
        return CurrentUser(id=u['id'], email=u['email'], role=actor['role'], contractor_id=actor['contractor_id'] if actor['role'] == 'contractor' else None)

    async def contractor():
        user = await current_user()
        if user.role != 'contractor':
            raise HTTPException(403, 'Open the contractor workspace.')
        return user

    async def homeowner():
        user = await current_user()
        if user.role != 'homeowner':
            raise HTTPException(403, 'Open the homeowner workspace.')
        return user

    async def no_external_sandbox():
        return SandboxContext(is_sandbox=True, stripe_key='', stripe_webhook_secret='', suppress_whatsapp=True)
    app.dependency_overrides.update({require_auth: current_user, optional_auth: current_user, require_contractor: contractor, require_homeowner: homeowner, resolve_sandbox: no_external_sandbox})

    @app.exception_handler(AppError)
    async def domain_error(_request, error):
        return JSONResponse({'detail': error.to_detail()}, status_code=error.status)

    @app.middleware('http')
    async def workspace(request: Request, call_next):
        path = request.url.path
        if prefix:
            if path == prefix:
                return RedirectResponse(prefix + '/', status_code=307)
            if not path.startswith(prefix + '/'):
                return JSONResponse({'detail': 'Choose this application path.'}, status_code=404)
            path = path[len(prefix):]
            request.scope['path'] = path
            request.scope['raw_path'] = path.encode()
        api = path.startswith(('/v1/', '/api/'))
        if not api and request.method not in {'GET', 'HEAD'}:
            return JSONResponse({'detail': 'Open a workspace page.'}, status_code=405)
        if api:
            if path.startswith('/v1/documents/') and request.query_params.get('format') == 'pdf':
                return JSONResponse({'detail': 'Open the HTML agreement or install the optional PDF renderer.', 'code': 'PDF_RENDERER_REQUIRED'}, status_code=503)
            local = path == '/api/local/session'
            allowed = local or (request.method in {'GET', 'HEAD'} and any((re.fullmatch(pattern, path) for pattern in READS))) or (request.method == 'POST' and any((re.fullmatch(pattern, path) for pattern in WRITES)))
            if not allowed:
                return JSONResponse({'detail': 'Connect your own provider for this action.', 'code': 'RECIPIENT_SERVICE_REQUIRED'}, status_code=503)
            if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
                expected = public_origin or str(request.base_url).rstrip('/')
                origin = request.headers.get('origin')
                if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and origin != expected):
                    return JSONResponse({'detail': 'Use the application origin.'}, status_code=403)
                length = request.headers.get('content-length')
                if length and (not length.isdecimal() or int(length) > 32768):
                    return JSONResponse({'detail': 'Use up to 32 KiB per request.'}, status_code=413)
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 32768:
                        return JSONResponse({'detail': 'Use up to 32 KiB per request.'}, status_code=413)
                request._body = bytes(body)
        if path == '/healthz':
            return await call_next(request)
        role = request.query_params.get('local_role') if not api and (path in {'/', '/dashboard', '/my-projects'} or path.startswith('/project/')) else None
        secret, actor, fresh = store.admit(request.cookies.get(COOKIE), role=role)
        token = VISITOR.set(actor)
        try:
            if api and request.method == 'POST':
                try:
                    payload = json.loads(request._body or b'{}')
                except (ValueError, AttributeError):
                    return JSONResponse({'detail': 'Use a JSON request.'}, status_code=400)
                if not isinstance(payload, dict):
                    return JSONResponse({'detail': 'Use a JSON object.'}, status_code=400)
                if path in {'/v1/quote/update', '/v1/quote/finalize'}:
                    if actor['role'] != 'contractor' or payload.get('contractor_id') != actor['contractor_id']:
                        return JSONResponse({'detail': 'Use your contractor workspace.'}, status_code=403)
                    if payload.get('auth_user_id') and payload['auth_user_id'] != actor['contractor_auth_id']:
                        return JSONResponse({'detail': 'Use your current identity.'}, status_code=403)
            if api and request.method == 'POST' and (path in {'/v1/milestone/submit-proof', '/v1/variation/create'}):
                if actor['role'] != 'contractor' or payload.get('contractor_auth_id') != actor['contractor_id']:
                    return JSONResponse({'detail': 'Use your contractor workspace.'}, status_code=403)
            with local_http_transport(transport):
                response = await call_next(request)
            if fresh:
                response.set_cookie(COOKIE, secret, httponly=True, secure=bool(public_origin), samesite='lax', path=prefix + '/', max_age=43200)
            response.headers['Cache-Control'] = 'private, no-store' if api else response.headers.get('Cache-Control', 'no-cache')
            return response
        finally:
            VISITOR.reset(token)

    @app.get('/api/local/session')
    async def session():
        return {'user': store.user(identity()), 'role': identity()['role'], 'mode': 'local', 'providers_enabled': False}

    @app.patch('/api/local/session')
    async def language(request: Request):
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(400, 'Use a JSON object.')
        return {'user': store.language(identity(), body.get('preferred_language'))}

    @app.delete('/api/local/session')
    async def logout():
        store.reset(identity())
        response = JSONResponse({'user': None})
        response.delete_cookie(COOKIE, path=prefix + '/')
        return response

    @app.get('/healthz')
    async def health():
        return {'status': 'ok', 'mode': 'local', 'storage': 'sqlite', 'providers_enabled': False}
    from routes import canvas, projects, milestone, milestones, messages, notifications, variations
    for module in [canvas, projects, milestones, messages, notifications, variations, milestone]:
        app.include_router(module.router, prefix='/v1')
    from routes import documents
    app.include_router(documents.router, prefix='/v1')
    if build is not None:
        build = Path(build).resolve()

        @app.get('/{path:path}')
        async def page(path: str):
            if path == '':
                return RedirectResponse(prefix + '/dashboard', status_code=307)
            target = (build / path).resolve()
            if not target.is_relative_to(build) or any((part.startswith('.') for part in Path(path).parts)):
                raise HTTPException(404, 'Choose a product page.')
            if target.is_file():
                return FileResponse(target)
            if Path(path).suffix:
                raise HTTPException(404, 'Asset not found.')
            return FileResponse(build / 'index.html')
    return app
