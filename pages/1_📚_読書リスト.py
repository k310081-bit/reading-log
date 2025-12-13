import streamlit as st
import pandas as pd
import requests

# --- 設定・関数定義 ---
st.set_page_config(page_title="読書リスト", layout="wide")

@st.cache_data
def get_book_cover(isbn, title, author):
    # 1. OpenBD (ISBN)
    if isbn and str(isbn).startswith('978'):
        clean_isbn = str(isbn).replace('-', '').replace(' ', '').split('.')[0]
        try:
            url = f"https://api.openbd.jp/v1/get?isbn={clean_isbn}"
            response = requests.get(url, timeout=1) 
            json_data = response.json()
            if json_data and json_data[0] and json_data[0].get('summary', {}).get('cover'):
                return json_data[0]['summary']['cover']
        except: pass
    
    # 2. GoogleBooks (Title)
    try:
        if not title: return None
        search_title = str(title).split(':')[0].split('　')[0]
        url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{search_title}"
        response = requests.get(url, timeout=1)
        data = response.json()
        if 'items' in data and len(data['items']) > 0:
            vol = data['items'][0].get('volumeInfo', {})
            links = vol.get('imageLinks', {})
            return links.get('thumbnail') or links.get('smallThumbnail')
    except: pass
    return None

# --- データ読み込み ---
try:
    col_names = ["サービスID", "アイテムID", "13桁ISBN", "カテゴリ", "評価", "読書状況", "レビュー", "タグ", "読書メモ(非公開)", "登録日時", "読了日", "タイトル", "作者名", "出版社名", "発行年", "タイプ", "ページ数"]
    df = pd.read_csv('reading_log.csv', encoding='cp932', header=None, names=col_names, dtype={'13桁ISBN': str})
    if '13桁ISBN' in df.columns: df = df.rename(columns={'13桁ISBN': 'ISBN'})
    if '作者名' in df.columns: df = df.rename(columns={'作者名': '著者'})
    if 'ISBN' in df.columns: df['ISBN'] = df['ISBN'].astype(str).str.replace(r'\.0$', '', regex=True)
    df = df.dropna(subset=['タイトル'])
    df = df[df['タイトル'].astype(str).str.strip() != '']
    df['読了日'] = pd.to_datetime(df['読了日'], errors='coerce')
    df['年'] = df['読了日'].dt.year
    df['月'] = df['読了日'].dt.month
except Exception: st.stop()

# --- サイドバー検索 ---
st.sidebar.header('🔍 検索・絞り込み')
unique_categories = df['カテゴリ'].unique()
selected_categories = st.sidebar.multiselect('カテゴリ', unique_categories, default=[])
search_author = st.sidebar.text_input('著者名', '')

df_display = df.copy()
if len(selected_categories) > 0:
    df_display = df_display[df_display['カテゴリ'].isin(selected_categories)]
if search_author:
    df_display = df_display[df_display['著者'].str.contains(search_author, na=False)]

# --- メイン表示 ---
st.title('📖 読書リスト')

if 'display_limit' not in st.session_state:
    st.session_state.display_limit = 30

if len(df_display) > 0:
    df_sorted = df_display.sort_values('読了日', ascending=False)
    current_limit = st.session_state.display_limit
    df_show = df_sorted.head(current_limit)
    
    cols_per_row = 3
    for i in range(0, len(df_show), cols_per_row):
        cols = st.columns(cols_per_row)
        batch = df_show.iloc[i:i+cols_per_row]
        for col, (_, book) in zip(cols, batch.iterrows()):
            with col:
                with st.container(border=True):
                    cover_url = get_book_cover(book.get('ISBN'), book.get('タイトル'), book.get('著者'))
                    if cover_url: st.image(cover_url, use_container_width=True)
                    else: st.markdown('<div style="background-color:#eee; height:150px; display:flex; align-items:center; justify-content:center; color:#888;">No Image</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"**{book.get('タイトル', '')}**")
                    st.caption(f"{book.get('著者', '')}")
                    st.write(f"⭐ {book.get('評価', '-')}")
                    with st.expander("詳細"):
                        date_str = book['読了日'].strftime('%Y-%m-%d') if pd.notnull(book['読了日']) else '-'
                        st.text(f"読了: {date_str}\nカテゴリ: {book.get('カテゴリ', '-')}")

    if len(df_display) > current_limit:
        st.markdown("---")
        if st.button("👇 さらに30冊を表示"):
            st.session_state.display_limit += 30
            st.rerun()
else:
    st.info("条件に一致する本がありません")