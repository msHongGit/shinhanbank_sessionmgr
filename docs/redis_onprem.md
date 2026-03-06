from redis.asyncio.sentinel import Sentinel
import asyncio

async def redis_client():
    sentinel_nodes = [
        ("172.23.254.140", 5001),
        ("172.23.254.140", 5002),
        ("272.23.254.140", 5003),
    ]
    redis_username="admin"
    redis_password="thePassword"
    redis_master_name="mymaster"

    sentinel_client=Sentinel(
        sentinel_nodes,
        sentinel_kwargs={}
        decode_responses=True
    )

    client = sentinel_client.master_for(
        redis_master_name,
        db="6",
        username=redis_username,
        password=redis_password,
        encoding="utf-8",
        decode_responses=True,
        max_connections=10
    )
    try:
        await client.ping()
        print('redis client connected')
    except Exception as e:
        print("redis ping failed")
