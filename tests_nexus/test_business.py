from datetime import timedelta
import io
import json
import pytest
from sqlalchemy import select
from app.nexus.db import transaction
from app.nexus.models import *
from app.nexus.jobs import calculate
from app.nexus import llm
from app.nexus.retrieval import register_gap
from app.nexus.schemas import Grade
from conftest import upload


def assignment(request,**changes):
    payload=dict(title='同纲运算',question_template='计算{a}+{b}',ranges={'a':[10,99],'b':[2,20]},
                 answer_expression='a+b',rubric='关注计算过程是否完整，以及最终结果是否正确。',deadline=(now()+timedelta(days=2)).isoformat())
    payload.update(changes)
    result=request('teacher_a','POST','/assignments',json=payload)
    assert result.status_code==201,result.json
    return result.json


def mock_grade(monkeypatch):
    def structured(prompt,payload,model,actor,trace):
        return Grade.model_validate({'score':100,'feedback':'检查计算过程和最终结果。'})
    monkeypatch.setattr(llm,'structured',structured)


def test_authentication_and_revocation(system):
    request,_,app=system
    assert app.test_client().get('/api/nexus/agents').status_code==401
    assert app.test_client().post('/api/nexus/login',json={'username':'teacher_a','password':'bad'}).status_code==401
    assert request('student_a1','POST','/templates',json={'name':'x','content':'x'}).status_code==403
    assert request('teacher_a','POST','/logout').status_code==200
    assert request('teacher_a','GET','/agents').status_code==401


def test_class_and_binding_isolation(system):
    request,_,_=system
    foreign=request('teacher_b','GET','/agents').json[0]
    own=request('teacher_a','GET','/agents').json[0]
    assert request('teacher_a','PATCH',f"/agents/{foreign['id']}",json={'name':'x'}).status_code==404
    template=request('teacher_b','GET','/templates').json[0]
    assert request('teacher_a','PATCH',f"/agents/{own['id']}",json={'template_id':template['id']}).status_code==404
    assert all(a['class_id']=='A' for a in request('student_a1','GET','/agents').json)


def test_upload_dialog_strategy_is_applied(system):
    request,run,_=system
    content='# 甲\n\n甲的正文。\n\n## 乙\n\n乙的正文。\n'
    response=request('teacher_a','POST','/materials',data={'title':'分段讲义','strategy':'hierarchy','max_chars':'800','overlap_pct':'10','file':(io.BytesIO(content.encode()),'lecture.md')})
    assert response.status_code==202,response.json
    run()
    with transaction() as db:
        rows=list(db.scalars(select(Chunk).where(Chunk.version_id==response.json['version_id']).order_by(Chunk.position)))
    assert len(rows)>=2
    assert any(row.content.startswith('# 甲') for row in rows)
    assert any(row.content.startswith('## 乙') for row in rows)
    rejected=request('teacher_a','POST','/materials',data={'title':'错误策略','strategy':'sentence','file':(io.BytesIO(b'body'),'lecture.txt')})
    assert rejected.status_code==400


def test_blank_material_title_is_generated(system,monkeypatch):
    request,_,_=system
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    headed=request('teacher_a','POST','/materials',data={'title':'  ','file':(io.BytesIO('# 校园分数练习\n\n先通分再相加。\n'.encode()),'notes.md')})
    assert headed.status_code==202,headed.json
    assert headed.json['title']=='校园分数练习'
    assert len(headed.json['title'])<=20
    assert request('teacher_a','GET','/materials').json[0]['title']=='校园分数练习'
    plain=request('teacher_a','POST','/materials',data={'file':(io.BytesIO('今天学习通分。\n第二行不采用。\n'.encode()),'lecture.txt')})
    assert plain.status_code==202,plain.json
    assert plain.json['title']=='今天学习通分'
    long_sentence='分数相加需要先通分，再把分子相加，分母保持不变，最后约分。'
    clipped=request('teacher_a','POST','/materials',data={'file':(io.BytesIO(long_sentence.encode()),'long.txt')})
    assert clipped.status_code==202,clipped.json
    assert clipped.json['title']=='分数相加需要先通分，再把分子相加'
    assert len(clipped.json['title'])<=20
    body=('甲'*900)+'乙的独特结论是潮汐锁定。'
    truncated=request('teacher_a','POST','/materials',data={'file':(io.BytesIO(body.encode()),'huge.txt')})
    assert truncated.status_code==202,truncated.json
    assert truncated.json['title']=='甲'*20
    assert '乙' not in truncated.json['title']
    kept=request('teacher_a','POST','/materials',data={'title':'教师指定标题','file':(io.BytesIO('# 另一标题\n正文。\n'.encode()),'kept.md')})
    assert kept.status_code==202 and kept.json['title']=='教师指定标题'


def test_model_title_uses_truncated_excerpt(system,monkeypatch):
    request,_,_=system
    from app.nexus import llm
    from app.nexus.schemas import LectureTitle
    seen={}
    def structured(prompt,payload,model,actor,trace):
        seen['excerpt']=payload['excerpt']
        seen['prompt']=prompt
        return LectureTitle(title='这是一个明显超过二十个字的模型标题应当被截断')
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    monkeypatch.setattr(llm,'structured',structured)
    body=('前言'*10)+('丙'*900)+'丁的结论不会进入标题。'
    response=request('teacher_a','POST','/materials',data={'file':(io.BytesIO(body.encode()),'model.txt')})
    assert response.status_code==202,response.json
    assert len(seen['excerpt'])<=800
    assert '丁的结论' not in seen['excerpt']
    assert '不超过20个字' in seen['prompt']
    assert len(response.json['title'])<=20
    assert response.json['title']=='这是一个明显超过二十个字的模型标题应当被'


