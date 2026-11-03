"""Operator-approved Streamable HTTP MCP connections and live authorization."""
import asyncio
import hashlib
import ipaddress
import json
import os
import re
import socket
from types import SimpleNamespace
from urllib.parse import urlsplit
import httpx
from jsonschema import Draft202012Validator, validate
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from .db import transaction, audit
from .models import Agent, MCPConnection
from .security import authenticate

NAME=re.compile(r'^ext_(\d+)__([A-Za-z0-9_-]{1,40})$')
RESERVED={'auth_token','class_id','user_id','role','agent_id'}

def safe_schema(value,depth=0):
    if depth>8:raise ValueError('工具参数模式过深')
    if isinstance(value,dict):
        if set(value)&{'$ref','$dynamicRef','$recursiveRef','pattern','patternProperties'}:
            raise ValueError('不支持外部引用或正则参数模式')
        for item in value.values():safe_schema(item,depth+1)
    elif isinstance(value,list):
        for item in value:safe_schema(item,depth+1)

def servers():
    try:
        value=json.loads(os.environ.get('NEXUS_MCP_SERVERS','{}'))
        if not isinstance(value,dict):raise ValueError()
        return value
    except Exception:raise ValueError('MCP服务端配置无效') from None

def config(key,klass):
    value=servers().get(key)
    if not isinstance(value,dict) or klass not in value.get('classes',[]):
        raise ValueError('该MCP服务器未获本班授权')
    url=value.get('url','');parsed=urlsplit(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname:
        raise ValueError('MCP地址配置无效')
    loopback=os.environ.get('NEXUS_MCP_ALLOW_LOOPBACK')=='1'
    try:addresses=[ipaddress.ip_address(x[4][0]) for x in socket.getaddrinfo(parsed.hostname,parsed.port or 443,type=socket.SOCK_STREAM)]
    except Exception:raise ValueError('MCP服务器地址无法解析') from None
    if not addresses or any(not a.is_global and not (loopback and a.is_loopback) for a in addresses):
        raise ValueError('MCP地址不在允许的网络范围')
    if parsed.scheme!='https' and not (loopback and parsed.scheme=='http' and all(a.is_loopback for a in addresses)):
        raise ValueError('MCP连接必须使用HTTPS')
    ref=value.get('credential_ref','')
    if not isinstance(ref,str) or (ref and not re.fullmatch(r'NEXUS_MCP_SECRET_[A-Z0-9_]+',ref)):
        raise ValueError('MCP凭据引用配置无效')
    secret=os.environ.get(ref,'') if ref else ''
    if ref and not secret:raise ValueError('MCP凭据未配置')
    allowed=value.get('tools',[])
    if not isinstance(allowed,list) or len(allowed)>20 or any(not isinstance(n,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',n) for n in allowed):
        raise ValueError('MCP工具白名单配置无效')
    fingerprint=hashlib.sha256(json.dumps([value,secret],sort_keys=True).encode()).hexdigest()
    return dict(url=url,ref=ref,secret=secret,allowed=allowed,fingerprint=fingerprint)

def redact(value,secret):
    if isinstance(value,str):return value.replace(secret,'[redacted]') if secret else value
    if isinstance(value,list):return [redact(item,secret) for item in value]
    if isinstance(value,dict):return {redact(key,secret):redact(item,secret) for key,item in value.items()}
    return value

async def remote(cfg,user=None,name=None,arguments=None):
    headers={}
    if cfg['secret']:headers['Authorization']='Bearer '+cfg['secret']
    if user:headers.update({'X-Nexus-Class-Id':user.class_id,'X-Nexus-Role':user.role,'X-Nexus-User-Id':str(user.id)})
    def client_factory(**kwargs):
        async def reject_redirect(response):
            if 300<=response.status_code<400:
                raise httpx.HTTPStatusError('MCP redirects are disabled',request=response.request,response=response)
        kwargs['follow_redirects']=False
        kwargs['trust_env']=False
        kwargs['event_hooks']={'response':[reject_redirect]}
        return httpx.AsyncClient(**kwargs)
    async with asyncio.timeout(20):
        async with streamablehttp_client(cfg['url'],headers=headers,timeout=10,sse_read_timeout=15,httpx_client_factory=client_factory) as (read,write,_):
            async with ClientSession(read,write) as session:
                await session.initialize()
                if name is not None:
                    response=await session.call_tool(name,arguments)
                    value=redact({'isError':bool(response.isError),'content':[c.text for c in response.content if c.type=='text']},cfg['secret'])
                    if len(json.dumps(value))>16000:return {'isError':True,'error':'工具返回过长，已拒绝显示'}
                    return value
                listed=await session.list_tools()
                tools=[]
                for tool in listed.tools:
                    if tool.name not in cfg['allowed']:continue
                    schema=tool.inputSchema
                    if schema.get('type')!='object' or RESERVED & set(schema.get('properties',{})):continue
                    safe_schema(schema)
                    Draft202012Validator.check_schema(schema)
                    schema={**schema,'additionalProperties':False}
                    value=redact({'name':tool.name,'description':(tool.description or '')[:1000],'parameters':schema},cfg['secret'])
                    if len(json.dumps(value))>8000:continue
                    tools.append(value)
                if not tools:raise ValueError('没有可授权的工具')
                return tools

def test_connection(row):
    cfg=config(row.server_key,row.class_id)
    tools=asyncio.run(remote(cfg))
    return cfg,tools

def definition(row,name,klass):
    if row.class_id!=klass or not row.enabled or row.state!='ready':raise PermissionError('MCP连接未就绪')
    cfg=config(row.server_key,klass)
    if cfg['fingerprint']!=row.fingerprint:raise PermissionError('MCP配置已变化，请重新测试')
    tool=next((t for t in row.tools if t['name']==name and name in cfg['allowed']),None)
    if not tool:raise PermissionError('工具不在已测试白名单')
    return cfg,tool

def validate_bindings(db,klass,names):
    for name in names:
        match=NAME.fullmatch(name)
        if not match:raise ValueError('外部工具名称无效')
        row=db.get(MCPConnection,int(match[1]))
        if not row or row.class_id!=klass:raise ValueError('MCP连接不可访问')
        try:definition(row,match[2],klass)
        except (ValueError,PermissionError) as error:raise ValueError(str(error)) from None

def discover(token,agent_id):
    if not token:return []
    with transaction() as db:
        user,_=authenticate(db,token);agent=db.get(Agent,agent_id)
        if not agent or not agent.enabled or agent.class_id!=user.class_id:raise PermissionError('应用不可访问')
        definitions=[]
        for name in agent.tools:
            match=NAME.fullmatch(name)
            if not match:continue
            row=db.get(MCPConnection,int(match[1]))
            if not row:continue
            try:_,tool=definition(row,match[2],user.class_id)
            except (PermissionError,ValueError):continue
            definitions.append({'type':'function','function':{'name':name,'description':tool['description'],'parameters':tool['parameters']}})
        return definitions

def invoke(token,agent_id,call):
    success=False;actor=None
    try:
        name=call['function']['name'];match=NAME.fullmatch(name)
        with transaction() as db:
            authenticated,_=authenticate(db,token)
            actor=SimpleNamespace(id=authenticated.id,class_id=authenticated.class_id,role=authenticated.role)
            agent=db.get(Agent,agent_id)
            if not match or not agent or not agent.enabled or agent.class_id!=actor.class_id or name not in agent.tools:
                raise PermissionError()
            row=db.get(MCPConnection,int(match[1]))
            if not row:raise PermissionError()
            cfg,tool=definition(row,match[2],actor.class_id)
            arguments=json.loads(call['function']['arguments'])
            if len(json.dumps(arguments))>8000:raise ValueError('工具参数过长')
            if not isinstance(arguments,dict) or RESERVED & set(arguments):raise PermissionError()
            validate(arguments,tool['parameters'])
        value=asyncio.run(remote(cfg,actor,match[2],arguments))
        success=not value['isError']
    except Exception:
        value={'isError':True,'error':'外部工具不可用或未获授权，请检查连接与绑定'}
    if actor:
        with transaction() as db:audit(db,actor,'mcp.external.call',agent_id,{'tool':call['function'].get('name','')[:64],'tool_call_id':str(call.get('id',''))[:100]},success)
    return {'role':'tool','tool_call_id':call['id'],'content':json.dumps(value,ensure_ascii=False)}
