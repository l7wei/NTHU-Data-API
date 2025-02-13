from fastapi import APIRouter, HTTPException, Path
from pydantic import HttpUrl

from src.api import schemas
from src.utils.scrapers import rpage_scraper

router = APIRouter()


@router.get(
    "/rpage/announcements/{full_path:path}",
    response_model=list[schemas.resources.RssData],
)
def get_rpage_data(
    full_path: HttpUrl = Path(
        ...,
        example="https://bulletin.site.nthu.edu.tw/p/403-1086-5081-1.php?Lang=zh-tw",
        description="Rpage 完整公告網址",
    ),
    start_page: int = 1,
    end_page: int = 1,
):
    """
    爬取指定 Rpage 公告的內容。
    """
    if "nthu.edu.tw" not in full_path.host:
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Please provide a valid NTHU Rpage announcement URL.",
        )
    if end_page < start_page or start_page < 1:
        raise HTTPException(
            status_code=400,
            detail="Invalid page range. Please provide a valid page range.",
        )
    if end_page - start_page > 10:
        raise HTTPException(
            status_code=400,
            detail="Page range too large. Please provide a page range of 10 or fewer.",
        )
    return rpage_scraper.get_announcement(
        url=str(full_path), start_page=start_page, end_page=end_page
    )
