from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware
import logging, time, uuid, subprocess, os

# Logging config
logging.basicConfig(
    #filename="/var/log/app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
# also log to file for /logs endpoint and shipping
try:
    os.makedirs("/var/log", exist_ok=True)
    _root_logger = logging.getLogger()
    if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', '') == "/var/log/app.log" for h in _root_logger.handlers):
        _fh = logging.FileHandler("/var/log/app.log")
        _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        _root_logger.addHandler(_fh)
except Exception:
    pass
logger = logging.getLogger("auth-service")

app = FastAPI(title="auth-service")
Instrumentator().instrument(app).expose(app)

# Enterprise middleware
class EnterpriseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
        request.state.trace_id = trace_id

        user_id = request.headers.get("x-user-id", "unknown")
        request.state.user_id = user_id

        start = time.time()
        response: Response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 2)

        logger.info(
            f"[trace={trace_id}] [user={user_id}] [route={request.url.path}] [duration_ms={duration_ms}]"
        )

        response.headers["x-trace-id"] = trace_id
        return response

app.add_middleware(EnterpriseMiddleware)

# Models
class LoginIn(BaseModel):
    username: str
    password: str

@app.get("/health")
async def health(request: Request):
    logger.info(f"[trace={request.state.trace_id}] [user={request.state.user_id}] health check")
    return {"status": "ok", "service": "auth"}

@app.post("/login")
async def login(request: Request, payload: LoginIn, response: Response):
    # set user id for this request (so middleware logs show it)
    request.state.user_id = payload.username
    # demo-only behavior
    if not payload.username:
        logger.warning(f"[trace={request.state.trace_id}] [user=unknown] Login failed: missing username")
        raise HTTPException(status_code=400, detail="username required")

    logger.info(f"[trace={request.state.trace_id}] [user={payload.username}] login success")
    # include x-user-id in response so client can use it in subsequent calls
    response.headers["x-user-id"] = payload.username
    response.headers["x-trace-id"] = request.state.trace_id
    return {"access_token": f"fake-token-for-{payload.username}", "token_type": "bearer"}

@app.get("/user/{username}")
async def get_user(request: Request, username: str):
    logger.info(f"[trace={request.state.trace_id}] [user={username}] fetched user")
    return {"username": username, "roles": ["user"]}

# @app.get("/logs")
# async def get_logs(lines: int = 50):
#     try:
#         result = subprocess.run(["tail", "-n", str(lines), "/var/log/app.log"],
#                                 capture_output=True, text=True, check=True)
#         return {"logs": result.stdout.splitlines()}
#     except subprocess.CalledProcessError as e:
#         return {"error": str(e)}
