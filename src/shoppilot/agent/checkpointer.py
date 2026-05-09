from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from redis.asyncio import Redis, from_url


async def make_checkpointer(redis_url: str) -> tuple[BaseCheckpointSaver, Redis]:
    """构造 AsyncRedisSaver 并完成首次索引建立。

    注：langgraph-checkpoint-redis 0.0.x 的 from_conn_string 在某些环境下创建的
    内部 client 会立刻断开（连 PING 都失败），所以这里改为外部创建 redis client
    再注入。返回 (saver, client) 让调用方在 shutdown 时一起关闭。

    Redis 必须启用 RediSearch + RedisJSON 模块（即 redis-stack 镜像）。
    """
    client = from_url(redis_url)
    saver = AsyncRedisSaver(redis_client=client)
    await saver.asetup()
    return saver, client
