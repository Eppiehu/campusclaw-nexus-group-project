from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
import re
import uuid
from flask import Blueprint, Response, abort, g, jsonify, request, session, stream_with_context, send_file
from sqlalchemy import select, func, delete as sql_delete
from werkzeug.security import check_password_hash
from .db import transaction, audit
from .security import require, scoped, issue, authenticate
from .models import (User, RevokedToken, PromptTemplate, Skill, Agent, Material, MaterialVersion, Chunk,
 KnowledgeGap, Conversation, Message, Assignment, Paper, Submission, WrongQuestion, WeeklyReport,
 Task, Audit, LearningEvent, now, week_start)
from .schemas import Login, AssignmentInput, LectureTitle, rubric_text
from .jobs import schedule, dispatch, redis_connection, calculate, claim_due_submissions

bp=Blueprint('nexus',__name__,url_prefix='/api/nexus')


def data():
    value=request.get_json(silent=True)
    if not isinstance(value,dict):raise ValueError('请提交JSON对象')
    return value


def output(row,exclude=()):
    payload={c.name:(getattr(row,c.name).isoformat() if isinstance(getattr(row,c.name),datetime) else getattr(row,c.name))
            for c in row.__table__.columns if c.name not in exclude}
    if isinstance(row,Assignment) and 'rubric' in payload:payload['rubric']=rubric_text(payload['rubric'])
    return payload


def text_field(values,name,maximum=4000):
    value=values.get(name)
    if not isinstance(value,str) or not value.strip() or len(value)>maximum:raise ValueError(name+'格式不正确')
    return value.strip()


def skill_text(values,name,maximum,label):
    value=values.get(name)
    if not isinstance(value,str) or not value.strip() or len(value.strip())>maximum:raise ValueError(f'{label}须为1至{maximum}字')
    return value.strip()


@bp.post('/login')
def login():
    values=Login.model_validate(data())
    limiter=redis_connection();key='nexus:login:'+hashlib.sha256((request.remote_addr or '').encode()).hexdigest()
    count=limiter.incr(key)
    if count==1:limiter.expire(key,60)
    if count>25:abort(429)
    with transaction() as db:
        user=db.scalar(select(User).where(User.username==values.username))
        if not user or not check_password_hash(user.password_hash,values.password):
            audit(db,user,'login.failed',success=False,request_id=g.request_id)
            return jsonify(error='用户名或密码错误'),401
        # Re-authentication revokes an explicitly supplied previous token.
        previous=request.headers.get('Authorization','').removeprefix('Bearer ')
        if previous:
            try:
                old,claims=authenticate(db,previous)
                if old.id==user.id:db.merge(RevokedToken(jti=claims['jti'],expires_at=datetime.fromtimestamp(claims['exp'],timezone.utc)))
            except PermissionError:pass
        token=issue(user);session.clear();session.update(user_id=user.id,role=user.role,class_id=user.class_id)
        audit(db,user,'login',request_id=g.request_id)
        return jsonify(token=token,user=output(user,('password_hash',)))


@bp.post('/logout')
@require()
def logout():
    with transaction() as db:
        db.merge(RevokedToken(jti=g.claims['jti'],expires_at=datetime.fromtimestamp(g.claims['exp'],timezone.utc)))
        audit(db,g.user,'logout',request_id=g.request_id)
    session.clear();return jsonify(ok=True)


@bp.get('/me')
@require()
def me():return jsonify(output(g.user,('password_hash',)))


@bp.get('/students')
@require('teacher')
def students():
    with transaction() as db:return jsonify([output(u,('password_hash',)) for u in db.scalars(select(User).where(User.class_id==g.user.class_id,User.role=='student'))])


@bp.get('/templates')
@require()
def templates():
    with transaction() as db:return jsonify([output(r) for r in db.scalars(select(PromptTemplate).where(PromptTemplate.class_id==g.user.class_id))])


@bp.post('/templates')
@require('teacher')
def new_template():
    values=data()
    with transaction() as db:
        row=PromptTemplate(class_id=g.user.class_id,name=text_field(values,'name',100),content=text_field(values,'content'))
        db.add(row);db.flush();return jsonify(output(row)),201


@bp.patch('/templates/<int:identifier>')
@require('teacher')
def edit_template(identifier):
    values=data()
    with transaction() as db:
        row=scoped(db,PromptTemplate,identifier,g.user,lock=True)
        for name in ['name','content']:
            if name in values:setattr(row,name,text_field(values,name,100 if name=='name' else 4000))
        if 'enabled' in values:
            if type(values['enabled']) is not bool:raise ValueError('enabled须为布尔值')
            row.enabled=values['enabled']
        return jsonify(output(row))


@bp.delete('/templates/<int:identifier>')
@require('teacher')
def delete_template(identifier):
    with transaction() as db:
        row=scoped(db,PromptTemplate,identifier,g.user,lock=True)
        for agent in db.scalars(select(Agent).where(Agent.class_id==row.class_id,Agent.template_id==row.id)):
            agent.template_id=None
        db.flush()
        db.delete(row)
        audit(db,g.user,'template.deleted',identifier,request_id=g.request_id)
    return jsonify(ok=True)


@bp.get('/skills')
@require()
def skills():
    with transaction() as db:return jsonify([output(r) for r in db.scalars(select(Skill).where(Skill.class_id==g.user.class_id))])