def test_material_index_download_and_snapshot(system):
    request,run,_=system
    material=upload(request);run()
    rows=request('teacher_a','GET','/materials').json
    assert rows[0]['active_version_id']==material['version_id']
    assert request('student_a1','GET',f"/materials/{material['id']}/download").status_code==200
    assert request('student_b1','GET',f"/materials/{material['id']}/download").status_code==404
    assert request('student_a1','POST','/materials',data={'title':'x','file':(io.BytesIO(b'x'),'x.txt')}).status_code==403
    agent=request('teacher_a','GET','/agents').json[0]
    request('teacher_a','PATCH',f"/agents/{agent['id']}",json={'material_ids':[material['id']]})
    hits=request('student_a1','POST','/search',json={'query':'分数相加通分','agent_id':agent['id']}).json['hits']
    assert hits and hits[0]['version_id']==material['version_id']
    snapshot=hits[0].copy()
    response=request('teacher_a','POST',f"/materials/{material['id']}/versions",data={'file':(io.BytesIO('分数相减同样先通分。'.encode()),'v2.md')})
    assert response.status_code==202
    assert request('teacher_a','GET','/materials').json[0]['active_version_id']==material['version_id']
    run()
    assert request('teacher_a','GET','/materials').json[0]['active_version_id']==response.json['version_id']
    assert snapshot['content']=='分数相加需要先通分，再把分子相加。分母保持不变。'
    assert snapshot['sha256']!=request('teacher_a','GET','/materials').json[0]['versions'][0]['sha256']


def test_edit_reindexes_with_selected_strategy(system):
    request,run,_=system
    material=upload(request,title='潮汐讲义',content='潮汐锁定只出现在这则撤回测试讲义中。')
    run()
    agent=request('teacher_a','GET','/agents').json[0]
    request('teacher_a','PATCH',f"/agents/{agent['id']}",json={'material_ids':[material['id']]})
    assert request('student_a1','POST','/search',json={'query':'潮汐锁定撤回测试讲义','agent_id':agent['id']}).json['hits']
    assert request('teacher_a','POST',f"/materials/{material['id']}/withdraw").status_code==200
    assert request('student_a1','GET',f"/materials/{material['id']}/download").status_code==404
    body='潮汐锁定'*15+'。'+'青柠课堂'*15+'。'
    revised=request('teacher_a','PUT',f"/materials/{material['id']}/content",json={'content':body,'strategy':'custom','delimiter':'period','max_chars':100,'overlap_pct':0})
    assert revised.status_code==202 and revised.json.get('task_id')
    stored=next(row for row in request('teacher_a','GET','/materials').json if row['id']==material['id'])
    assert stored['versions'][0]['chunk_options']['strategy']=='custom'
    assert stored['versions'][0]['chunk_options']['max_chars']==100
    assert request('student_a1','GET',f"/materials/{material['id']}/download").status_code==404
    run()
    assert '青柠课堂' in request('student_a1','GET',f"/materials/{material['id']}/download").data.decode()
    hits=request('student_a1','POST','/search',json={'query':'青柠课堂的索引','agent_id':agent['id']}).json['hits']
    assert hits and hits[0]['version_id']==revised.json['version_id']
    with transaction() as db:
        chunks=list(db.scalars(select(Chunk).where(Chunk.version_id==revised.json['version_id']).order_by(Chunk.position)))
    assert len(chunks)>=2
    assert any('潮汐锁定' in row.content for row in chunks)
    assert any('青柠课堂' in row.content for row in chunks)
    assert request('student_a1','DELETE',f"/materials/{material['id']}").status_code==403
    assert request('teacher_a','DELETE',f"/materials/{material['id']}").status_code==200
    assert request('teacher_a','GET',f"/materials/{material['id']}/download").status_code==404


def test_failed_index_preserves_active_version(system,monkeypatch):
    request,run,_=system
    material=upload(request);run()
    result=request('teacher_a','POST',f"/materials/{material['id']}/versions",data={'file':(io.BytesIO('更新材料'.encode()),'v2.md')})
    from app.nexus import retrieval
    monkeypatch.setattr(retrieval,'embed',lambda value:(_ for _ in ()).throw(RuntimeError('embedding unavailable')))
    run()
    row=request('teacher_a','GET','/materials').json[0]
    assert row['active_version_id']==material['version_id']
    assert row['versions'][0]['state']=='index_failed'


def test_similar_questions_merge_by_meaning(system,monkeypatch):
    _,_,_=system
    from app.nexus import retrieval
    vectors={
        '冰能变成水吗':[1.0,0.0],
        '冰能融化成水吗':[0.896,0.444055],
        '水的沸点是多少':[0.511,0.859581],
    }
    monkeypatch.setattr(retrieval,'embed',lambda value:vectors[value])
    with transaction() as db:
        user=db.scalar(select(User).where(User.username=='student_a1'))
        rejected=KnowledgeGap(class_id=user.class_id,fingerprint='gap-rejected-ice',question='冰能变成水吗',heat=1,student_ids=[user.id],state='rejected',before_hits=[],after_hits=[])
        db.add(rejected);db.flush()
        first=register_gap(db,user,'冰能变成水吗',[])
        second=register_gap(db,user,'冰能融化成水吗',[])
        other=register_gap(db,user,'水的沸点是多少',[])
        assert first.id==second.id and second.heat==2 and first.state=='pending'
        assert other.id!=first.id and other.heat==1
        assert db.get(KnowledgeGap,rejected.id).heat==1 and db.get(KnowledgeGap,rejected.id).state=='rejected'


