import datetime
import json
import re
from typing import Literal

from cachetools import TTLCache, cached

from src.utils import cached_request


def after_specific_time(
    target_list,
    time,
    time_route: list = None,
) -> list:
    hour, minute = time.split(":")

    res = []

    for bus in target_list:
        if len(time_route) == 1:
            bus_hour, bus_minute = bus[time_route[0]].split(":")
        elif len(time_route) == 2:
            bus_hour, bus_minute = bus[time_route[0]][time_route[1]].split(":")

        if int(bus_hour) > int(hour):
            res.append(bus)
        elif int(bus_hour) == int(hour) and int(bus_minute) >= int(minute):
            res.append(bus)

    return res


def gen_all_field(target_list) -> None:
    # 生成 main 和 nanda all 欄位
    for scope in ["main", "nanda"]:
        for direction in ["up", "down"]:
            target_list[scope][direction]["all"] = (
                target_list[scope][direction]["weekday"]
                + target_list[scope][direction]["weekend"]
            )

    # 生成 all 的 weekday 和 weekend 欄位
    for direction in ["up", "down"]:
        for day in ["weekday", "weekend"]:
            target_list["all"][direction][day] = (
                target_list["main"][direction][day]
                + target_list["nanda"][direction][day]
            )

    # 生成 all 的 all 欄位
    for direction in ["up", "down"]:
        target_list["all"][direction]["all"] = (
            target_list["all"][direction]["weekday"]
            + target_list["all"][direction]["weekend"]
        )


class Stop:
    def __init__(self, name, name_en) -> None:
        self.name = name
        self.name_en = name_en
        self.stoped_bus = {
            "main": {
                "up": {"weekday": [], "weekend": [], "all": []},
                "down": {"weekday": [], "weekend": [], "all": []},
            },
            "nanda": {
                "up": {"weekday": [], "weekend": [], "all": []},
                "down": {"weekday": [], "weekend": [], "all": []},
            },
            "all": {
                "up": {"weekday": [], "weekend": [], "all": []},
                "down": {"weekday": [], "weekend": [], "all": []},
            },
        }

    def gen_whole_bus_list(self) -> None:
        gen_all_field(self.stoped_bus)
        self._sort_bus()

    def _sort_bus(self) -> None:
        for scope in ["main", "nanda", "all"]:
            for direction in ["up", "down"]:
                for day in ["weekday", "weekend", "all"]:
                    self.stoped_bus[scope][direction][day].sort(
                        key=lambda x: datetime.datetime.strptime(
                            x["arrive_time"], "%H:%M"
                        )
                    )


M1 = Stop("北校門口", "North Main Gate")
M2 = Stop("綜二館", "General Building II")
M3 = Stop("楓林小徑", "Maple Path")
M4 = Stop("人社院/生科館", "CHSS/CLS Building")
M5 = Stop("台積館", "TSMC Building")
M6 = Stop("奕園停車場", "Yi Pavilion Parking Lot")
M7 = Stop("南門停車場", "South Gate Parking Lot")
S1 = Stop("南大校區校門口右側(食品路校牆邊)", "The right side of NandaCampus front gate(Shipin Road)")
stops = {"M1": M1, "M2": M2, "M3": M3, "M4": M4, "M5": M5, "M6": M6, "M7": M7, "S1": S1}

# 清大路網圖 (單位：分鐘)
#                        M4
#     1      1     2/         \2    15
# M1 --- M2 --- M3              M5 ---- S1
#                 1\          /1
#                   M6 --- M7
#                       2


class Route:
    def __init__(self, *arg) -> None:
        self.route: list[Stop] = list(arg)
        self._delta_time_table = {
            M1: {M2: 1},
            M2: {M1: 1, M3: 1, M4: 3},
            M3: {M2: 1, M4: 2, M6: 1},
            M4: {M2: 3, M3: 2, M5: 2},
            M5: {M4: 2, M7: 1, S1: 15},
            M6: {M3: 1, M7: 2},
            M7: {M5: 1, M6: 2},
            S1: {M5: 15},
        }

    def gen_accu_time(self) -> list:
        res = [0]
        for i in range(0, len(self.route) - 1):
            res.append(
                res[i] + self._delta_time_table[self.route[i]][self.route[i + 1]]
            )
        return res


red_M1_M5 = Route(M1, M2, M3, M4, M5)  # 紅線 北校門 往 台積館
red_M5_M1 = Route(M5, M7, M6, M3, M2, M1)  # 紅線 台積館 往 北校門
red_M2_M5 = Route(M2, M3, M4, M5)  # 紅線 綜二館 往 台積館
red_M5_M2 = Route(M5, M7, M6, M3, M2)  # 紅線 台積館 往 綜二館