@bp.post('/skills')
@require('teacher')
def upload_skill():
    from app.skill_files import parse_skill
    if request.is_json:
        values=data()
        name=skill_text(values,'name',64,'技能标题')
        description=skill_text(values,'description',2000,'适用条件')
        body=skill_text(values,'body',2000,'技能正文')
        source=values.get('source_text') or ''
        if not isinstance(source,str) or len(source)>8000:raise ValueError('技能原文不得超过8000字')
        with transaction() as db:
            row=Skill(class_id=g.user.class_id,name=name,description=description,body=body,source_text=source)
            db.add(row);db.flush();audit(db,g.user,'skill.uploaded',row.id,request_id=g.request_id)
            return jsonify(output(row)),201
    file=request.files.get('file')
    if not file or not file.filename.lower().endswith(('.md','.txt')):raise ValueError('仅支持TXT或Markdown技能')
    try:parsed=parse_skill(file.read(32001).decode('utf-8-sig'))
    except UnicodeError:raise ValueError('请使用UTF-8编码')
    with transaction() as db:
        row=Skill(class_id=g.user.class_id,name=parsed['name'],description=parsed['trigger_text'],body=parsed['description'],source_text=parsed['source_text'])
        db.add(row);db.flush();audit(db,g.user,'skill.uploaded',row.id,request_id=g.request_id)
        return jsonify(output(row)),201


@bp.patch('/skills/<int:identifier>')
@require('teacher')
def update_skill(identifier):
    values=data()
    with transaction() as db:
        row=scoped(db,Skill,identifier,g.user,lock=True)
        changed=False
        if 'enabled' in values:
            if type(values['enabled']) is not bool:raise ValueError('enabled须为布尔值')
            row.enabled=values['enabled'];changed=True
        if 'name' in values:
            row.name=skill_text(values,'name',64,'技能标题');changed=True
        if 'description' in values:
            row.description=skill_text(values,'description',2000,'适用条件');changed=True
        if 'body' in values:
            row.body=skill_text(values,'body',2000,'技能正文');changed=True
        if not changed:raise ValueError('没有可更新的字段')
        audit(db,g.user,'skill.updated' if 'name' in values or 'description' in values or 'body' in values else 'skill.toggled',row.id,{'enabled':row.enabled},request_id=g.request_id)
        return jsonify(output(row))


@bp.delete('/skills/<int:identifier>')
@require('teacher')
def delete_skill(identifier):
    with transaction() as db:
        row=scoped(db,Skill,identifier,g.user,lock=True)
        for message in db.scalars(select(Message).where(Message.skill_id==row.id)):
            message.skill_id=None
        for agent in db.scalars(select(Agent).where(Agent.class_id==row.class_id)):
            if row.id in (agent.skill_ids or []):
                agent.skill_ids=[item for item in agent.skill_ids if item!=row.id]
        db.delete(row)
        audit(db,g.user,'skill.deleted',identifier,request_id=g.request_id)
    return jsonify(ok=True)


@bp.get('/agents')
@require()
def agents():
    with transaction() as db:
        query=select(Agent).where(Agent.class_id==g.user.class_id)
        if g.user.role=='student':query=query.where(Agent.enabled==True)
        return jsonify([output(r) for r in db.scalars(query)])


def agent_values(db,row,values):
    if 'name' in values:row.name=text_field(values,'name',100)
    if 'prompt' in values:row.prompt=text_field(values,'prompt')
    if 'enabled' in values:
        if type(values['enabled']) is not bool:raise ValueError('enabled须为布尔值')
        row.enabled=values['enabled']
    if 'template_id' in values:
        if values['template_id'] is not None:scoped(db,PromptTemplate,values['template_id'],g.user)
        row.template_id=values['template_id']
    for key,model in [('material_ids',Material),('skill_ids',Skill)]:
        if key in values:
            if not isinstance(values[key],list) or len(values[key])>50:raise ValueError('绑定数量无效')
            for value in values[key]:scoped(db,model,value,g.user)
            setattr(row,key,list(dict.fromkeys(values[key])))
    if 'tools' in values:
        from .mcp_client import TOOL_NAMES
        if not isinstance(values['tools'],list) or set(values['tools'])-TOOL_NAMES:raise ValueError('工具名称无效')
        row.tools=list(dict.fromkeys(values['tools']))


@bp.post('/agents')
@require('teacher')
def new_agent():
    values=data()
    with transaction() as db:
        row=Agent(class_id=g.user.class_id,name=text_field(values,'name',100));agent_values(db,row,values)
        db.add(row);db.flush();return jsonify(output(row)),201


@bp.patch('/agents/<int:identifier>')
@require('teacher')
def edit_agent(identifier):
    with transaction() as db:
        row=scoped(db,Agent,identifier,g.user,lock=True);agent_values(db,row,data())
        audit(db,g.user,'agent.updated',row.id,request_id=g.request_id);return jsonify(output(row))


