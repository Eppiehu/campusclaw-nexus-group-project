"""Isolated SQLite authorization + real loopback Streamable HTTP MCP transport.
No production databases, public endpoints or external models are contacted.
"""
import json
import socket
import threading
import time
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash

@pytest.fixture
def mcp_system(monkeypatch):
    import uvicorn
    from mcp.server.fastmcp import FastMCP
    from app.nexus import db, external_mcp
    from app.nexus.models import User, RevokedToken, PromptTemplate, Agent, MCPConnection, Audit
    from app.nexus.security import issue
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    secret='dummy-external-test-credential'
    server=FastMCP('isolated-test',stateless_http=True,json_response=True)
    seen=[];calls=[];redirect=[False];paths=[]
    @server.tool()
    def echo(topic:str)->str:
        calls.append(topic)
        return 'fact:'+topic+' '+secret
    @server.tool()
    def forbidden()->str:return 'must not be listed'
    inner=server.streamable_http_app()
    async def capture(scope,receive,send):
        if scope['type']=='http':
            seen.append(dict(scope['headers']));paths.append(scope['path'])
            if redirect[0]:
                await send({'type':'http.response.start','status':307,'headers':[(b'location',b'/private')]})
                await send({'type':'http.response.body','body':b''})
                return
        await inner(scope,receive,send)
    http=uvicorn.Server(uvicorn.Config(capture,host='127.0.0.1',port=port,log_level='error'))
    thread=threading.Thread(target=http.run,daemon=True);thread.start()
    for _ in range(100):
        if http.started:break
        time.sleep(.05)
    assert http.started
    monkeypatch.setenv('NEXUS_MCP_ALLOW_LOOPBACK','1')
    monkeypatch.setenv('NEXUS_MCP_SECRET_DEMO',secret)
    cfg={'course':{'url':f'http://127.0.0.1:{port}/mcp','classes':['A'],'tools':['echo'],'credential_ref':'NEXUS_MCP_SECRET_DEMO'}}
    monkeypatch.setenv('NEXUS_MCP_SERVERS',json.dumps(cfg))
    monkeypatch.setenv('NEXUS_SIGNING_KEY','isolated-test-signing-key-0123456789abcdef')
    sql=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
    for table in [User.__table__,RevokedToken.__table__,PromptTemplate.__table__,Agent.__table__,MCPConnection.__table__,Audit.__table__]:table.create(sql)
    monkeypatch.setattr(db,'engine',lambda *args:sql)
    with db.transaction() as session:
        users=[User(username=n,password_hash=generate_password_hash('test-only'),role=r,class_id=c) for n,r,c in [('ta','teacher','A'),('tb','teacher','B'),('sa','student','A')]]
        session.add_all(users);session.flush()
        tokens={u.username:issue(u) for u in users}
    from app.nexus import create_app
    app=create_app({'TESTING':True});client=app.test_client()
    def request(actor,method,path,**kwargs):
        headers={'Authorization':'Bearer '+tokens[actor]} if actor else {}
        return client.open('/api/nexus'+path,method=method,headers=headers,**kwargs)
    state=SimpleNamespace(request=request,tokens=tokens,secret=secret,cfg=cfg,seen=seen,calls=calls,external=external_mcp,redirect=redirect,paths=paths)
    yield state
    http.should_exit=True;thread.join(5);sql.dispose()

def ready(s):
    row=s.request('ta','POST','/mcp/connections',json={'name':'课程工具','server_key':'course'})
    assert row.status_code==201
    cid=row.json['id']
    tested=s.request('ta','POST',f'/mcp/connections/{cid}/test')
    assert tested.status_code==200,tested.json
    assert [t['name'] for t in tested.json['tools']]==['echo']
    assert tested.json['tools'][0]['parameters']['properties']['topic']['type']=='string'
    assert s.secret not in json.dumps(tested.json)
    return cid,tested.json['tools'][0]['binding']

def test_http_binding_invocation_and_isolation(mcp_system):
    s=mcp_system;cid,binding=ready(s)
    agent=s.request('ta','POST','/agents',json={'name':'外部工具助手','tools':[binding]}).json
    call={'id':'call-test-1','function':{'name':binding,'arguments':json.dumps({'topic':'photosynthesis'})}}
    result=s.external.invoke(s.tokens['sa'],agent['id'],call)
    assert result['tool_call_id']=='call-test-1'
    value=json.loads(result['content']);assert not value['isError']
    assert 'fact:photosynthesis' in result['content'] and s.secret not in result['content']
    assert any(h.get(b'authorization')==('Bearer '+s.secret).encode() and h.get(b'x-nexus-class-id')==b'A' for h in s.seen)
    assert all(s.tokens['sa'].encode() not in h.values() for h in s.seen)
    before=len(s.calls)
    invalid={**call,'function':{**call['function'],'arguments':'{"topic":"test","class_id":"B"}'}}
    assert json.loads(s.external.invoke(s.tokens['sa'],agent['id'],invalid)['content'])['isError']
    assert len(s.calls)==before
    assert s.request('tb','GET','/mcp/connections').json==[]
    assert s.request('tb','POST',f'/mcp/connections/{cid}/test').status_code==404
    assert s.request('tb','POST','/agents',json={'name':'越权','tools':[binding]}).status_code==400
    assert json.loads(s.external.invoke(s.tokens['tb'],agent['id'],call)['content'])['isError']
    s.request('ta','PATCH',f"/agents/{agent['id']}",json={'tools':[]})
    assert json.loads(s.external.invoke(s.tokens['sa'],agent['id'],call)['content'])['isError']
    assert len(s.calls)==before