green_M1_M5 = Route(M1, M2, M3, M6, M7, M5)  # 綠線 北校門 往 台積館
green_M5_M1 = Route(M5, M4, M3, M2, M1)  # 綠線 台積館 往 北校門
green_M2_M5 = Route(M2, M3, M6, M7, M5)  # 綠線 綜二館 往 台積館
green_M5_M2 = Route(M5, M4, M3, M2)  # 綠線 台積館 往 綜二館

nanda_M1_S1 = Route(M1, M2, M4, M5, S1)  # 校區區間車 南大校區校門口右側(食品路校牆邊) 往 北校門
nanda_S1_M1 = Route(S1, M5, M4, M2, M1)  # 校區區間車 北校門 往 南大校區校門口右側(食品路校牆邊)


class Buses:
    # 校本部公車
    # https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw
    # 南大區間車
    # https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw
    def __init__(self) -> None:
        self._res_text = ""
        self._start_from_gen_2_bus_info = []
        self.detailed_data = {}

    def _parse_campus_info(self, variable_string: str):
        regex_pattern = r"const " + variable_string + " = (\{.*?\})"
        data = re.search(regex_pattern, self._res_text, re.S)
        if data is not None:
            data = data.group(1)
        else:
            return None
        data = data.replace("'", "|")
        data = data.replace('"', '\\"')
        data = data.replace("|", '"')
        data = data.replace("\n", "")
        data = data.replace("direction", '"direction"')
        data = data.replace("duration", '"duration"')
        data = data.replace("route", '"route"', 1)
        data = data.replace("routeEN", '"routeEN"')
        data = json.loads(data)
        return data

    def _parse_bus_schedule(self, variable_string: str):
        regex_pattern = r"const " + variable_string + " = (\[.*?\])"
        data = re.search(regex_pattern, self._res_text, re.S)
        if data is not None:
            data = data.group(1)
        else:
            return None
        data = data.replace("'", '"')
        data = data.replace("\n", "")
        data = data.replace("time", '"time"')
        data = data.replace("description", '"description"')
        data = data.replace("depStop", '"depStop"')
        data = data.replace("line", '"line"')
        data = data.replace(",    ]", "]")
        data = data.replace(",  ]", "]")
        data = json.loads(data)

        try:
            data[0]["line"]
            for i in data:
                i["route"] = "校園公車"
        except KeyError:
            for i in data:
                i["route"] = "南大區間車"

        return data

    def get_main_data(self) -> dict:
        url = "https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw"
        self._res_text = cached_request.get(url)

        # 往台積館資訊
        self.toward_tsmc_building_info = self._parse_campus_info(
            "towardTSMCBuildingInfo"
        )

        # 往台積館時刻表(平日)
        self.weekday_bus_schedule_toward_tsmc_building = self._parse_bus_schedule(
            "weekdayBusScheduleTowardTSMCBuilding"
        )

        # 往台積館時刻表(假日)
        self.weekend_bus_schedule_toward_tsmc_building = self._parse_bus_schedule(
            "weekendBusScheduleTowardTSMCBuilding"
        )

        # 往校門口資訊
        self.toward_main_gate_info = self._parse_campus_info("towardMainGateInfo")

        # 往校門口時刻表(平日)
        self.weekday_bus_schedule_toward_main_gate = self._parse_bus_schedule(
            "weekdayBusScheduleTowardMainGate"
        )

        # 往校門口時刻表(假日)
        self.weekend_bus_schedule_toward_main_gate = self._parse_bus_schedule(
            "weekendBusScheduleTowardMainGate"
        )

        # 輸出 json 檔案
        main_dataset = {
            "toward_TSMC_building_info": self.toward_tsmc_building_info,
            "weekday_bus_schedule_toward_TSMC_building": self.weekday_bus_schedule_toward_tsmc_building,
            "weekend_bus_schedule_toward_TSMC_building": self.weekend_bus_schedule_toward_tsmc_building,
            "toward_main_gate_info": self.toward_main_gate_info,
            "weekday_bus_schedule_toward_main_gate": self.weekday_bus_schedule_toward_main_gate,
            "weekend_bus_schedule_toward_main_gate": self.weekend_bus_schedule_toward_main_gate,
        }

        return main_dataset

    def get_nanda_data(self) -> dict:
        url = "https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw"
        self._res_text = cached_request.get(url)

        # 往南大校區資訊
        self.toward_south_campus_info = self._parse_campus_info("towardSouthCampusInfo")

        # 往南大校區時刻表(平日)
        self.weekday_bus_schedule_toward_south_campus = self._parse_bus_schedule(
            "weekdayBusScheduleTowardSouthCampus"
        )

        # 往南大校區時刻表(假日)
        self.weekend_bus_schedule_toward_south_campus = self._parse_bus_schedule(
            "weekendBusScheduleTowardSouthCampus"
        )

        # 往校本部資訊
        self.toward_main_campus_info = self._parse_campus_info("towardMainCampusInfo")

        # 往校本部時刻表(平日)
        self.weekday_bus_schedule_toward_main_campus = self._parse_bus_schedule(
            "weekdayBusScheduleTowardMainCampus"
        )

        # 往校本部時刻表(假日)
        self.weekend_bus_schedule_toward_main_campus = self._parse_bus_schedule(
            "weekendBusScheduleTowardMainCampus"
        )

        # 輸出 json 檔案
        nanda_dataset = {
            "toward_south_campus_info": self.toward_south_campus_info,
            "weekday_bus_schedule_toward_south_campus": self.weekday_bus_schedule_toward_south_campus,
            "weekend_bus_schedule_toward_south_campus": self.weekend_bus_schedule_toward_south_campus,
            "toward_main_campus_info": self.toward_main_campus_info,
            "weekday_bus_schedule_toward_main_campus": self.weekday_bus_schedule_toward_main_campus,
            "weekend_bus_schedule_toward_main_campus": self.weekend_bus_schedule_toward_main_campus,
        }

        return nanda_dataset

    # 更新資料，並清除 _start_from_gen_2_bus_info
    def _update_data(self):
        self.get_main_data()
        self.get_nanda_data()
        self._start_from_gen_2_bus_info = []

    def _add_on_time(self, start_time: str, time_delta: int) -> str:
        st = datetime.datetime.strptime(start_time, "%H:%M")
        st = st + datetime.timedelta(minutes=time_delta)
        return str(st.strftime("%H:%M"))

    # 用字串尋找對應的 Stop 物件
    def _find_stop_from_str(self, stop_str: str) -> Stop:
        for stop in stops.values():
            if stop.name == stop_str:
                return stop
        return None

    def _route_selector(
        self, dep_stop: str, line: str, from_gen_2: bool = False
    ) -> Route:
        # 這裡不用 match 的原因是因為資料中有些會多空格
        # 下山
        if dep_stop.count("台積") > 0:
            if line.count("red") > 0 and from_gen_2:
                return red_M5_M2
            elif line.count("red") > 0 and not from_gen_2:
                return red_M5_M1
            elif line.count("green") > 0 and from_gen_2:
                return green_M5_M2
            elif line.count("green") > 0 and not from_gen_2:
                return green_M5_M1
            else:
                print(dep_stop, line)
        # 上山
        else:
            if dep_stop.count("校門") > 0 and line.count("red") > 0:
                return red_M1_M5
            elif dep_stop.count("綜二") > 0 and line.count("red") > 0:
                return red_M2_M5
            elif dep_stop.count("校門") > 0 and line.count("green") > 0:
                return green_M1_M5
            elif dep_stop.count("綜二") > 0 and line.count("green") > 0:
                return green_M2_M5
            else:
                print(dep_stop, line)

    def _gen_detailed_bus_schedule(
        self,
        bus_schedule: list,
        *,
        scope: Literal["main", "nanda"] = "main",
        direction: Literal["up", "down"] = "up",
        day: Literal["weekday", "weekend"] = "weekday",
    ) -> list:
        res = []
        for bus in bus_schedule:
            temp_bus = {"dep_info": bus, "stops_time": []}

            this_route = None
            # 校本部公車
            if scope == "main":
                # 判斷路線
                dep_stop = bus["depStop"]
                line = bus["line"]

                # 判斷是否上山時從綜二館出發，將影響下山的終點站
                # 有 0 的情況是因為資料中有些時間是 8:00 這種格式
                if (
                    self._start_from_gen_2_bus_info.count(bus["time"] + line) > 0
                    or self._start_from_gen_2_bus_info.count("0" + bus["time"] + line)
                    > 0
                ):
                    this_route = self._route_selector(dep_stop, line, True)
                else:
                    this_route = self._route_selector(dep_stop, line)

                # 如果從綜二出發，紀錄該班資訊
                if dep_stop.count("綜二") > 0:
                    self._start_from_gen_2_bus_info.append(
                        str(self._add_on_time(bus["time"], 7) + line)
                    )
            # 南大區間車
            elif scope == "nanda":
                # 判斷路線
                if direction == "up":
                    this_route = nanda_S1_M1
                elif direction == "down":
                    this_route = nanda_M1_S1

            for index, stop in enumerate(this_route.route):
                arrive_time = self._add_on_time(
                    bus["time"],
                    this_route.gen_accu_time()[index],
                )

                # 處理各站牌資訊
                self._find_stop_from_str(stop.name).stoped_bus[scope][direction][
                    day
                ].append({"bus_info": bus, "arrive_time": arrive_time})

                temp_bus["stops_time"].append(
                    {"stop_name": stop.name, "time": arrive_time}
                )

            res.append(temp_bus)

        return res

    def _sort_bus(self) -> None:
        for scope in ["main", "nanda", "all"]:
            for direction in ["up", "down"]:
                for day in ["weekday", "weekend", "all"]:
                    self.detailed_data[scope][direction][day].sort(
                        key=lambda x: datetime.datetime.strptime(
                            x["dep_info"]["time"], "%H:%M"
                        )
                    )

    @cached(TTLCache(maxsize=1024, ttl=60 * 60))
    def get_bus_detailed_schedule_and_update_stops_data(self) -> dict:
        self.detailed_data = {
            "main": {
                "up": {"weekday": [], "weekend": [], "all": []},
                "down": {"weekday": [], "weekend": [], "all": []},
            },
            "nanda": {
                "up": {"weekday": [], "weekend": [], "all": []},
                "down": {"weekday": [], "weekend": [], "all": []},
            },
            "all": {
                "up": {"weekday": [], "weekend": [], "all": []},
                "down": {"weekday": [], "weekend": [], "all": []},
            },
        }

        #########################################
        # 校門口往返台積館公車時刻表（平日）
        #########################################
        self._update_data()
        self.detailed_data["main"]["up"]["weekday"] = self._gen_detailed_bus_schedule(
            self.weekday_bus_schedule_toward_tsmc_building,
            scope="main",
            direction="up",
            day="weekday",
        )
        self.detailed_data["main"]["down"]["weekday"] = self._gen_detailed_bus_schedule(
            self.weekday_bus_schedule_toward_main_gate,
            scope="main",
            direction="down",
            day="weekday",
        )
        #########################################

        #########################################
        # 校門口往返台積館公車時刻表（假日）
        #########################################
        self._update_data()
        self.detailed_data["main"]["up"]["weekend"] = self._gen_detailed_bus_schedule(
            self.weekend_bus_schedule_toward_tsmc_building,
            scope="main",
            direction="up",
            day="weekend",
        )
        self.detailed_data["main"]["down"]["weekend"] = self._gen_detailed_bus_schedule(
            self.weekend_bus_schedule_toward_main_gate,
            scope="main",
            direction="down",
            day="weekend",
        )
        #########################################

        #########################################
        # 校門口往返南大校區區間車時刻表（平日）
        #########################################
        # 區間車不用 update 是因為不會有從綜二出發的情況
        self.detailed_data["nanda"]["up"]["weekday"] = self._gen_detailed_bus_schedule(
            self.weekday_bus_schedule_toward_south_campus,
            scope="nanda",
            direction="up",
            day="weekday",
        )
        self.detailed_data["nanda"]["down"][
            "weekday"
        ] = self._gen_detailed_bus_schedule(
            self.weekday_bus_schedule_toward_main_campus,
            scope="nanda",
            direction="down",
            day="weekday",
        )
        #########################################

        #########################################
        # 校門口往返南大校區區間車時刻表（假日）
        #########################################
        # 區間車不用 update 是因為不會有從綜二出發的情況
        self.detailed_data["nanda"]["up"]["weekend"] = self._gen_detailed_bus_schedule(
            self.weekend_bus_schedule_toward_south_campus,
            scope="nanda",
            direction="up",
            day="weekend",
        )
        self.detailed_data["nanda"]["down"][
            "weekend"
        ] = self._gen_detailed_bus_schedule(
            self.weekend_bus_schedule_toward_main_campus,
            scope="nanda",
            direction="down",
            day="weekend",
        )
        #########################################

        for stop in stops.values():
            stop.gen_whole_bus_list()

        gen_all_field(self.detailed_data)
        self._sort_bus()

        return self.detailed_data