@bp.delete('/agents/<int:identifier>')
@require('teacher')
def delete_agent(identifier):
    with transaction() as db:
        row=scoped(db,Agent,identifier,g.user,lock=True)
        conversation_ids=list(db.scalars(select(Conversation.id).where(Conversation.agent_id==row.id)))
        if conversation_ids:
            db.execute(sql_delete(Message).where(Message.conversation_id.in_(conversation_ids)))
            db.execute(sql_delete(Conversation).where(Conversation.id.in_(conversation_ids)))
        db.delete(row)
        audit(db,g.user,'agent.deleted',identifier,request_id=g.request_id)
    return jsonify(ok=True)


@bp.get('/materials')
@require()
def materials():
    with transaction() as db:
        rows=db.scalars(select(Material).where(Material.class_id==g.user.class_id).order_by(Material.id.desc()))
        result=[]
        for row in rows:
            versions=db.scalars(select(MaterialVersion).where(MaterialVersion.material_id==row.id).order_by(MaterialVersion.number.desc())).all()
            if g.user.role=='student' and not row.active_version_id:continue
            value=output(row)
            value['versions']=[output(v,('content',)) for v in versions if g.user.role=='teacher' or v.id==row.active_version_id]
            result.append(value)
        return jsonify(result)


def parse_material():
    file=request.files.get('file')
    if not file:raise ValueError('请选择材料文件')
    value=file.read();name=file.filename.lower()
    if name.endswith('.pdf'):
        from pypdf import PdfReader
        try:
            reader=PdfReader(io.BytesIO(value));content='\n'.join(page.extract_text() or '' for page in reader.pages[:200])
        except Exception:raise ValueError('PDF解析失败')
    elif name.endswith(('.txt','.md')):
        try:content=value.decode('utf-8-sig')
        except UnicodeError:raise ValueError('请上传UTF-8文本')
    else:raise ValueError('仅支持TXT、Markdown和可提取文字的PDF')
    if not content.strip() or len(content)>500000:raise ValueError('材料为空或正文超过50万字')
    return content


TITLE_LIMIT=20
TITLE_SOURCE_LIMIT=800


def lecture_excerpt(content):
    text=content.replace('\r\n','\n').replace('\r','\n')
    text=re.sub(r'```[\s\S]*?```',' ',text)
    text=re.sub(r'!\[[^\]]*\]\([^)]*\)',' ',text)
    text=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',text)
    text=re.sub(r'(?m)^#{1,6}\s*','',text)
    text=re.sub(r'[*_`>]+','',text)
    text=re.sub(r'[ \t]+',' ',text)
    text=re.sub(r'\n+','\n',text).strip()
    if len(text)>TITLE_SOURCE_LIMIT:text=text[:TITLE_SOURCE_LIMIT]
    return text


def bounded_title(raw):
    title=re.sub(r'\s+','',raw or '')
    title=title.strip('。！？；，、,.!?;:："“”\'‘’《》【】[]()（）#*_`>-')
    if len(title)<=TITLE_LIMIT:return title
    window=title[:TITLE_LIMIT]
    for mark in ('，','、','；','：',',',';'):
        pos=window.rfind(mark)
        if pos>=8:
            window=window[:pos]
            break
    return window.strip('，、；：,;') or title[:TITLE_LIMIT]


def local_title(excerpt):
    parts=[part.strip() for part in re.split(r'[。！？!?\n]',excerpt) if part.strip()]
    useful=[]
    for part in parts:
        compact=re.sub(r'\s+','',part)
        if re.fullmatch(r'第?[0-9一二三四五六七八九十百零]+[章节课讲篇部]?',compact):continue
        if compact in ('目录','前言','引言','摘要'):continue
        useful.append(part)
    if not useful:return '未命名讲义'
    return bounded_title(useful[0]) or '未命名讲义'


def material_title(content, supplied):
    title=(supplied or '').strip()
    if len(title)>200:raise ValueError('材料标题不能超过200字')
    if title:return title
    excerpt=lecture_excerpt(content)
    if not excerpt:return '未命名讲义'
    if os.environ.get('OPENAI_API_KEY') and getattr(g,'user',None) is not None:
        try:
            from .llm import structured
            result=structured('根据讲义摘录概括一个中文标题，不超过20个字，不要标点、引号或换行。摘录如果已经截断，只根据可见内容概括。',{'excerpt':excerpt},LectureTitle,g.user.id,getattr(g,'request_id',None))
            summarized=bounded_title(result.title)
            if summarized:return summarized
        except Exception:
            pass
    return local_title(excerpt)


def parse_chunk_options(source, default='hierarchy'):
    strategy=source.get('strategy') or default
    if not isinstance(strategy,str) or strategy.strip() not in ('auto','hierarchy','custom'):raise ValueError('切片方式不正确')
    strategy=strategy.strip();options={'strategy':strategy}
    if strategy=='auto':return options
    try:
        maximum=int(source.get('max_chars') or 800);percent=int(source.get('overlap_pct') or 10)
    except (TypeError,ValueError):raise ValueError('切片长度或重叠度不正确')
    if not 100<=maximum<=2000 or not 0<=percent<=50:raise ValueError('切片长度须为100至2000，重叠度须为0至50')
    options.update(max_chars=maximum,overlap_pct=percent)
    if strategy=='custom':
        delimiter=source.get('delimiter') or 'newline'
        if not isinstance(delimiter,str) or delimiter.strip() not in ('blank','newline','period'):raise ValueError('分段标识符不正确')
        flag=lambda name: source.get(name) in (True,1,'1','true')
        options.update(delimiter=delimiter.strip(),collapse_ws=flag('collapse_ws'),strip_urls=flag('strip_urls'))
    return options


