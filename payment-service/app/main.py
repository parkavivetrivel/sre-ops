from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware
import logging, time, uuid, subprocess, random, os

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
logger = logging.getLogger("payment-service")

app = FastAPI(title="payment-service")
Instrumentator().instrument(app).expose(app)

class EnterpriseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
        request.state.trace_id = trace_id

        user_id = request.headers.get("x-user-id", "unknown")
        request.state.user_id = user_id

        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 2)

        logger.info(
            f"[trace={trace_id}] [user={user_id}] [route={request.url.path}] [duration_ms={duration_ms}]"
        )

        response.headers["x-trace-id"] = trace_id
        return response

app.add_middleware(EnterpriseMiddleware)

class Payment(BaseModel):
    id: str
    order_id: str
    amount: float

@app.get("/health")
async def health(request: Request):
    logger.info(f"[trace={request.state.trace_id}] [user={request.state.user_id}] payment health check")
    return {"status": "ok", "service": "payment"}

@app.post("/charge")
async def charge(request: Request, p: Payment, response: Response):
    # simulate a payment failure sometimes for testing alerts
    fail = random.random() < 0.1  # 10% simulated failure
    if fail:
        logger.error(f"[trace={request.state.trace_id}] [user={request.state.user_id}] Payment failed for order {p.order_id} amount={p.amount}")
        # still return 200 for demo, but include error in body
        response.headers["x-trace-id"] = request.state.trace_id
        return {"status": "failed", "payment_id": p.id}
    else:
        logger.info(f"[trace={request.state.trace_id}] [user={request.state.user_id}] Charged payment {p.id} for order {p.order_id} amount={p.amount}")
        response.headers["x-trace-id"] = request.state.trace_id
        return {"status": "ok", "payment_id": p.id, "charged": p.amount}

@app.get("/logs")
async def get_logs(lines: int = 50):
    try:
        result = subprocess.run(["tail", "-n", str(lines), "/var/log/app.log"],
                                capture_output=True, text=True, check=True)
        return {"logs": result.stdout.splitlines()}
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}
