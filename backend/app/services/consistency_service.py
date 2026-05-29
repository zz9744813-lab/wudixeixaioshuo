"""
Consistency Service - 元数据对齐检查服务 (B4)
人设、战力、时间线一致性检查
"""

import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from difflib import SequenceMatcher

from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_

from app.models.consistency import (
    ConsistencyRule, ConsistencyCheckResult, ConsistencyIssue,
    ConsistencyCheckType, ConsistencyIssueSeverity,
    CharacterConsistencyLog, TimelineEvent
)
from app.models.chapter import Chapter
from app.models.project import Project
from app.models.memory import CharacterMemory

logger = logging.getLogger(__name__)


class ConsistencyService:
    """一致性检查服务"""

    def __init__(self, db: Session):
        self.db = db

    # ========== 规则管理 ==========

    def create_rule(
        self,
        project_id: int,
        rule_type: ConsistencyCheckType,
        rule_name: str,
        description: str = "",
        rule_config: dict = None,
        auto_check: bool = True,
        check_frequency: str = "per_chapter",
        alert_threshold: ConsistencyIssueSeverity = ConsistencyIssueSeverity.MAJOR,
    ) -> ConsistencyRule:
        """创建一致性检查规则"""
        rule = ConsistencyRule(
            project_id=project_id,
            rule_type=rule_type,
            rule_name=rule_name,
            description=description,
            rule_config=rule_config or {},
            auto_check=auto_check,
            check_frequency=check_frequency,
            alert_threshold=alert_threshold,
            is_active=True,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        logger.info(f"创建一致性规则: project_id={project_id}, type={rule_type}, name={rule_name}")
        return rule

    def get_project_rules(
        self,
        project_id: int,
        rule_type: Optional[ConsistencyCheckType] = None,
        active_only: bool = True
    ) -> List[ConsistencyRule]:
        """获取项目的一致性规则"""
        query = self.db.query(ConsistencyRule).filter(
            ConsistencyRule.project_id == project_id
        )

        if rule_type:
            query = query.filter(ConsistencyRule.rule_type == rule_type)

        if active_only:
            query = query.filter(ConsistencyRule.is_active == True)

        return query.order_by(ConsistencyRule.created_at.desc()).all()

    def get_rule(self, rule_id: int) -> Optional[ConsistencyRule]:
        """获取规则详情"""
        return self.db.query(ConsistencyRule).filter(
            ConsistencyRule.id == rule_id
        ).first()

    def update_rule(self, rule_id: int, **kwargs) -> Optional[ConsistencyRule]:
        """更新规则"""
        rule = self.get_rule(rule_id)
        if not rule:
            return None

        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, rule_id: int) -> bool:
        """删除规则"""
        rule = self.get_rule(rule_id)
        if not rule:
            return False

        self.db.delete(rule)
        self.db.commit()
        return True

    # ========== 自动规则创建 ==========

    def create_character_rules_from_bible(self, project_id: int) -> List[ConsistencyRule]:
        """从圣经中的人物设定自动创建人设一致性规则"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project or not project.bible:
            return []

        rules = []
        characters = project.bible.characters or []

        for char in characters:
            if isinstance(char, dict):
                char_name = char.get("name") or char.get("姓名")
                if not char_name:
                    continue

                # 提取人设关键属性
                attributes = []
                for key in ["性格", "外貌", "口头禅", "习惯动作", "核心价值观", "能力", "修为"]:
                    if key in char:
                        attributes.append(key)

                if attributes:
                    rule = self.create_rule(
                        project_id=project_id,
                        rule_type=ConsistencyCheckType.CHARACTER,
                        rule_name=f"人设一致性：{char_name}",
                        description=f"检查{char_name}的人设在各章节保持一致",
                        rule_config={
                            "character_name": char_name,
                            "character_data": char,
                            "key_attributes": attributes,
                            "forbidden_changes": ["核心价值观", "核心能力"],
                        },
                        auto_check=True,
                        check_frequency="per_chapter",
                    )
                    rules.append(rule)

        logger.info(f"从圣经创建了 {len(rules)} 个人设一致性规则")
        return rules

    def create_power_system_rules(self, project_id: int, power_system_config: dict) -> ConsistencyRule:
        """创建战力体系一致性规则"""
        rule = self.create_rule(
            project_id=project_id,
            rule_type=ConsistencyCheckType.POWER,
            rule_name=f"战力体系：{power_system_config.get('name', '默认')}",
            description="检查战力体系的一致性和合理性",
            rule_config={
                "power_system_name": power_system_config.get("name", "修炼体系"),
                "levels": power_system_config.get("levels", []),
                "level_hierarchy": power_system_config.get("hierarchy", {}),
                "power_growth_rules": power_system_config.get("growth_rules", []),
                "battle_rules": power_system_config.get("battle_rules", []),
            },
            auto_check=True,
            check_frequency="per_chapter",
            alert_threshold=ConsistencyIssueSeverity.CRITICAL,
        )
        return rule

    def create_timeline_rules(self, project_id: int, timeline_config: dict) -> ConsistencyRule:
        """创建时间线一致性规则"""
        rule = self.create_rule(
            project_id=project_id,
            rule_type=ConsistencyCheckType.TIMELINE,
            rule_name="时间线一致性",
            description="检查故事时间线的连续性和合理性",
            rule_config={
                "time_flow": timeline_config.get("flow", "linear"),  # linear, flashback, parallel
                "time_unit": timeline_config.get("unit", "day"),  # day, month, year
                "key_events": timeline_config.get("key_events", []),
                "allow_flashback": timeline_config.get("allow_flashback", True),
                "max_time_jump": timeline_config.get("max_jump", None),  # 最大时间跳跃
            },
            auto_check=True,
            check_frequency="per_chapter",
            alert_threshold=ConsistencyIssueSeverity.MAJOR,
        )
        return rule

    # ========== 一致性检查 ==========

    def check_consistency(
        self,
        project_id: int,
        chapter_id: Optional[int] = None,
        rule_ids: Optional[List[int]] = None,
        scope: str = "auto"  # auto, single, recent, volume, full
    ) -> ConsistencyCheckResult:
        """
        执行一致性检查

        Args:
            project_id: 项目ID
            chapter_id: 特定章节ID（可选）
            rule_ids: 指定规则ID列表（可选，默认检查所有活跃规则）
            scope: 检查范围
        """
        # 获取要检查的规则
        if rule_ids:
            rules = [
                self.get_rule(rid) for rid in rule_ids
                if self.get_rule(rid) and self.get_rule(rid).is_active
            ]
        else:
            rules = self.get_project_rules(project_id, active_only=True)

        if not rules:
            # 创建默认规则
            rules = self._create_default_rules(project_id)

        # 确定检查范围
        check_chapters = self._get_check_scope(project_id, chapter_id, scope)

        # 创建检查结果
        result = ConsistencyCheckResult(
            project_id=project_id,
            chapter_id=chapter_id,
            checked_chapters=[c.id for c in check_chapters],
            check_scope=scope,
            status="running",
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)

        # 执行检查
        total_issues = []
        for rule in rules:
            issues = self._check_by_rule(rule, check_chapters, result.id)
            total_issues.extend(issues)

        # 更新结果统计
        result.total_issues = len(total_issues)
        result.critical_count = sum(1 for i in total_issues if i.severity == ConsistencyIssueSeverity.CRITICAL)
        result.major_count = sum(1 for i in total_issues if i.severity == ConsistencyIssueSeverity.MAJOR)
        result.minor_count = sum(1 for i in total_issues if i.severity == ConsistencyIssueSeverity.MINOR)
        result.info_count = sum(1 for i in total_issues if i.severity == ConsistencyIssueSeverity.INFO)
        result.status = "completed"
        result.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(result)

        logger.info(f"一致性检查完成: result_id={result.id}, issues={len(total_issues)}")
        return result

    def _create_default_rules(self, project_id: int) -> List[ConsistencyRule]:
        """创建默认的一致性规则"""
        rules = []

        # 从圣经创建人设规则
        character_rules = self.create_character_rules_from_bible(project_id)
        rules.extend(character_rules)

        # 如果没有人物规则，创建一个通用规则
        if not character_rules:
            rule = self.create_rule(
                project_id=project_id,
                rule_type=ConsistencyCheckType.CHARACTER,
                rule_name="人设基础一致性",
                description="检查主要人物人设的基本一致性",
                rule_config={"check_basic_attributes": True},
            )
            rules.append(rule)

        # 创建时间线规则
        timeline_rule = self.create_rule(
            project_id=project_id,
            rule_type=ConsistencyCheckType.TIMELINE,
            rule_name="时间线基础一致性",
            description="检查时间线的基本连续性",
            rule_config={"check_continuity": True},
        )
        rules.append(timeline_rule)

        return rules

    def _get_check_scope(
        self,
        project_id: int,
        chapter_id: Optional[int],
        scope: str
    ) -> List[Chapter]:
        """获取检查范围对应的章节列表"""
        base_query = self.db.query(Chapter).filter(
            Chapter.project_id == project_id
        )

        if scope == "single" and chapter_id:
            # 只检查指定章节
            chapter = base_query.filter(Chapter.id == chapter_id).first()
            return [chapter] if chapter else []

        elif scope == "recent":
            # 最近10章
            return base_query.order_by(desc(Chapter.chapter_index)).limit(10).all()

        elif scope == "volume":
            # 获取指定章节所在卷的所有章节
            if chapter_id:
                chapter = base_query.filter(Chapter.id == chapter_id).first()
                if chapter and hasattr(chapter, 'volume_index'):
                    return base_query.filter(
                        Chapter.volume_index == chapter.volume_index
                    ).order_by(Chapter.chapter_index).all()
            # 默认返回最近一卷
            return base_query.order_by(desc(Chapter.chapter_index)).limit(50).all()

        elif scope == "full":
            # 全部章节
            return base_query.order_by(Chapter.chapter_index).all()

        else:  # auto
            # 自动判断：如果有指定章节，检查该章节和最近5章
            if chapter_id:
                chapter = base_query.filter(Chapter.id == chapter_id).first()
                if chapter:
                    recent = base_query.filter(
                        Chapter.chapter_index <= chapter.chapter_index
                    ).order_by(desc(Chapter.chapter_index)).limit(6).all()
                    return recent

            # 默认最近5章
            return base_query.order_by(desc(Chapter.chapter_index)).limit(5).all()

    def _check_by_rule(
        self,
        rule: ConsistencyRule,
        chapters: List[Chapter],
        result_id: int
    ) -> List[ConsistencyIssue]:
        """根据规则执行检查"""
        if rule.rule_type == ConsistencyCheckType.CHARACTER:
            return self._check_character_consistency(rule, chapters, result_id)
        elif rule.rule_type == ConsistencyCheckType.POWER:
            return self._check_power_consistency(rule, chapters, result_id)
        elif rule.rule_type == ConsistencyCheckType.TIMELINE:
            return self._check_timeline_consistency(rule, chapters, result_id)
        elif rule.rule_type == ConsistencyCheckType.WORLD_SETTING:
            return self._check_world_setting_consistency(rule, chapters, result_id)
        elif rule.rule_type == ConsistencyCheckType.RELATIONSHIP:
            return self._check_relationship_consistency(rule, chapters, result_id)

        return []

    # ========== 具体检查实现 ==========

    def _check_character_consistency(
        self,
        rule: ConsistencyRule,
        chapters: List[Chapter],
        result_id: int
    ) -> List[ConsistencyIssue]:
        """检查人设一致性"""
        issues = []
        config = rule.rule_config or {}
        char_name = config.get("character_name")
        key_attrs = config.get("key_attributes", [])
        forbidden_changes = config.get("forbidden_changes", [])

        if not chapters or not char_name:
            return issues

        # 按章节顺序排序
        sorted_chapters = sorted(chapters, key=lambda c: c.chapter_index)

        # 获取人物的历史记录
        char_logs = self.db.query(CharacterConsistencyLog).filter(
            CharacterConsistencyLog.project_id == rule.project_id,
            CharacterConsistencyLog.character_name == char_name,
        ).order_by(CharacterConsistencyLog.created_at).all()

        # 构建属性历史
        attr_history = {}  # {attribute: [(chapter_id, value), ...]}
        for log in char_logs:
            attrs = log.attributes or {}
            for attr, value in attrs.items():
                if attr not in attr_history:
                    attr_history[attr] = []
                attr_history[attr].append((log.chapter_id, value))

        # 检查关键属性的变化
        for attr in key_attrs:
            if attr not in attr_history or len(attr_history[attr]) < 2:
                continue

            history = attr_history[attr]
            # 检查是否有突变（非渐进式变化）
            for i in range(1, len(history)):
                prev_chapter_id, prev_value = history[i - 1]
                curr_chapter_id, curr_value = history[i]

                # 判断是否发生了不允许的变化
                if self._is_significant_change(prev_value, curr_value, attr):
                    # 检查是否是被禁止的变化类型
                    severity = ConsistencyIssueSeverity.MAJOR
                    if attr in forbidden_changes:
                        severity = ConsistencyIssueSeverity.CRITICAL

                    # 获取章节信息
                    curr_chapter = next(
                        (c for c in sorted_chapters if c.id == curr_chapter_id), None
                    )
                    if curr_chapter:
                        issue = ConsistencyIssue(
                            result_id=result_id,
                            chapter_id=curr_chapter_id,
                            issue_type=ConsistencyCheckType.CHARACTER,
                            severity=severity,
                            title=f"{char_name}的{attr}发生突变",
                            description=f"{char_name}的{attr}从前一状态的'{prev_value}'突变为'{curr_value}'",
                            location=f"第{curr_chapter.chapter_index}章",
                            expected_value=str(prev_value),
                            actual_value=str(curr_value),
                            reference_location=f"第{self._get_chapter_index_by_id(prev_chapter_id)}章",
                            fix_suggestion=f"检查{char_name}的{attr}变化是否有合理铺垫，或修正为渐进式变化",
                        )
                        self.db.add(issue)
                        issues.append(issue)

        self.db.commit()
        return issues

    def _check_power_consistency(
        self,
        rule: ConsistencyRule,
        chapters: List[Chapter],
        result_id: int
    ) -> List[ConsistencyIssue]:
        """检查战力体系一致性"""
        issues = []
        config = rule.rule_config or {}
        levels = config.get("levels", [])
        hierarchy = config.get("level_hierarchy", {})

        if not levels:
            return issues

        # 构建等级映射
        level_order = {level: idx for idx, level in enumerate(levels)}

        # 检查每个章节中的战力描述
        for chapter in chapters:
            content = chapter.final_content or chapter.draft_content or ""
            if not content:
                continue

            # 简单的战力关键词检测（实际应该使用更复杂的NLP或LLM分析）
            # 这里作为示例，检查是否有越级战斗的描述
            # TODO: 集成LLM进行更准确的战力分析

        self.db.commit()
        return issues

    def _check_timeline_consistency(
        self,
        rule: ConsistencyRule,
        chapters: List[Chapter],
        result_id: int
    ) -> List[ConsistencyIssue]:
        """检查时间线一致性"""
        issues = []
        config = rule.rule_config or {}
        time_flow = config.get("time_flow", "linear")

        # 获取时间线事件
        events = self.db.query(TimelineEvent).filter(
            TimelineEvent.project_id == rule.project_id,
        ).order_by(TimelineEvent.story_time_order).all()

        if len(events) < 2:
            return issues

        # 检查时间顺序
        for i in range(1, len(events)):
            prev_event = events[i - 1]
            curr_event = events[i]

            # 检查时间顺序是否合理
            if (curr_event.story_time_order is not None and
                prev_event.story_time_order is not None and
                curr_event.story_time_order < prev_event.story_time_order):

                # 检查是否标记为回忆/倒叙
                if not curr_event.is_flashback:
                    issue = ConsistencyIssue(
                        result_id=result_id,
                        chapter_id=curr_event.chapter_id,
                        issue_type=ConsistencyCheckType.TIMELINE,
                        severity=ConsistencyIssueSeverity.MAJOR,
                        title="时间线逆序",
                        description=f"事件'{curr_event.event_name}'的时间({curr_event.story_time})早于前一事件'{prev_event.event_name}'的时间({prev_event.story_time})",
                        location=f"第{self._get_chapter_index_by_id(curr_event.chapter_id)}章" if curr_event.chapter_id else "未知",
                        expected_value=f"时间应晚于 {prev_event.story_time}",
                        actual_value=curr_event.story_time,
                        fix_suggestion="检查时间设置是否正确，或标记为回忆/倒叙",
                    )
                    self.db.add(issue)
                    issues.append(issue)

        self.db.commit()
        return issues

    def _check_world_setting_consistency(
        self,
        rule: ConsistencyRule,
        chapters: List[Chapter],
        result_id: int
    ) -> List[ConsistencyIssue]:
        """检查世界观设定一致性"""
        issues = []
        # TODO: 实现世界观设定检查
        return issues

    def _check_relationship_consistency(
        self,
        rule: ConsistencyRule,
        chapters: List[Chapter],
        result_id: int
    ) -> List[ConsistencyIssue]:
        """检查人物关系一致性"""
        issues = []
        # TODO: 实现人物关系检查
        return issues

    # ========== 辅助方法 ==========

    def _is_significant_change(self, prev_value: Any, curr_value: Any, attr_name: str) -> bool:
        """判断是否为显著变化"""
        # 字符串相似度检查
        if isinstance(prev_value, str) and isinstance(curr_value, str):
            similarity = SequenceMatcher(None, prev_value, curr_value).ratio()
            # 相似度低于0.5认为是显著变化
            return similarity < 0.5

        # 列表比较
        if isinstance(prev_value, list) and isinstance(curr_value, list):
            set_prev = set(str(x) for x in prev_value)
            set_curr = set(str(x) for x in curr_value)
            # 如果交集小于并集的50%，认为是显著变化
            if not set_prev and not set_curr:
                return False
            intersection = len(set_prev & set_curr)
            union = len(set_prev | set_curr)
            return intersection / union < 0.5 if union > 0 else False

        # 其他类型直接比较
        return str(prev_value) != str(curr_value)

    def _get_chapter_index_by_id(self, chapter_id: Optional[int]) -> str:
        """通过ID获取章节序号"""
        if not chapter_id:
            return "?"
        chapter = self.db.query(Chapter).filter(Chapter.id == chapter_id).first()
        return str(chapter.chapter_index) if chapter else "?"

    # ========== 检查结果管理 ==========

    def get_check_result(self, result_id: int) -> Optional[ConsistencyCheckResult]:
        """获取检查结果"""
        return self.db.query(ConsistencyCheckResult).filter(
            ConsistencyCheckResult.id == result_id
        ).first()

    def get_project_results(
        self,
        project_id: int,
        limit: int = 20
    ) -> List[ConsistencyCheckResult]:
        """获取项目的检查结果历史"""
        return self.db.query(ConsistencyCheckResult).filter(
            ConsistencyCheckResult.project_id == project_id
        ).order_by(desc(ConsistencyCheckResult.created_at)).limit(limit).all()

    def get_issues(
        self,
        result_id: Optional[int] = None,
        project_id: Optional[int] = None,
        severity: Optional[ConsistencyIssueSeverity] = None,
        status: Optional[str] = None,
    ) -> List[ConsistencyIssue]:
        """获取问题列表"""
        query = self.db.query(ConsistencyIssue)

        if result_id:
            query = query.filter(ConsistencyIssue.result_id == result_id)

        if project_id:
            query = query.join(ConsistencyCheckResult).filter(
                ConsistencyCheckResult.project_id == project_id
            )

        if severity:
            query = query.filter(ConsistencyIssue.severity == severity)

        if status:
            query = query.filter(ConsistencyIssue.status == status)

        return query.order_by(desc(ConsistencyIssue.created_at)).all()

    def update_issue_status(
        self,
        issue_id: int,
        status: str,
        fixed_by: Optional[str] = None
    ) -> Optional[ConsistencyIssue]:
        """更新问题状态"""
        issue = self.db.query(ConsistencyIssue).filter(
            ConsistencyIssue.id == issue_id
        ).first()

        if not issue:
            return None

        issue.status = status
        if status == "fixed":
            issue.fixed_at = datetime.utcnow()
            issue.fixed_by = fixed_by or "manual"

        self.db.commit()
        self.db.refresh(issue)
        return issue

    # ========== 人物一致性日志 ==========

    def log_character_state(
        self,
        project_id: int,
        character_name: str,
        chapter_id: int,
        attributes: Dict[str, Any],
        change_type: str = "unchanged",
    ) -> CharacterConsistencyLog:
        """记录人物状态快照"""
        # 检测变化字段
        changed_fields = []
        prev_log = self.db.query(CharacterConsistencyLog).filter(
            CharacterConsistencyLog.project_id == project_id,
            CharacterConsistencyLog.character_name == character_name,
        ).order_by(desc(CharacterConsistencyLog.created_at)).first()

        if prev_log and prev_log.attributes:
            for key, value in attributes.items():
                if key not in prev_log.attributes or prev_log.attributes[key] != value:
                    changed_fields.append(key)

        log = CharacterConsistencyLog(
            project_id=project_id,
            character_name=character_name,
            chapter_id=chapter_id,
            attributes=attributes,
            changed_fields=changed_fields,
            change_type=change_type if changed_fields else "unchanged",
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_character_history(
        self,
        project_id: int,
        character_name: str,
    ) -> List[CharacterConsistencyLog]:
        """获取人物历史状态"""
        return self.db.query(CharacterConsistencyLog).filter(
            CharacterConsistencyLog.project_id == project_id,
            CharacterConsistencyLog.character_name == character_name,
        ).order_by(CharacterConsistencyLog.created_at).all()

    # ========== 时间线事件 ==========

    def add_timeline_event(
        self,
        project_id: int,
        event_name: str,
        story_time: str,
        story_time_order: float,
        event_description: str = "",
        chapter_id: Optional[int] = None,
        related_characters: List[str] = None,
        related_locations: List[str] = None,
        is_key_event: bool = False,
        is_flashback: bool = False,
    ) -> TimelineEvent:
        """添加时间线事件"""
        event = TimelineEvent(
            project_id=project_id,
            chapter_id=chapter_id,
            event_name=event_name,
            event_description=event_description,
            story_time=story_time,
            story_time_order=story_time_order,
            related_characters=related_characters or [],
            related_locations=related_locations or [],
            is_key_event=is_key_event,
            is_flashback=is_flashback,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_timeline(self, project_id: int) -> List[TimelineEvent]:
        """获取项目时间线"""
        return self.db.query(TimelineEvent).filter(
            TimelineEvent.project_id == project_id
        ).order_by(TimelineEvent.story_time_order).all()

    # ========== Prompt 生成 ==========

    def generate_consistency_prompt(self, project_id: int, chapter_id: int) -> str:
        """
        生成用于Critic的一致性检查prompt片段

        这个prompt片段可以插入到Critic的prompt中，让LLM检查一致性
        """
        # 获取相关规则
        rules = self.get_project_rules(project_id, active_only=True)

        if not rules:
            return ""

        sections = ["\n## 一致性检查要求"]

        for rule in rules:
            if rule.rule_type == ConsistencyCheckType.CHARACTER:
                config = rule.rule_config or {}
                char_name = config.get("character_name")
                if char_name:
                    sections.append(f"\n**人设一致性 - {char_name}**:")
                    sections.append(f"- 确保{char_name}的言行符合人设")
                    # 获取最近的人物状态
                    recent_log = self.db.query(CharacterConsistencyLog).filter(
                        CharacterConsistencyLog.project_id == project_id,
                        CharacterConsistencyLog.character_name == char_name,
                    ).order_by(desc(CharacterConsistencyLog.created_at)).first()
                    if recent_log and recent_log.attributes:
                        sections.append(f"- 当前状态: {json.dumps(recent_log.attributes, ensure_ascii=False)}")

            elif rule.rule_type == ConsistencyCheckType.TIMELINE:
                sections.append("\n**时间线一致性**:")
                sections.append("- 确保时间顺序合理，无逻辑矛盾")
                sections.append("- 如有时间跳跃，需有明确过渡")

            elif rule.rule_type == ConsistencyCheckType.POWER:
                config = rule.rule_config or {}
                levels = config.get("levels", [])
                if levels:
                    sections.append(f"\n**战力体系一致性**:")
                    sections.append(f"- 等级体系: {' → '.join(levels[:5])}")
                    sections.append("- 确保战力表现符合等级设定")

        return "\n".join(sections)
