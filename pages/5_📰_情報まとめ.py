import streamlit as st
import feedparser
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="情報まとめ", layout="wide")
st.title("📰 読書・トレンド情報収集")

# 保存ファイル名
CSV_FILE = "sources.csv"

# --- 1. データ管理機能（読み込み・保存） ---

def load_sources():
    # ファイルがなければデフォルトデータを作成
    if not os.path.exists(CSV_FILE):
        default_data = {
            "type": ["YouTube", "YouTube", "RSS", "RSS", "Website"],
            "name": ["文学YouTuberベル", "PIVOT 公式", "ブクログ通信", "Lifehacker", "Amazonランキング"],
            "value": [
                "UCL4QAujePZpVwwukBWXmx8Q",
                "UC8yHb-3xL522u_d4HqB7Gcg",
                "https://hon.booklog.jp/feed",
                "https://www.lifehacker.jp/feed/index.xml",
                "https://www.amazon.co.jp/gp/bestsellers/books"
            ]
        }
        df = pd.DataFrame(default_data)
        df.to_csv(CSV_FILE, index=False)
        return df
    else:
        return pd.read_csv(CSV_FILE)

def save_source(source_type, name, value):
    df = load_sources()
    new_row = pd.DataFrame({"type": [source_type], "name": [name], "value": [value]})
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)

def delete_source(index):
    df = load_sources()
    df = df.drop(index)
    df.to_csv(CSV_FILE, index=False)

# --- 2. サイドバー：登録・管理画面 ---
with st.sidebar:
    st.header("⚙️ 登録管理")
    
    # 追加フォーム
    with st.expander("➕ 新規追加", expanded=False):
        # ★選択肢に「Webサイト」を追加
        add_type = st.radio("種類", ["YouTube", "RSS(ブログ/ニュース)", "Webサイト"])
        
        add_name = st.text_input("表示名（例：〇〇のサイト）")
        
        if add_type == "YouTube":
            st.caption("チャンネルIDを入力してください")
            add_value = st.text_input("チャンネルID")
        elif add_type == "RSS(ブログ/ニュース)":
            st.caption("RSSのURLを入力してください")
            add_value = st.text_input("RSS URL")
        else:
            # Webサイトの場合
            st.caption("サイトのトップページURLを入力してください")
            add_value = st.text_input("サイトURL", placeholder="https://...")
            
        if st.button("追加する"):
            if add_name and add_value:
                # 内部的なタイプ名を統一
                type_code = "Website" if add_type == "Webサイト" else ("RSS" if "RSS" in add_type else "YouTube")
                save_source(type_code, add_name, add_value)
                st.success("追加しました！")
                st.rerun()
            else:
                st.error("名前とURLは必須です")

    # 削除フォーム
    with st.expander("🗑️ 登録解除", expanded=False):
        df_sources = load_sources()
        if len(df_sources) > 0:
            delete_target = st.selectbox(
                "削除する項目", 
                df_sources.index, 
                format_func=lambda x: f"{df_sources.iloc[x]['name']} ({df_sources.iloc[x]['type']})"
            )
            if st.button("削除実行"):
                delete_source(delete_target)
                st.rerun()
        else:
            st.info("登録データがありません")

# --- 3. データ取得ロジック ---

def get_youtube_rss_url(channel_id):
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

@st.cache_data(ttl=3600)
def fetch_feed_data(url, source_name, is_youtube=False):
    try:
        feed = feedparser.parse(url)
        entries = []
        for entry in feed.entries[:4]: 
            title = entry.title
            link = entry.link
            date_str = "-"
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt = datetime(*entry.published_parsed[:6])
                date_str = dt.strftime('%m/%d')
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                dt = datetime(*entry.updated_parsed[:6])
                date_str = dt.strftime('%m/%d')

            item = {
                "source": source_name,
                "title": title,
                "link": link,
                "date": date_str,
                "thumbnail": None
            }
            if is_youtube and 'media_thumbnail' in entry:
                item['thumbnail'] = entry.media_thumbnail[0]['url']
            
            entries.append(item)
        return entries
    except:
        return []

# --- 4. メイン表示 ---

df_current = load_sources()

# ★タブを3つに拡張
tab1, tab2, tab3 = st.tabs(["📺 YouTube", "🗞️ RSSニュース", "🌐 Webサイト"])

# === Tab 1: YouTube ===
with tab1:
    yt_sources = df_current[df_current['type'] == 'YouTube']
    if len(yt_sources) > 0:
        for _, row in yt_sources.iterrows():
            rss_url = get_youtube_rss_url(row['value'])
            videos = fetch_feed_data(rss_url, row['name'], is_youtube=True)
            if videos:
                st.markdown(f"##### {row['name']}")
                cols = st.columns(4)
                for i, video in enumerate(videos):
                    with cols[i]:
                        st.markdown(f"""
                        <a href="{video['link']}" target="_blank">
                            <img src="{video['thumbnail']}" style="width:100%; border-radius:8px;">
                        </a>
                        <div style="font-size:0.8em; line-height:1.2; margin-top:5px;">
                            <a href="{video['link']}" target="_blank" style="text-decoration:none; color:#333;">
                                {video['title'][:30]}...
                            </a>
                        </div>
                        <div style="font-size:0.7em; color:gray;">{video['date']}</div>
                        """, unsafe_allow_html=True)
                st.markdown("---")
    else:
        st.info("サイドバーからYouTubeチャンネルを追加してください")

# === Tab 2: RSS ===
with tab2:
    rss_sources = df_current[df_current['type'] == 'RSS']
    if len(rss_sources) > 0:
        col_a, col_b = st.columns(2)
        all_news = []
        for _, row in rss_sources.iterrows():
            items = fetch_feed_data(row['value'], row['name'])
            all_news.extend(items)
        
        all_news.sort(key=lambda x: x['date'], reverse=True)

        for i, item in enumerate(all_news):
            target_col = col_a if i % 2 == 0 else col_b
            with target_col:
                with st.container(border=True):
                    st.caption(f"{item['source']} | {item['date']}")
                    st.markdown(f"**[{item['title']}]({item['link']})**")
    else:
        st.info("サイドバーからRSSを追加してください")

# === Tab 3: Webサイト (新機能) ===
with tab3:
    web_sources = df_current[df_current['type'] == 'Website']
    
    if len(web_sources) > 0:
        st.write("よく見るサイトのリンク集")
        
        # グリッド表示（3列）
        cols_web = st.columns(3)
        
        for i, (index, row) in enumerate(web_sources.iterrows()):
            col_idx = i % 3
            site_url = row['value']
            site_name = row['name']
            
            # Googleのサービスを使ってファビコン（アイコン）を取得
            favicon_url = f"https://www.google.com/s2/favicons?domain={site_url}&sz=128"
            
            with cols_web[col_idx]:
                # カード風のデザイン
                st.markdown(f"""
                <a href="{site_url}" target="_blank" style="text-decoration:none; color:inherit;">
                    <div style="
                        border:1px solid #ddd; border-radius:10px; padding:15px; 
                        display:flex; align-items:center; gap:15px; 
                        background-color:white; box-shadow:0 2px 5px rgba(0,0,0,0.05);
                        transition: transform 0.2s;
                    " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                        <img src="{favicon_url}" style="width:40px; height:40px; border-radius:5px;">
                        <div style="font-weight:bold; font-size:1.1em; color:#333;">{site_name}</div>
                    </div>
                </a>
                <div style="height:15px;"></div>
                """, unsafe_allow_html=True)
                
    else:
        st.info("サイドバーからWebサイトを追加してください（RSSがないサイト用）")