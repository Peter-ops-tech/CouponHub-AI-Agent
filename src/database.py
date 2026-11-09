
import re
import sqlite3
from contextlib import closing
from pathlib import Path

# 資料庫位置
DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "couponhub.db"
)

# 預設分類
DEFAULT_CATEGORIES = [
    ("美食", 1),
    ("購物", 2),
    ("商城", 3),
    ("外送", 4),
]


def create_offers_table(conn, table_name):
    """建立新的優惠資料表。"""

    if table_name not in ("offers", "offers_new"):
        raise ValueError("不允許的資料表名稱")

    conn.execute(f"""
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL
                REFERENCES categories(name),
            channel TEXT NOT NULL,
            description TEXT NOT NULL,
            valid_from TEXT,
            valid_until TEXT,
            terms TEXT,
            source_url TEXT NOT NULL,
            review_status TEXT NOT NULL DEFAULT 'pending'
                CHECK(review_status IN (
                    'pending', 'approved', 'rejected'
                )),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


def init_db():
    """初始化資料庫，必要時升級舊分類結構。"""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    migrated = False

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        with conn:
            # 建立分類資料表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    name TEXT PRIMARY KEY,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1
                        CHECK(is_active IN (0, 1))
                )
            """)

            # 加入預設分類，不覆蓋既有分類
            conn.executemany("""
                INSERT OR IGNORE INTO categories
                    (name, sort_order)
                VALUES (?, ?)
            """, DEFAULT_CATEGORIES)

            # 檢查 offers 是否已經存在
            existing = conn.execute("""
                SELECT sql
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'offers'
            """).fetchone()

            if existing is None:
                # 新資料庫：直接建立新版資料表
                create_offers_table(conn, "offers")

            else:
                old_schema = existing[0]

                # 判斷是否仍是舊版固定三分類結構
                has_old_constraint = re.search(
                    r"CHECK\s*\(\s*category\s+IN\s*\(",
                    old_schema,
                    flags=re.IGNORECASE
                )

                if has_old_constraint:
                    # 建立新版資料表
                    create_offers_table(conn, "offers_new")

                    # 保留舊資料，包括 ID 與審核狀態
                    conn.execute("""
                        INSERT INTO offers_new (
                            id, merchant, title, category,
                            channel, description,
                            valid_from, valid_until,
                            terms, source_url,
                            review_status, created_at
                        )
                        SELECT
                            id, merchant, title, category,
                            channel, description,
                            valid_from, valid_until,
                            terms, source_url,
                            review_status, created_at
                        FROM offers
                    """)

                    # 以新資料表取代舊資料表
                    conn.execute("DROP TABLE offers")
                    conn.execute(
                        "ALTER TABLE offers_new RENAME TO offers"
                    )

                    migrated = True

    if migrated:
        print("舊版優惠資料表已升級，原有資料已保留。")

    print(f"資料庫已建立：{DB_PATH}")


def get_categories():
    """取得所有啟用中的分類，依照顯示順序排列。"""

    with closing(sqlite3.connect(DB_PATH)) as conn:
        rows = conn.execute("""
            SELECT name
            FROM categories
            WHERE is_active = 1
            ORDER BY sort_order ASC, name ASC
        """).fetchall()

    return [row[0] for row in rows]


def add_category(name):
    """新增分類，若分類已存在則顯示錯誤。"""

    name = name.strip()

    if not name:
        raise ValueError("分類名稱不可空白。")

    if len(name) > 30:
        raise ValueError("分類名稱不可超過 30 個字元。")

    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            existing = conn.execute("""
                SELECT name
                FROM categories
                WHERE name = ?
            """, (name,)).fetchone()

            if existing:
                raise ValueError(
                    f"分類「{name}」已經存在。"
                )

            next_order = conn.execute("""
                SELECT COALESCE(MAX(sort_order), 0) + 1
                FROM categories
            """).fetchone()[0]

            conn.execute("""
                INSERT INTO categories (
                    name, sort_order, is_active
                )
                VALUES (?, ?, 1)
            """, (name, next_order))


if __name__ == "__main__":
    init_db()

    # 顯示目前分類及優惠數量
    with closing(sqlite3.connect(DB_PATH)) as conn:
        categories = conn.execute("""
            SELECT name
            FROM categories
            WHERE is_active = 1
            ORDER BY sort_order, name
        """).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM offers"
        ).fetchone()[0]

    print("目前分類：", [row[0] for row in categories])
    print("優惠資料筆數：", total)
