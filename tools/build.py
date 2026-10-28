#!/usr/bin/env python3
"""Build the UI with an explicit public-variable allowlist."""
from pathlib import Path
import argparse,json,os,subprocess
from configure import read_env,DEFAULT
ROOT=Path(__file__).resolve().parents[1]
PUBLIC={'VITE_API_URL','VITE_SUPABASE_URL','VITE_SUPABASE_ANON_KEY','VITE_MAPBOX_ACCESS_TOKEN','VITE_POSTHOG_KEY'}
def public_values(values):
 out={'VITE_API_URL':'http://127.0.0.1:18261','VITE_SUPABASE_URL':'http://127.0.0.1:54321','VITE_SUPABASE_ANON_KEY':'local-reel-only-anon-key','VITE_MAPBOX_ACCESS_TOKEN':'','VITE_POSTHOG_KEY':''}
 for src,dst in [('SUPABASE_URL','VITE_SUPABASE_URL'),('SUPABASE_ANON_KEY','VITE_SUPABASE_ANON_KEY'),('MARKETPLACE_API_URL','VITE_API_URL')]:
  if values.get(src):out[dst]=values[src]
 out.update({k:v for k,v in values.items() if k in PUBLIC})
 return out

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--env-file',type=Path);a=p.parse_args()
 values=read_env(a.env_file) if a.env_file else {}
 env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','LANG','LC_ALL','TMPDIR','SSL_CERT_FILE','SSL_CERT_DIR']}
 env['NPM_CONFIG_USERCONFIG']='/dev/null';env.update(public_values(values))
 subprocess.run(['npx','--yes','pnpm@9.0.0','run','build'],cwd=ROOT,env=env,check=True)
 print(json.dumps({'build':'original React UI','configuration':'explicit recipient file' if a.env_file else 'local scripted defaults','public_names':sorted(PUBLIC),'backend_secret_names_exported':[]}))
if __name__=='__main__':main()
