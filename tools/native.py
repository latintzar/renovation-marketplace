"""Build or run the normal marketplace UI with original routes and owned local state."""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'apps/scope/product/backend'
BUILD = ROOT / 'apps/scope/product/public/app'

def environment(state, prefix):
    home = state / 'home'
    home.mkdir(parents=True, exist_ok=True, mode=448)
    env = {k: v for k, v in os.environ.items() if k in {'PATH', 'LANG', 'LC_ALL', 'TMPDIR', 'SSL_CERT_FILE', 'SSL_CERT_DIR'}}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'), XDG_CACHE_HOME=str(home / '.cache'), XDG_DATA_HOME=str(home / '.local/share'), PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1', AWS_EC2_METADATA_DISABLED='true', AWS_CONFIG_FILE=os.devnull, AWS_SHARED_CREDENTIALS_FILE=os.devnull, GOOGLE_APPLICATION_CREDENTIALS='/local-provider-not-configured', VITE_LOCAL_MODE='1', VITE_APP_BASE_PATH=prefix + '/', SCOPE_WEB_BASE_PATH=prefix, SUPABASE_URL='http://local.marketplace.invalid', SUPABASE_SERVICE_ROLE_KEY='local-internal-transport-only')
    return env

def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'start'])
    parser.add_argument('--state', type=Path, default=Path.home() / '.local/state/renovation-marketplace')
    parser.add_argument('--base-path', default='/app')
    parser.add_argument('--public-origin', default='')
    parser.add_argument('--port', type=int, default=18260)
    args = parser.parse_args()
    if args.base_path and (not re.fullmatch('(?:/[A-Za-z0-9_-]+)+', args.base_path)):
        parser.error('Choose a slash-separated application path.')
    if not 1024 <= args.port <= 65535:
        parser.error('Choose an unprivileged loopback port.')
    if any((p.name != '.env.example' for p in ROOT.rglob('.env*') if p.is_file() and 'node_modules' not in p.parts and ('.venv' not in p.parts))):
        parser.error('Keep provider configuration outside this local-mode checkout.')
    state = args.state.expanduser().absolute()
    if state.is_symlink() or state.resolve().is_relative_to(ROOT.resolve()):
        parser.error('Choose an owned private state directory outside the checkout.')
    state.mkdir(parents=True, exist_ok=True, mode=448)
    state.chmod(0o700)
    marker = state / '.renovation-local.json'
    if marker.exists():
        if marker.is_symlink() or marker.stat().st_mode & 63 or json.loads(marker.read_text()).get('schema') != 'renovation-local-v1':
            parser.error('Choose an owned local-mode state directory.')
    else:
        if any(state.iterdir()):
            parser.error('Choose fresh state for this local workspace.')
        marker.write_text(json.dumps({'schema': 'renovation-local-v1'}) + '\n')
        marker.chmod(0o600)
    env = environment(state, args.base_path)
    if args.action == 'build':
        node = shutil.which('node', path=env.get('PATH'))
        npx = shutil.which('npx', path=env.get('PATH'))
        if not node or not npx:
            parser.error('Install Node22.12+ and run make install.')
        version = subprocess.check_output([node, '--version'], env=env, text=True).strip()
        major, minor = map(int, version.lstrip('v').split('.')[:2])
        if major < 22 or (major == 22 and minor < 12):
            parser.error('Use Node22.12+ for the Vite application.')
        subprocess.run([npx, '--yes', 'pnpm@9.0.0', 'run', 'build'], cwd=ROOT, env=env, check=True)
        (BUILD / 'native-build.json').write_text(json.dumps({'schema': 1, 'base_path': args.base_path, 'mode': 'local'}, indent=2) + '\n')
        return
    metadata = BUILD / 'native-build.json'
    if not metadata.is_file() or json.loads(metadata.read_text()).get('base_path') != args.base_path:
        parser.error('Build local mode with the same application base path first.')
    env['APP_BASE_URL'] = args.public_origin or f'http://127.0.0.1:{args.port}'
    os.environ.clear()
    os.environ.update(env)
    sys.path.insert(0, str(ROOT / 'tools/offline'))
    import sitecustomize
    sys.path[:0] = [str(BACKEND)] + [str(p / 'src') for p in (ROOT / 'packages').iterdir() if (p / 'src').is_dir()]
    from local_mode.server import create_app
    import uvicorn
    app = create_app(state, prefix=args.base_path, public_origin=args.public_origin, build=BUILD)
    print('Marketplace: ' + (args.public_origin or f'http://127.0.0.1:{args.port}') + args.base_path + '/', flush=True)
    uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False)
if __name__ == '__main__':
    main()
