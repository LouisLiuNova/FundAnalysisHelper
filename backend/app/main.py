from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import analysis, fund
from app.api.deps import get_config, get_analysis_service
from app.graph.workflow import set_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    set_config(config)
    get_analysis_service()  # pre-init
    yield


app = FastAPI(
    title="FundAnalysisHelper",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router)
app.include_router(fund.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
