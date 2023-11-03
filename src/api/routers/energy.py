from fastapi import APIRouter, HTTPException
from ..models.energy import Energy

router = APIRouter(
    prefix="/energy",
    tags=["energy"],
    responses={404: {"description": "Not found"}},
)

energy = Energy()


@router.get(
    "/electricity_usage",
    responses={
        200: {
            "description": "校園電力即時使用量",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "name": "北區一號",
                            "data": 2027,
                            "capacity": 5200,
                            "unit": "kW",
                            "last_updated": "2023-11-03 03:06:12",
                        },
                        {
                            "name": "北區二號",
                            "data": -999,
                            "capacity": 5600,
                            "unit": "kW",
                            "last_updated": "2023-11-03 03:06:12",
                        },
                        {
                            "name": "仙宮",
                            "data": 683,
                            "capacity": 1500,
                            "unit": "kW",
                            "last_updated": "2023-11-03 03:06:12",
                        },
                    ]
                },
            },
        },
    },
)
async def get_realtime_electricity_usage():
    try:
        return energy.get_realtime_electricity_usage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))