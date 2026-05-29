"""
Prompt Template Service - Prompt模板服务
支持获取、渲染、版本化管理
"""

import json
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.models.prompt_template import PromptTemplate
from app.utils.time_utils import utc_now


class PromptTemplateService:
    def __init__(self, db: Session):
        self.db = db

    def get_active_template(self, role: str, project_id: Optional[int] = None) -> Optional[PromptTemplate]:
        """获取指定角色的活跃模板"""
        query = self.db.query(PromptTemplate).filter(
            PromptTemplate.role == role,
            PromptTemplate.is_active == 1,
        )

        if project_id is not None:
            template = query.filter(PromptTemplate.project_id == project_id).order_by(
                PromptTemplate.version.desc()
            ).first()
            if template:
                return template

        return query.filter(PromptTemplate.project_id == None).order_by(
            PromptTemplate.version.desc()
        ).first()

    def render(self, role: str, variables: Dict, fallback: str, project_id: Optional[int] = None) -> str:
        """渲染模板"""
        template = self.get_active_template(role, project_id)
        content = template.content if template else fallback

        try:
            return content.format(**variables)
        except KeyError as e:
            missing = str(e)
            raise ValueError(f"Prompt 模板缺少变量: {missing}")

    def create_new_version(
        self,
        role: str,
        name: str,
        content: str,
        description: str = "",
        project_id: Optional[int] = None,
        activate: bool = True,
    ) -> PromptTemplate:
        """创建新版本模板"""
        latest = self.db.query(PromptTemplate).filter(
            PromptTemplate.role == role,
            PromptTemplate.project_id == project_id,
        ).order_by(PromptTemplate.version.desc()).first()

        next_version = (latest.version + 1) if latest else 1

        if activate:
            self.db.query(PromptTemplate).filter(
                PromptTemplate.role == role,
                PromptTemplate.project_id == project_id,
            ).update({"is_active": 0})

        template = PromptTemplate(
            role=role,
            name=name,
            version=next_version,
            content=content,
            description=description,
            project_id=project_id,
            is_active=1 if activate else 0,
        )

        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def list_templates(self, role: Optional[str] = None, project_id: Optional[int] = None):
        """列出版本历史"""
        query = self.db.query(PromptTemplate)

        if role:
            query = query.filter(PromptTemplate.role == role)
        if project_id is not None:
            query = query.filter(PromptTemplate.project_id == project_id)

        return query.order_by(PromptTemplate.role, PromptTemplate.version.desc()).all()

    def activate_template(self, template_id: int) -> PromptTemplate:
        """激活指定版本"""
        template = self.db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
        if not template:
            raise ValueError(f"模板不存在: {template_id}")

        # 停用同角色其他版本
        self.db.query(PromptTemplate).filter(
            PromptTemplate.role == template.role,
            PromptTemplate.project_id == template.project_id,
            PromptTemplate.id != template_id,
        ).update({"is_active": 0})

        template.is_active = 1
        self.db.commit()
        self.db.refresh(template)
        return template

    def disable_template(self, template_id: int) -> PromptTemplate:
        """停用指定版本"""
        template = self.db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
        if not template:
            raise ValueError(f"模板不存在: {template_id}")

        template.is_active = 0
        self.db.commit()
        self.db.refresh(template)
        return template