def test_roles_unapproved_and_untested(mcp_system):
    s=mcp_system
    assert s.request(None,'GET','/mcp/connections').status_code==401
    assert s.request('sa','GET','/mcp/connections').status_code==403
    assert s.request('ta','POST','/mcp/connections',json={'name':'bad','server_key':'unknown'}).status_code==400
    assert s.request('ta','POST','/mcp/connections',json={'name':'bad','server_key':'course','url':'http://169.254.169.254'}).status_code==400
    row=s.request('ta','POST','/mcp/connections',json={'name':'not-tested','server_key':'course'}).json
    assert s.request('ta','POST','/agents',json={'name':'bad','tools':[f"ext_{row['id']}__echo"]}).status_code==400

def test_disable_failure_and_config_rotation(mcp_system,monkeypatch):
    s=mcp_system;cid,binding=ready(s)
    agent=s.request('ta','POST','/agents',json={'name':'demo','tools':[binding]}).json
    call={'id':'call-stop','function':{'name':binding,'arguments':'{"topic":"test"}'}}
    monkeypatch.setenv('NEXUS_MCP_SECRET_DEMO','rotated-dummy-secret')
    assert s.request('ta','GET','/mcp/tools').json==[]
    assert json.loads(s.external.invoke(s.tokens['sa'],agent['id'],call)['content'])['isError']
    assert not s.calls
    s.request('ta','PATCH',f'/mcp/connections/{cid}',json={'enabled':False})
    assert s.request('ta','POST',f'/mcp/connections/{cid}/test').status_code==409
    s.request('ta','PATCH',f'/mcp/connections/{cid}',json={'enabled':True})
    async def broken(*args,**kwargs):raise RuntimeError('remote echoed '+s.secret)
    monkeypatch.setattr(s.external,'remote',broken)
    failed=s.request('ta','POST',f'/mcp/connections/{cid}/test')
    assert failed.status_code==502 and failed.json['state']=='failed'
    assert s.secret not in json.dumps(failed.json)

def test_no_arbitrary_network(mcp_system,monkeypatch):
    s=mcp_system
    monkeypatch.delenv('NEXUS_MCP_ALLOW_LOOPBACK')
    with pytest.raises(ValueError):s.external.config('course','A')
    s.cfg['course']['url']='http://169.254.169.254/mcp'
    monkeypatch.setenv('NEXUS_MCP_SERVERS',json.dumps(s.cfg))
    with pytest.raises(ValueError):s.external.config('course','A')

def test_builtin_dispatch_preserved_and_round_limit(monkeypatch):
    from app.nexus import mcp_client,external_mcp
    executed=[]
    async def builtin(allowed,token=None,agent_id=None,calls=None):
        executed.append(('builtin',allowed))
        return [{'role':'tool','tool_call_id':c['id'],'content':'{}'} for c in calls]
    def remote(token,agent,call):
        executed.append(('external',call['id']))
        return {'role':'tool','tool_call_id':call['id'],'content':'{}'}
    monkeypatch.setattr(mcp_client,'exchange',builtin)
    monkeypatch.setattr(external_mcp,'invoke',remote)
    calls=[{'id':'external','function':{'name':'ext_1__echo','arguments':'{}'}},{'id':'builtin','function':{'name':'lecture_search','arguments':'{}'}}]
    allowed=['lecture_search','ext_1__echo']
    assert [r['tool_call_id'] for r in mcp_client.invoke(allowed,'token',1,calls)]==['external','builtin']
    assert executed[0]==('builtin',['lecture_search'])
    executed.clear()
    assert all(json.loads(r['content'])['isError'] for r in mcp_client.invoke(allowed,'token',1,calls*3))
    assert executed==[]

def test_redirect_and_remote_schema_references_rejected(mcp_system):
    s=mcp_system
    for schema in ({'$ref':'http://169.254.169.254/'},{'properties':{'x':{'pattern':'(a+)+$'}}}):
        with pytest.raises(ValueError):s.external.safe_schema(schema)
    cid,_=ready(s)
    s.redirect[0]=True
    response=s.request('ta','POST',f'/mcp/connections/{cid}/test')
    assert response.status_code==502 and response.json['state']=='failed'
    assert '/private' not in s.paths

