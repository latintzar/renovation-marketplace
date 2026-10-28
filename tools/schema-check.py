#!/usr/bin/env python3
"""Check the reconstructed core in an isolated, disposable PostgreSQL cluster."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
AUTH='11111111-1111-4111-8111-111111111111'
HOMEOWNER='22222222-2222-4222-8222-222222222222'
OTHER='33333333-3333-4333-8333-333333333333'
CONTRACTOR='44444444-4444-4444-8444-444444444444'
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);parser.add_argument('--pg-bindir',type=Path,default=Path('/usr/lib/postgresql/16/bin'));args=parser.parse_args()
 if os.geteuid()==0:raise SystemExit('Run the isolated PostgreSQL check as an unprivileged user.')
 bindir=args.pg_bindir
 for name in ['initdb','pg_ctl','psql','postgres']:
  if not (bindir/name).is_file():raise SystemExit('Install PostgreSQL16 tools or select --pg-bindir.')
 result={'schema_kind':'developer reconstruction from original route contracts','historical_schema_recovered':False,'postgres':subprocess.check_output([str(bindir/'postgres'),'-V'],text=True).strip(),'network':'private Unix socket only','provider_calls':0,'customer_rows_read':0,'checks':{}}
 with tempfile.TemporaryDirectory(prefix='renovation-schema-') as temp:
  base=Path(temp);data=base/'data';sock=base/'socket';sock.mkdir(mode=0o700)
  subprocess.run([str(bindir/'initdb'),'-D',str(data),'--no-locale','--encoding=UTF8','--auth=trust'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  options=f"-c listen_addresses='' -c unix_socket_directories={sock} -c port=18461 -c shared_buffers=16MB -c max_connections=10 -c max_wal_size=64MB -c min_wal_size=32MB -c fsync=on"
  def start():subprocess.run([str(bindir/'pg_ctl'),'-D',str(data),'-l',str(base/'postgres.log'),'-o',options,'-w','start'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  def stop():subprocess.run([str(bindir/'pg_ctl'),'-D',str(data),'-w','-m','fast','stop'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  def sql(text,ok=True):
   p=subprocess.run([str(bindir/'psql'),'-X','-h',str(sock),'-p','18461','-d','postgres','-v','ON_ERROR_STOP=1','-At'],input=text,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   if ok and p.returncode:raise RuntimeError('Isolated schema SQL failed; inspect the selected source migration.')
   return p
  start()
  try:
   sql("CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN; CREATE ROLE service_role NOLOGIN BYPASSRLS; CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY,email text); CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT NULLIF(pg_catalog.current_setting('request.jwt.claim.sub',true),'')::uuid $$; GRANT USAGE ON SCHEMA auth TO authenticated,service_role;")
   sql((ROOT/'supabase/migrations/0001_developer_core.sql').read_text());result['checks']['migration_applies']=True
   sql(f"INSERT INTO auth.users(id,email) VALUES ('{AUTH}','contractor@example.invalid'),('{HOMEOWNER}','homeowner@example.invalid'),('{OTHER}','other@example.invalid'); SET ROLE service_role; INSERT INTO public.contractors(id,auth_user_id,name) VALUES ('{CONTRACTOR}','{AUTH}','Roble Reformas'); INSERT INTO public.quotes(token,contractor_id,homeowner_auth_id,homeowner_email,quote_data,milestones,amount_total_cents,status,payment_status) VALUES ('sample-project','{CONTRACTOR}','{HOMEOWNER}','homeowner@example.invalid','{{\"title\":\"Bathroom preparation\"}}','[{{\"title\":\"Preparation\",\"amount_cents\":140000,\"status\":\"proof_submitted\"}}]',147000,'in_progress','paid'); INSERT INTO public.milestone_updates(scope_token,milestone_index,photos,note) VALUES ('sample-project',0,ARRAY['/app/sample-attachment.png'],'Sample work record'); INSERT INTO public.job_messages(scope_token,sender_role,sender_id,body) VALUES ('sample-project','contractor','{CONTRACTOR}','Sample project discussion'); INSERT INTO public.notifications(user_id,scope_token,type,milestone_index) VALUES ('{HOMEOWNER}','sample-project','proof_submitted',0);")
   result['checks']['original_route_field_shapes_persist']=True
   def rows(subject,table):return sql(f"SET ROLE authenticated; SET request.jwt.claim.sub='{subject}'; SELECT count(*) FROM public.{table};").stdout.splitlines()[-1]
   result['checks']['homeowner_can_read_project']=rows(HOMEOWNER,'quotes')=='1'
   result['checks']['contractor_can_read_project']=rows(AUTH,'quotes')=='1'
   result['checks']['outsider_cannot_read_project']=rows(OTHER,'quotes')=='0'
   result['checks']['proof_and_chat_follow_project_access']=rows(HOMEOWNER,'milestone_updates')=='1' and rows(HOMEOWNER,'job_messages')=='1' and rows(OTHER,'milestone_updates')=='0' and rows(OTHER,'job_messages')=='0'
   result['checks']['notifications_are_recipient_scoped']=rows(HOMEOWNER,'notifications')=='1' and rows(OTHER,'notifications')=='0'
   result['checks']['anonymous_direct_read_denied']=sql('SET ROLE anon; SELECT * FROM public.quotes;',False).returncode!=0
   result['checks']['authenticated_direct_write_denied']=sql(f"SET ROLE authenticated; SET request.jwt.claim.sub='{HOMEOWNER}'; UPDATE public.quotes SET payment_status='paid';",False).returncode!=0
   result['checks']['negative_proof_index_constraint']=sql("INSERT INTO public.milestone_updates(scope_token,milestone_index) VALUES ('sample-project',-1);",False).returncode!=0
   sql("SET ROLE service_role; UPDATE public.milestone_updates SET status='released',released_at=now(),stripe_transfer_id='sample-transfer-only' WHERE scope_token='sample-project' AND milestone_index=0; UPDATE public.quotes SET milestones=jsonb_set(milestones,'{0,status}','\"released\"') WHERE token='sample-project';")
   stop();start()
   persisted=sql("SELECT amount_total_cents::text||':'||(milestones->0->>'status') FROM public.quotes WHERE token='sample-project';").stdout.strip()
   result['checks']['restart_preserves_quote_and_approved_phase']=persisted=='147000:released'
   result['checks']['restart_preserves_rls']=rows(OTHER,'quotes')=='0' and rows(HOMEOWNER,'quotes')=='1'
  finally:stop()
 if not all(result['checks'].values()):raise SystemExit('An isolated core schema contract check failed.')
 if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