def chunk_options():
    return parse_chunk_options(request.form)


def add_version(db,material,content,options=None,state='indexing'):
    number=(db.scalar(select(func.max(MaterialVersion.number)).where(MaterialVersion.material_id==material.id)) or 0)+1
    row=MaterialVersion(material_id=material.id,class_id=material.class_id,number=number,content=content,
                         sha256=hashlib.sha256(content.encode()).hexdigest(),state=state,chunk_options=options or {'strategy':'hierarchy'})
    db.add(row);db.flush();return row


@bp.post('/materials')
@require('teacher')
def upload_material():
    content=parse_material();title=material_title(content,request.form.get('title',''));options=chunk_options()
    with transaction() as db:
        row=Material(class_id=g.user.class_id,owner_id=g.user.id,title=title);db.add(row);db.flush()
        version=add_version(db,row,content,options);identifier=row.id;version_id=version.id
        audit(db,g.user,'material.uploaded',identifier,request_id=g.request_id)
    task=schedule('index',version_id,g.user.class_id)
    return jsonify(id=identifier,version_id=version_id,task_id=task,title=title),202


@bp.post('/materials/<int:identifier>/versions')
@require('teacher')
def replace_material(identifier):
    content=parse_material();options=chunk_options()
    with transaction() as db:
        row=scoped(db,Material,identifier,g.user,lock=True);version=add_version(db,row,content,options);version_id=version.id
    return jsonify(version_id=version_id,task_id=schedule('index',version_id,g.user.class_id)),202


def readable_version(db,material,user):
    latest=db.scalar(select(MaterialVersion).where(MaterialVersion.material_id==material.id).order_by(MaterialVersion.number.desc()))
    if user.role=='teacher':return latest
    version=db.get(MaterialVersion,material.active_version_id) if material.active_version_id else None
    if version and version.state=='active':return version
    return None


@bp.get('/materials/<int:identifier>/download')
@require()
def download(identifier):
    with transaction() as db:
        row=scoped(db,Material,identifier,g.user)
        version=readable_version(db,row,g.user)
        if not version:abort(404)
        db.add(LearningEvent(user_id=g.user.id,class_id=g.user.class_id,kind='material_view',resource_id=identifier))
        return send_file(io.BytesIO(version.content.encode()),mimetype='text/plain; charset=utf-8',as_attachment=True,download_name=f'material-{identifier}.txt')


@bp.post('/materials/<int:identifier>/withdraw')
@require('teacher')
def withdraw(identifier):
    with transaction() as db:
        row=scoped(db,Material,identifier,g.user,lock=True)
        for version in db.scalars(select(MaterialVersion).where(MaterialVersion.material_id==identifier)):
            version.state='withdrawn'
        row.active_version_id=None;audit(db,g.user,'material.withdrawn',row.id,request_id=g.request_id)
    return jsonify(ok=True)


@bp.put('/materials/<int:identifier>/content')
@require('teacher')
def edit_material_content(identifier):
    values=data();content=values.get('content')
    if not isinstance(content,str) or not content.strip() or len(content)>500000:raise ValueError('材料为空或正文超过50万字')
    content=content.strip();chosen=parse_chunk_options(values) if 'strategy' in values else None
    with transaction() as db:
        row=scoped(db,Material,identifier,g.user,lock=True)
        previous=db.scalar(select(MaterialVersion).where(MaterialVersion.material_id==row.id).order_by(MaterialVersion.number.desc()))
        options=chosen or (dict(previous.chunk_options or {'strategy':'hierarchy'}) if previous else {'strategy':'hierarchy'})
        version=add_version(db,row,content,options,state='indexing');version_id=version.id
        audit(db,g.user,'material.edited',row.id,request_id=g.request_id)
    return jsonify(version_id=version_id,task_id=schedule('index',version_id,g.user.class_id)),202


@bp.post('/materials/<int:identifier>/publish')
@require('teacher')
def publish_material(identifier):
    with transaction() as db:
        row=scoped(db,Material,identifier,g.user,lock=True)
        version=db.scalar(select(MaterialVersion).where(MaterialVersion.material_id==row.id).order_by(MaterialVersion.number.desc()))
        if not version:abort(404)
        if row.active_version_id==version.id and version.state=='active':return jsonify(ok=True)
        version.state='indexing';version.error=None;version_id=version.id
        audit(db,g.user,'material.published',row.id,request_id=g.request_id)
    return jsonify(version_id=version_id,task_id=schedule('index',version_id,g.user.class_id)),202


@bp.delete('/materials/<int:identifier>')
@require('teacher')
def delete_material(identifier):
    with transaction() as db:
        row=scoped(db,Material,identifier,g.user,lock=True)
        version_ids=list(db.scalars(select(MaterialVersion.id).where(MaterialVersion.material_id==row.id)))
        if version_ids:
            db.execute(sql_delete(Chunk).where(Chunk.version_id.in_(version_ids)))
            for gap in db.scalars(select(KnowledgeGap).where(KnowledgeGap.version_id.in_(version_ids))):
                gap.version_id=None
            db.flush()
            row.active_version_id=None
            db.execute(sql_delete(MaterialVersion).where(MaterialVersion.id.in_(version_ids)))
        for agent in db.scalars(select(Agent).where(Agent.class_id==row.class_id)):
            if row.id in (agent.material_ids or []):
                agent.material_ids=[item for item in agent.material_ids if item!=row.id]
        db.delete(row)
        audit(db,g.user,'material.deleted',identifier,request_id=g.request_id)
    return jsonify(ok=True)


