import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="読みたい本リスト", layout="wide")
st.title("🔖 読みたい本リスト")

# 保存ファイル名
CSV_FILE = "wishlist.csv"

# --- 1. データの読み込み ---
if os.path.exists(CSV_FILE):
    try:
        # 読み込み
        df_wish = pd.read_csv(CSV_FILE)
    except:
        st.error("データの読み込みに失敗しました")
        df_wish = pd.DataFrame(columns=["タイトル", "著者", "メモ", "登録日"])
else:
    # ファイルがない場合は空のデータフレームを作成
    df_wish = pd.DataFrame(columns=["タイトル", "著者", "メモ", "登録日"])

# --- 2. リストの表示 ---
if len(df_wish) > 0:
    st.write(f"現在、**{len(df_wish)}冊** がリストに入っています。")
    
    # 新しい順に並べ替え
    df_wish = df_wish.sort_values("登録日", ascending=False)

    st.dataframe(
        df_wish,
        use_container_width=True,
        hide_index=True,
        column_config={
            "タイトル": st.column_config.TextColumn("書籍タイトル", width="medium"),
            "著者": st.column_config.TextColumn("著者名"),
            "メモ": st.column_config.TextColumn("メモ・推薦理由"),
            "登録日": st.column_config.DateColumn("登録日", format="YYYY/MM/DD"),
        }
    )
    
    # --- 簡易削除機能（おまけ） ---
    st.markdown("---")
    with st.expander("🗑️ リストから削除する"):
        title_to_delete = st.selectbox("削除する本を選んでください", df_wish["タイトル"].unique())
        if st.button("削除実行"):
            # 選ばれた本以外を残して上書き保存
            new_df = df_wish[df_wish["タイトル"] != title_to_delete]
            new_df.to_csv(CSV_FILE, index=False)
            st.rerun() # 画面更新

else:
    st.info("まだリストは空っぽです。AIコンシェルジュから追加してみましょう！")