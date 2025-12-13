import streamlit as st
import pandas as pd

# --- 設定 ---
st.set_page_config(page_title="My Reading Log", layout="wide")
THEME_COLOR = '#8D6E63'

st.title('🏠 ホーム：読書実績ダッシュボード')

# --- データの読み込み ---
# ※各ページで共通して使うため、このブロックは他のページにも入れています
try:
    col_names = [
        "サービスID", "アイテムID", "13桁ISBN", "カテゴリ", "評価", 
        "読書状況", "レビュー", "タグ", "読書メモ(非公開)", "登録日時", 
        "読了日", "タイトル", "作者名", "出版社名", "発行年", 
        "タイプ", "ページ数"
    ]
    df = pd.read_csv(
        'reading_log.csv', encoding='cp932', header=None, names=col_names, dtype={'13桁ISBN': str}
    )
    if '13桁ISBN' in df.columns: df = df.rename(columns={'13桁ISBN': 'ISBN'})
    if '作者名' in df.columns: df = df.rename(columns={'作者名': '著者'})
    if 'ISBN' in df.columns: df['ISBN'] = df['ISBN'].astype(str).str.replace(r'\.0$', '', regex=True)
    df = df.dropna(subset=['タイトル'])
    df = df[df['タイトル'].astype(str).str.strip() != '']
    df['読了日'] = pd.to_datetime(df['読了日'], errors='coerce')
    df['年'] = df['読了日'].dt.year
    df['月'] = df['読了日'].dt.month

except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    st.stop()

# --- メインコンテンツ（実績表示） ---
st.write("左側のメニューから機能を選んでください。")
st.markdown("### 🏆 現在の積み上げ実績")

total_books = len(df)
total_pages = df['ページ数'].sum()
# 本の厚さを1冊平均2cmと仮定
book_height_meter = (total_books * 2.0) / 100 

col1, col2, col3 = st.columns(3)
col1.metric("📚 読んだ総冊数", f"{total_books} 冊")
col2.metric("📄 総ページ数", f"{int(total_pages):,} ページ")
col3.metric("📏 積み上げた高さ", f"{book_height_meter:.2f} m")

if book_height_meter < 1.5: comparison = "小学生の身長くらい"
elif book_height_meter < 3: comparison = "バスケットゴールくらい"
elif book_height_meter < 13: comparison = "鎌倉の大仏くらい"
elif book_height_meter < 333: comparison = "ビル・マンション級"
else: comparison = "東京タワー級！"

st.info(f"あなたが読んだ本を積み上げると、**{comparison}** です！")