
import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch

from src.database import init_db
from src.tools import search_offers


class TestSearchOffers(unittest.TestCase):

    def test_search_filters(self):
        # 建立臨時資料夾，測試結束後自動刪除
        with tempfile.TemporaryDirectory() as temp_dir:
            test_db = Path(temp_dir) / "test.db"

            # 在測試資料庫建立 offers 資料表
            with patch("src.database.DB_PATH", test_db):
                init_db()

            today = date.today()
            start = (today - timedelta(days=3)).isoformat()
            end = (today + timedelta(days=3)).isoformat()
            expired = (today - timedelta(days=1)).isoformat()

            # 建立三筆完全虛構的測試優惠
            def make_offer(title, end_date, status):
                return (
                    "測試商家", title, "購物", "門市",
                    "僅供測試，不是真實優惠",
                    start, end_date, "測試條款",
                    "https://example.com/test", status
                )

            offers = [
                make_offer("[測試] 有效優惠", end, "approved"),
                make_offer("[測試] 過期優惠", expired, "approved"),
                make_offer("[測試] 待審核優惠", end, "pending")
            ]

            with sqlite3.connect(test_db) as conn:
                conn.executemany("""
                    INSERT INTO offers (
                        merchant, title, category, channel,
                        description, valid_from, valid_until,
                        terms, source_url, review_status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, offers)

            # 關閉資料庫連線，避免 Windows 鎖定檔案
            conn.close()
            # 讓搜尋工具使用臨時資料庫
            with patch("src.tools.DB_PATH", test_db):
                results = search_offers(merchant="測試商家")
                no_results = search_offers(merchant="不存在的商家")

            # 驗證搜尋結果
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "[測試] 有效優惠")
            self.assertEqual(no_results, [])


if __name__ == "__main__":
    unittest.main()