@bp.post('/search')
@require()
def search():
    from .retrieval import search as retrieve
    values=data();question=text_field(values,'query',1000)
    with transaction() as db:
        agent=scoped(db,Agent,values.get('agent_id'),g.user)
        return jsonify(hits=retrieve(db,g.user,question,agent.material_ids))


@bp.get('/gaps')
@require('teacher')
def gaps():
    with transaction() as db:return jsonify([output(r) for r in db.scalars(select(KnowledgeGap).where(KnowledgeGap.class_id==g.user.class_id).order_by(KnowledgeGap.heat.desc()))])


@bp.post('/gaps/<int:identifier>/review')
@require('teacher')
def review_gap(identifier):
    values=data();decision=values.get('decision')
    if decision not in ('approve','reject'):raise ValueError('请选择通过或驳回')
    with transaction() as db:
        gap=scoped(db,KnowledgeGap,identifier,g.user,lock=True)
        if decision=='reject':
            if gap.state not in ('pending','approved','indexing','filled','index_failed'):abort(409)
            gap.teacher_id=g.user.id;gap.note=str(values.get('note',''))[:2000];gap.state='rejected'
            audit(db,g.user,'gap.rejected',gap.id,request_id=g.request_id)
            return jsonify(output(gap))
        if gap.state not in ('pending','approved','rejected','index_failed'):abort(409)
        gap.teacher_id=g.user.id;gap.note=str(values.get('note',''))[:2000];gap.state='approved'
        audit(db,g.user,'gap.approved',gap.id,request_id=g.request_id)
        return jsonify(output(gap))


@bp.post('/gaps/<int:identifier>/supplement')
@require('teacher')
def supplement(identifier):
    revising=None
    if request.files.get('file'):
        content=parse_material();title=material_title(content,request.form.get('title',''));options=chunk_options()
    else:
        values=data()
        revising=values.get('material_id')
        if revising:
            content=values.get('content')
            if not isinstance(content,str) or not content.strip() or len(content)>500000:raise ValueError('材料为空或正文超过50万字')
            content=content.strip()
            supplied=values.get('title')
            if supplied is not None and (not isinstance(supplied,str) or len(supplied.strip())>200):raise ValueError('材料标题不能超过200字')
            title=(supplied or '').strip()
            options=parse_chunk_options(values) if values.get('strategy') else None
        else:
            content=text_field(values,'content',50000);title=text_field(values,'title',200)
            options=parse_chunk_options(values) if values.get('strategy') else {'strategy':'hierarchy'}
    with transaction() as db:
        gap=scoped(db,KnowledgeGap,identifier,g.user,lock=True)
        if gap.state not in ('approved','index_failed'):abort(409)
        if revising:
            row=scoped(db,Material,revising,g.user,lock=True)
            if title:row.title=title
            else:title=row.title
            if options is None:
                previous=db.scalar(select(MaterialVersion).where(MaterialVersion.material_id==row.id).order_by(MaterialVersion.number.desc()))
                options=dict(previous.chunk_options or {'strategy':'hierarchy'}) if previous else {'strategy':'hierarchy'}
        else:
            row=Material(class_id=g.user.class_id,owner_id=g.user.id,title=title);db.add(row);db.flush()
        version=add_version(db,row,content,options);gap.version_id=version.id;gap.teacher_id=g.user.id;gap.state='indexing'
        # The teacher explicitly adds the supplemental lecture to this class's assistants.
        for agent in db.scalars(select(Agent).where(Agent.class_id==g.user.class_id)):
            agent.material_ids=list(dict.fromkeys(agent.material_ids+[row.id]))
        version_id=version.id;material_id=row.id;title=row.title
        audit(db,g.user,'gap.supplemented',gap.id,{'material_id':material_id},request_id=g.request_id)
    return jsonify(id=material_id,version_id=version_id,title=title,task_id=schedule('index',version_id,g.user.class_id)),202


@bp.delete('/gaps/<int:identifier>')
@require('teacher')
def delete_gap(identifier):
    with transaction() as db:
        row=scoped(db,KnowledgeGap,identifier,g.user,lock=True)
        db.delete(row)
        audit(db,g.user,'gap.deleted',identifier,request_id=g.request_id)
    return jsonify(ok=True)


@bp.get('/conversations')
@require()
def conversations():
    with transaction() as db:return jsonify([output(r) for r in db.scalars(select(Conversation).where(Conversation.class_id==g.user.class_id,Conversation.user_id==g.user.id).order_by(Conversation.id.desc()))])


@bp.post('/conversations')
@require()
def new_conversation():
    values=data()
    with transaction() as db:
        agent=scoped(db,Agent,values.get('agent_id'),g.user)
        if not agent.enabled:abort(409)
        row=Conversation(user_id=g.user.id,class_id=g.user.class_id,agent_id=agent.id);db.add(row);db.flush()
        return jsonify(output(row)),201


