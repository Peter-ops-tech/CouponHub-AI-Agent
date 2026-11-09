
import sqlite3
from contextlib import closing
from datetime import date
from urllib.parse import urlparse

import streamlit as st

from src.database import (
    DB_PATH,
    init_db,
    get_categories,
    add_category,
)
from src.tools import check_duplicate


st.set_page_config(
    page_title="CouponHub 管理後台",
    page_icon="⚙️",
    layout="wide"
)

init_db()


def check_date(value):
    """驗證日期格式，空字串表示日期未知。"""
    if not value:
        return None

    parsed = date.fromisoformat(value)

    if parsed.isoformat() != value:
        raise ValueError("日期格式必須是 YYYY-MM-DD")

    return value



def add_offer(values):
    """新增優惠前先檢查是否重複。"""

    duplicate = check_duplicate(
        merchant=values[0],
        title=values[1],
        category=values[2],
        channel=values[3],
        valid_from=values[5],
        valid_until=values[6]
    )

    if duplicate:
        raise ValueError(
            f"發現疑似重複優惠！"
            f"原始優惠 ID：{duplicate['id']}，"
            f"目前狀態：{duplicate['review_status']}"
        )

    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute("""
                INSERT INTO offers (
                    merchant, title, category, channel,
                    description, valid_from, valid_until,
                    terms, source_url, review_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, values)



def get_pending_offers():
    """讀取所有待審核優惠。"""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT *
            FROM offers
            WHERE review_status = 'pending'
            ORDER BY id ASC
        """).fetchall()

        return [dict(row) for row in rows]


def update_status(offer_id, status):
    """核准或拒絕指定優惠。"""
    if status not in ("approved", "rejected"):
        raise ValueError("不允許的審核狀態")

    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            cursor = conn.execute("""
                UPDATE offers
                SET review_status = ?
                WHERE id = ?
                  AND review_status = 'pending'
            """, (status, offer_id))

            return cursor.rowcount == 1