def test_gap_refusal_merge_review_and_fill(system):
    request,run,_=system
    agent=request('teacher_a','GET','/agents').json[0]
    cid=request('student_a1','POST','/conversations',json={'agent_id':agent['id']}).json['id']
    for _ in range(2):
        reply=request('student_a1','POST',f'/conversations/{cid}/messages',json={'question':'月球潮汐锁定的形成原因是什么'})
        assert reply.status_code==200 and '候选知识缺口' in reply.text and 'event: done' in reply.text
    gaps=request('teacher_a','GET','/gaps').json
    assert len(gaps)==1 and gaps[0]['heat']==2
    gap=gaps[0]
    assert request('teacher_b','POST',f"/gaps/{gap['id']}/review",json={'decision':'approve'}).status_code==404
    assert request('teacher_a','POST',f"/gaps/{gap['id']}/supplement",json={'title':'x','content':'x'}).status_code==409
    request('teacher_a','POST',f"/gaps/{gap['id']}/review",json={'decision':'approve'})
    result=request('teacher_a','POST',f"/gaps/{gap['id']}/supplement",json={'title':'潮汐锁定','content':'月球潮汐锁定的形成原因：地球引力造成潮汐形变，耗散转动能，最终自转与公转周期相同。'})
    assert result.status_code==202
    assert request('teacher_a','GET','/gaps').json[0]['state']=='indexing'
    run()
    gap=request('teacher_a','GET','/gaps').json[0]
    assert gap['state']=='filled' and gap['after_hits'] and gap['before_hits']==[]


def test_gap_supplement_accepts_lecture_upload(system):
    request,_,_=system
    with transaction() as db:
        teacher=db.scalar(select(User).where(User.username=='teacher_a'))
        gap=KnowledgeGap(class_id=teacher.class_id,fingerprint='gap-file-upload',question='为什么要通分',heat=1,student_ids=[],state='approved',before_hits=[],after_hits=[])
        db.add(gap);db.flush();gap_id=gap.id
    content='# 通分说明\n\n通分是把分母变成相同。\n'
    denied=request('student_a1','POST',f'/gaps/{gap_id}/supplement',data={'title':'通分说明','strategy':'hierarchy','max_chars':'800','overlap_pct':'10','file':(io.BytesIO(content.encode()),'gap.md')})
    assert denied.status_code==403
    assert request('teacher_b','POST',f'/gaps/{gap_id}/supplement',data={'file':(io.BytesIO(content.encode()),'gap.md')}).status_code==404
    rejected=request('teacher_a','POST',f'/gaps/{gap_id}/supplement',data={'strategy':'sentence','file':(io.BytesIO(content.encode()),'gap.md')})
    assert rejected.status_code==400
    created=request('teacher_a','POST',f'/gaps/{gap_id}/supplement',data={'title':'  ','strategy':'hierarchy','max_chars':'800','overlap_pct':'10','file':(io.BytesIO(content.encode()),'gap.md')})
    assert created.status_code==202,created.json
    assert created.json['title']=='通分说明'
    with transaction() as db:
        version=db.get(MaterialVersion,created.json['version_id'])
        assert version.chunk_options['strategy']=='hierarchy' and version.chunk_options['max_chars']==800
        assert db.get(KnowledgeGap,gap_id).state=='indexing' and db.get(KnowledgeGap,gap_id).version_id==version.id
        assert db.get(Material,created.json['id']).title=='通分说明'


def test_gap_supplement_can_revise_existing_material(system):
    request,_,_=system
    material=upload(request)
    foreign=upload(request,teacher='teacher_b',title='乙班讲义')
    with transaction() as db:
        teacher=db.scalar(select(User).where(User.username=='teacher_a'))
        gap=KnowledgeGap(class_id=teacher.class_id,fingerprint='gap-edit-existing',question='如何修订已有讲义',heat=1,student_ids=[],state='approved',before_hits=[],after_hits=[])
        db.add(gap);db.flush();gap_id=gap.id
    before=len(request('teacher_a','GET','/materials').json)
    assert request('student_a1','POST',f'/gaps/{gap_id}/supplement',json={'material_id':material['id'],'title':'修订','content':'修订正文'}).status_code==403
    assert request('teacher_a','POST',f'/gaps/{gap_id}/supplement',json={'material_id':foreign['id'],'title':'修订','content':'修订正文'}).status_code==404
    revised=request('teacher_a','POST',f'/gaps/{gap_id}/supplement',json={'material_id':material['id'],'title':'修订后的分数运算','content':'分数相加需要先通分，再把分子相加。这里是修订。','strategy':'hierarchy','max_chars':800,'overlap_pct':10})
    assert revised.status_code==202,revised.json
    assert revised.json['id']==material['id'] and revised.json['title']=='修订后的分数运算'
    assert len(request('teacher_a','GET','/materials').json)==before
    with transaction() as db:
        version=db.get(MaterialVersion,revised.json['version_id'])
        assert version.material_id==material['id'] and version.number==2
        assert version.content.startswith('分数相加需要先通分') and version.chunk_options['strategy']=='hierarchy'
        stored=db.get(KnowledgeGap,gap_id)
        assert stored.state=='indexing' and stored.version_id==version.id
        assert db.get(Material,material['id']).title=='修订后的分数运算'


