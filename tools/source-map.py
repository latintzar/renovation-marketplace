#!/usr/bin/env python3
"""Generate source navigation from named Python/TypeScript definitions."""
from pathlib import Path
import ast,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
 records=[];routes=[];config=set()
 folders=[ROOT/'apps/scope/product/backend']+[p/'src' for p in (ROOT/'packages').iterdir() if (p/'src').is_dir()]
 for folder in folders:
  for p in sorted(folder.rglob('*.py')):
   if any(k in p.parts for k in ['tests','__pycache__','node_modules']):continue
   try:tree=ast.parse(p.read_text())
   except (SyntaxError,UnicodeError):continue
   relative=str(p.relative_to(ROOT))
   for n in ast.walk(tree):
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
     doc=ast.get_docstring(n) or '';first=doc.split('\n\n')[0].replace('\n',' ').strip()
     records.append({'language':'Python','file':relative,'name':n.name,'line':n.lineno,'arguments':[a.arg for a in n.args.args],'description':first[:400]})
     for d in n.decorator_list:
      if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr in ['get','post','patch','put','delete'] and d.args and isinstance(d.args[0],ast.Constant) and isinstance(d.args[0].value,str):routes.append({'method':d.func.attr.upper(),'path':d.args[0].value,'function':n.name,'file':relative,'line':n.lineno})
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ['getenv','get'] and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str) and re.fullmatch(r'[A-Z][A-Z0-9_]+',n.args[0].value):config.add(n.args[0].value)
 for p in (ROOT/'apps/scope/product/web/src').rglob('*'):
  if p.suffix in ['.ts','.tsx']:config.update(re.findall(r'import\.meta\.env\.([A-Z][A-Z0-9_]+)',p.read_text()))
 # The existing TypeScript compiler parses source without executing it.
 ts=subprocess.run(['node',str(ROOT/'tools/source-map.cjs')],cwd=ROOT,capture_output=True,text=True,check=True)
 records.extend(json.loads(ts.stdout))
 records.sort(key=lambda r:(r['file'],r['line'],r['name']))
 data={'definition':'Named source functions; nested definitions remain with their module. Arguments list names, with credential/default values excluded.','functions':records,'routes':routes,'configuration_names':sorted(config)}
 (ROOT/'docs/source-map.json').write_text(json.dumps(data,indent=2)+'\n')
 lines=['# Source reference','','[Architecture](architecture.md) · [Workflows](workflows.md) · [Configuration](setup.md)','','This index is generated from the released source. File links preserve the containing implementation and its local context.','','## HTTP routes','','| Method | Path | Source |','| --- | --- | --- |']
 for row in routes:lines.append(f"| {row['method']} | `{row['path']}` | [{row['function']}](../{row['file']}#L{row['line']}) |")
 lines+=['','## Configuration names','','Values stay in the recipient’s private runtime file. [Setup](setup.md) groups the load-bearing credentials by feature.','',', '.join('`'+x+'`' for x in sorted(config)),'','## Functions']
 current=None
 for row in records:
  if row['file']!=current:
   current=row['file'];lines+=['','### '+current,'','| Function | Arguments | Purpose |','| --- | --- | --- |']
  desc=row['description'].replace('|','/').replace('\n',' ')
  lines.append(f"| [{row['name']}](../{row['file']}#L{row['line']}) | {', '.join(row['arguments'])} | {desc} |")
 (ROOT/'docs/reference.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'named_functions':len(records),'routes':len(routes),'configuration_names':len(config)}))
if __name__=='__main__':main()
