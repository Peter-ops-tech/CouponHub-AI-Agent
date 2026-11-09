
import sqlite3
from contextlib import closing
from datetime import date

from src.database import DB_PATH


def search_offers(merchant=None, category=None, channel=None):
    """搜尋已審核、目前在有效期間內的優惠。"""

    today = date.today().isoformat()

    sql = """
        SELECT id, merchant, title, category, channel,
               description, valid_from, valid_until,
               terms, source_url
        FROM offers
        WHERE review_status = 'approved'
          AND valid_from IS NOT NULL
          AND valid_until IS NOT NULL
          AND date(valid_from) <= date(?)
          AND date(valid_until) >= date(?)
    """

    params = [today, today]

    if merchant:
        sql += " AND merchant LIKE ?"
        params.append(f"%{merchant}%")

    if category:
        sql += " AND category = ?"
        params.append(category)

    if channel:
        sql += " AND channel LIKE ?"
        params.append(f"%{channel}%")

    sql += " ORDER BY valid_until ASC LIMIT 20"

    # closing 確保不會留下鎖定中的資料庫檔案
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


if __name__ == "__main__":
    results = search_offers(merchant="麥當勞")
    print("搜尋結果：", results)
    
def check_duplicate(
    merchant, title, category, channel,
    valid_from, valid_until
):
    """檢查是否存在相同商家、活動與有效期間的優惠。"""

    sql = """
        SELECT id, merchant, title, review_status
        FROM offers
        WHERE merchant = ?
          AND title = ?
          AND category = ?
          AND channel = ?
          AND COALESCE(valid_from, '') = COALESCE(?, '')
          AND COALESCE(valid_until, '') = COALESCE(?, '')
          AND review_status IN ('pending', 'approved')
        LIMIT 1
    """

    params = (
        merchant, title, category, channel,
        valid_from, valid_until
    )

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        result = conn.execute(sql, params).fetchone()

    return dict(result) if result else None
