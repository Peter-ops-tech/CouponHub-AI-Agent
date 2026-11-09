
import streamlit as st

from src.database import init_db, get_categories
from src.tools import search_offers
from src.agent import ask_agent


# ========== 網站基本設定 ==========

st.set_page_config(
    page_title="CouponHub｜AI 智慧優惠整合平台",
    page_icon="🎟️",
    layout="wide"
)

# 初始化資料庫
init_db()


# ========== 顯示優惠卡片 ==========

def show_offers(offers):
    """顯示查詢到的優惠資料。"""

    if not offers:
        st.info("目前沒有符合條件且有效的優惠。")
        return

    for offer in offers:
        with st.container(border=True):

            st.subheader(offer["title"])

            st.write(f"**商家：** {offer['merchant']}")
            st.write(f"**類別：** {offer['category']}")
            st.write(f"**適用通路：** {offer['channel']}")

            st.write(offer["description"])

            start = offer.get("valid_from") or "未提供"
            end = offer.get("valid_until") or "未提供"

            st.caption(
                f"有效期間：{start} ～ {end}"
            )

            if offer.get("terms"):
                st.caption(
                    f"使用條件：{offer['terms']}"
                )

            if offer.get("source_url"):
                st.link_button(
                    "查看活動來源",
                    offer["source_url"]
                )


# ========== 網站首頁 ==========

st.title("🎟️ CouponHub")
st.header("AI 智慧優惠整合平台")

st.write(
    "整合美食、購物、商城與外送優惠，"
    "幫你找到適合的活動！"
)

st.divider()


# ========== 動態優惠分類 ==========

categories = get_categories()

category_icons = {
    "美食": "🍔",
    "購物": "🛍️",
    "商城": "🛒",
    "外送": "🛵"
}

if categories:

    tab_names = [
        f"{category_icons.get(category, '🏷️')} {category}"
        for category in categories
    ]

    tabs = st.tabs(tab_names)

    for tab, category in zip(tabs, categories):

        with tab:

            st.header(f"{category}優惠")

            offers = search_offers(
                category=category
            )

            show_offers(offers)

else:
    st.info("目前尚未建立優惠分類。")


# ========== 一般優惠搜尋 ==========

st.divider()

st.header("🔎 搜尋優惠")

with st.form("offer_search_form"):

    merchant_query = st.text_input(
        "商家名稱",
        placeholder="例如：麥當勞、必勝客"
    )

    selected_category = st.selectbox(
        "優惠分類",
        ["全部"] + categories
    )

    channel_query = st.text_input(
        "適用通路（選填）",
        placeholder="例如：門市、App、官網"
    )

    search_clicked = st.form_submit_button(
        "搜尋優惠"
    )


if search_clicked:

    category_filter = (
        None
        if selected_category == "全部"
        else selected_category
    )

    filtered_offers = search_offers(
        merchant=merchant_query.strip() or None,
        category=category_filter,
        channel=channel_query.strip() or None
    )

    st.subheader("搜尋結果")

    show_offers(filtered_offers)


# ========== AI 智慧優惠助理 ==========

st.divider()

st.header("🤖 AI 智慧優惠助理")

st.caption(
    "使用自然語言詢問優惠。"
    "AI 會透過工具查詢已核准且目前有效的活動。"
    "實際使用資格與限制仍請以官方公告為準。"
)


# 初始化聊天紀錄
if "agent_messages" not in st.session_state:
    st.session_state.agent_messages = []


# 顯示聊天紀錄
for message in st.session_state.agent_messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# 使用者輸入訊息
prompt = st.chat_input(
    "例如：請幫我查詢麥當勞目前有哪些有效優惠"
)


if prompt:

    # 儲存使用者訊息
    st.session_state.agent_messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # AI 回答
    with st.chat_message("assistant"):

        with st.spinner("AI 正在查詢優惠..."):

            try:
                answer = ask_agent(prompt)

            except Exception as error:

                # 只在開發終端機顯示詳細錯誤
                print(
                    "AI Agent 發生錯誤：",
                    repr(error)
                )

                answer = (
                    "AI 服務目前無法正常完成查詢，"
                    "請稍後再試。"
                )

        st.markdown(answer)

    # 儲存 AI 回答
    st.session_state.agent_messages.append({
        "role": "assistant",
        "content": answer
    })


st.caption(
    "目前為第一版 AI Agent："
    "畫面會保留聊天紀錄，"
    "但 AI 尚未具備完整的多輪上下文理解。"
)
