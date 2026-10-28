#!/usr/bin/env python3
"""Serve the original scripted marketplace UI from a loopback-only source build."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlsplit,unquote
import argparse,json,subprocess,os
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'apps/scope/product/public/app'
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  path=urlsplit(self.path).path
  if path=='/healthz':
   raw=json.dumps({'status':'ok','mode':'scripted product walkthrough','provider_calls':0}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
  if path in ['/','/app','/app/']:
   if path!='/app/':self.send_response(302);self.send_header('Location','/app/quote/first?reel=set-milestones');self.end_headers();return
  if not path.startswith('/app/'):self.send_error(404);return
  name=unquote(path.removeprefix('/app/'))
  target=(BUILD/name).resolve()
  if not target.is_relative_to(BUILD.resolve()) or any(x.startswith('.') for x in Path(name).parts):self.send_error(404);return
  if not target.is_file() and not Path(name).suffix:self.path='/index.html'
  else:self.path='/'+name
  return super().do_GET()
 def list_directory(self,path):self.send_error(404)
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=18260);parser.add_argument('--no-build',action='store_true');args=parser.parse_args()
 if not 1024<=args.port<=65535:raise ValueError('Use an unprivileged local port.')
 if not args.no_build and not (BUILD/'index.html').is_file():
  env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','LANG','LC_ALL','TMPDIR','SSL_CERT_FILE','SSL_CERT_DIR']}
  env['NPM_CONFIG_USERCONFIG']='/dev/null'
  subprocess.run(['npx','--yes','pnpm@9.0.0','run','build'],cwd=ROOT,env=env,check=True)
 if not (BUILD/'index.html').is_file():raise SystemExit('Run make build first.')
 os.chdir(BUILD)
 print(f'Original scripted quote: http://127.0.0.1:{args.port}/app/quote/first?reel=set-milestones',flush=True)
 ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
if __name__=='__main__':main()
