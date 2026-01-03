#!/usr/bin/env bash
# Quick Start Guide - Redis Integration Testing
# Location: /docs/REDIS_QUICKSTART.md

# =================================================================
# REDIS INTEGRATION - PHASE 1 QUICK START
# =================================================================

# STEP 1: Set Environment Variables
# Replace <your-access-key> with your actual Azure Redis access key
export REDIS_HOST=redis-shinhan-sol-test.koreacentral.redis.azure.net
export REDIS_PORT=10000
export REDIS_PASSWORD='40eMR6v24M6rghbwNjZeAZJxZIABPERQHAzCaFCHkJY='
export REDIS_DB=0
export REDIS_SSL=true

# STEP 2: Verify Installation
uv run python -c "import redis; print('✅ redis library installed')"

# STEP 3: Run Test
# Option A: Basic connectivity test (fastest)
uv run python scripts/test_redis_connection.py

# Option B: All tests (comprehensive)
uv run python scripts/test_redis_connection.py --full

# Option C: Test priority queue specifically
uv run python scripts/test_redis_connection.py --test-priority

# STEP 4: Verify All Operations Pass
# You should see output like:
# ✅ Connected to Redis 7.0.x
# ✅ Task pushed to queue
# ✅ Fetched 1 task(s) from queue
# ✅ Test execution complete!

# =================================================================
# EXPECTED OUTPUT (Success)
# =================================================================
# ======================================================================
# 🚀 Redis Master Agent Task Queue - Connectivity Test
# ======================================================================
# Configuration:
#   Host: redis-shinhan-sol-test.koreacentral.redis.azure.net:10000
#   DB: 0
#   SSL: true
# ======================================================================
# 
# 🔍 Testing Redis Connectivity...
# ✅ Connected to Redis 7.0.x
#    Host: redis-shinhan-sol-test.koreacentral.redis.azure.net:10000
#    DB: 0
#    SSL: true
#    Connected Clients: 1
#    Used Memory: 1.5 MB
#    Uptime (days): 45
# 
# ✅ Test execution complete!

# =================================================================
# WHAT TO DO AFTER SUCCESS
# =================================================================
# 1. Report success back to agent
# 2. Agent will proceed to Phase 2: Redis Client Wrapper
# 3. Expected timeline: ~2 weeks for full integration

# =================================================================
# TROUBLESHOOTING
# =================================================================

# If you see: "NOAUTH Authentication required"
# → Check REDIS_PASSWORD is set correctly
# → Password should be the ACCESS KEY (not the password field)
echo "DEBUG: REDIS_PASSWORD length: ${#REDIS_PASSWORD}"

# If you see: "Connection timeout"
# → Verify network connectivity:
ping redis-shinhan-sol-test.koreacentral.redis.azure.net
# → Check SSL is enabled:
# export REDIS_SSL=true

# If you see: "Connection refused"
# → Check host and port:
# Host: redis-shinhan-sol-test.koreacentral.redis.azure.net
# Port: 10000

# If redis library not found:
pip install redis
# or with uv:
uv pip install redis

# =================================================================
# DOCUMENTATION
# =================================================================
# Design Details: docs/09-redis-integration-design.md
# Full Plan: docs/09-redis-integration-plan.md
# Current Status: docs/10-redis-integration-status.md
# Test Script: scripts/test_redis_connection.py

# =================================================================
# COMMANDS REFERENCE
# =================================================================
# Test all operations:
# uv run python scripts/test_redis_connection.py --full

# Test specific operations:
uv run python scripts/test_redis_connection.py --test-put       # RPUSH
uv run python scripts/test_redis_connection.py --test-get       # LRANGE
uv run python scripts/test_redis_connection.py --test-pop       # LPOP
uv run python scripts/test_redis_connection.py --test-delete    # DEL
uv run python scripts/test_redis_connection.py --test-hash      # HSET
uv run python scripts/test_redis_connection.py --test-priority  # ZADD

# Cleanup test data:
uv run python scripts/test_redis_connection.py --cleanup

# =================================================================