def test_teacher_can_reopen_rejected_gap_and_reject_filled(system):
    request,_,_=system
    with transaction() as db:
        teacher=db.scalar(select(User).where(User.username=='teacher_a'))
        rejected=KnowledgeGap(class_id=teacher.class_id,fingerprint='gap-reopen',question='驳回后如何重新补充',heat=1,student_ids=[],state='rejected',before_hits=[],after_hits=[])
        filled=KnowledgeGap(class_id=teacher.class_id,fingerprint='gap-filled-reject',question='已补入后如何驳回',heat=1,student_ids=[],state='filled',before_hits=[],after_hits=[{'id':1}])
        indexing=KnowledgeGap(class_id=teacher.class_id,fingerprint='gap-indexing-reject',question='索引中如何驳回',heat=1,student_ids=[],state='indexing',before_hits=[],after_hits=[])
        db.add_all([rejected,filled,indexing]);db.flush()
        rejected_id,filled_id,indexing_id=rejected.id,filled.id,indexing.id
    assert request('student_a1','POST',f'/gaps/{rejected_id}/review',json={'decision':'approve'}).status_code==403
    assert request('teacher_b','POST',f'/gaps/{rejected_id}/review',json={'decision':'approve'}).status_code==404
    assert request('teacher_a','POST',f'/gaps/{rejected_id}/supplement',json={'title':'补充','content':'先重新打开这个缺口。'}).status_code==409
    reopened=request('teacher_a','POST',f'/gaps/{rejected_id}/review',json={'decision':'approve'})
    assert reopened.status_code==200 and reopened.json['state']=='approved'
    supplemented=request('teacher_a','POST',f'/gaps/{rejected_id}/supplement',json={'title':'重新补充','content':'驳回后重新打开，再补充这段材料。'})
    assert supplemented.status_code==202
    assert next(item for item in request('teacher_a','GET','/gaps').json if item['id']==rejected_id)['state']=='indexing'
    assert request('teacher_a','POST',f'/gaps/{filled_id}/review',json={'decision':'approve'}).status_code==409
    assert request('teacher_a','POST',f'/gaps/{filled_id}/review',json={'decision':'reject'}).json['state']=='rejected'
    assert request('teacher_a','POST',f'/gaps/{indexing_id}/review',json={'decision':'reject'}).json['state']=='rejected'


def test_unique_papers_no_answer_leak_and_freeze(system):
    request,run,_=system
    a=assignment(request)
    assert 'answer_expression' not in a
    request('teacher_a','POST',f"/assignments/{a['id']}/publish");run()
    p1=request('student_a1','GET','/papers').json[0];p2=request('student_a2','GET','/papers').json[0]
    assert p1['state']=='ready' and p2['state']=='ready'
    assert p1['parameters']!=p2['parameters'] and 'standard_answer' not in p1
    assert request('student_a2','POST',f"/papers/{p1['id']}/start").status_code==404
    assert request('student_b1','POST',f"/papers/{p1['id']}/start").status_code==404
    start=request('student_a1','POST',f"/papers/{p1['id']}/start").json
    assert start['state']=='frozen' and start['frozen_at']
    assert request('student_a1','POST',f"/papers/{p1['id']}/start").json['question']==start['question']


def test_one_paper_failure_does_not_rollback_others(system):
    request,run,_=system
    a=assignment(request,ranges={'a':[1,1],'b':[1,1]})
    request('teacher_a','POST',f"/assignments/{a['id']}/publish");run()
    papers=request('teacher_a','GET','/papers').json
    assert sorted(p['state'] for p in papers)==['issue_failed','ready']


def test_grading_exchange_guard_and_review(system,monkeypatch):
    request,run,_=system;mock_grade(monkeypatch)
    a=assignment(request);request('teacher_a','POST',f"/assignments/{a['id']}/publish");run()
    p1=request('student_a1','GET','/papers').json[0];p2=request('student_a2','GET','/papers').json[0]
    with transaction() as db:wrong=db.get(Paper,p2['id']).standard_answer['value']
    response=request('student_a1','POST',f"/papers/{p1['id']}/submit",json={'answer':'先写错'})
    assert response.status_code==200
    revised=request('student_a1','POST',f"/papers/{p1['id']}/submit",json={'answer':'最终答案 '+str(wrong)})
    assert revised.status_code==200 and revised.json['id']==response.json['id']
    assert request('student_a1','GET','/submissions').json[0]['answer'].endswith(str(wrong))
    assert 'ai_score' not in request('teacher_a','GET','/submissions').json[0]
    assert request('teacher_a','POST',f"/submissions/{response.json['id']}/review",json={'score':80,'note':'x'}).status_code==409
    with transaction() as db:db.get(Assignment,a['id']).deadline=now()-timedelta(seconds=1)
    request('teacher_a','GET','/assignments');run();sub=request('teacher_a','GET','/submissions').json[0]
    assert sub['ai_score']<=40 and sub['ai_raw']['model_score']==100
    assert len(request('student_a1','GET','/wrong-questions').json)==1
    assert request('student_a1','POST',f"/papers/{p1['id']}/submit",json={'answer':'截止后不能改'}).status_code==409
    assert request('teacher_b','POST',f"/submissions/{sub['id']}/review",json={'score':80,'note':'x'}).status_code==404
    result=request('teacher_a','POST',f"/submissions/{sub['id']}/review",json={'score':75,'note':'过程有部分得分'})
    assert result.json['ai_score']==sub['ai_score'] and result.json['final_score']==75
    failed=request('student_a2','POST',f"/papers/{p2['id']}/submit",json={'answer':'我不会做'})
    assert failed.status_code==409
    with transaction() as db:
        late=Submission(paper_id=p2['id'],user_id=db.scalar(select(User).where(User.username=='student_a2')).id,class_id='A',answer='我不会做',state='grade_failed')
        db.add(late);db.flush();late_id=late.id
        db.get(Paper,p2['id']).state='submitted'
    assert request('teacher_a','POST',f"/submissions/{late_id}/review",json={'score':30,'note':'批改失败后人工给分'}).json['state']=='reviewed'
    assert request('student_a2','GET','/submissions').json[0]['final_score']==30


