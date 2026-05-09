from fastapi import Request


def get_graph(request: Request):
    return request.app.state.graph


def get_checkpointer(request: Request):
    return request.app.state.checkpointer


def get_redis(request: Request):
    return request.app.state.redis
