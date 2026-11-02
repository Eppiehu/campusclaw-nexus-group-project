from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')


class Login(Strict):
    username:str=Field(min_length=1,max_length=64)
    password:str=Field(min_length=1,max_length=200)


class LectureTitle(Strict):
    title:str=Field(min_length=1,max_length=40)


def rubric_text(value)->str:
    if isinstance(value,str):return value.strip()
    if isinstance(value,list):
        names=[]
        for item in value:
            if isinstance(item,dict) and str(item.get('name') or '').strip():names.append(str(item['name']).strip())
            elif isinstance(item,str) and item.strip():names.append(item.strip())
        return '、'.join(names)
    return ''


class AssignmentInput(Strict):
    title:str=Field(min_length=1,max_length=200)
    question_template:str=Field(min_length=1,max_length=4000)
    ranges:dict[str,list[int]]
    answer_expression:str=Field(min_length=1,max_length=200)
    answer_hint:str=Field(default='',max_length=2000)
    rubric:str=Field(min_length=1,max_length=2000)
    deadline:str

    @model_validator(mode='after')
    def valid(self):
        import re
        for key,bounds in self.ranges.items():
            if not re.fullmatch('[a-z][a-z0-9_]{0,15}',key) or len(bounds)!=2 or not -10000<=bounds[0]<=bounds[1]<=10000:
                raise ValueError('参数名或范围不合法')
        if not self.ranges or len(self.ranges)>5:raise ValueError('参数数量须为1到5')
        text=self.rubric.strip()
        if not text or len(text)>2000:raise ValueError('评分说明须为1至2000字')
        self.rubric=text
        hint=self.answer_hint.strip()
        if len(hint)>2000:raise ValueError('作答提示不能超过2000字')
        self.answer_hint=hint
        return self


class Grade(Strict):
    score:float=Field(ge=0,le=100)
    feedback:str=Field(min_length=1,max_length=3000)


class WeeklyComment(Strict):
    observations:list[str]=Field(max_length=6)
    suggestions:list[str]=Field(max_length=6)
    evidence_keys:list[str]=Field(max_length=12)
