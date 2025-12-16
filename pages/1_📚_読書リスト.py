import streamlit as st
import pandas as pd
import requests
import random

# --- 設定・関数定義 ---
st.set_page_config(page_title="読書リスト", layout="wide")

@st.cache_data
def get_book_cover(isbn, title, author):
    # 1. OpenBD (ISBN)
    if isbn and str(isbn).startswith('978'):
        clean_isbn = str(isbn).replace('-', '').replace(' ', '').split('.')[0]
        try:
            url = f"https://api.openbd.jp/v1/get?isbn={clean_isbn}"
            # ★修正1：タイムアウトを3秒に延長
            response = requests.get(url, timeout=3) 
            json_data = response.json()
            if json_data and json_data[0] and json_data[0].get('summary', {}).get('cover'):
                cover_url = json_data[0]['summary']['cover']
                # ★修正2：http を https に強制変換（空文字対策も含む）
                if cover_url:
                    return cover_url.replace("http://", "https://")
        except: pass
    
    # 2. GoogleBooks (Title)
    try:
        if not title: return None
        search_title = str(title).split(':')[0].split('　')[0]
        url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{search_title}"
        # ★修正1：タイムアウトを3秒に延長
        response = requests.get(url, timeout=3)
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            vol = data['items'][0].get('volumeInfo', {})
            links = vol.get('imageLinks', {})
            cover_url = links.get('thumbnail') or links.get('smallThumbnail')
            
            # ★修正2：http を https に強制変換
            if cover_url:
                return cover_url.replace("http://", "https://")
    except: pass
    
    return None


def get_spine_color():
    colors = [
        "#8D6E63", "#5D4037", "#795548", "#3E2723", 
        "#1A237E", "#283593", "#303F9F", 
        "#B71C1C", "#C62828", "#D32F2F", 
        "#004D40", "#00695C", "#2E7D32", 
        "#455A64", "#37474F", "#263238" 
    ]
    return random.choice(colors)

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
    df['評価'] = pd.to_numeric(df['評価'], errors='coerce').fillna(0)
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

col_head1, col_head2 = st.columns([2, 2])
with col_head1:
    st.write(f"全 {len(df_display)} 冊を表示中")
with col_head2:
    view_mode = st.radio("表示モード", ["Grid ▦", "List ≡", "Bookshelf 📚"], horizontal=True, label_visibility="collapsed")

st.markdown("---")

if len(df_display) > 0:
    df_sorted = df_display.sort_values('読了日', ascending=False)

    # === List ===
    if view_mode == "List ≡":
        display_cols = ["タイトル", "著者", "評価", "カテゴリ", "読了日", "ページ数"]
        st.dataframe(
            df_sorted[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "タイトル": st.column_config.TextColumn("書籍タイトル", width="medium"),
                "読了日": st.column_config.DateColumn("読了日", format="YYYY/MM/DD"),
                "評価": st.column_config.NumberColumn("評価", format="⭐ %d"),
                "ページ数": st.column_config.NumberColumn("ページ", format="%d p"),
            }
        )
    
    # === Grid ===
    elif view_mode == "Grid ▦":
        if 'display_limit' not in st.session_state:
            st.session_state.display_limit = 30
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

    # === Bookshelf ===
    elif view_mode == "Bookshelf 📚":
        st.markdown("""
        <style>
        .bookshelf-container {
            display: flex; flex-wrap: wrap; align-items: flex-end;
            gap: 2px; padding: 20px 10px; background-color: #f5f5f5;
            border-bottom: 15px solid #8D6E63; margin-bottom: 30px;
            box-shadow: 0px 10px 15px -5px rgba(0,0,0,0.3);
        }
        .book-faceout {
            width: 120px; margin: 0 10px; box-shadow: 3px 3px 8px rgba(0,0,0,0.4);
            transition: transform 0.2s; cursor: pointer;
        }
        .book-faceout:hover { transform: scale(1.05); }
        .book-faceout img { width: 100%; border-radius: 2px; }

        /* ★追加：画像なし面陳列のデザイン */
        .book-faceout-no-image {
            width: 120px; height: 170px; /* 高さを固定 */
            margin: 0 10px; background-color: #FFF3E0; /* 薄いクリーム色 */
            border: 1px solid #d3d3d3;
            box-shadow: 3px 3px 8px rgba(0,0,0,0.2);
            padding: 15px; display: flex; justify-content: center; align-items: center;
            text-align: center; font-family: "Yu Mincho", serif; font-weight: bold;
            color: #5D4037; transition: transform 0.2s; cursor: pointer;
            overflow: hidden;
        }
        .book-faceout-no-image:hover { transform: scale(1.05); }

        .book-spine {
            width: 35px; height: 180px; padding: 10px 5px;
            color: white; font-size: 14px; font-family: "Yu Mincho", serif;
            writing-mode: vertical-rl; text-orientation: mixed;
            border-radius: 3px; box-shadow: inset 2px 0 5px rgba(0,0,0,0.3);
            cursor: pointer; transition: margin-bottom 0.2s;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .book-spine:hover { margin-bottom: 10px; }
        .shelf-label {
            font-size: 1.2em; font-weight: bold; color: #5D4037;
            margin-top: 20px; border-left: 5px solid #8D6E63; padding-left: 10px;
        }
        a { text-decoration: none; color: inherit; }
        </style>
        """, unsafe_allow_html=True)

        st.info("💡 本をクリックするとAmazon検索が開きます")

        categories = df_sorted['カテゴリ'].unique()
        
        for category in categories:
            st.markdown(f'<div class="shelf-label">{category} の棚</div>', unsafe_allow_html=True)
            books_in_cat = df_sorted[df_sorted['カテゴリ'] == category]
            
            html_books = '<div class="bookshelf-container">'
            
            for _, book in books_in_cat.iterrows():
                title = book['タイトル']
                author = book['著者']
                rating = book['評価']
                amazon_url = f"https://www.amazon.co.jp/s?k={title}+{author}"
                
                # ★星5の場合は「面陳列」
                if rating == 5:
                    isbn = book.get('ISBN')
                    cover_url = get_book_cover(isbn, title, author)
                    
                    if cover_url:
                        # 画像がある場合（今まで通り）
                        html_books += f'<a href="{amazon_url}" target="_blank" title="{title} ({author})"><div class="book-faceout"><img src="{cover_url}"></div></a>'
                    else:
                        # ★画像がない場合（新しいデザインでタイトル表示）
                        html_books += f'<a href="{amazon_url}" target="_blank" title="{title} ({author})"><div class="book-faceout-no-image">{title}</div></a>'
                
                # ★星4以下の場合は「背表紙」
                else:
                    bg_color = get_spine_color()
                    display_title = title[:15] + ".." if len(title) > 15 else title
                    
                    html_books += f'<a href="{amazon_url}" target="_blank" title="{title} ({author})"><div class="book-spine" style="background-color: {bg_color};">{display_title}</div></a>'
            
            html_books += '</div>'
            st.markdown(html_books, unsafe_allow_html=True)

else:
    st.info("条件に一致する本がありません")