def get_all_offers():
    """取得所有優惠，包含待審核、已核准及已拒絕。"""

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT *
            FROM offers
            ORDER BY id DESC
        """).fetchall()

    return [dict(row) for row in rows]


def update_offer(offer_id, values):
    """修改優惠，檢查重複並將狀態重新設為 pending。"""

    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:

            # 檢查是否與其他優惠重複，排除正在編輯的自己
            duplicate = conn.execute("""
                SELECT id
                FROM offers
                WHERE id != ?
                  AND review_status IN ('pending', 'approved')
                  AND merchant = ?
                  AND title = ?
                  AND category = ?
                  AND channel = ?
                  AND COALESCE(valid_from, '') = COALESCE(?, '')
                  AND COALESCE(valid_until, '') = COALESCE(?, '')
                LIMIT 1
            """, (
                offer_id, values[0], values[1],
                values[2], values[3], values[5], values[6]
            )).fetchone()

            if duplicate:
                raise ValueError(
                    f"與優惠 ID {duplicate[0]} 疑似重複，請先確認。"
                )

            # 更新優惠內容，修改後重新送審
            cursor = conn.execute("""
                UPDATE offers
                SET merchant = ?,
                    title = ?,
                    category = ?,
                    channel = ?,
                    description = ?,
                    valid_from = ?,
                    valid_until = ?,
                    terms = ?,
                    source_url = ?,
                    review_status = 'pending'
                WHERE id = ?
            """, (*values, offer_id))

            if cursor.rowcount != 1:
                raise ValueError("找不到指定的優惠紀錄。")


st.title("⚙️ CouponHub 管理後台")
st.warning(
    "目前為本機開發版本，尚未加入管理者登入驗證，"
    "請勿公開部署或開放給其他使用者。"
)

tab_import, tab_review, tab_edit, tab_category = st.tabs(
    [
        "➕ 新增優惠",
        "✅ 審核優惠",
        "✏️ 編輯優惠",
        "📁 分類管理",
    ]
)

# ---------- 新增優惠 ----------
with tab_import:
    st.header("新增優惠活動")

    with st.form("offer_form", clear_on_submit=True):
        merchant = st.text_input("商家名稱")
        title = st.text_input("活動標題")

        category = st.selectbox(
            "優惠分類",
            get_categories()
        )

        channel = st.text_input(
            "適用通路",
            placeholder="例如：門市、官方網站、App"
        )

        description = st.text_area("優惠內容")

        valid_from = st.text_input(
            "開始日期",
            placeholder="YYYY-MM-DD，未知可留空"
        )

        valid_until = st.text_input(
            "結束日期",
            placeholder="YYYY-MM-DD，未知可留空"
        )

        terms = st.text_area("使用條件")

        source_url = st.text_input(
            "官方活動來源網址",
            placeholder="https://..."
        )

        submitted = st.form_submit_button("新增優惠")

    if submitted:
        parsed_url = urlparse(source_url.strip())

        if not all([
            merchant.strip(),
            title.strip(),
            channel.strip(),
            description.strip()
        ]):
            st.error("商家、標題、通路及內容不可留空。")

        elif (
            parsed_url.scheme != "https"
            or not parsed_url.hostname
        ):
            st.error("請輸入完整的 HTTPS 來源網址。")

        else:
            try:
                start = check_date(valid_from.strip())
                end = check_date(valid_until.strip())

                if start and end and start > end:
                    raise ValueError(
                        "結束日期不可早於開始日期"
                    )

                add_offer((
                    merchant.strip(),
                    title.strip(),
                    category,
                    channel.strip(),
                    description.strip(),
                    start,
                    end,
                    terms.strip(),
                    source_url.strip()
                ))

                st.success(
                    "優惠已新增，狀態為 pending（待審核）。"
                )

            except ValueError as error:
                st.error(str(error))

            except sqlite3.Error as error:
                st.error(f"資料庫操作失敗：{error}")


# ---------- 審核優惠 ----------
with tab_review:
    st.header("待審核優惠")

    pending = get_pending_offers()

    if not pending:
        st.info("目前沒有待審核的優惠。")

    else:
        st.write(f"目前有 {len(pending)} 筆待審核資料。")

        offer_ids = [offer["id"] for offer in pending]

        selected_id = st.selectbox(
            "選擇優惠",
            offer_ids,
            format_func=lambda i: next(
                f"#{o['id']}｜{o['merchant']}｜{o['title']}"
                for o in pending if o["id"] == i
            )
        )

        selected = next(
            o for o in pending
            if o["id"] == selected_id
        )

        with st.container(border=True):
            st.subheader(selected["title"])
            st.write(f"商家：{selected['merchant']}")
            st.write(f"分類：{selected['category']}")
            st.write(f"通路：{selected['channel']}")
            st.write(selected["description"])

            st.write(
                f"有效期間："
                f"{selected['valid_from'] or '未知'} ～ "
                f"{selected['valid_until'] or '未知'}"
            )

            st.write(
                f"使用條件：{selected['terms'] or '未提供'}"
            )

            st.write(f"來源：{selected['source_url']}")

            st.link_button(
                "開啟活動來源進行核對",
                selected["source_url"]
            )

        verified = st.checkbox(
            "我已人工確認活動來源、期限及使用條件",
            key=f"verified_{selected_id}"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "✅ 核准優惠",
                disabled=not verified,
                use_container_width=True
            ):
                if (
                    not selected["valid_from"]
                    or not selected["valid_until"]
                ):
                    st.error(
                        "活動日期不完整，暫時不可核准。"
                    )
                else:
                    if update_status(
                        selected_id, "approved"
                    ):
                        st.success("優惠已核准。")
                        st.rerun()

        with col2:
            if st.button(
                "❌ 拒絕優惠",
                use_container_width=True
            ):
                if update_status(
                    selected_id, "rejected"
                ):
                    st.success("優惠已拒絕。")
                    st.rerun()


# ---------- 編輯優惠 ----------
with tab_edit:
    st.header("編輯優惠活動")

    all_offers = get_all_offers()

    if not all_offers:
        st.info("目前沒有可編輯的優惠。")

    else:
        offer_map = {
            offer["id"]: offer for offer in all_offers
        }

        selected_id = st.selectbox(
            "選擇要編輯的優惠",
            options=list(offer_map.keys()),
            format_func=lambda i: (
                f"#{i}｜{offer_map[i]['merchant']}｜"
                f"{offer_map[i]['title']}｜"
                f"{offer_map[i]['review_status']}"
            )
        )

        selected = offer_map[selected_id]

        st.info(
            "修改後會重新設為 pending（待審核），"
            "必須再次核准才能公開顯示。"
        )

        with st.form(f"edit_form_{selected_id}"):

            merchant = st.text_input(
                "商家名稱",
                value=selected["merchant"]
            )

            title = st.text_input(
                "活動標題",
                value=selected["title"]
            )

            categories = get_categories()

            category = st.selectbox(
                "優惠分類",
                categories,
                index=categories.index(selected["category"])
            )

            channel = st.text_input(
                "適用通路",
                value=selected["channel"]
            )

            description = st.text_area(
                "優惠內容",
                value=selected["description"]
            )

            valid_from = st.text_input(
                "開始日期",
                value=selected["valid_from"] or ""
            )

            valid_until = st.text_input(
                "結束日期",
                value=selected["valid_until"] or ""
            )

            terms = st.text_area(
                "使用條件",
                value=selected["terms"] or ""
            )

            source_url = st.text_input(
                "官方活動來源網址",
                value=selected["source_url"]
            )

            saved = st.form_submit_button("💾 儲存修改")

        if saved:
            parsed_url = urlparse(source_url.strip())

            if not all([
                merchant.strip(),
                title.strip(),
                channel.strip(),
                description.strip()
            ]):
                st.error("商家、標題、通路及內容不可留空。")

            elif (
                parsed_url.scheme != "https"
                or not parsed_url.hostname
            ):
                st.error("請輸入完整的 HTTPS 來源網址。")

            else:
                try:
                    start = check_date(valid_from.strip())
                    end = check_date(valid_until.strip())

                    if start and end and start > end:
                        raise ValueError(
                            "結束日期不可早於開始日期。"
                        )

                    values = (
                        merchant.strip(),
                        title.strip(),
                        category,
                        channel.strip(),
                        description.strip(),
                        start,
                        end,
                        terms.strip(),
                        source_url.strip()
                    )

                    update_offer(selected_id, values)

                    st.success(
                        "修改成功！優惠已重新送審，"
                        "請到審核分頁確認。"
                    )

                except ValueError as error:
                    st.error(str(error))

                except sqlite3.Error as error:
                    st.error(f"資料庫錯誤：{error}")

# ---------- 分類管理 ----------
with tab_category:
    st.header("📁 分類管理")

    st.write(
        "你可以在這裡新增優惠分類，"
        "新增後，前台及後台都可以使用這個分類。"
    )

    st.subheader("新增分類")

    with st.form("add_category_form", clear_on_submit=True):
        new_category_name = st.text_input(
            "分類名稱",
            placeholder="例如：旅遊、娛樂、住宿"
        )

        submitted = st.form_submit_button(
            "➕ 新增分類"
        )

    if submitted:
        try:
            add_category(new_category_name)

            st.success(
                f"分類「{new_category_name.strip()}」"
                "新增成功！"
            )

        except ValueError as error:
            st.error(str(error))

        except sqlite3.Error as error:
            st.error(f"資料庫發生錯誤：{error}")

    st.divider()

    st.subheader("目前已啟用的分類")

    categories = get_categories()

    if not categories:
        st.info("目前尚未建立分類。")

    else:
        st.write(f"目前共有 {len(categories)} 個分類。")

        for index, name in enumerate(categories, start=1):
            st.write(f"{index}. {name}")

    st.caption(
        "目前支援新增與查看分類。"
        "分類重新命名、停用及排序功能之後再加入。"
    )
