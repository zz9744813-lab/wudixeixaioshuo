-- P4 完整数据库迁移
-- Phase 1-5 所有表结构

-- ============================================
-- Phase 1: Memory System
-- ============================================

-- Character Memory 角色记忆
CREATE TABLE IF NOT EXISTS character_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    aliases JSON DEFAULT '[]',
    role_type VARCHAR(50),
    stable_profile JSON DEFAULT '{}',
    dynamic_state JSON DEFAULT '{}',
    personality JSON DEFAULT '{}',
    goals JSON DEFAULT '[]',
    secrets JSON DEFAULT '[]',
    first_appearance_chapter INTEGER,
    last_seen_chapter INTEGER,
    importance_score FLOAT DEFAULT 0.5,
    summary TEXT,
    latest_update_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_char_mem_project ON character_memories(project_id);
CREATE INDEX IF NOT EXISTS idx_char_mem_name ON character_memories(project_id, name);
CREATE INDEX IF NOT EXISTS idx_char_mem_importance ON character_memories(project_id, importance_score);

-- World Memory 世界观记忆
CREATE TABLE IF NOT EXISTS world_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    category VARCHAR(50),
    name VARCHAR(200) NOT NULL,
    aliases JSON DEFAULT '[]',
    description TEXT,
    rules JSON DEFAULT '[]',
    constraints JSON DEFAULT '[]',
    related_characters JSON DEFAULT '[]',
    related_chapters JSON DEFAULT '[]',
    importance_score FLOAT DEFAULT 0.5,
    is_canon INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_world_mem_project ON world_memories(project_id);
CREATE INDEX IF NOT EXISTS idx_world_mem_category ON world_memories(project_id, category);

-- Chapter Memory 章节记忆
CREATE TABLE IF NOT EXISTS chapter_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    chapter_index INTEGER NOT NULL,
    short_summary TEXT,
    detailed_summary TEXT,
    key_events JSON DEFAULT '[]',
    character_changes JSON DEFAULT '[]',
    world_updates JSON DEFAULT '[]',
    relationship_changes JSON DEFAULT '[]',
    unresolved_questions JSON DEFAULT '[]',
    foreshadow_updates JSON DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chap_mem_project ON chapter_memories(project_id);
CREATE INDEX IF NOT EXISTS idx_chap_mem_chapter ON chapter_memories(chapter_id);
CREATE INDEX IF NOT EXISTS idx_chap_mem_index ON chapter_memories(project_id, chapter_index);

-- Relationship Memory 关系记忆
CREATE TABLE IF NOT EXISTS relationship_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    character_a VARCHAR(200),
    character_b VARCHAR(200),
    relationship_type VARCHAR(100),
    current_status TEXT,
    tension_level INTEGER DEFAULT 0,
    trust_level INTEGER DEFAULT 0,
    history JSON DEFAULT '[]',
    last_changed_chapter INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rel_mem_project ON relationship_memories(project_id);
CREATE INDEX IF NOT EXISTS idx_rel_mem_chars ON relationship_memories(project_id, character_a, character_b);

-- Memory Query Log 记忆查询日志
CREATE TABLE IF NOT EXISTS memory_query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER,
    query_type VARCHAR(50),
    query_params JSON,
    results_count INTEGER,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Phase 2: Skill Taxonomy
-- ============================================

