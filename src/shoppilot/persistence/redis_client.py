from redis.asyncio import Redis, from_url


def make_redis(url: str) -> Redis:
    return from_url(url, decode_responses=True)