@bp.patch('/conversations/<int:identifier>/agent')
@require()
def set_conversation_agent(identifier):
    agent_id=data().get('agent_id')
    if type(agent_id) is not int:raise ValueError('请选择学习助手')
    with transaction() as db:
        row=scoped(db,Conversation,identifier,g.user,owner=True,lock=True)
        if db.scalar(select(func.count()).select_from(Message).where(Message.conversation_id==row.id)):abort(409)
        agent=scoped(db,Agent,agent_id,g.user)
        if not agent.enabled:abort(409)
        row.agent_id=agent.id
        audit(db,g.user,'conversation.agent_changed',row.id,{'agent_id':agent.id},request_id=g.request_id)
        return jsonify(output(row))


@bp.get('/conversations/<int:identifier>/messages')
@require()
def messages(identifier):
    with transaction() as db:
        scoped(db,Conversation,identifier,g.user,owner=True)
        return jsonify([output(r) for r in db.scalars(select(Message).where(Message.conversation_id==identifier).order_by(Message.id))])


@bp.delete('/conversations/<int:identifier>')
@require()
def delete_conversation(identifier):
    with transaction() as db:
        row=scoped(db,Conversation,identifier,g.user,owner=True,lock=True)
        db.execute(sql_delete(Message).where(Message.conversation_id==row.id))
        db.delete(row)
        audit(db,g.user,'conversation.deleted',identifier,request_id=g.request_id)
    return jsonify(ok=True)


@bp.post('/conversations/<int:identifier>/messages')
@require()
def send(identifier):
    from .agent import stream
    question=text_field(data(),'question',4000)
    with transaction() as db:
        conversation=scoped(db,Conversation,identifier,g.user,owner=True);agent_id=conversation.agent_id
    # One active generation per conversation; expiry protects against killed HTTP workers.
    lock=redis_connection().lock(f'nexus:conversation:{identifier}',timeout=360,blocking_timeout=0)
    if not lock.acquire(blocking=False):abort(409)
    capacity=redis_connection().lock('nexus:agent-capacity',timeout=360,blocking_timeout=0)
    if not capacity.acquire(blocking=False):
        lock.release();abort(429)
    user_id,token,trace_id=g.user.id,g.token,g.request_id
    def generate():
        try:yield from stream(question,user_id,agent_id,identifier,token,trace_id)
        finally:
            try:lock.release()
            except Exception:pass
            try:capacity.release()
            except Exception:pass
    return Response(stream_with_context(generate()),mimetype='text/event-stream',headers={'X-Accel-Buffering':'no','Cache-Control':'no-cache'})


def parsed_assignment(values):
    parsed=AssignmentInput.model_validate(values);payload=parsed.model_dump()
    deadline=datetime.fromisoformat(payload.pop('deadline').replace('Z','+00:00'))
    if deadline.tzinfo is None or deadline<=now():raise ValueError('截止时间须为带时区的未来时间')
    calculate(parsed.answer_expression,{k:v[0] for k,v in parsed.ranges.items()})
    try:parsed.question_template.format(**{k:v[0] for k,v in parsed.ranges.items()})
    except (KeyError,ValueError):raise ValueError('题干参数与范围不匹配')
    return payload,deadline


def visible_assignment_ids():
    return select(Assignment.id).where(Assignment.class_id==g.user.class_id,Assignment.state=='published')


def assignment_payload(row):
    hidden=[]
    if g.user.role!='teacher':
        hidden.append('answer_expression')
        if row.deadline>now():hidden.append('rubric')
    return output(row,tuple(hidden))


def paper_payload(db,row):
    hidden=['standard_answer']
    if g.user.role=='student':
        assignment=db.get(Assignment,row.assignment_id)
        if assignment and assignment.deadline<=now():hidden=[]
    return output(row,tuple(hidden))


def queue_due_grades(db):
    if g.user.role!='teacher':return []
    return claim_due_submissions(db,g.user.class_id)


def submission_view(db,row):
    payload=output(row)
    paper=db.get(Paper,row.paper_id)
    assignment=db.get(Assignment,paper.assignment_id) if paper else None
    if assignment and assignment.deadline>now():
        for key in ('ai_score','final_score','ai_raw','feedback','review_note'):payload.pop(key,None)
        payload['state']='submitted'
    return payload


@bp.get('/assignments')
@require()
def assignments():
    due=[]
    with transaction() as db:
        due=queue_due_grades(db)
        query=select(Assignment).where(Assignment.class_id==g.user.class_id)
        if g.user.role=='student':query=query.where(Assignment.state=='published')
        payload=[assignment_payload(r) for r in db.scalars(query.order_by(Assignment.id.desc()))]
    for identifier in due:schedule('grade',identifier,g.user.class_id)
    return jsonify(payload)


@bp.post('/assignments')
@require('teacher')
def create_assignment():
    payload,deadline=parsed_assignment(data())
    with transaction() as db:
        row=Assignment(class_id=g.user.class_id,teacher_id=g.user.id,deadline=deadline,**payload)
        db.add(row);db.flush();return jsonify(output(row,('answer_expression',))),201


