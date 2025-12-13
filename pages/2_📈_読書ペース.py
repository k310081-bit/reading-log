import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
from wordcloud import WordCloud
from janome.tokenizer import Tokenizer
from collections import Counter

st.set_page_config(page_title="読書分析", layout="wide")
THEME_COLOR = '#8D6E63' 

# --- データ読み込み ---
try:
    col_names = ["サービスID", "アイテムID", "13桁ISBN", "カテゴリ", "評価", "読書状況", "レビュー", "タグ", "読書メモ(非公開)", "登録日時", "読了日", "タイトル", "作者名", "出版社名", "発行年", "タイプ", "ページ数"]
    df = pd.read_csv('reading_log.csv', encoding='cp932', header=None, names=col_names, dtype={'13桁ISBN': str})
    if '13桁ISBN' in df.columns: df = df.rename(columns={'13桁ISBN': 'ISBN'})
    if '作者名' in df.columns: df = df.rename(columns={'作者名': '著者'})
    df = df.dropna(subset=['タイトル'])
    df['読了日'] = pd.to_datetime(df['読了日'], errors='coerce')
    df['年'] = df['読了日'].dt.year
    df['月'] = df['読了日'].dt.month
except Exception:
    st.error("データの読み込みに失敗しました")
    st.stop()

st.title('📊 読書データの可視化')

# ==========================================
# 1. 年ごとの読書ペース（既存機能）
# ==========================================
st.subheader('📅 年ごとの読書ペース')
years_list = sorted(df['年'].dropna().astype(int).unique(), reverse=True)

if len(years_list) > 0:
    col1, col2 = st.columns([1, 3])
    with col1:
        selected_year = st.selectbox('表示する年', years_list, index=0)
    
    df_year = df[df['年'] == selected_year]
    monthly_counts = pd.Series(0, index=range(1, 13))
    actual_counts = df_year['月'].value_counts()
    monthly_counts.update(actual_counts)

    fig, ax = plt.subplots(figsize=(8, 3))
    bars = ax.bar(monthly_counts.index, monthly_counts.values, color=THEME_COLOR)
    ax.set_title(f'{selected_year}年の月別冊数')
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([f"{m}月" for m in range(1, 13)])
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}', ha='center', va='bottom')
    st.pyplot(fig)
else:
    st.info("データがありません")

st.markdown("---")

# ==========================================
# 2. カテゴリ推移（積み上げ棒グラフ）
# ==========================================
st.subheader('📚 カテゴリの変遷')
st.caption("年ごとに、どのジャンルをよく読んでいたかの比較です")

if len(df) > 0:
    # クロス集計を作成（行：年、列：カテゴリ）
    cross_tab = pd.crosstab(df['年'], df['カテゴリ'])
    
    # グラフ描画
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    # colormapは 'tab20' (20色のパレット) などが見やすいです
    cross_tab.plot(kind='bar', stacked=True, ax=ax2, colormap='tab20', alpha=0.8)
    
    ax2.set_title('年ごとのカテゴリ内訳推移')
    ax2.set_xlabel('年')
    ax2.set_ylabel('冊数')
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0, title="カテゴリ")
    ax2.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    
    st.pyplot(fig2)

st.markdown("---")

# ==========================================
# 3. キーワードクラウド
# ==========================================
st.subheader('☁️ 読書ワードクラウド')
st.caption("よく出てくる言葉を大きさで可視化します")

# フォントパスの設定（プロジェクト内のフォントファイルを使用）
import os
font_path = 'ipaexg.ttf' 

# ※もし読み込めない場合のエラーハンドリングを追加しておくと親切です
if not os.path.exists(font_path):
    # Windowsで開発中にフォントファイルを入れ忘れた時のフォールバック
    font_path = 'C:/Windows/Fonts/msgothic.ttc'

# タブで表示内容を切り替え
tab1, tab2, tab3 = st.tabs(["👤 著者別", "🏷️ カテゴリ別", "📖 タイトル単語"])

def generate_wordcloud(text_data, stop_words=[]):
    try:
        wc = WordCloud(
            width=800, height=500, 
            background_color='white', 
            font_path=font_path,
            regexp=r"[\w']+", # 日本語対応のための正規表現
            collocations=False, # 2語の連なりを無効化
            stopwords=set(stop_words)
        ).generate(text_data)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')
        return fig
    except Exception as e:
        return None

# --- タブ1: 著者 ---
with tab1:
    if len(df) > 0:
        # 著者をスペース区切りで連結
        text_author = " ".join(df['著者'].dropna().astype(str).tolist())
        fig_wc1 = generate_wordcloud(text_author)
        if fig_wc1:
            st.pyplot(fig_wc1)
        else:
            st.error("フォントが見つからない等のエラーです。コード内の font_path を確認してください。")

# --- タブ2: カテゴリ ---
with tab2:
    if len(df) > 0:
        text_category = " ".join(df['カテゴリ'].dropna().astype(str).tolist())
        fig_wc2 = generate_wordcloud(text_category)
        if fig_wc2: st.pyplot(fig_wc2)

# --- タブ3: タイトル単語 (Janomeで解析) ---
with tab3:
    if len(df) > 0:
        with st.spinner('タイトルを解析中...'):
            t = Tokenizer()
            words = []
            # 除外したい一般的な単語
            stop_words = ['の', 'に', 'は', 'を', 'た', 'て', 'と', 'が', 'で', '巻', '版', '上', '下', '1', '2', '3']

            for title in df['タイトル'].dropna():
                tokens = t.tokenize(title)
                for token in tokens:
                    # 名詞だけを抽出
                    if token.part_of_speech.split(',')[0] == '名詞':
                        if token.surface not in stop_words and len(token.surface) > 1: # 1文字は除外
                            words.append(token.surface)
            
            text_title = " ".join(words)
            fig_wc3 = generate_wordcloud(text_title)
            if fig_wc3: st.pyplot(fig_wc3)