"""
Add Agent Run Models P0

添加P0阶段Agent运行相关模型：
- agent_runs: Agent运行记录
- agent_plans: Agent计划
- agent_steps: Agent步骤
- subagent_tasks: 子Agent任务
- provider_route_configs: Provider路由配置
- research_runs/sources: 研究运行和来源
- knowledge_patterns/reader_insights/trend_reports: 知识沉淀
- prompt_evolution_policies/runs: Prompt进化

Revision ID: 7b6f2991235c
Revises: cf572852293f
Create Date: 2026-05-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b6f2991235c'
down_revision: Union[str, None] = 'add_consistency_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Agent Run 相关表 ###

    # agent_runs 表
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('user_request', sa.Text(), nullable=False),
        sa.Column('mode', sa.String(32), default='autonomous'),
        sa.Column('status', sa.String(32), default='pending'),
        sa.Column('budget_tokens', sa.Integer(), nullable=True),
        sa.Column('budget_cost', sa.Float(), nullable=True),
        sa.Column('used_tokens', sa.Integer(), default=0),
        sa.Column('used_cost', sa.Float(), default=0.0),
        sa.Column('max_steps', sa.Integer(), default=30),
        sa.Column('max_retries', sa.Integer(), default=2),
        sa.Column('max_concurrency', sa.Integer(), default=3),
        sa.Column('final_report', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_runs_id', 'agent_runs', ['id'])
    op.create_index('ix_agent_runs_project_id', 'agent_runs', ['project_id'])
    op.create_index('ix_agent_runs_status', 'agent_runs', ['status'])

    # agent_plans 表
    op.create_table(
        'agent_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('plan_json', sa.JSON(), nullable=False),
        sa.Column('planner_model', sa.String(128), nullable=True),
        sa.Column('status', sa.String(32), default='created'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE')
    )
    op.create_index('ix_agent_plans_id', 'agent_plans', ['id'])
    op.create_index('ix_agent_plans_run_id', 'agent_plans', ['run_id'])

    # agent_steps 表
    op.create_table(
        'agent_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('step_key', sa.String(64), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('tool_name', sa.String(128), nullable=False),
        sa.Column('args_json', sa.JSON(), nullable=True),
        sa.Column('depends_on', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(32), default='pending'),
        sa.Column('attempt_count', sa.Integer(), default=0),
        sa.Column('input_snapshot', sa.JSON(), nullable=True),
        sa.Column('output_json', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), default=0),
        sa.Column('output_tokens', sa.Integer(), default=0),
        sa.Column('total_tokens', sa.Integer(), default=0),
        sa.Column('cost', sa.Float(), default=0.0),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['agent_plans.id'], ondelete='CASCADE')
    )
    op.create_index('ix_agent_steps_id', 'agent_steps', ['id'])
    op.create_index('ix_agent_steps_run_id', 'agent_steps', ['run_id'])
    op.create_index('ix_agent_steps_plan_id', 'agent_steps', ['plan_id'])
    op.create_index('ix_agent_steps_status', 'agent_steps', ['status'])

    # subagent_tasks 表
    op.create_table(
        'subagent_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('parent_step_id', sa.Integer(), nullable=True),
        sa.Column('task_type', sa.String(64), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('role', sa.String(64), nullable=False),
        sa.Column('status', sa.String(32), default='pending'),
        sa.Column('context_json', sa.JSON(), nullable=True),
        sa.Column('input_prompt', sa.Text(), nullable=True),
        sa.Column('output_text', sa.Text(), nullable=True),
        sa.Column('parsed_output', sa.JSON(), nullable=True),
        sa.Column('provider_name', sa.String(128), nullable=True),
        sa.Column('model_name', sa.String(128), nullable=True),
        sa.Column('token_count', sa.Integer(), default=0),
        sa.Column('cost', sa.Float(), default=0.0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_step_id'], ['agent_steps.id'], ondelete='CASCADE')
    )
    op.create_index('ix_subagent_tasks_id', 'subagent_tasks', ['id'])
    op.create_index('ix_subagent_tasks_run_id', 'subagent_tasks', ['run_id'])
    op.create_index('ix_subagent_tasks_parent_step_id', 'subagent_tasks', ['parent_step_id'])
    op.create_index('ix_subagent_tasks_status', 'subagent_tasks', ['status'])

    # ### Provider Route Config 表 ###
    op.create_table(
        'provider_route_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(64), nullable=False),
        sa.Column('priority', sa.Integer(), default=100),
        sa.Column('weight', sa.Integer(), default=1),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('rpm_limit', sa.Integer(), nullable=True),
        sa.Column('tpm_limit', sa.Integer(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), default=60),
        sa.Column('max_retries', sa.Integer(), default=2),
        sa.Column('circuit_breaker_threshold', sa.Integer(), default=5),
        sa.Column('circuit_breaker_reset_seconds', sa.Integer(), default=300),
        sa.Column('consecutive_failures', sa.Integer(), default=0),
        sa.Column('circuit_breaker_opened_at', sa.DateTime(), nullable=True),
        sa.Column('total_calls', sa.Integer(), default=0),
        sa.Column('success_calls', sa.Integer(), default=0),
        sa.Column('failed_calls', sa.Integer(), default=0),
        sa.Column('avg_latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['provider_id'], ['model_providers.id'], ondelete='CASCADE')
    )
    op.create_index('ix_provider_route_configs_id', 'provider_route_configs', ['id'])
    op.create_index('ix_provider_route_configs_provider_id', 'provider_route_configs', ['provider_id'])
    op.create_index('ix_provider_route_configs_role', 'provider_route_configs', ['role'])

    # ### Research 相关表 ###

    # research_runs 表
    op.create_table(
        'research_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.Column('topic', sa.String(255), nullable=False),
        sa.Column('research_type', sa.String(64), nullable=False),
        sa.Column('status', sa.String(32), default='pending'),
        sa.Column('query_plan_json', sa.JSON(), nullable=True),
        sa.Column('extracted_summary', sa.Text(), nullable=True),
        sa.Column('result_json', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='SET NULL')
    )
    op.create_index('ix_research_runs_id', 'research_runs', ['id'])
    op.create_index('ix_research_runs_project_id', 'research_runs', ['project_id'])
    op.create_index('ix_research_runs_run_id', 'research_runs', ['run_id'])

    # research_sources 表
    op.create_table(
        'research_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('research_run_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(64), nullable=True),
        sa.Column('trust_score', sa.Float(), default=0.5),
        sa.Column('extracted_text_hash', sa.String(128), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('used_for', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['research_run_id'], ['research_runs.id'], ondelete='CASCADE')
    )
    op.create_index('ix_research_sources_id', 'research_sources', ['id'])
    op.create_index('ix_research_sources_research_run_id', 'research_sources', ['research_run_id'])

    # knowledge_patterns 表
    op.create_table(
        'knowledge_patterns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('genre', sa.String(128), nullable=True),
        sa.Column('tag', sa.String(128), nullable=True),
        sa.Column('pattern_name', sa.String(255), nullable=False),
        sa.Column('pattern_type', sa.String(64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('applicable_scene', sa.Text(), nullable=True),
        sa.Column('anti_patterns', sa.Text(), nullable=True),
        sa.Column('source_ids', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), default=0.5),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_patterns_id', 'knowledge_patterns', ['id'])
    op.create_index('ix_knowledge_patterns_genre', 'knowledge_patterns', ['genre'])
    op.create_index('ix_knowledge_patterns_pattern_type', 'knowledge_patterns', ['pattern_type'])

    # reader_insights 表
    op.create_table(
        'reader_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('genre', sa.String(128), nullable=True),
        sa.Column('insight_type', sa.String(64), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('source_ids', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), default=0.5),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reader_insights_id', 'reader_insights', ['id'])
    op.create_index('ix_reader_insights_genre', 'reader_insights', ['genre'])
    op.create_index('ix_reader_insights_insight_type', 'reader_insights', ['insight_type'])

    # trend_reports 表
    op.create_table(
        'trend_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('genre', sa.String(128), nullable=True),
        sa.Column('platform', sa.String(128), nullable=True),
        sa.Column('report_title', sa.String(255), nullable=False),
        sa.Column('report_body', sa.Text(), nullable=False),
        sa.Column('trend_tags', sa.JSON(), nullable=True),
        sa.Column('source_ids', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trend_reports_id', 'trend_reports', ['id'])
    op.create_index('ix_trend_reports_genre', 'trend_reports', ['genre'])
    op.create_index('ix_trend_reports_platform', 'trend_reports', ['platform'])

    # ### Prompt Evolution 相关表 ###

    # prompt_evolution_policies 表
    op.create_table(
        'prompt_evolution_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(64), nullable=False),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('min_sample_count', sa.Integer(), default=20),
        sa.Column('min_average_score', sa.Float(), default=80.0),
        sa.Column('max_rewrite_rate', sa.Float(), default=0.4),
        sa.Column('trigger_window_days', sa.Integer(), default=7),
        sa.Column('candidate_count', sa.Integer(), default=3),
        sa.Column('ab_test_sample_count', sa.Integer(), default=10),
        sa.Column('min_improvement', sa.Float(), default=3.0),
        sa.Column('auto_apply', sa.Boolean(), default=True),
        sa.Column('rollout_ratio', sa.Float(), default=0.2),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prompt_evolution_policies_id', 'prompt_evolution_policies', ['id'])
    op.create_index('ix_prompt_evolution_policies_role', 'prompt_evolution_policies', ['role'])

    # prompt_evolution_runs 表
    op.create_table(
        'prompt_evolution_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(64), nullable=False),
        sa.Column('status', sa.String(32), default='pending'),
        sa.Column('diagnosis', sa.Text(), nullable=True),
        sa.Column('failure_samples_json', sa.JSON(), nullable=True),
        sa.Column('candidate_prompts_json', sa.JSON(), nullable=True),
        sa.Column('ab_test_result_json', sa.JSON(), nullable=True),
        sa.Column('applied_prompt_version_id', sa.Integer(), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('rolled_back_at', sa.DateTime(), nullable=True),
        sa.Column('rollback_reason', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['policy_id'], ['prompt_evolution_policies.id'], ondelete='CASCADE')
    )
    op.create_index('ix_prompt_evolution_runs_id', 'prompt_evolution_runs', ['id'])
    op.create_index('ix_prompt_evolution_runs_policy_id', 'prompt_evolution_runs', ['policy_id'])
    op.create_index('ix_prompt_evolution_runs_role', 'prompt_evolution_runs', ['role'])
    op.create_index('ix_prompt_evolution_runs_status', 'prompt_evolution_runs', ['status'])


def downgrade() -> None:
    # 删除所有新表（逆序），先删除索引以兼容 SQLite 批量迁移场景
    op.drop_index('ix_prompt_evolution_runs_status', table_name='prompt_evolution_runs')
    op.drop_index('ix_prompt_evolution_runs_role', table_name='prompt_evolution_runs')
    op.drop_index('ix_prompt_evolution_runs_policy_id', table_name='prompt_evolution_runs')
    op.drop_index('ix_prompt_evolution_runs_id', table_name='prompt_evolution_runs')
    op.drop_table('prompt_evolution_runs')

    op.drop_index('ix_prompt_evolution_policies_role', table_name='prompt_evolution_policies')
    op.drop_index('ix_prompt_evolution_policies_id', table_name='prompt_evolution_policies')
    op.drop_table('prompt_evolution_policies')

    op.drop_index('ix_trend_reports_platform', table_name='trend_reports')
    op.drop_index('ix_trend_reports_genre', table_name='trend_reports')
    op.drop_index('ix_trend_reports_id', table_name='trend_reports')
    op.drop_table('trend_reports')

    op.drop_index('ix_reader_insights_insight_type', table_name='reader_insights')
    op.drop_index('ix_reader_insights_genre', table_name='reader_insights')
    op.drop_index('ix_reader_insights_id', table_name='reader_insights')
    op.drop_table('reader_insights')

    op.drop_index('ix_knowledge_patterns_pattern_type', table_name='knowledge_patterns')
    op.drop_index('ix_knowledge_patterns_genre', table_name='knowledge_patterns')
    op.drop_index('ix_knowledge_patterns_id', table_name='knowledge_patterns')
    op.drop_table('knowledge_patterns')

    op.drop_index('ix_research_sources_research_run_id', table_name='research_sources')
    op.drop_index('ix_research_sources_id', table_name='research_sources')
    op.drop_table('research_sources')

    op.drop_index('ix_research_runs_run_id', table_name='research_runs')
    op.drop_index('ix_research_runs_project_id', table_name='research_runs')
    op.drop_index('ix_research_runs_id', table_name='research_runs')
    op.drop_table('research_runs')

    op.drop_index('ix_provider_route_configs_role', table_name='provider_route_configs')
    op.drop_index('ix_provider_route_configs_provider_id', table_name='provider_route_configs')
    op.drop_index('ix_provider_route_configs_id', table_name='provider_route_configs')
    op.drop_table('provider_route_configs')

    op.drop_index('ix_subagent_tasks_status', table_name='subagent_tasks')
    op.drop_index('ix_subagent_tasks_parent_step_id', table_name='subagent_tasks')
    op.drop_index('ix_subagent_tasks_run_id', table_name='subagent_tasks')
    op.drop_index('ix_subagent_tasks_id', table_name='subagent_tasks')
    op.drop_table('subagent_tasks')

    op.drop_index('ix_agent_steps_status', table_name='agent_steps')
    op.drop_index('ix_agent_steps_plan_id', table_name='agent_steps')
    op.drop_index('ix_agent_steps_run_id', table_name='agent_steps')
    op.drop_index('ix_agent_steps_id', table_name='agent_steps')
    op.drop_table('agent_steps')

    op.drop_index('ix_agent_plans_run_id', table_name='agent_plans')
    op.drop_index('ix_agent_plans_id', table_name='agent_plans')
    op.drop_table('agent_plans')

    op.drop_index('ix_agent_runs_status', table_name='agent_runs')
    op.drop_index('ix_agent_runs_project_id', table_name='agent_runs')
    op.drop_index('ix_agent_runs_id', table_name='agent_runs')
    op.drop_table('agent_runs')
