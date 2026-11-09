
import sqlite3
from contextlib import closing
from datetime import date
from urllib.parse import urlparse

from src.database import DB_PATH, init_db


def required_input(label):
    """要求使用者輸入不可為空的欄位。"""
    while True:
        value = input(f"{label}：").strip()
        if value:
            return value
        print("此欄位不可留空。")


def date_input(label):
    """檢查日期格式；留空代表日期尚未確認。"""
    while True:
        value = input(f"{label}（YYYY-MM-DD，可留空）：").strip()

        if not value:
            return None

        try:
            date.fromisoformat(value)
            return value
        except ValueError:
            print("日期格式錯誤，例如：2026-10-31")


def import_offer():
    init_db()

    print("\n=== CouponHub 優惠資料匯入 ===")

    merchant = required_input("商家名稱")
    title = required_input("優惠標題")

    # 限制分類只能使用指定的三大類
    categories = ("購物", "商城", "外送")

    while True:
        category = required_input("分類（購物/商城/外送）")
        if category in categories:
            break
        print("請選擇購物、商城或外送。")

    channel = required_input("適用通路")
    description = required_input("優惠內容")

    valid_from = date_input("開始日期")
    valid_until = date_input("結束日期")

    if valid_from and valid_until and valid_from > valid_until:
        print("錯誤：結束日期不能早於開始日期。")
        return

    terms = input("使用條件（可留空）：").strip()

    while True:
        source_url = required_input("官方活動來源網址")
        parsed = urlparse(source_url)

        if parsed.scheme == "https" and parsed.netloc:
            break

        print("請輸入完整的 HTTPS 網址。")

    # 新增優惠：一律先標示 pending
    sql = """
        INSERT INTO offers (
            merchant, title, category, channel,
            description, valid_from, valid_until,
            terms, source_url, review_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
    """

    values = (
        merchant, title, category, channel,
        description, valid_from, valid_until,
        terms, source_url
    )

    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            cursor = conn.execute(sql, values)
            offer_id = cursor.lastrowid

    print(f"\n優惠匯入成功！ID：{offer_id}")
    print("目前審核狀態：pending（待審核）")


if __name__ == "__main__":
    import_offer()
