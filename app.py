import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import google.generativeai as genai 

# --- 設定・関数定義 ---

st.set_page_config(page_title="My Reading Log", layout="wide")
THEME_COLOR = '#8D6E63' 

# --- メイン処理 ---

st.title('📚 私の読書記録ダッシュボード')

# 1. データの読み込み
try:
    df = pd.read_csv('reading_log.csv')
    df = df.dropna(subset=['タイトル'])
    df = df[df['タイトル'].astype(str).str.strip() != '']
    df = df[df['タイトル'].astype(str) != 'nan']
    df = df[df['タイトル'].astype(str) != 'None']
    df['読了日'] = pd.to_datetime(df['読了日'])
    df['年'] = df['読了日'].dt.year
    df['月'] = df['読了日'].dt.month

    if '著者' not in df.columns and '作者名' in df.columns:
        df = df.rename(columns={'作者名': '著者'})
    
except FileNotFoundError:
    st.error('CSVファイルが見つかりません。')
    st.stop()

# --- サイドバー ---
st.sidebar.header('⚙️ 設定')

# ★ここが変わりました：セキュリティ強化版
# 手動入力欄を廃止し、secrets.toml からのみ読み込みます
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("🔑 認証成功（セキュアモード）")
except FileNotFoundError:
    st.sidebar.error("鍵が見つかりません")
    st.sidebar.info("PCに .streamlit/secrets.toml を作成してください")
    api_key = None # キーがない場合は空にしておく

st.sidebar.markdown("---")
st.sidebar.header('🔍 検索・絞り込み')

unique_categories = df['カテゴリ'].unique()
selected_categories = st.sidebar.multiselect('カテゴリを選択', unique_categories, default=[])
search_author = st.sidebar.text_input('著者名で検索', '')

# フィルタリング
df_display = df.copy()
if len(selected_categories) > 0:
    df_display = df_display[df_display['カテゴリ'].isin(selected_categories)]
if search_author:
    df_display = df_display[df_display['著者'].str.contains(search_author, na=False)]

# --- 実績ビジュアライズ ---
st.markdown("### 🏆 積み上げ実績")

total_books = len(df_display)
total_pages = df_display['ページ数'].sum()
book_height_meter = (total_books * 2.0) / 100 

col1, col2, col3, col4 = st.columns(4)
col1.metric("読んだ冊数", f"{total_books} 冊")
col2.metric("総ページ数", f"{int(total_pages):,} ページ")
col3.metric("積み上げた高さ", f"{book_height_meter:.2f} m")

if book_height_meter < 1.5: comparison = "小学生の身長くらい"
elif book_height_meter < 3: comparison = "バスケットゴールくらい"
elif book_height_meter < 13: comparison = "鎌倉の大仏くらい"
elif book_height_meter < 333: comparison = "ビル・マンション級"
else: comparison = "東京タワー級！"

col4.info(f"これは **{comparison}** です！")
st.markdown("---")

# --- メインコンテンツ ---
left_column, right_column = st.columns([1.2, 1])

with left_column:
    st.subheader('📖 読書リスト')
    target_columns = ['読書状況', 'タイトル', '著者', '出版社名', '発行年', 'カテゴリ', '評価', '読了日', 'ページ数']
    display_cols = [c for c in target_columns if c in df_display.columns]
    
    if len(display_cols) > 0:
        st.dataframe(df_display[display_cols], hide_index=True, height=400)
    else:
        st.warning("表示できる列がありません")

    # --- 🤖 GeminiによるAIレコメンド ---
    st.subheader('🤖 AIコンシェルジュのおすすめ')
    
    if not api_key:
        st.warning("⚠️ サイドバーの鍵設定を確認してください")
    else:
        genai.configure(api_key=api_key)
        
        if st.button("✨ 私の読書傾向を分析して、おすすめ本TOP5を教えて！"):
            with st.spinner('Gemini 2.5 Flash があなたの全読書データを照合中...'):
                try:
                    fav_books = df.sort_values('評価', ascending=False).head(50)
                    fav_text = ""
                    for index, row in fav_books.iterrows():
                        fav_text += f"- {row['タイトル']} (著者: {row['著者']})\n"

                    all_read_titles = df['タイトル'].unique().tolist()
                    all_read_text = ", ".join(map(str, all_read_titles))
                    
                    prompt = f"""
                    あなたはプロのブックコンシェルジュです。
                    私の読書データを元に、まだ読んでいない「おすすめ本」を5冊提案してください。

                    【私の好み（高評価だった本）】
                    以下の本を好んで読みます。この傾向を分析してください。
                    {fav_text}
                    
                    【既読リスト（絶対に提案しないでください）】
                    以下の本はすでに読みました。これらと同一、またはシリーズ続編などで私が既に読んでいる可能性が高い本は提案から除外してください。
                    （多少の表記揺れがあっても、同じ本だと判断したら除外すること）
                    {all_read_text}
                    
                    【依頼内容】
                    上記を踏まえ、私がまだ読んでいなさそうで、かつ好みにドンピシャな本を5冊選んでください。
                    出力はMarkdownの表形式（カラム：書籍名、著者名、推薦理由）でお願いします。
                    """
                    
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(prompt)
                    
                    st.success("分析完了！既読を除外したおすすめはこちらです👇")
                    st.markdown(response.text)
                    
                except Exception as e:
                    if "429" in str(e):
                        st.error("⚠️ AIへのリクエストが集中しています。1分ほど待ってからもう一度押してください。")
                    else:
                        st.error(f"エラーが発生しました: {e}")

with right_column:
    st.subheader('📊 年ごとの読書ペース')
    years_list = sorted(df_display['年'].dropna().astype(int).unique(), reverse=True)

    if len(years_list) > 0:
        monthly_max = df_display.groupby(['年', '月']).size().max()
        y_axis_max = monthly_max + 2

        selected_year = st.selectbox('表示する年を選択', years_list, index=0)
        df_year = df_display[df_display['年'] == selected_year]
        
        monthly_counts = pd.Series(0, index=range(1, 13))
        actual_counts = df_year['月'].value_counts()
        monthly_counts.update(actual_counts)

        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(monthly_counts.index, monthly_counts.values, color=THEME_COLOR)
        
        ax.set_title(f'{selected_year}年の読書冊数推移', fontsize=12)
        ax.set_xlabel('月')
        ax.set_ylabel('冊数')
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels([f"{m}月" for m in range(1, 13)])
        ax.set_ylim(0, y_axis_max)
        ax.grid(axis='y', linestyle='--', alpha=0.5)

        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}', ha='center', va='bottom')

        st.pyplot(fig)
        st.caption(f"📅 {selected_year}年の合計: **{len(df_year)}冊**")
    else:
        st.info("データがありません")