def test_grading_timer_releases_only_after_deadline(system,monkeypatch):
    request,run,_=system;mock_grade(monkeypatch)
    from app.nexus.jobs import release_due_grades
    open_assignment=assignment(request);request('teacher_a','POST',f"/assignments/{open_assignment['id']}/publish");run()
    closed=assignment(request);request('teacher_a','POST',f"/assignments/{closed['id']}/publish");run()
    open_paper=next(item for item in request('student_a1','GET','/papers').json if item['assignment_id']==open_assignment['id'])
    closed_paper=next(item for item in request('student_a1','GET','/papers').json if item['assignment_id']==closed['id'])
    assert request('student_a1','POST',f"/papers/{open_paper['id']}/submit",json={'answer':'最终答案 1'}).status_code==200
    assert request('student_a1','POST',f"/papers/{closed_paper['id']}/submit",json={'answer':'最终答案 2'}).status_code==200
    assert release_due_grades()==[]
    request('teacher_a','POST',f"/assignments/{closed['id']}/withdraw")
    with transaction() as db:db.get(Assignment,closed['id']).deadline=now()-timedelta(seconds=1)
    assert release_due_grades()==[]
    with transaction() as db:db.get(Assignment,open_assignment['id']).deadline=now()-timedelta(seconds=1)
    queued=release_due_grades()
    assert queued and release_due_grades()==[]
    run()
    graded=next(item for item in request('teacher_a','GET','/submissions').json if item['paper_id']==open_paper['id'])
    held=next(item for item in request('teacher_a','GET','/submissions').json if item['paper_id']==closed_paper['id'])
    assert graded['state']=='graded' and graded['ai_score'] is not None
    assert held['state']=='submitted' and held['ai_score'] is None and held['final_score'] is None


def test_prose_rubric_is_judged_as_one_score(system,monkeypatch):
    request,run,_=system
    seen={}
    def structured(prompt,payload,model,actor,trace):
        seen['prompt']=prompt
        seen['rubric']=payload['rubric']
        return Grade.model_validate({'score':88,'feedback':'过程完整，结果正确。'})
    monkeypatch.setattr(llm,'structured',structured)
    text='关注计算过程是否完整，以及最终结果是否正确。'
    created=assignment(request,rubric=text)
    assert created['rubric']==text
    listed=next(item for item in request('teacher_a','GET','/assignments').json if item['id']==created['id'])
    assert listed['rubric']==text
    rejected=request('teacher_a','POST','/assignments',json=dict(
        title='旧分项',question_template='计算{a}+{b}',ranges={'a':[1,2],'b':[1,2]},
        answer_expression='a+b',rubric=[{'name':'过程','points':40},{'name':'答案','points':60}],
        deadline=(now()+timedelta(days=2)).isoformat()))
    assert rejected.status_code==400
    request('teacher_a','POST',f"/assignments/{created['id']}/publish");run()
    paper=next(item for item in request('student_a1','GET','/papers').json if item['assignment_id']==created['id'])
    with transaction() as db:value=db.get(Paper,paper['id']).standard_answer['value']
    assert request('student_a1','POST',f"/papers/{paper['id']}/submit",json={'answer':f'最终答案 {value}'}).status_code==200
    with transaction() as db:db.get(Assignment,created['id']).deadline=now()-timedelta(seconds=1)
    request('teacher_a','GET','/assignments');run()
    graded=next(item for item in request('teacher_a','GET','/submissions').json if item['paper_id']==paper['id'])
    assert seen['rubric']==text and '自行判断' in seen['prompt'] and '固定分项' in seen['prompt']
    assert graded['ai_score']==88 and graded['ai_raw']['model_score']==88
    assert graded['feedback']=='过程完整，结果正确。'
    assert 'items' not in graded['ai_raw']


def test_hint_stays_out_of_grading_until_deadline(system,monkeypatch):
    request,run,_=system
    seen={}
    def structured(prompt,payload,model,actor,trace):
        seen['payload']=payload
        return Grade.model_validate({'score':90,'feedback':'结果正确。'})
    monkeypatch.setattr(llm,'structured',structured)
    hint='先算括号，再做乘法。这段文字只是作答提示。'
    created=assignment(request,answer_hint=hint)
    assert created['answer_hint']==hint and 'answer_expression' not in created
    request('teacher_a','POST',f"/assignments/{created['id']}/publish");run()
    early=next(item for item in request('student_a1','GET','/assignments').json if item['id']==created['id'])
    assert early['answer_hint']==hint and 'rubric' not in early and 'answer_expression' not in early
    paper=next(item for item in request('student_a1','GET','/papers').json if item['assignment_id']==created['id'])
    assert 'standard_answer' not in paper
    teacher=next(item for item in request('teacher_a','GET','/assignments').json if item['id']==created['id'])
    assert teacher['rubric'] and teacher['answer_expression']=='a+b' and teacher['answer_hint']==hint
    from app.nexus.mcp_server import execute
    from app.nexus.security import issue
    with transaction() as db:
        student=db.scalar(select(User).where(User.username=='student_a1'));token=issue(student)
        value=db.get(Paper,paper['id']).standard_answer['value']
    agent=next(item for item in request('teacher_a','GET','/agents').json if 'assignment_rubric' in item['tools'])
    with pytest.raises(PermissionError):execute('assignment_rubric',token,agent['id'],assignment_id=created['id'])
    assert request('student_a1','POST',f"/papers/{paper['id']}/submit",json={'answer':f'最终答案 {value}'}).status_code==200
    with transaction() as db:db.get(Assignment,created['id']).deadline=now()-timedelta(seconds=1)
    late=next(item for item in request('student_a1','GET','/assignments').json if item['id']==created['id'])
    late_paper=next(item for item in request('student_a1','GET','/papers').json if item['id']==paper['id'])
    assert late['rubric']==created['rubric'] and late['answer_hint']==hint and 'answer_expression' not in late
    assert late_paper['standard_answer']['value']==value
    revealed=execute('assignment_rubric',token,agent['id'],assignment_id=created['id'])
    assert revealed['rubric']==created['rubric'] and 'answer_hint' not in revealed and hint not in str(revealed)
    request('teacher_a','GET','/assignments');run()
    assert set(seen['payload'])=={'question','standard_answer','student_answer','rubric'}
    assert hint not in str(seen['payload'])


