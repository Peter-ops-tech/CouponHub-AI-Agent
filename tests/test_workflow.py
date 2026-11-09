
import sqlite3
import tempfile
import unittest

from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from src.database import init_db
from src.import_offer import import_offer
from src.review_offers import review_offers
from src.tools import search_offers


class TestOfferWorkflow(unittest.TestCase):

    def test_import_review_search(self):

        # 建立臨時資料庫，不影響正式資料
        with tempfile.TemporaryDirectory() as temp_dir:

            test_db = Path(temp_dir) / "test_workflow.db"

            # 讓四個模組都使用同一個測試資料庫
            with (
                patch("src.database.DB_PATH", test_db),
                patch("src.import_offer.DB_PATH", test_db),
                patch("src.review_offers.DB_PATH", test_db),
                patch("src.tools.DB_PATH", test_db)
            ):

                init_db()

                today = date.today()
                start = (today - timedelta(days=1)).isoformat()
                end = (today + timedelta(days=7)).isoformat()

                # 使用模擬的終端機輸入，執行真正的匯入函式
                def add_test_offer(title):

                    answers = [
                        "測試商家",
                        title,
                        "購物",
                        "門市",
                        "這是測試資料，不是真實優惠",
                        start,
                        end,
                        "僅供系統測試",
                        "https://example.com/test"
                    ]

                    with patch("builtins.input", side_effect=answers):
                        import_offer()

                # 新增兩筆待審核測試優惠
                add_test_offer("[測試] 核准案例")
                add_test_offer("[測試] 拒絕案例")

                # 檢查匯入後的狀態
                with closing(sqlite3.connect(test_db)) as conn:
                    rows = conn.execute("""
                        SELECT id, title, review_status
                        FROM offers
                        ORDER BY id
                    """).fetchall()

                self.assertEqual(len(rows), 2)
                self.assertTrue(
                    all(row[2] == "pending" for row in rows)
                )

                approved_id = rows[0][0]
                rejected_id = rows[1][0]

                # 尚未審核，不應該搜尋得到
                results = search_offers(merchant="測試商家")
                self.assertEqual(results, [])

                # 管理者核准第一筆
                with patch(
                    "builtins.input",
                    side_effect=[str(approved_id), "a"]
                ):
                    review_offers()

                # 管理者拒絕第二筆
                with patch(
                    "builtins.input",
                    side_effect=[str(rejected_id), "r"]
                ):
                    review_offers()

                # 驗證資料庫的審核結果
                with closing(sqlite3.connect(test_db)) as conn:
                    statuses = dict(conn.execute("""
                        SELECT title, review_status
                        FROM offers
                    """).fetchall())

                self.assertEqual(
                    statuses["[測試] 核准案例"],
                    "approved"
                )

                self.assertEqual(
                    statuses["[測試] 拒絕案例"],
                    "rejected"
                )

                # 搜尋只能回傳核准的優惠
                results = search_offers(merchant="測試商家")

                self.assertEqual(len(results), 1)
                self.assertEqual(
                    results[0]["title"],
                    "[測試] 核准案例"
                )


if __name__ == "__main__":
    unittest.main()
