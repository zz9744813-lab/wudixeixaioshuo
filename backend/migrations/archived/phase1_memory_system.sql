-- Phase 1: 记忆系统数据库迁移
-- 创建 CharacterMemory, WorldMemory, ChapterMemory, RelationshipMemory 表

-- CharacterMemory 表
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX idx_char_memory_project ON character_memories(project_id);
CREATE INDEX idx_char_memory_project_name ON character_memories(project_id, name);
CREATE INDEX idx_char_memory_importance ON character_memories(project_id, importance_score);

-- WorldMemory 表
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX idx_world_memory_project ON world_memories(project_id);
CREATE INDEX idx_world_memory_project_cat ON world_memories(project_id, category);
CREATE INDEX idx_world_memory_project_name ON world_memories(project_id, name);

-- ChapterMemory 表
CREATE TABLE IF NOT EXISTS chapter_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    chapter_index INTEGER,
    short_summary TEXT,
    detailed_summary TEXT,
    key_events JSON DEFAULT '[]',
    character_changes JSON DEFAULT '[]',
    world_updates JSON DEFAULT '[]',
    relationship_changes JSON DEFAULT '[]',
    unresolved_questions JSON DEFAULT '[]',
    foreshadow_updates JSON DEFAULT '[]',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
);

CREATE INDEX idx_chapter_memory_project ON chapter_memories(project_id);
CREATE INDEX idx_chapter_memory_project_idx ON chapter_memories(project_id, chapter_index);
CREATE INDEX idx_chapter_memory_chapter ON chapter_memories(chapter_id);

-- RelationshipMemory 表
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX idx_rel_memory_project ON relationship_memories(project_id);
CREATE INDEX idx_rel_memory_project_chars ON relationship_memories(project_id, character_a, character_b);

-- MemoryQueryLog 表（用于优化检索策略）
CREATE TABLE IF NOT EXISTS memory_query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    chapter_id INTEGER,
    query_type VARCHAR(50),
    query_params JSON DEFAULT '{}',
    results_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
);

CREATE INDEX idx_memory_query_project ON memory_query_logs(project_id);