def test_deadline_and_invalid_template(system):
    request,run,_=system
    a=assignment(request);request('teacher_a','POST',f"/assignments/{a['id']}/publish");run()
    paper=request('student_a1','GET','/papers').json[0]
    with transaction() as db:db.get(Assignment,a['id']).deadline=now()-timedelta(seconds=1)
    assert request('student_a1','POST',f"/papers/{paper['id']}/submit",json={'answer':'1'}).status_code==409
    with pytest.raises(ValueError):calculate('__import__("os").system("x")',{})


def test_weekly_sparse_review_and_class_scope(system):
    request,run,_=system
    result=request('teacher_a','POST','/weekly');assert result.status_code==202;run()
    row=request('teacher_a','GET','/weekly').json[0]
    assert row['state']=='draft' and not row['facts']['sample_sufficient'] and '记录不够' in row['teacher_comment']
    assert request('student_a1','GET','/weekly').json==[]
    assert request('teacher_b','POST',f"/weekly/{row['id']}/publish",json={'comment':'x'}).status_code==404
    assert request('teacher_a','POST',f"/weekly/{row['id']}/publish",json={'comment':row['teacher_comment']}).status_code==200
    assert len(request('student_a1','GET','/weekly').json)==1
    assert request('student_b1','GET','/weekly').json==[]


def test_skill_upload_and_toggle(system):
    request,_,_=system
    source='---\nname: history\ndescription: 历史探究课程\n---\n# 提示\n先询问年代和主题。'
    row=request('teacher_a','POST','/skills',data={'file':(io.BytesIO(source.encode()),'SKILL.md')})
    assert row.status_code==201
    assert request('student_a1','POST','/skills',data={'file':(io.BytesIO(source.encode()),'SKILL.md')}).status_code==403
    assert request('teacher_a','PATCH',f"/skills/{row.json['id']}",json={'enabled':False}).json['enabled'] is False


def test_skill_confirm_fields_and_edit(system):
    request,_,_=system
    created=request('teacher_a','POST','/skills',json={'name':'历史探究','description':'历史,年代','body':'先询问年代和主题。','source_text':'名称：历史探究'})
    assert created.status_code==201
    assert created.json['name']=='历史探究' and created.json['description']=='历史,年代' and created.json['body']=='先询问年代和主题。'
    assert request('student_a1','POST','/skills',json={'name':'历史探究','description':'历史','body':'正文'}).status_code==403
    edited=request('teacher_a','PATCH',f"/skills/{created.json['id']}",json={'name':'年代探究','description':'年代,主题','body':'先确认年代。'})
    assert edited.status_code==200 and edited.json['name']=='年代探究' and edited.json['enabled'] is True
    assert request('teacher_b','PATCH',f"/skills/{created.json['id']}",json={'name':'跨班'}).status_code==404
    assert request('teacher_a','PATCH',f"/skills/{created.json['id']}",json={'name':''}).status_code==400


def test_teacher_can_delete_skill_and_detach_references(system):
    request,_,_=system
    created=request('teacher_a','POST','/skills',json={'name':'待删除技能','description':'临时','body':'这段正文只用于删除验收。'})
    assert created.status_code==201
    skill_id=created.json['id']
    agent=request('teacher_a','GET','/agents').json[0]
    assert request('teacher_a','PATCH',f"/agents/{agent['id']}",json={'skill_ids':list(dict.fromkeys([*agent['skill_ids'],skill_id]))}).status_code==200
    with transaction() as db:
        user=db.scalar(select(User).where(User.username=='teacher_a'))
        conversation=Conversation(class_id='A',user_id=user.id,agent_id=agent['id'],title='删除验收')
        db.add(conversation);db.flush()
        message=Message(conversation_id=conversation.id,role='assistant',content='曾引用技能',citations=[],trace_id='skill-delete',skill_id=skill_id)
        db.add(message);db.flush();message_id=message.id
    assert request('student_a1','DELETE',f"/skills/{skill_id}").status_code==403
    assert request('teacher_b','DELETE',f"/skills/{skill_id}").status_code==404
    assert request('teacher_a','DELETE',f"/skills/{skill_id}").status_code==200
    assert all(item['id']!=skill_id for item in request('teacher_a','GET','/skills').json)
    refreshed=next(item for item in request('teacher_a','GET','/agents').json if item['id']==agent['id'])
    assert skill_id not in refreshed['skill_ids']
    with transaction() as db:
        assert db.get(Skill,skill_id) is None
        assert db.get(Message,message_id).skill_id is None


def test_teacher_can_delete_agent_and_its_conversations(system):
    request,_,_=system
    created=request('teacher_a','POST','/agents',json={'name':'待删除应用'})
    assert created.status_code==201
    agent_id=created.json['id']
    conversation=request('student_a1','POST','/conversations',json={'agent_id':agent_id})
    assert conversation.status_code==201
    with transaction() as db:
        message=Message(conversation_id=conversation.json['id'],role='user',content='还在吗',citations=[],trace_id='agent-delete')
        db.add(message);db.flush();message_id=message.id
    assert request('student_a1','DELETE',f"/agents/{agent_id}").status_code==403
    assert request('teacher_b','DELETE',f"/agents/{agent_id}").status_code==404
    assert request('teacher_a','DELETE',f"/agents/{agent_id}").status_code==200
    assert all(item['id']!=agent_id for item in request('teacher_a','GET','/agents').json)
    with transaction() as db:
        assert db.get(Agent,agent_id) is None
        assert db.get(Conversation,conversation.json['id']) is None
        assert db.get(Message,message_id) is None


