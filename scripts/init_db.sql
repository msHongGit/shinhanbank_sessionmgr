-- Session Manager v3.0 - Database Initialization

-- Sessions (Global Session)
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    global_session_key VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    conversation_id VARCHAR(100),
    context_id VARCHAR(100),
    session_state VARCHAR(10) NOT NULL DEFAULT 'start',
    close_reason VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT chk_session_state CHECK (session_state IN ('start', 'talk', 'end'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_state ON sessions(session_state);

-- Session Mappings (Global↔Local)
CREATE TABLE IF NOT EXISTS session_mappings (
    id SERIAL PRIMARY KEY,
    global_session_key VARCHAR(100) NOT NULL,
    local_session_key VARCHAR(100) NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    agent_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT uq_mapping UNIQUE (global_session_key, agent_id)
);

CREATE INDEX IF NOT EXISTS idx_mappings_global ON session_mappings(global_session_key);

-- Context (대화 이력 메타)
CREATE TABLE IF NOT EXISTS contexts (
    id SERIAL PRIMARY KEY,
    context_id VARCHAR(100) UNIQUE NOT NULL,
    global_session_key VARCHAR(100) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contexts_session ON contexts(global_session_key);
CREATE INDEX IF NOT EXISTS idx_contexts_user ON contexts(user_id);

-- Conversation Turns (대화 턴)
CREATE TABLE IF NOT EXISTS conversation_turns (
    id SERIAL PRIMARY KEY,
    context_id VARCHAR(100) NOT NULL,
    turn_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_role CHECK (role IN ('user', 'assistant', 'system'))
);

CREATE INDEX IF NOT EXISTS idx_turns_context ON conversation_turns(context_id);

-- Customer Profiles
CREATE TABLE IF NOT EXISTS customer_profiles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    attribute_key VARCHAR(100) NOT NULL,
    attribute_value TEXT,
    source_system VARCHAR(50) NOT NULL,
    segment VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_profile_attr UNIQUE (user_id, attribute_key)
);

CREATE INDEX IF NOT EXISTS idx_profiles_user ON customer_profiles(user_id);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
