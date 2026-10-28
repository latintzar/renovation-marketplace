#!/usr/bin/env python3
"""List or export the source release, excluding generated/private contexts."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,tarfile
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','node_modules','.venv','.local','__pycache__','.pytest_cache','.vercel'}
def files():
 for p in sorted(ROOT.rglob('*')):
  rel=p.relative_to(ROOT)
  if not p.is_file() or any(x in EXCLUDED for x in rel.parts):continue
  if p.is_symlink():raise ValueError('Review source symlinks before export.')
  if rel.parts[:5]==('apps','scope','product','public','app'):continue
  if rel.parts[:2] in [('supabase','.temp'),('supabase','.branches')]:continue
  if p.name.startswith('.env') and p.name!='.env.example':raise ValueError('Keep recipient configuration outside source exports.')
  if p.suffix in ['.pyc','.tsbuildinfo','.db','.sqlite','.sqlite3'] or p.name.endswith('.tar.gz'):continue
  yield p
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--scan-directory',type=Path);parser.add_argument('--archive',type=Path);parser.add_argument('--manifest',type=Path);args=parser.parse_args()
 selected=list(files());record={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in selected if p!=args.manifest}
 if args.scan_directory:
  target=args.scan_directory.resolve()
  if target.exists():raise ValueError('Select a new private scan directory.')
  target.mkdir(mode=0o700,parents=True)
  for p in selected:
   dest=target/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True)
   os.link(p,dest)
 if args.archive:
  if args.archive.resolve().is_relative_to(ROOT):raise ValueError('Export to a private path outside the checkout.')
  with tarfile.open(args.archive,'x:gz') as tar:
   for p in selected:tar.add(p,arcname='renovation-marketplace/'+str(p.relative_to(ROOT)),recursive=False)
  args.archive.chmod(0o600)
 if args.manifest:
  args.manifest.write_text(json.dumps({'algorithm':'SHA-256','excluded':'private contexts, dependencies, caches and generated builds','files':record},indent=2)+'\n')
 print(json.dumps({'source_files':len(selected),'source_bytes':sum(p.stat().st_size for p in selected),'history_included':False,'private_contexts_included':False}))
if __name__=='__main__':main()
