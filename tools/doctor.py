#!/usr/bin/env python3
"""Check local starter prerequisites without contacting providers."""
from pathlib import Path
import sys,subprocess,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def main():
 node=shutil.which('node');node_version=subprocess.check_output([node,'--version'],text=True).strip() if node else ''
 node_parts=tuple(int(x) for x in node_version.lstrip('v').split('.')) if node_version else (0,0,0)
 checks={'python_3_12':sys.version_info>=(3,12),'node_22_12':node_parts>=(22,12,0),'web_dependencies':(ROOT/'apps/scope/product/web/node_modules').is_dir(),'source_reels':(ROOT/'apps/scope/product/web/src/reel/registry.ts').is_file(),'developer_schema':(ROOT/'supabase/migrations/0001_developer_core.sql').is_file()}
 print(json.dumps({'checks':checks,'mode':'original scripted UI','provider_requests':0,'connected_setup':'docs/setup.md'},indent=2))
 return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
