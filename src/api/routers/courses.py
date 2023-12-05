from fastapi import APIRouter, Body, HTTPException, Path, Query, Response

from src.api import schemas
from src.api.models.courses import Conditions, Processor

router = APIRouter()
courses = Processor(json_path="data/courses/11210.json")
DESCRIPTION_OF_LIMITS = "最大回傳資料筆數"


@router.get("/", response_model=list[schemas.courses.CourseData])
async def get_all_courses_list(
    response: Response,
    limits: int = Query(None, ge=1, example=5, description=DESCRIPTION_OF_LIMITS),
):
    """
    取得所有課程。
    """
    result = courses.course_data[:limits]
    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.get("/fields/info", response_model=dict[str, str])
async def get_all_fields_list_info():
    """
    取得所有欄位的資訊。
    """
    return {
        "id": "科號",
        "chinese_title": "課程中文名稱",
        "english_title": "課程英文名稱",
        "credit": "學分數",
        "size_limit": "人限：若為空字串表示無人數限制",
        "freshman_reservation": "新生保留人數：若為0表示無新生保留人數",
        "object": "通識對象：[代碼說明(課務組)](https://curricul.site.nthu.edu.tw/p/404-1208-11133.php)",
        "ge_type": "通識類別",
        "language": '授課語言："中"、"英"',
        "note": "備註",
        "suspend": '停開註記："停開"或空字串',
        "class_room_and_time": "教室與上課時間：一間教室對應一個上課時間，中間以tab分隔；多個上課教室以new line字元分開",
        "teacher": "授課教師：多位教師授課以new line字元分開；教師中英文姓名以tab分開",
        "prerequisite": "擋修說明：會有html entities",
        "limit_note": "課程限制說明",
        "expertise": "第一二專長對應：對應多個專長用tab字元分隔",
        "program": "學分學程對應：用半形/分隔",
        "no_extra_selection": "不可加簽說明",
        "required_optional_note": "必選修說明：多個必選修班級用tab字元分隔",
    }


@router.get("/fields/{field_name}", response_model=list[str])
async def get_selected_fields_list(
    field_name: schemas.courses.CourseFieldName = Path(
        ..., example="id", description="欄位名稱"
    ),
    limits: int = Query(None, ge=1, example=20, description=DESCRIPTION_OF_LIMITS),
):
    """
    取得指定欄位的列表。
    """
    result = courses.list_selected_fields(field_name)[:limits]
    return result


@router.get(
    "/fields/{field_name}/{value}", response_model=list[schemas.courses.CourseData]
)
async def get_selected_field_and_value_data(
    field_name: schemas.courses.CourseFieldName = Path(
        ..., example="chinese_title", description="搜尋的欄位名稱"
    ),
    value: str = Path(..., example="產業創新與生涯探索", description="搜尋的值"),
    limits: int = Query(None, ge=1, example=5, description=DESCRIPTION_OF_LIMITS),
):
    """
    取得指定欄位滿足搜尋值的課程列表。
    """
    condition = Conditions(field_name, value, False)
    result = courses.query(condition)[:limits]
    return result


@router.get("/lists/16weeks", response_model=list[schemas.courses.CourseData])
async def get_16weeks_courses_list(
    response: Response,
    limits: int = Query(None, ge=1, example=5, description=DESCRIPTION_OF_LIMITS),
) -> list[schemas.courses.CourseData]:
    """
    取得 16 週課程列表。
    """
    condition = Conditions("note", "16週課程", True)
    result = courses.query(condition)[:limits]
    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.get("/lists/microcredits", response_model=list[schemas.courses.CourseData])
async def get_microcredits_courses_list(
    response: Response,
    limits: int = Query(None, ge=1, description=DESCRIPTION_OF_LIMITS),
) -> list[schemas.courses.CourseData]:
    """
    取得微學分課程列表。
    """
    condition = Conditions("credit", "[0-9].[0-9]", True)
    result = courses.query(condition)[:limits]
    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.get("/lists/xclass", response_model=list[schemas.courses.CourseData])
async def get_xclass_courses_list(
    response: Response,
    limits: int = Query(None, ge=1, description=DESCRIPTION_OF_LIMITS),
) -> list[schemas.courses.CourseData]:
    """
    取得 X-class 課程列表。
    """
    condition = Conditions("note", "X-Class", True)
    result = courses.query(condition)[:limits]
    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.get("/searches", response_model=list[schemas.courses.CourseData])
async def search_by_field_and_value(
    field: schemas.courses.CourseFieldName = Query(
        ...,
        example=schemas.courses.CourseFieldName.chinese_title,
        description="搜尋的欄位名稱",
    ),
    value: str = Query(..., example="產業.+生涯", description="搜尋的值（可以使用 Regex，正則表達式）"),
    limits: int = Query(None, ge=1, example=5, description=DESCRIPTION_OF_LIMITS),
):
    """
    取得指定欄位滿足搜尋值的課程列表。
    """
    condition = Conditions(field, value, True)
    result = courses.query(condition)[:limits]
    return result


