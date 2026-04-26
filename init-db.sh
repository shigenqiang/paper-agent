#!/bin/bash
# PostgreSQL数据库初始化脚本

set -e

# 创建扩展
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 启用向量扩展（用于语义搜索）
    CREATE EXTENSION IF NOT EXISTS vector;

    -- 启用UUID扩展
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- 创建自定义类型
    DO $$ BEGIN
        CREATE TYPE agent_state AS ENUM ('idle', 'running', 'error', 'disabled');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;

    -- 创建主表
    CREATE TABLE IF NOT EXISTS agents (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(255) NOT NULL UNIQUE,
        type VARCHAR(100) NOT NULL,
        state agent_state DEFAULT 'idle',
        config JSONB DEFAULT '{}',
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- 创建记忆表
    CREATE TABLE IF NOT EXISTS memories (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
        memory_type VARCHAR(100) NOT NULL,
        content TEXT NOT NULL,
        embedding VECTOR(1536),
        metadata JSONB DEFAULT '{}',
        importance_score FLOAT DEFAULT 0.5,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- 创建索引
    CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id);
    CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
    CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance_score DESC);

    -- 向量相似度索引
    CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING ivfflat(embedding vector_cosine_ops);

    -- 创建会话表
    CREATE TABLE IF NOT EXISTS sessions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
        user_id VARCHAR(255),
        context JSONB DEFAULT '{}',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        ended_at TIMESTAMP WITH TIME ZONE
    );

    -- 创建执行历史表
    CREATE TABLE IF NOT EXISTS execution_history (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
        session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
        action VARCHAR(255) NOT NULL,
        input_data JSONB,
        output_data JSONB,
        execution_time_ms INTEGER,
        status VARCHAR(50) DEFAULT 'success',
        error_message TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- 创建执行历史索引
    CREATE INDEX IF NOT EXISTS idx_execution_agent ON execution_history(agent_id);
    CREATE INDEX IF NOT EXISTS idx_execution_session ON execution_history(session_id);
    CREATE INDEX IF NOT EXISTS idx_execution_created ON execution_history(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_execution_status ON execution_history(status);

    -- 创建函数：自动更新updated_at
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    -- 创建触发器
    DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;
    CREATE TRIGGER update_agents_updated_at
        BEFORE UPDATE ON agents
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();

EOSQL

echo "Database initialization completed successfully"