import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# ページ設定
st.set_page_config(page_title="読みたい本リスト", layout="wide")
st.title("🔖 読みたい本リスト (Cloud Sync)")

# --- 1. スプレッドシートへの接続 ---
# secrets.toml の [connections.gsheets] セクションを自動参照します
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """スプレッドシートから最新データを読み込む"""
    try:
        # ttl=0 にすることで、キャッシュさせずに毎回最新を取得
        return conn.read(ttl=0)
    except Exception:
        # シートが空、または読み込めない場合は空のDFを返す
        return pd.DataFrame(columns=["タイトル", "著者", "メモ", "登録日"])

df_wish = load_data()

# --- 2. 新規追加フォーム ---
with st.expander("➕ 新しい本をリストに追加する"):
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_title = st.text_input("書籍タイトル")
            new_author = st.text_input("著者名")
        with col2:
            new_memo = st.text_area("メモ・推薦理由")
            new_date = st.date_input("登録日", datetime.now())
        
        submit = st.form_submit_button("リストに保存")
        
        if submit:
            if new_title:
                # 新しい行を作成
                new_row = pd.DataFrame([{
                    "タイトル": new_title,
                    "著者": new_author,
                    "メモ": new_memo,
                    "登録日": new_date.strftime("%Y/%m/%d")
                }])
                
                # 既存データと結合して更新
                updated_df = pd.concat([df_wish, new_row], ignore_index=True)
                conn.update(data=updated_df)
                
                st.success(f"「{new_title}」を保存しました！")
                st.rerun()
            else:
                st.error("タイトルは必須入力です")

# --- 3. リストの表示 ---
st.markdown("---")
if not df_wish.empty:
    st.write(f"現在、**{len(df_wish)}冊** がリストに入っています。")
    
    # 新しい順に並べ替え
    df_wish_display = df_wish.copy()
    df_wish_display["登録日"] = pd.to_datetime(df_wish_display["登録日"])
    df_wish_display = df_wish_display.sort_values("登録日", ascending=False)

    st.dataframe(
        df_wish_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "タイトル": st.column_config.TextColumn("書籍タイトル", width="medium"),
            "著者": st.column_config.TextColumn("著者名"),
            "メモ": st.column_config.TextColumn("メモ・推薦理由"),
            "登録日": st.column_config.DateColumn("登録日", format="YYYY/MM/DD"),
        }
    )
    
    # --- 削除機能 ---
    with st.expander("🗑️ リストから削除する"):
        title_to_delete = st.selectbox("削除する本を選んでください", df_wish["タイトル"].unique())
        if st.button("削除実行"):
            updated_df = df_wish[df_wish["タイトル"] != title_to_delete]
            conn.update(data=updated_df)
            st.success(f"「{title_to_delete}」を削除しました。")
            st.rerun()
else:
    st.info("まだリストは空っぽです。上のフォームから追加してみましょう！")