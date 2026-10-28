from pathlib import Path
import importlib.util,os,stat,json
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('recipient_configure',ROOT/'tools/configure.py');config=importlib.util.module_from_spec(spec);spec.loader.exec_module(config)

def test_private_roundtrip(tmp_path):
 folder=tmp_path/'private';folder.mkdir(mode=0o700);path=folder/'runtime.env'
 config.write_env(path,{'SUPABASE_URL':'http://127.0.0.1:54321','SUPABASE_SERVICE_ROLE_KEY':'example-private-value'})
 assert config.read_env(path)['SUPABASE_SERVICE_ROLE_KEY']=='example-private-value'
 assert stat.S_IMODE(path.stat().st_mode)==0o600

def test_public_or_linked_key_file_is_refused(tmp_path):
 folder=tmp_path/'private';folder.mkdir(mode=0o700);target=folder/'shared.env';target.write_text('VALUE=example\n');target.chmod(0o644)
 with pytest.raises(ValueError):config.read_env(target)
 target.chmod(0o600);linked=folder/'linked.env';linked.symlink_to(target)
 with pytest.raises(ValueError):config.read_env(linked)
 assert target.read_text()=='VALUE=example\n'

def test_checkout_is_refused():
 with pytest.raises(ValueError):config.private_parent(ROOT/'runtime.env')

def test_frontend_export_contains_public_fields_only(tmp_path,monkeypatch,capsys):
 folder=tmp_path/'private';folder.mkdir(mode=0o700);path=folder/'runtime.env'
 config.write_env(path,{'SUPABASE_URL':'http://127.0.0.1:54321','SUPABASE_ANON_KEY':'example-public-value','SUPABASE_SERVICE_ROLE_KEY':'example-private-value','STRIPE_SECRET_KEY_TEST':'example-payment-private-value'})
 monkeypatch.setattr('sys.argv',['configure.py','frontend','--env-file',str(path)])
 config.main();output=capsys.readouterr().out;public=config.read_env(folder/'frontend-public.env')
 assert set(public)=={'VITE_API_URL','VITE_SUPABASE_URL','VITE_SUPABASE_ANON_KEY','VITE_MAPBOX_ACCESS_TOKEN'}
 assert not any('private-value' in v for v in public.values())
 assert 'example-public-value' not in output and 'example-private-value' not in output

def test_local_supabase_import_is_private(tmp_path,monkeypatch,capsys):
 from types import SimpleNamespace
 folder=tmp_path/'private';folder.mkdir(mode=0o700);path=folder/'runtime.env'
 def status(command,**kwargs):
  assert command==['supabase','status','--output','env']
  assert kwargs['capture_output'] is True
  return SimpleNamespace(returncode=0,stdout='API_URL="http://127.0.0.1:54321"\nANON_KEY="example-client"\nSERVICE_ROLE_KEY="example-private"\nDB_URL="postgresql://unused"\n')
 monkeypatch.setattr(config.subprocess,'run',status)
 monkeypatch.setattr('sys.argv',['configure.py','from-local','--env-file',str(path)])
 config.main();output=capsys.readouterr().out;values=config.read_env(path)
 assert values['SUPABASE_URL']=='http://127.0.0.1:54321'
 assert values['SUPABASE_SERVICE_ROLE_KEY']=='example-private'
 assert 'DB_URL' not in values
 assert not any(v in output for v in ['example-client','example-private'])

def test_local_import_rejects_hosted_context(tmp_path,monkeypatch):
 from types import SimpleNamespace
 folder=tmp_path/'private';folder.mkdir(mode=0o700);path=folder/'runtime.env'
 monkeypatch.setattr(config.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout='API_URL="https://example.invalid"\nANON_KEY="example-client"\nSERVICE_ROLE_KEY="example-private"\n'))
 monkeypatch.setattr('sys.argv',['configure.py','from-local','--env-file',str(path)])
 with pytest.raises(ValueError):config.main()
 assert not path.exists()