def test_owner_can_delete_own_conversation(system):
    request,_,_=system
    agent=request('teacher_a','GET','/agents').json[0]
    own=request('student_a1','POST','/conversations',json={'agent_id':agent['id']})
    other=request('teacher_a','POST','/conversations',json={'agent_id':agent['id']})
    assert own.status_code==201 and other.status_code==201
    with transaction() as db:
        message=Message(conversation_id=own.json['id'],role='user',content='待删除',citations=[],trace_id='conversation-delete')
        db.add(message);db.flush();message_id=message.id
    assert request('teacher_a','DELETE',f"/conversations/{own.json['id']}").status_code==404
    assert request('student_b1','DELETE',f"/conversations/{own.json['id']}").status_code==404
    assert request('student_a1','DELETE',f"/conversations/{own.json['id']}").status_code==200
    assert all(item['id']!=own.json['id'] for item in request('student_a1','GET','/conversations').json)
    assert any(item['id']==other.json['id'] for item in request('teacher_a','GET','/conversations').json)
    with transaction() as db:
        assert db.get(Conversation,own.json['id']) is None
        assert db.get(Message,message_id) is None


def test_empty_conversation_can_switch_agent_until_it_starts(system):
    request,_,_=system
    enabled=[item for item in request('teacher_a','GET','/agents').json if item['enabled']]
    assert len(enabled)>=2
    created=request('student_a1','POST','/conversations',json={'agent_id':enabled[0]['id']})
    assert created.status_code==201
    cid=created.json['id']
    switched=request('student_a1','PATCH',f'/conversations/{cid}/agent',json={'agent_id':enabled[1]['id']})
    assert switched.status_code==200 and switched.json['agent_id']==enabled[1]['id']
    assert request('teacher_a','PATCH',f'/conversations/{cid}/agent',json={'agent_id':enabled[0]['id']}).status_code==404
    assert request('student_b1','PATCH',f'/conversations/{cid}/agent',json={'agent_id':enabled[0]['id']}).status_code==404
    foreign=request('teacher_b','GET','/agents').json[0]['id']
    assert request('student_a1','PATCH',f'/conversations/{cid}/agent',json={'agent_id':foreign}).status_code==404
    disabled=request('teacher_a','POST','/agents',json={'name':'停用助手','enabled':False})
    assert disabled.status_code==201
    assert request('student_a1','PATCH',f'/conversations/{cid}/agent',json={'agent_id':disabled.json['id']}).status_code==409
    with transaction() as db:
        db.add(Message(conversation_id=cid,role='user',content='开始了',citations=[],trace_id='switch-lock'))
    assert request('student_a1','PATCH',f'/conversations/{cid}/agent',json={'agent_id':enabled[0]['id']}).status_code==409


def test_teacher_can_delete_template_and_detach_agents(system):
    request,_,_=system
    created=request('teacher_a','POST','/templates',json={'name':'待删除模板','content':'只用于删除验收。'})
    assert created.status_code==201
    template_id=created.json['id']
    agent=request('teacher_a','GET','/agents').json[0]
    assert request('teacher_a','PATCH',f"/agents/{agent['id']}",json={'template_id':template_id}).status_code==200
    assert request('student_a1','DELETE',f'/templates/{template_id}').status_code==403
    assert request('teacher_b','DELETE',f'/templates/{template_id}').status_code==404
    assert request('teacher_a','DELETE',f'/templates/{template_id}').status_code==200
    assert all(item['id']!=template_id for item in request('teacher_a','GET','/templates').json)
    refreshed=next(item for item in request('teacher_a','GET','/agents').json if item['id']==agent['id'])
    assert refreshed['template_id'] is None


def test_teacher_can_delete_gap_and_keep_lecture(system):
    request,_,_=system
    material=upload(request,title='缺口删除后仍保留')
    with transaction() as db:
        version=db.scalar(select(MaterialVersion).where(MaterialVersion.material_id==material['id']))
        gap=KnowledgeGap(class_id='A',fingerprint='gap-delete',question='删除后讲义还在吗',heat=1,student_ids=[],state='filled',version_id=version.id,before_hits=[],after_hits=[])
        db.add(gap);db.flush();gap_id=gap.id
    assert request('student_a1','DELETE',f'/gaps/{gap_id}').status_code==403
    assert request('teacher_b','DELETE',f'/gaps/{gap_id}').status_code==404
    assert request('teacher_a','DELETE',f'/gaps/{gap_id}').status_code==200
    assert all(item['id']!=gap_id for item in request('teacher_a','GET','/gaps').json)
    assert any(item['id']==material['id'] for item in request('teacher_a','GET','/materials').json)
    with transaction() as db:assert db.get(KnowledgeGap,gap_id) is None and db.get(Material,material['id']) is not None