-- 扩展 technique_cards 表
ALTER TABLE technique_cards ADD COLUMN taxonomy_level_1 VARCHAR(100);
ALTER TABLE technique_cards ADD COLUMN taxonomy_level_2 VARCHAR(100);
ALTER TABLE technique_cards ADD COLUMN scene_stage VARCHAR(100);
ALTER TABLE technique_cards ADD COLUMN suitable_chapter_range JSON DEFAULT '[]';
ALTER TABLE technique_cards ADD COLUMN source_book_type VARCHAR(100);
ALTER TABLE technique_cards ADD COLUMN difficulty INTEGER DEFAULT 3;
ALTER TABLE technique_cards ADD COLUMN risk_level INTEGER DEFAULT 1;
ALTER TABLE technique_cards ADD COLUMN effectiveness_score FLOAT DEFAULT 0.0;
ALTER TABLE technique_cards ADD COLUMN positive_review_count INTEGER DEFAULT 0;
ALTER TABLE technique_cards ADD COLUMN negative_review_count INTEGER DEFAULT 0;
ALTER TABLE technique_cards ADD COLUMN used_in_chapters JSON DEFAULT '[]';
ALTER TABLE technique_cards ADD COLUMN cluster_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_tech_taxonomy1 ON technique_cards(taxonomy_level_1);
CREATE INDEX IF NOT EXISTS idx_tech_taxonomy2 ON technique_cards(taxonomy_level_2);
CREATE INDEX IF NOT EXISTS idx_tech_effectiveness ON technique_cards(effectiveness_score);

-- Book Profile 书籍档案
CREATE TABLE IF NOT EXISTS book_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER UNIQUE NOT NULL,
    genre VARCHAR(100),
    sub_genre VARCHAR(100),
    audience VARCHAR(100),
    style_tags JSON DEFAULT '[]',
    narrative_pov VARCHAR(50),
    pacing_type VARCHAR(50),
    commercial_density INTEGER DEFAULT 5,
    adult_level INTEGER DEFAULT 0,
    strengths JSON DEFAULT '[]',
    weaknesses JSON DEFAULT '[]',
    reusable_skill_categories JSON DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Phase 3: Foreshadow System
-- ============================================

-- Foreshadow 伏笔表
CREATE TABLE IF NOT EXISTS foreshadows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title VARCHAR(300) NOT NULL,
    foreshadow_type VARCHAR(100),
    setup_chapter INTEGER,
    expected_payoff_chapter INTEGER,
    actual_payoff_chapter INTEGER,
    status VARCHAR(50) DEFAULT 'planned',
    setup_content TEXT,
    development_notes JSON DEFAULT '[]',
    payoff_plan TEXT,
    payoff_content TEXT,
    related_characters JSON DEFAULT '[]',
    related_items JSON DEFAULT '[]',
    related_world_rules JSON DEFAULT '[]',
    importance_score FLOAT DEFAULT 0.5,
    risk_score FLOAT DEFAULT 0.0,
    reader_expectation FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_foreshadow_project ON foreshadows(project_id);
CREATE INDEX IF NOT EXISTS idx_foreshadow_status ON foreshadows(project_id, status);
CREATE INDEX IF NOT EXISTS idx_foreshadow_setup ON foreshadows(project_id, setup_chapter);

-- Foreshadow Plan 章节伏笔计划
CREATE TABLE IF NOT EXISTS foreshadow_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    chapter_index INTEGER NOT NULL,
    new_foreshadows JSON DEFAULT '[]',
    develop_foreshadow_ids JSON DEFAULT '[]',
    payoff_foreshadow_ids JSON DEFAULT '[]',
    must_include_lines JSON DEFAULT '[]',
    risky_foreshadow_ids JSON DEFAULT '[]',
    is_executed INTEGER DEFAULT 0,
    execution_result JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_foreshadow_plan_project ON foreshadow_plans(project_id, chapter_index);

-- Foreshadow Review 伏笔评审
CREATE TABLE IF NOT EXISTS foreshadow_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    forgotten_foreshadows JSON DEFAULT '[]',
    premature_payoffs JSON DEFAULT '[]',
    delayed_payoffs JSON DEFAULT '[]',
    payoff_quality_issues JSON DEFAULT '[]',
    contradictions JSON DEFAULT '[]',
    foreshadow_score FLOAT DEFAULT 0.0,
    suggestions JSON DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Phase 4: Independent Review System
-- ============================================

