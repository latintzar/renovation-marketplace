#!/usr/bin/env python3
"""Save recipient configuration outside the checkout through hidden input."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,getpass,json,os,re,stat,subprocess
ROOT=Path(__file__).resolve().parents[1]
DEFAULT=Path.home()/'.config/renovation-marketplace/runtime.env'
GROUPS={
 'auth':['SUPABASE_URL','SUPABASE_ANON_KEY','SUPABASE_SERVICE_ROLE_KEY','APP_BASE_URL'],
 'stripe':['STRIPE_SECRET_KEY_TEST','STRIPE_WEBHOOK_SECRET_TEST'],
 'whatsapp':['WHATSAPP_TOKEN','WHATSAPP_PHONE_NUMBER_ID','WHATSAPP_VERIFY_TOKEN'],
 'voice':['DEEPGRAM_API_KEY','GROQ_API_KEY'],
 'maps':['VITE_MAPBOX_ACCESS_TOKEN'],
 'agent':['LITELLM_BASE_URL','LITELLM_API_KEY','LEO_PRIMARY_MODEL','HERMES_VENDOR_PATH','LEO_AWS_ACCOUNT'],
}
def private_parent(path):
 path=path.absolute()
 if path.resolve().is_relative_to(ROOT):raise ValueError('Choose a private configuration file outside this checkout.')
 path.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
 if path.parent.is_symlink() or path.parent.resolve()!=path.parent or path.parent.stat().st_uid!=os.geteuid() or stat.S_IMODE(path.parent.stat().st_mode)&0o077:raise ValueError('Use an owner-only configuration directory.')
 return path

def read_env(path):
 path=private_parent(path)
 if not path.exists():return {}
 st=path.lstat()
 if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)&0o077:raise ValueError('Use an owner-only regular configuration file.')
 values={}
 for line in path.read_text().splitlines():
  if not line or line.startswith('#'):continue
  key,sep,value=line.partition('=')
  if not sep or not re.fullmatch(r'[A-Z][A-Z0-9_]+',key) or '\x00' in value:raise ValueError('Use NAME=value entries.')
  values[key]=value
 return values

def write_env(path,values):
 path=private_parent(path);read_env(path)
 temp=path.with_name(path.name+'.new')
 fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,'w') as f:
   for key,value in sorted(values.items()):f.write(key+'='+value+'\n')
   f.flush();os.fsync(f.fileno())
  os.replace(temp,path)
 finally:
  if temp.exists():temp.unlink()

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['init','doctor','frontend','from-local']);parser.add_argument('--env-file',type=Path,default=DEFAULT);parser.add_argument('--features',default='auth');args=parser.parse_args()
 groups=args.features.split(',');unknown=set(groups)-set(GROUPS)
 if unknown:raise ValueError('Select documented feature names.')
 values=read_env(args.env_file)
 if args.command=='from-local':
  result=subprocess.run(['supabase','status','--output','env'],cwd=ROOT,capture_output=True,text=True)
  if result.returncode:raise ValueError('Start the local Supabase stack before importing its configuration.')
  local={}
  for line in result.stdout.splitlines():
   key,sep,value=line.partition('=')
   if sep and key in {'API_URL','ANON_KEY','SERVICE_ROLE_KEY'}:local[key]=value.strip().strip('"')
  if urlsplit(local.get('API_URL','')).hostname not in {'127.0.0.1','localhost','::1'}:raise ValueError('This command imports a local Supabase stack.')
  if not all(local.get(k) for k in ['API_URL','ANON_KEY','SERVICE_ROLE_KEY']):raise ValueError('The local stack did not return the expected key names.')
  values.update(SUPABASE_URL=local['API_URL'],SUPABASE_ANON_KEY=local['ANON_KEY'],SUPABASE_SERVICE_ROLE_KEY=local['SERVICE_ROLE_KEY'],APP_BASE_URL='http://127.0.0.1:18260')
  write_env(args.env_file,values)
  print(json.dumps({'saved':str(args.env_file),'configured_names':['SUPABASE_URL','SUPABASE_ANON_KEY','SUPABASE_SERVICE_ROLE_KEY','APP_BASE_URL'],'values_printed':False}))
  return
 if args.command=='init':
  for key in dict.fromkeys(k for group in groups for k in GROUPS[group]):
   value=getpass.getpass(key+' (hidden; Enter keeps the current entry): ').strip()
   if value:
    if '\n' in value or '\r' in value or '\x00' in value:raise ValueError('Use a single-line value.')
    values[key]=value
  if 'agent' in groups:
   alias=values.get('LEO_AWS_ACCOUNT','').strip().upper().replace('-','_')
   if not re.fullmatch(r'[A-Z][A-Z0-9_]*',alias):raise ValueError('Choose a named AWS account alias.')
   values['LEO_AWS_ACCOUNT']=alias
   for key in ['AWS_ACCESS_KEY_ID_'+alias,'AWS_SECRET_ACCESS_KEY_'+alias]:
    value=getpass.getpass(key+' (hidden; Enter keeps the current entry): ').strip()
    if value:
     if any(c in value for c in ['\n','\r','\x00']):raise ValueError('Use a single-line value.')
     values[key]=value
  write_env(args.env_file,values);print(json.dumps({'saved':str(args.env_file),'configured_names':sorted(values),'permissions':'0600'}));return
 if args.command=='frontend':
  public={'VITE_API_URL':values.get('MARKETPLACE_API_URL','http://127.0.0.1:18261'),'VITE_SUPABASE_URL':values.get('SUPABASE_URL','http://127.0.0.1:54321'),'VITE_SUPABASE_ANON_KEY':values.get('SUPABASE_ANON_KEY','local-reel-only-anon-key'),'VITE_MAPBOX_ACCESS_TOKEN':values.get('VITE_MAPBOX_ACCESS_TOKEN','')}
  target=args.env_file.with_name('frontend-public.env');write_env(target,public);print(json.dumps({'public_build_file':str(target),'names':sorted(public),'backend_secret_names_exported':[]}));return
 required=list(dict.fromkeys(k for group in groups for k in GROUPS[group]))
 if 'agent' in groups:
  alias=values.get('LEO_AWS_ACCOUNT','').strip().upper().replace('-','_')
  if re.fullmatch(r'[A-Z][A-Z0-9_]*',alias):required += ['AWS_ACCESS_KEY_ID_'+alias,'AWS_SECRET_ACCESS_KEY_'+alias]
 missing=[k for k in required if not values.get(k)]
 print(json.dumps({'configuration_file':str(args.env_file),'features':groups,'missing_names':missing,'values_printed':False,'first_result':'make dev uses the scripted UI independently of connected accounts'},indent=2))
 if missing:raise SystemExit(1)
if __name__=='__main__':main()
