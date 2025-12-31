-- Session Manager - Database Initialization Script

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    session_key_scope VARCHAR(10) NOT NULL,
    session_key_value VARCHAR(100) NOT NULL,
    session_state VARCHAR(10) NOT NULL DEFAULT 'start',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    close_reason VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_session_state CHECK (session_state IN ('start', 'talk', 'end')),
    CONSTRAINT chk_close_reason CHECK (close_reason IN ('user_exit', 'timeout', 'transfer'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_session_key ON sessions(session_key_scope, session_key_value);
CREATE INDEX IF NOT EXISTS idx_sessions_state ON sessions(session_state);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- Session Status table
CREATE TABLE IF NOT EXISTS session_status (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL REFERENCES sessions(session_id),
    conversation_id VARCHAR(50) NOT NULL,
    turn_id VARCHAR(50),
    conversation_status VARCHAR(10) NOT NULL DEFAULT 'start',
    task_queue_status VARCHAR(10) NOT NULL DEFAULT 'null',
    subagent_status VARCHAR(20) NOT NULL DEFAULT 'undefined',
    action_owner VARCHAR(50),
    reference_information JSONB,
    cushion_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_conversation_status CHECK (conversation_status IN ('start', 'talk', 'end')),
    CONSTRAINT chk_task_queue_status CHECK (task_queue_status IN ('null', 'notnull')),
    CONSTRAINT chk_subagent_status CHECK (subagent_status IN ('undefined', 'continue', 'end'))
);

CREATE INDEX IF NOT EXISTS idx_session_status_session_id ON session_status(session_id);
CREATE INDEX IF NOT EXISTS idx_session_status_conversation_id ON session_status(conversation_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_session_status_unique ON session_status(session_id, conversation_id);

-- Customer Profiles table
CREATE TABLE IF NOT EXISTS customer_profiles (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    context_id VARCHAR(50),
    attribute_key VARCHAR(100) NOT NULL,
    attribute_value TEXT,
    source_system VARCHAR(50) NOT NULL,
    computed_at TIMESTAMP WITH TIME ZONE,
    valid_from DATE,
    valid_to DATE,
    batch_period VARCHAR(10),
    permission_scope VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_profile_attribute UNIQUE (user_id, attribute_key)
);

CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON customer_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_profiles_source ON customer_profiles(source_system);
CREATE INDEX IF NOT EXISTS idx_profiles_valid ON customer_profiles(valid_from, valid_to);

-- Conversation History table
CREATE TABLE IF NOT EXISTS conversation_history (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL REFERENCES sessions(session_id),
    conversation_id VARCHAR(50) NOT NULL,
    turn_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content_masked TEXT,
    outcome VARCHAR(20),
    subagent_status VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_role CHECK (role IN ('user', 'assistant', 'system'))
);

CREATE INDEX IF NOT EXISTS idx_history_session_id ON conversation_history(session_id);
CREATE INDEX IF NOT EXISTS idx_history_conversation_id ON conversation_history(conversation_id);
CREATE INDEX IF NOT EXISTS idx_history_created_at ON conversation_history(created_at);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
