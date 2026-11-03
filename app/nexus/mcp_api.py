from flask import Blueprint, abort, g, jsonify, request
from sqlalchemy import select
from .db import transaction, audit
from .models import MCPConnection
from .security import require, scoped
from . import external_mcp as external

bp=Blueprint('mcp_connections',__name__,url_prefix='/api/nexus/mcp')

def public(row):
    ready=False
    try:ready=row.enabled and row.state=='ready' and external.config(row.server_key,row.class_id)['fingerprint']==row.fingerprint
    except ValueError:pass
    return dict(id=row.id,name=row.name,server_key=row.server_key,enabled=row.enabled,
                state='ready' if ready else ('untested' if row.state=='ready' else row.state),
                tools=[dict(t,binding=f"ext_{row.id}__{t['name']}") for t in row.tools] if ready else [])

@bp.get('/servers')
@require('teacher')
def servers():
    return jsonify([{'key':key} for key,value in external.servers().items() if isinstance(value,dict) and g.user.class_id in value.get('classes',[])])

@bp.get('/connections')
@require('teacher')
def connections():
    with transaction() as db:return jsonify([public(r) for r in db.scalars(select(MCPConnection).where(MCPConnection.class_id==g.user.class_id))])

@bp.post('/connections')
@require('teacher')
def create():
    data=request.get_json(silent=True)
    if not isinstance(data,dict) or set(data)-{'name','server_key'}:raise ValueError('仅接受名称和已批准的服务器别名')
    name=data.get('name');key=data.get('server_key')
    if not isinstance(name,str) or not 1<=len(name.strip())<=100 or not isinstance(key,str) or len(key)>64:raise ValueError('连接字段无效')
    cfg=external.config(key,g.user.class_id)
    with transaction() as db:
        row=MCPConnection(class_id=g.user.class_id,name=name.strip(),server_key=key,credential_ref=cfg['ref'])
        db.add(row);db.flush();audit(db,g.user,'mcp.connection.created',row.id,request_id=g.request_id)
        return jsonify(public(row)),201

@bp.post('/connections/<int:identifier>/test')
@require('teacher')
def test(identifier):
    with transaction() as db:
        row=scoped(db,MCPConnection,identifier,g.user,lock=True)
        if not row.enabled:abort(409)
        try:
            cfg,tools=external.test_connection(row)
            row.tools=tools;row.fingerprint=cfg['fingerprint'];row.credential_ref=cfg['ref'];row.state='ready'
        except Exception:
            row.tools=[];row.fingerprint='';row.state='failed'
        audit(db,g.user,'mcp.connection.test',row.id,success=row.state=='ready',request_id=g.request_id)
        value=public(row)
        if row.state!='ready':value['error']='连接测试失败：请检查服务器、凭据和工具白名单后重试'
        return jsonify(value),200 if row.state=='ready' else 502

@bp.patch('/connections/<int:identifier>')
@require('teacher')
def enable(identifier):
    data=request.get_json(silent=True)
    if not isinstance(data,dict) or set(data)!={'enabled'} or type(data['enabled']) is not bool:raise ValueError('请提供enabled布尔值')
    with transaction() as db:
        row=scoped(db,MCPConnection,identifier,g.user,lock=True);row.enabled=data['enabled']
        if not row.enabled:row.state='untested';row.tools=[];row.fingerprint=''
        audit(db,g.user,'mcp.connection.toggled',row.id,{'enabled':row.enabled},request_id=g.request_id)
        return jsonify(public(row))

@bp.get('/tools')
@require('teacher')
def tools():
    with transaction() as db:
        return jsonify([dict(tool,connection=row.name) for row in db.scalars(select(MCPConnection).where(MCPConnection.class_id==g.user.class_id)) for tool in public(row)['tools']])
