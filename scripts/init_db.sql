-- ============================================================================
-- Session Manager v4.0 - MariaDB Schema
-- Sprint 3: Context DB 초기화 스크립트
-- ============================================================================

-- 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS session_manager
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE session_manager;

-- ============================================================================
-- 1. sessions 테이블
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    global_session_key VARCHAR(255) NOT NULL UNIQUE,
    conversation_id VARCHAR(255) NOT NULL,
    context_id VARCHAR(255) NOT NULL,
    channel VARCHAR(50),
    user_id VARCHAR(255),
    session_state VARCHAR(20) NOT NULL DEFAULT 'start',
    task_queue_status VARCHAR(20) DEFAULT 'null',
    subagent_status VARCHAR(20) DEFAULT 'undefined',
    current_subagent_id VARCHAR(255),
    metadata JSON,
    profile JSON COMMENT 'User profile attributes at session creation',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    last_updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    expires_at DATETIME(6),
    INDEX idx_global_session_key (global_session_key),
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 2. agent_sessions 테이블 (구 local_sessions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    global_session_key VARCHAR(255) NOT NULL,
    agent_session_key VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    last_used_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    expires_at DATETIME(6),
    UNIQUE KEY unique_mapping (global_session_key, agent_id),
    INDEX idx_global_session_key (global_session_key),
    INDEX idx_agent_session_key (agent_session_key),
    INDEX idx_agent_id (agent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 3. contexts 테이블
-- ============================================================================
CREATE TABLE IF NOT EXISTS contexts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    context_id VARCHAR(255) NOT NULL UNIQUE,
    global_session_key VARCHAR(255) NOT NULL,
    current_intent VARCHAR(255),
    current_slots JSON,
    entities JSON,
    turn_count INT NOT NULL DEFAULT 0,
    metadata JSON,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    last_updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_context_id (context_id),
    INDEX idx_global_session_key (global_session_key),
    FOREIGN KEY (global_session_key) REFERENCES sessions(global_session_key) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 4. conversation_turns 테이블
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversation_turns (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    turn_id VARCHAR(255) NOT NULL UNIQUE,
    context_id VARCHAR(255) NOT NULL,
    global_session_key VARCHAR(255) NOT NULL,
    turn_number INT NOT NULL,
    role VARCHAR(20) NOT NULL,
    agent_id VARCHAR(255),
    agent_type VARCHAR(50),
    metadata JSON COMMENT 'intent, confidence, slots, API 호출 결과 등',
    timestamp DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_turn_id (turn_id),
    INDEX idx_context_id (context_id),
    INDEX idx_global_session_key (global_session_key),
    INDEX idx_timestamp (timestamp),
    FOREIGN KEY (context_id) REFERENCES contexts(context_id) ON DELETE CASCADE,
    FOREIGN KEY (global_session_key) REFERENCES sessions(global_session_key) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 5. profile_attributes 테이블
-- ============================================================================
CREATE TABLE IF NOT EXISTS profile_attributes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    attribute_id VARCHAR(100) NOT NULL UNIQUE,
    user_id VARCHAR(100) NOT NULL,
    context_id VARCHAR(100) NOT NULL,
    attribute_key VARCHAR(100) NOT NULL,
    attribute_value TEXT,
    source_system VARCHAR(100),
    computed_at DATETIME(6) NOT NULL,
    valid_from DATE NOT NULL,
    valid_to DATE,
    batch_period VARCHAR(1) NOT NULL COMMENT 'D=Daily, W=Weekly, M=Monthly, A=Ad-hoc',
    permission_scope JSON COMMENT 'Agent access control',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_attribute_id (attribute_id),
    INDEX idx_user_context (user_id, context_id),
    INDEX idx_user_key (user_id, attribute_key),
    INDEX idx_valid_dates (valid_from, valid_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 인덱스 최적화
-- ============================================================================

-- 복합 인덱스 추가
CREATE INDEX idx_sessions_state_updated ON sessions(session_state, last_updated_at);
CREATE INDEX idx_agent_sessions_active ON agent_sessions(is_active, last_used_at);
CREATE INDEX idx_turns_context_number ON conversation_turns(context_id, turn_number);

-- ============================================================================
-- 완료
-- ============================================================================
SELECT 'Session Manager v4.0 Schema Created Successfully' AS message;
