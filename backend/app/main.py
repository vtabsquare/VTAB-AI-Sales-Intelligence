from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.db import Base, engine

from app.models import entities as _entities  # noqa: F401
from app.models import sales_followup as _sales_followup  # noqa: F401
from app.models import platform as _platform  # noqa: F401
from app.models import intelligence as _intelligence  # noqa: F401
from app.models import sales_agent as _sales_agent  # noqa: F401

from app.api.sales_manager_routes import r as sales_manager_router
from app.api.intelligence_routes import r as intelligence_router
from app.api.routes import r as core_router
from app.api.sales_intelligence_routes import r as sales_intelligence_router
from app.api.integration_routes import r as integration_router
from app.api.platform_routes import r as platform_router
from app.api.auth_routes import r as auth_router
from app.api.outreach_guardrails_routes import r as outreach_guardrails_router
from app.api.policy_guardrails_routes import r as policy_guardrails_router

app = FastAPI(
    title="VTAB Global Opportunity Agent",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def require_auth(request, call_next):
    from fastapi.responses import JSONResponse
    from app.api.auth_routes import verify_token
    path=request.url.path
    public={"/api/health","/api/auth/login","/api/auth/verify","/docs","/openapi.json","/redoc"}
    if path.startswith("/api/") and path not in public:
        if request.method == "OPTIONS":
            return await call_next(request)
        auth=request.headers.get("authorization","")
        token=auth[7:] if auth.lower().startswith("bearer ") else ""
        if not verify_token(token):
            return JSONResponse({"detail":"Authentication required."},status_code=401)
    return await call_next(request)


@app.on_event("startup")
def startup() -> None:
    from app.core.config import settings
    if settings.initialize_schema:
        Base.metadata.create_all(bind=engine)
        from app.services.schema_compat import ensure_platform_schema
        ensure_platform_schema()

    # Governance baseline: never permit automatic initial outreach or automatic replies.
    # The agent may discover, qualify, research and draft automatically; delivery stays human-controlled.
    try:
        from app.models.db import SessionLocal
        from app.services.sales_manager import policy_for
        db = SessionLocal()
        try:
            policy = policy_for(db)
            changed = False
            if policy.auto_initial_outreach:
                policy.auto_initial_outreach = False
                changed = True
            if policy.auto_acknowledge:
                policy.auto_acknowledge = False
                changed = True
            if changed:
                db.commit()
        finally:
            db.close()
    except Exception:
        pass

    if not settings.scheduler_enabled:
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.services.workflow_scheduler import scheduler_tick
    global _scheduler
    _scheduler=BackgroundScheduler(daemon=True)
    _scheduler.add_job(scheduler_tick, "interval", minutes=1, id="workflow_tick", replace_existing=True)
    _scheduler.start()


app.include_router(intelligence_router)
app.include_router(auth_router)
app.include_router(core_router)
app.include_router(outreach_guardrails_router)
app.include_router(policy_guardrails_router)
app.include_router(sales_intelligence_router)
app.include_router(integration_router)
app.include_router(platform_router)
app.include_router(sales_manager_router)


@app.on_event("shutdown")
def shutdown() -> None:
    scheduler = globals().get('_scheduler')
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)


@app.exception_handler(Exception)
async def internal_error(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": "The operation failed on the server. Check database schema/connectivity and provider configuration."},
    )
