from fastapi import Request


def get_user_id(request: Request) -> str:
    user_id = request.headers.get("x-user-id", "").strip()
    if not user_id or len(user_id) > 80:
        return "anonymous"
    return user_id