@bp.patch('/assignments/<int:identifier>')
@require('teacher')
def edit_assignment(identifier):
    payload,deadline=parsed_assignment(data())
    with transaction() as db:
        row=scoped(db,Assignment,identifier,g.user,lock=True)
        if row.state not in ('draft','withdrawn'):abort(409)
        for key,value in payload.items():setattr(row,key,value)
        row.deadline=deadline
        audit(db,g.user,'assignment.updated',row.id,request_id=g.request_id)
        return jsonify(output(row,('answer_expression',)))


@bp.post('/assignments/<int:identifier>/withdraw')
@require('teacher')
def withdraw_assignment(identifier):
    with transaction() as db:
        row=scoped(db,Assignment,identifier,g.user,lock=True)
        if row.state!='published':abort(409)
        row.state='withdrawn'
        audit(db,g.user,'assignment.withdrawn',row.id,request_id=g.request_id)
        return jsonify(output(row,('answer_expression',)))


@bp.post('/assignments/<int:identifier>/publish')
@require('teacher')
def publish_assignment(identifier):
    pending=[]
    with transaction() as db:
        assignment=scoped(db,Assignment,identifier,g.user,lock=True)
        if assignment.deadline<=now():abort(409)
        reissue=assignment.state=='withdrawn'
        for user in db.scalars(select(User).where(User.class_id==g.user.class_id,User.role=='student')):
            paper=db.scalar(select(Paper).where(Paper.assignment_id==identifier,Paper.user_id==user.id))
            if not paper:
                paper=Paper(assignment_id=identifier,user_id=user.id,class_id=user.class_id);db.add(paper);db.flush();pending.append(paper.id)
            elif reissue and paper.state!='submitted':
                paper.state='issuing';paper.question='';paper.parameters={};paper.standard_answer={};paper.error=None;paper.frozen_at=None
                pending.append(paper.id)
        assignment.state='published';audit(db,g.user,'assignment.published',identifier,request_id=g.request_id)
    return jsonify(task_ids=[schedule('issue',pid,g.user.class_id) for pid in pending]),202


@bp.delete('/assignments/<int:identifier>')
@require('teacher')
def delete_assignment(identifier):
    with transaction() as db:
        row=scoped(db,Assignment,identifier,g.user,lock=True)
        paper_ids=list(db.scalars(select(Paper.id).where(Paper.assignment_id==row.id)))
        if paper_ids:
            submission_ids=list(db.scalars(select(Submission.id).where(Submission.paper_id.in_(paper_ids))))
            if submission_ids:
                db.execute(sql_delete(WrongQuestion).where(WrongQuestion.submission_id.in_(submission_ids)))
                db.execute(sql_delete(Submission).where(Submission.id.in_(submission_ids)))
            db.execute(sql_delete(Paper).where(Paper.id.in_(paper_ids)))
        db.delete(row)
        audit(db,g.user,'assignment.deleted',identifier,request_id=g.request_id)
    return jsonify(ok=True)


@bp.get('/papers')
@require()
def papers():
    with transaction() as db:
        query=select(Paper).where(Paper.class_id==g.user.class_id)
        if g.user.role=='student':query=query.where(Paper.user_id==g.user.id,Paper.assignment_id.in_(visible_assignment_ids()))
        return jsonify([paper_payload(db,r) for r in db.scalars(query.order_by(Paper.id.desc()))])


@bp.post('/papers/<int:identifier>/start')
@require('student')
def start_paper(identifier):
    with transaction() as db:
        row=scoped(db,Paper,identifier,g.user,owner=True,lock=True)
        assignment=db.get(Assignment,row.assignment_id)
        if assignment.state!='published' or assignment.deadline<=now():abort(409)
        if row.state not in ('ready','frozen'):abort(409)
        row.state='frozen';row.frozen_at=row.frozen_at or now()
        return jsonify(output(row,('standard_answer',)))


@bp.post('/papers/<int:identifier>/submit')
@require('student')
def submit(identifier):
    answer=text_field(data(),'answer',12000)
    with transaction() as db:
        row=scoped(db,Paper,identifier,g.user,owner=True,lock=True)
        assignment=db.get(Assignment,row.assignment_id)
        if assignment.state!='published' or assignment.deadline<=now():abort(409)
        if row.state not in ('ready','frozen','submitted'):abort(409)
        row.state='submitted';row.frozen_at=row.frozen_at or now()
        sub=db.scalar(select(Submission).where(Submission.paper_id==row.id).with_for_update())
        if sub and sub.state=='grading':abort(409)
        if sub:
            sub.answer=answer;sub.state='submitted';sub.ai_score=None;sub.final_score=None;sub.ai_raw={};sub.feedback='';sub.review_note='';sub.reviewed_by=None
            wrong=db.scalar(select(WrongQuestion).where(WrongQuestion.submission_id==sub.id))
            if wrong:db.delete(wrong)
            sid=sub.id;audit(db,g.user,'submission.revised',sid,request_id=g.request_id)
        else:
            sub=Submission(paper_id=row.id,user_id=g.user.id,class_id=g.user.class_id,answer=answer,state='submitted')
            db.add(sub);db.flush();sid=sub.id
            audit(db,g.user,'submission.created',sid,request_id=g.request_id)
    return jsonify(id=sid),200


