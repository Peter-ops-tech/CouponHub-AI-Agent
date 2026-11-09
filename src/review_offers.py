
import sqlite3
from contextlib import closing

from src.database import DB_PATH, init_db


def review_offers():
    """列出待審核優惠，讓管理者決定核准或拒絕。"""

    init_db()

    # 建立資料庫連線，並確保結束時關閉
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row

        # 查詢所有待審核優惠
        offers = conn.execute("""
            SELECT *
            FROM offers
            WHERE review_status = 'pending'
            ORDER BY id ASC
        """).fetchall()

        if not offers:
            print("目前沒有待審核的優惠。")
            return

        print("\n=== CouponHub 待審核優惠 ===")

        for offer in offers:
            print("\n-------------------------")
            print(f"ID：{offer['id']}")
            print(f"商家：{offer['merchant']}")
            print(f"標題：{offer['title']}")
            print(f"類別：{offer['category']}")
            print(f"通路：{offer['channel']}")
            print(f"內容：{offer['description']}")
            print(
                f"有效期間：{offer['valid_from'] or '未知'}"
                f" ～ {offer['valid_until'] or '未知'}"
            )
            print(f"使用條件：{offer['terms'] or '未提供'}")
            print(f"來源：{offer['source_url']}")

        print("\n-------------------------")

        # 選擇要審核的優惠
        selected = input("請輸入要審核的優惠 ID（q 離開）：").strip()

        if selected.lower() == "q":
            print("已離開審核程式。")
            return

        try:
            offer_id = int(selected)
        except ValueError:
            print("錯誤：請輸入有效的整數 ID。")
            return

        pending_ids = {offer["id"] for offer in offers}

        if offer_id not in pending_ids:
            print("找不到這筆待審核優惠。")
            return

        # 管理者確認優惠來源與條件後，決定狀態
        print("\n請先確認官方來源、活動日期及使用限制。")
        action = input("輸入 a 核准、r 拒絕、其他鍵取消：").strip().lower()

        if action == "a":
            status = "approved"
        elif action == "r":
            status = "rejected"
        else:
            print("已取消審核。")
            return

        # 更新資料庫中的審核狀態
        with conn:
            cursor = conn.execute("""
                UPDATE offers
                SET review_status = ?
                WHERE id = ?
                  AND review_status = 'pending'
            """, (status, offer_id))

        if cursor.rowcount == 1:
            print(f"\n優惠 ID {offer_id} 審核完成！")
            print(f"目前狀態：{status}")
        else:
            print("更新失敗：優惠可能已被其他操作處理。")


if __name__ == "__main__":
    review_offers()
