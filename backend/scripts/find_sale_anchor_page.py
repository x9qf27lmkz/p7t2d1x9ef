# backend/scripts/find_sale_anchor_page.py

from app.utils.seoul_tail_scanner import find_anchor_page_reverse
import os

def main():
    api_key   = os.getenv("SEOUL_API_KEY_SALE") or os.getenv("SEOUL_API_KEY")
    service   = os.getenv("SEOUL_SALE_SERVICE") or "tbLnOpendataRtmsV"
    page_size = int(os.getenv("SEOUL_PAGE_SIZE", "1000"))
    throttle  = float(os.getenv("SEOUL_API_THROTTLE", "0.02"))
    hint_pages = int(os.getenv("SEOUL_SEEK_SCAN_PAGES", "400"))

    # 여기만 바꿔주면 됨: 우리가 신뢰하는 anchor row의 id
    anchor_id = int(os.getenv("FORCE_SALE_ANCHOR_ID"))

    anchor_page = find_anchor_page_reverse(
        api_key=api_key,
        service=service,
        page_size=page_size,
        throttle=throttle,
        anchor_id=anchor_id,
        max_scan_pages=hint_pages,
        verbose=True,
    )

    print("ANCHOR_PAGE_RESULT=", anchor_page)

if __name__ == "__main__":
    main()
