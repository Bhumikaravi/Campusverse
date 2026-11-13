import time
from collections import defaultdict
from fastapi import Request, HTTPException, status
from app.config import settings

class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Filter out requests older than window
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > cutoff]
        
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
            
        self.requests[client_ip].append(now)
        return True

# 60 requests per 5 minutes for auth attempts
auth_limiter = InMemoryRateLimiter(max_requests=60, window_seconds=5 * 60)

# 40 uploads per hour per IP
upload_limiter = InMemoryRateLimiter(max_requests=40, window_seconds=60 * 60)

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

async def check_auth_rate_limit(request: Request):
    ip = get_client_ip(request)
    if not auth_limiter.is_allowed(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts from your device. Please wait a few moments and try again."
        )

async def check_upload_rate_limit(request: Request):
    ip = get_client_ip(request)
    if not upload_limiter.is_allowed(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Upload limit reached. Please wait before uploading more materials."
        )
