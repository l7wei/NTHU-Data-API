from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends

from src.api import constant, schemas
from src.api.models.buses import Buses, after_specific_time, stops

router = APIRouter()
buses = Buses()


def get_current_time_state():
    current = datetime.now()
    current_time = current.time().strftime("%H:%M")
    current_day = "weekday" if current.now().weekday() < 5 else "weekend"
    return current_day, current_time


@router.get("/main", response_model=schemas.buses.BusMainData)
def get_main():
    """
    校本部公車資訊。
    """
    buses.get_all_data()
    return buses.get_main_data()


@router.get("/nanda", response_model=schemas.buses.BusNandaData)
def get_nanda():
    """
    南大校區區間車資訊。
    """
    buses.get_all_data()
    return buses.get_nanda_data()


@router.get(
    "/info/{bus_type}/{direction}",
    response_model=list[schemas.buses.BusInfo],
)
def get_bus_info(
    bus_type: Literal["main", "nanda"] = constant.buses.BUS_TYPE_PATH,
    direction: schemas.buses.BusDirection = constant.buses.BUS_DIRECTION_PATH,
):
    """
    取得公車路線資訊。
    """
    buses.get_all_data()
    return buses.info_data.loc[(bus_type, direction), "data"]


@router.get("/info/stops", response_model=list[schemas.buses.BusStopsInfo])
def get_bus_stops_info():
    """
    取得停靠站資訊
    """
    return buses.gen_bus_stops_info()


@router.get(
    "/schedules/",
    response_model=list[
        schemas.buses.BusMainSchedule | schemas.buses.BusNandaSchedule | None
    ],
)
def get_bus_schedule(
    bus_type: schemas.buses.BusType = constant.buses.BUS_TYPE_QUERY,
    day: schemas.buses.BusDayWithCurrent = constant.buses.BUS_DAY_QUERY,
    direction: schemas.buses.BusDirection = constant.buses.BUS_DIRECTION_QUERY,
):
    """
    取得公車時刻表。
    """
    buses.get_all_data()

    if day != "current":
        return buses.raw_schedule_data.loc[(bus_type, day, direction), "data"]
    else:
        current_day, current_time = get_current_time_state()

        res = after_specific_time(
            buses.raw_schedule_data.loc[(bus_type, current_day, direction), "data"],
            current_time,
            ["time"],
        )

        return res[: constant.buses.DEFAULT_LIMIT_DAY_CURRENT]


@router.get(
    "/stops/{stop_name}/",
    response_model=list[schemas.buses.BusStopsQueryResult | None],
)
def get_stop_bus(
    stop_name: schemas.buses.StopsName = constant.buses.STOPS_NAME_PATH,
    bus_type: schemas.buses.BusType = constant.buses.BUS_TYPE_QUERY,
    day: schemas.buses.BusDayWithCurrent = constant.buses.BUS_DAY_QUERY,
    direction: schemas.buses.BusDirection = constant.buses.BUS_DIRECTION_QUERY,
    query: schemas.buses.BusQuery = Depends(),
):
    """
    取得公車站牌停靠公車資訊。
    """
    buses.gen_bus_detailed_schedule_and_update_stops_data()

    return_limit = (
        query.limits
        if day != "current"
        else min(filter(None, (query.limits, constant.buses.DEFAULT_LIMIT_DAY_CURRENT)))
    )
    find_day, after_time = (
        (day, query.time) if day != "current" else get_current_time_state()
    )

    return after_specific_time(
        stops[stop_name.name].stopped_bus.loc[(bus_type, find_day, direction), "data"],
        after_time,
        ["arrive_time"],
    )[:return_limit]


@router.get(
    "/detailed/",
    response_model=list[
        schemas.buses.BusMainDetailedSchedule
        | schemas.buses.BusNandaDetailedSchedule
        | None
    ],
)
def get_bus_detailed_schedule(
    bus_type: schemas.buses.BusType = constant.buses.BUS_TYPE_QUERY,
    day: schemas.buses.BusDayWithCurrent = constant.buses.BUS_DAY_QUERY,
    direction: schemas.buses.BusDirection = constant.buses.BUS_DIRECTION_QUERY,
    query: schemas.buses.BusQuery = Depends(),
):
    """
    取得詳細公車資訊，包含抵達各站時間。
    """
    buses.gen_bus_detailed_schedule_and_update_stops_data()

    return_limit = (
        query.limits
        if day != "current"
        else min(filter(None, (query.limits, constant.buses.DEFAULT_LIMIT_DAY_CURRENT)))
    )
    find_day, after_time = (
        (day, query.time) if day != "current" else get_current_time_state()
    )

    return after_specific_time(
        buses.detailed_schedule_data.loc[(bus_type, find_day, direction), "data"],
        after_time,
        ["dep_info", "time"],
    )[:return_limit]