@router.post("/searches", response_model=list[schemas.courses.CourseData])
async def get_courses_by_condition(
    query_condition: (
        schemas.courses.CourseQueryCondition | schemas.courses.CourseCondition
    ) = Body(
        openapi_examples={
            "normal_1": {
                "summary": "單一搜尋條件",
                "description": "只使用單一搜尋條件，類似於 GET 方法",
                "value": {
                    "row_field": "chinese_title",
                    "matcher": "數統導論",
                    "regex_match": True,
                },
            },
            "normal_2": {
                "summary": "兩個搜尋條件",
                "description": "使用兩個搜尋條件，例如：黃姓老師 或 孫姓老師開設的課程",
                "value": [
                    {
                        "row_field": "teacher",
                        "matcher": "黃",
                        "regex_match": True,
                    },
                    "or",
                    {
                        "row_field": "teacher",
                        "matcher": "孫",
                        "regex_match": True,
                    },
                ],
            },
            "normal_nested": {
                "summary": "多層搜尋條件",
                "description": "使用巢狀搜尋條件，例如：(3學分的課程) 且 ((統計所 或 數學系開設的課程) 且 (開課時間是T3T4 或 開課時間是R3R4))",
                "value": [
                    {"row_field": "credit", "matcher": "3", "regex_match": True},
                    "and",
                    [
                        [
                            {"row_field": "id", "matcher": "STAT", "regex_match": True},
                            "or",
                            {"row_field": "id", "matcher": "MATH", "regex_match": True},
                        ],
                        "and",
                        [
                            {
                                "row_field": "class_room_and_time",
                                "matcher": "T3T4",
                                "regex_match": True,
                            },
                            "or",
                            {
                                "row_field": "class_room_and_time",
                                "matcher": "R3R4",
                                "regex_match": True,
                            },
                        ],
                    ],
                ],
            },
        }
    ),
    limits: int = Query(None, ge=1, example=5, description=DESCRIPTION_OF_LIMITS),
):
    """
    根據條件取得課程。
    """
    if type(query_condition) is schemas.courses.CourseCondition:
        condition = Conditions(
            query_condition.row_field.value,
            query_condition.matcher,
            query_condition.regex_match,
        )
    elif type(query_condition) is schemas.courses.CourseQueryCondition:
        # 設定 mode="json" 是為了讓 dump 出來的內容不包含 python 的實體 (instance)
        condition = Conditions(
            list_build_target=query_condition.model_dump(mode="json")
        )
    result = courses.query(condition)[:limits]
    return result


@router.get("/searches/id/{course_id}", response_model=list[schemas.courses.CourseData])
async def search_courses_by_id(course_id: str = Path(..., description="搜尋的課號")):
    """
    根據課號取得課程。
    """
    if len(course_id) < 7:
        raise HTTPException(
            status_code=400, detail="Bad Request, course id is too short."
        )
    # 課號是 11210AES 520100，但是有些人會用 11210AES520100
    if course_id[-7] != " ":
        course_id = course_id[:-6] + " " + course_id[-6:]
    condition = Conditions("id", course_id, True)
    result = courses.query(condition)
    if result == []:
        raise HTTPException(status_code=404, detail="There is no course id match.")
    return result


@router.get(
    "/searches/credits/{credits_number}",
    response_model=list[schemas.courses.CourseData],
)
async def search_courses_by_credits(
    credits_number: float = Path(..., example=3, description="搜尋的學分數"),
    op: schemas.courses.CourseCreditOperation = Query(
        None, example="gt", description="比較運算子，可以是 >(gt)、<(lt)、>=(gte)、<=(lte)"
    ),
    limits: int = Query(None, description=DESCRIPTION_OF_LIMITS),
) -> list[schemas.courses.CourseData]:
    """
    取得指定學分數的課程。
    """
    result = courses.list_credit(credits_number, op)[:limits]
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this credits."
        )
    return result


@router.get(
    "/searches/classroom/{classroom_name}",
    response_model=list[schemas.courses.CourseData],
)
async def search_courses_by_classroom(
    classroom_name: str = Path(..., description="搜尋的教室"),
    limits: int = Query(None, description=DESCRIPTION_OF_LIMITS),
):
    """
    根據教室取得課程，可以用中文或英文教室名稱，也可以使用系館代碼。
    """
    condition = Conditions("class_room_and_time", classroom_name, True)
    result = courses.query(condition)[:limits]
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this classroom."
        )
    return result


@router.get(
    "/searches/time/{class_time}", response_model=list[schemas.courses.CourseData]
)
async def search_courses_by_time(
    class_time: str = Path(..., example="M1M2", description="搜尋的上課時間"),
    limits: int = Query(None, ge=1, example=5, description=DESCRIPTION_OF_LIMITS),
):
    """
    根據上課時間取得課程，使用 M1M2 表示星期一第一節到第二節。
    """
    condition = Conditions("class_room_and_time", class_time, True)
    result = courses.query(condition)[:limits]
    if result == []:
        raise HTTPException(status_code=404, detail="There is no course at this time.")
    return result


@router.get(
    "/searches/teacher/{teacher_name}", response_model=list[schemas.courses.CourseData]
)
async def search_courses_by_teacher(
    teacher_name: str = Path(..., example="顏東勇", description="搜尋的教師姓名"),
    limits: int = Query(None, description=DESCRIPTION_OF_LIMITS),
) -> list[schemas.courses.CourseData]:
    """
    根據教師姓名取得課程，可以用中英文姓名，也可以只用姓氏。
    """
    condition = Conditions("teacher", teacher_name, True)
    result = courses.query(condition)[:limits]
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this teacher."
        )
    return result
