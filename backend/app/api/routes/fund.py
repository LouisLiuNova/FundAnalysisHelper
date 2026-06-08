from fastapi import APIRouter, Query
from app.graph.workflow import get_datasource

router = APIRouter(prefix="/api/v1/funds", tags=["基金"])


@router.get("/search")
async def search_funds(q: str = Query(..., min_length=1)):
    ds = get_datasource()
    try:
        info = await ds.get_fund_basic(q)
        return [{
            "code": info.code,
            "name": info.name,
            "fund_type": info.fund_type,
            "establish_date": info.establish_date,
        }]
    except Exception:
        return []