-- Review Profile 评审配置
CREATE TABLE IF NOT EXISTS review_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    name VARCHAR(200) NOT NULL,
    is_default INTEGER DEFAULT 0,
    reviewer_roles JSON DEFAULT '[]',
    quality_threshold FLOAT DEFAULT 80.0,
    rewrite_threshold FLOAT DEFAULT 75.0,
    auto_reject_threshold FLOAT DEFAULT 60.0,
    weights JSON DEFAULT '{}',
    strictness INTEGER DEFAULT 5,
    max_review_rounds INTEGER DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_review_profile_project ON review_profiles(project_id);

-- Review Result 评审结果
CREATE TABLE IF NOT EXISTS review_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    version_id INTEGER,
    reviewer_role VARCHAR(100),
    reviewer_model VARCHAR(200),
    provider_name VARCHAR(100),
    total_score FLOAT,
    score_breakdown JSON DEFAULT '{}',
    problems JSON DEFAULT '[]',
    suggestions JSON DEFAULT '[]',
    required_fixes JSON DEFAULT '[]',
    pass_status VARCHAR(50),
    raw_output TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_review_result_chapter ON review_results(chapter_id, reviewer_role);
CREATE INDEX IF NOT EXISTS idx_review_result_task ON review_results(task_id, created_at);

-- Final Review 最终评审
CREATE TABLE IF NOT EXISTS final_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    version_id INTEGER,
    weighted_score FLOAT,
    min_score FLOAT,
    max_score FLOAT,
    review_result_ids JSON DEFAULT '[]',
    dimension_scores JSON DEFAULT '{}',
    critical_issues JSON DEFAULT '[]',
    warnings JSON DEFAULT '[]',
    final_status VARCHAR(50),
    rewrite_focus JSON DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_final_review_chapter ON final_reviews(chapter_id);

-- ============================================
-- Phase 5: Production Scheduler
-- ============================================

-- Production Policy 生产策略
CREATE TABLE IF NOT EXISTS production_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER UNIQUE NOT NULL,
    enabled INTEGER DEFAULT 0,
    target_daily_words INTEGER DEFAULT 10000,
    target_daily_chapters INTEGER DEFAULT 3,
    max_daily_cost FLOAT DEFAULT 5.0,
    max_daily_tokens INTEGER DEFAULT 500000,
    min_quality_score FLOAT DEFAULT 80.0,
    max_rewrite_rounds INTEGER DEFAULT 2,
    max_consecutive_failures INTEGER DEFAULT 3,
    auto_create_next_chapter INTEGER DEFAULT 1,
    auto_pause_on_failure INTEGER DEFAULT 1,
    auto_pause_on_budget INTEGER DEFAULT 1,
    active_hours JSON DEFAULT '[]',
    priority INTEGER DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_production_policy_enabled ON production_policies(enabled);

-- Production Log 生产日志
CREATE TABLE IF NOT EXISTS production_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    log_type VARCHAR(50),
    chapter_id INTEGER,
    task_id INTEGER,
    words_written INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    cost FLOAT DEFAULT 0.0,
    message TEXT,
    details JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_production_log_project ON production_logs(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_production_log_type ON production_logs(log_type, created_at);

-- Production Stats 生产统计
CREATE TABLE IF NOT EXISTS production_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    date VARCHAR(10) NOT NULL,
    chapters_completed INTEGER DEFAULT 0,
    words_written INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    total_cost FLOAT DEFAULT 0.0,
    avg_score FLOAT DEFAULT 0.0,
    rewrite_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    word_goal_achievement FLOAT DEFAULT 0.0,
    chapter_goal_achievement FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, date)
);

CREATE INDEX IF NOT EXISTS idx_production_stats_project ON production_stats(project_id, date);

-- ============================================
-- 扩展现有表
-- ============================================

-- 扩展 chapters 表
ALTER TABLE chapters ADD COLUMN memory_updated_at TIMESTAMP;
ALTER TABLE chapters ADD COLUMN foreshadow_updated_at TIMESTAMP;
ALTER TABLE chapters ADD COLUMN review_status VARCHAR(50);

-- 扩展 chapter_versions 表
ALTER TABLE chapter_versions ADD COLUMN review_result_id INTEGER;
ALTER TABLE chapter_versions ADD COLUMN prompt_pack_id INTEGER;
