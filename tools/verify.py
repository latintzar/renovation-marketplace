#!/usr/bin/env python3
"""Run source/domain suites with a clean, provider-free Python environment."""
from pathlib import Path
import json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
def main():
 env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','LANG','LC_ALL','TMPDIR']}
 env['PYTHONPATH']=os.pathsep.join([str(ROOT/'tools/offline'),str(ROOT/'apps/scope/product/backend')]+[str(p/'src') for p in (ROOT/'packages').iterdir() if (p/'src').is_dir()])
 stages=[('release-safety',['tests']),('state-machine',['--noconftest','apps/scope/product/backend/tests/test_state_machine.py']),('payment-domain',['packages/payments/tests']),('document-payloads',['--confcutdir='+str(ROOT/'apps/scope/product/backend/tests/documents'),'apps/scope/product/backend/tests/documents/test_payloads.py'])]
 output=ROOT/'.local/verification';output.mkdir(parents=True,exist_ok=True);results=[]
 for name,args in stages:
  start=time.monotonic();r=subprocess.run([sys.executable,'-m','pytest','-q',*args],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  (output/(name+'.log')).write_text(r.stdout);results.append({'suite':name,'returncode':r.returncode,'seconds':round(time.monotonic()-start,2),'summary':r.stdout.splitlines()[-1:]});print(name,'passed' if not r.returncode else 'FAILED; inspect private local verification log',flush=True)
 (output/'checks.json').write_text(json.dumps({'python_network':'loopback-only','suites':results},indent=2)+'\n')
 return int(any(r['returncode'] for r in results))
if __name__=='__main__':raise SystemExit(main())