def test_assignment_withdraw_edit_republish_and_delete(system,monkeypatch):
    request,run,_=system
    mock_grade(monkeypatch)
    from app.nexus.mcp_server import execute
    from app.nexus.security import issue
    created=assignment(request)
    aid=created['id']
    body=dict(title='撤回后修改',question_template='计算{a}-{b}',ranges={'a':[10,99],'b':[2,20]},
              answer_expression='a-b',rubric='关注计算过程是否完整，以及最终结果是否正确。',deadline=(now()+timedelta(days=3)).isoformat())
    assert request('student_a1','DELETE',f'/assignments/{aid}').status_code==403
    assert request('teacher_b','POST',f'/assignments/{aid}/withdraw').status_code==404
    assert request('teacher_a','POST',f'/assignments/{aid}/withdraw').status_code==409
    request('teacher_a','POST',f'/assignments/{aid}/publish');run()
    visible=request('student_a1','GET','/assignments').json
    assert visible and visible[0]['id']==aid and 'answer_expression' not in visible[0]
    owned=next(item for item in request('teacher_a','GET','/assignments').json if item['id']==aid)
    assert owned['answer_expression']=='a+b'
    assert request('teacher_a','PATCH',f'/assignments/{aid}',json=body).status_code==409
    paper=next(item for item in request('student_a1','GET','/papers').json if item['assignment_id']==aid)
    other=next(item for item in request('student_a2','GET','/papers').json if item['assignment_id']==aid)
    old_question=paper['question']
    submitted=request('student_a1','POST',f"/papers/{paper['id']}/submit",json={'answer':'最终答案 1'})
    assert submitted.status_code==200
    assert request('teacher_a','POST',f'/assignments/{aid}/withdraw').json['state']=='withdrawn'
    assert request('student_a1','GET','/assignments').json==[]
    assert request('student_a1','GET','/papers').json==[]
    assert request('student_a1','GET','/submissions').json==[]
    assert request('student_a2','POST',f"/papers/{other['id']}/start").status_code==409
    with transaction() as db:
        student=db.scalar(select(User).where(User.username=='student_a1'));token=issue(student)
    agent=next(item for item in request('teacher_a','GET','/agents').json if 'current_assignments' in item['tools'])
    assert all(item['id']!=aid for item in execute('current_assignments',token,agent['id'])['assignments'])
    edited=request('teacher_a','PATCH',f'/assignments/{aid}',json=body)
    assert edited.status_code==200 and edited.json['title']=='撤回后修改' and 'answer_expression' not in edited.json
    request('teacher_a','POST',f'/assignments/{aid}/publish');run()
    kept=next(item for item in request('teacher_a','GET','/papers').json if item['id']==paper['id'])
    fresh=next(item for item in request('student_a2','GET','/papers').json if item['assignment_id']==aid)
    assert kept['state']=='submitted' and kept['question']==old_question
    assert fresh['state']=='ready' and '-' in fresh['question'] and '+' not in fresh['question']
    assert request('teacher_b','DELETE',f'/assignments/{aid}').status_code==404
    assert request('teacher_a','DELETE',f'/assignments/{aid}').status_code==200
    assert request('teacher_a','GET','/assignments').json==[]
    assert request('teacher_a','GET','/papers').json==[]
    with transaction() as db:
        assert db.get(Assignment,aid) is None and db.get(Paper,paper['id']) is None and db.get(Submission,submitted.json['id']) is None


def test_teacher_can_clear_finished_tasks_and_own_audit(system):
    request,_,_=system
    with transaction() as db:
        db.add(Task(id='finished-a',kind='index',target_id=1,class_id='A',state='succeeded'))
        db.add(Task(id='active-a',kind='grade',target_id=1,class_id='A',state='queued'))
        db.add(Task(id='finished-b',kind='index',target_id=1,class_id='B',state='failed'))
        db.add(Audit(class_id='B',action='kept',request_id='class-b',success=True,details={}))
    assert request('student_a1','DELETE','/tasks').status_code==403
    assert request('student_a1','DELETE','/audit').status_code==403
    cleared=request('teacher_a','DELETE','/tasks')
    assert cleared.status_code==200 and cleared.json['removed']>=1
    assert [item['id'] for item in request('teacher_a','GET','/tasks').json]==['active-a']
    with transaction() as db:assert db.get(Task,'finished-a') is None and db.get(Task,'finished-b').state=='failed'
    result=request('teacher_a','DELETE','/audit')
    assert result.status_code==200 and result.json['removed']>=1
    assert [item['action'] for item in request('teacher_a','GET','/audit').json]==['audit.cleared']
    assert any(item['action']=='kept' for item in request('teacher_b','GET','/audit').json)


def test_mcp_second_authorization(system):
    request,_,_=system
    from app.nexus.mcp_server import execute
    from app.nexus.security import issue
    with transaction() as db:
        user=db.scalar(select(User).where(User.username=='student_a1'));token=issue(user)
    a=request('teacher_a','GET','/agents').json[0];b=request('teacher_b','GET','/agents').json[0]
    with pytest.raises(PermissionError):execute('lecture_search',token,b['id'],query='x')
    with pytest.raises(PermissionError):execute('class_statistics',token,a['id'])
    assert 'assignments' in execute('current_assignments',token,request('teacher_a','GET','/agents').json[1]['id'])


@pytest.mark.parametrize('kind,question',[('guide','数学解题引导：方程怎么检查'),('grading','作业批改评分怎么核对'),('explain','错题错因讲解怎么进行')])
def test_three_builtin_skills_have_effect_and_can_be_disabled(system,monkeypatch,kind,question):
    request,run,_=system
    material=upload(request,content='数学解题引导：方程要检查条件。作业批改评分逐项核对标准。错题错因讲解从错误步骤分析。');run()
    skill=next(s for s in request('teacher_a','GET','/skills').json if s['kind']==kind)
    agent=request('teacher_a','GET','/agents').json[0]
    request('teacher_a','PATCH',f"/agents/{agent['id']}",json={'material_ids':[material['id']],'skill_ids':[skill['id']],'tools':[]})
    captured=[]
    def model(messages,actor,trace,tools=None,emit=None,**kwargs):
        captured.append(messages[0]['content'])
        if emit:emit({'event':'delta','text':'测试回答'})
        return {'role':'assistant','content':'测试回答'}
    monkeypatch.setattr(llm,'call',model)
    cid=request('student_a1','POST','/conversations',json={'agent_id':agent['id']}).json['id']
    response=request('student_a1','POST',f'/conversations/{cid}/messages',json={'question':question})
    assert 'event: done' in response.text and skill['body'] in captured[-1]
    request('teacher_a','PATCH',f"/skills/{skill['id']}",json={'enabled':False})
    response=request('student_a1','POST',f'/conversations/{cid}/messages',json={'question':question})
    assert 'event: done' in response.text and skill['body'] not in captured[-1]