@bp.get('/submissions')
@require()
def submissions():
    due=[]
    with transaction() as db:
        due=queue_due_grades(db)
        query=select(Submission).where(Submission.class_id==g.user.class_id)
        if g.user.role=='student':
            query=query.where(Submission.user_id==g.user.id,Submission.paper_id.in_(select(Paper.id).where(Paper.assignment_id.in_(visible_assignment_ids()))))
        payload=[submission_view(db,r) for r in db.scalars(query.order_by(Submission.id.desc()))]
    for identifier in due:schedule('grade',identifier,g.user.class_id)
    return jsonify(payload)


@bp.post('/submissions/<int:identifier>/review')
@require('teacher')
def review_grade(identifier):
    values=data();score=values.get('score')
    if type(score) not in (int,float) or not 0<=score<=100:raise ValueError('分数须为0至100')
    note=text_field(values,'note',2000)
    with transaction() as db:
        row=scoped(db,Submission,identifier,g.user,lock=True)
        paper=db.get(Paper,row.paper_id);assignment=db.get(Assignment,paper.assignment_id)
        if assignment.deadline>now():abort(409)
        if row.state not in ('graded','reviewed','grade_failed'):abort(409)
        row.final_score=score;row.reviewed_by=g.user.id;row.review_note=note;row.state='reviewed'
        wrong=db.scalar(select(WrongQuestion).where(WrongQuestion.submission_id==row.id))
        if score<100 and not wrong:db.add(WrongQuestion(submission_id=row.id,user_id=row.user_id,class_id=row.class_id,explanation=row.feedback))
        if score==100 and wrong:db.delete(wrong)
        audit(db,g.user,'submission.reviewed',row.id,{'ai_score':row.ai_score,'final_score':score,'note':note},request_id=g.request_id)
        return jsonify(output(row))


@bp.get('/wrong-questions')
@require()
def wrong_questions():
    with transaction() as db:
        due=select(Submission.id).join(Paper,Paper.id==Submission.paper_id).join(Assignment,Assignment.id==Paper.assignment_id).where(Assignment.deadline<=now())
        query=select(WrongQuestion).where(WrongQuestion.class_id==g.user.class_id,WrongQuestion.submission_id.in_(due))
        if g.user.role=='student':query=query.where(WrongQuestion.user_id==g.user.id)
        return jsonify([output(r) for r in db.scalars(query)])


@bp.get('/weekly')
@require()
def weeklies():
    with transaction() as db:
        query=select(WeeklyReport).where(WeeklyReport.class_id==g.user.class_id)
        if g.user.role=='student':query=query.where(WeeklyReport.state=='published')
        return jsonify([output(r) for r in db.scalars(query.order_by(WeeklyReport.id.desc()))])


@bp.post('/weekly')
@require('teacher')
def new_weekly():
    start=week_start()
    with transaction() as db:
        if db.scalar(select(WeeklyReport).where(WeeklyReport.class_id==g.user.class_id,WeeklyReport.period_start==start)):abort(409)
        row=WeeklyReport(class_id=g.user.class_id,period_start=start);db.add(row);db.flush();identifier=row.id
    return jsonify(id=identifier,task_id=schedule('weekly',identifier,g.user.class_id)),202


@bp.post('/weekly/<int:identifier>/publish')
@require('teacher')
def publish_weekly(identifier):
    values=data()
    with transaction() as db:
        row=scoped(db,WeeklyReport,identifier,g.user,lock=True)
        if row.state!='draft':abort(409)
        row.teacher_comment=text_field(values,'comment',5000);row.state='published';row.published_by=g.user.id
        audit(db,g.user,'weekly.published',row.id,request_id=g.request_id);return jsonify(output(row))


@bp.get('/tasks')
@require('teacher')
def tasks():
    with transaction() as db:return jsonify([output(r) for r in db.scalars(select(Task).where(Task.class_id==g.user.class_id).order_by(Task.created_at.desc()).limit(100))])


@bp.delete('/tasks')
@require('teacher')
def clear_tasks():
    with transaction() as db:
        result=db.execute(sql_delete(Task).where(Task.class_id==g.user.class_id,Task.state.notin_(('pending','queued','running'))))
        audit(db,g.user,'tasks.cleared','',{'removed':result.rowcount},request_id=g.request_id)
    return jsonify(removed=result.rowcount)


@bp.post('/tasks/<identifier>/retry')
@require('teacher')
def retry(identifier):
    with transaction() as db:
        row=db.get(Task,identifier)
        if not row or row.class_id!=g.user.class_id:abort(404)
        if row.state not in ('failed','dispatch_failed'):abort(409)
        if row.kind=='index':
            for gap in db.scalars(select(KnowledgeGap).where(KnowledgeGap.version_id==row.target_id,KnowledgeGap.state=='index_failed')):gap.state='indexing'
        audit(db,g.user,'task.retried',identifier,request_id=g.request_id)
    dispatch(identifier);return jsonify(ok=True),202


@bp.get('/audit')
@require('teacher')
def audits():
    with transaction() as db:
        query=select(Audit).where(Audit.class_id==g.user.class_id).order_by(Audit.id.desc()).limit(100)
        return jsonify([output(r) for r in db.scalars(query)])


@bp.delete('/audit')
@require('teacher')
def clear_audit():
    with transaction() as db:
        result=db.execute(sql_delete(Audit).where(Audit.class_id==g.user.class_id))
        audit(db,g.user,'audit.cleared','',{'removed':result.rowcount},request_id=g.request_id)
    return jsonify(removed=result.rowcount)
