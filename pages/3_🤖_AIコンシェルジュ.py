import streamlit as st
import pandas as pd
import google.generativeai as genai 

st.set_page_config(page_title="AIコンシェルジュ", layout="wide")

# --- 設定 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("secrets.toml に GEMINI_API_KEY が設定されていません")
    st.stop()

# --- データ読み込み ---
try:
    col_names = ["サービスID", "アイテムID", "13桁ISBN", "カテゴリ", "評価", "読書状況", "レビュー", "タグ", "読書メモ(非公開)", "登録日時", "読了日", "タイトル", "作者名", "出版社名", "発行年", "タイプ", "ページ数"]
    df = pd.read_csv('reading_log.csv', encoding='cp932', header=None, names=col_names, dtype={'13桁ISBN': str})
    if '作者名' in df.columns: df = df.rename(columns={'作者名': '著者'})
    df = df.dropna(subset=['タイトル'])
except Exception: st.stop()

# --- メイン表示 ---
st.title('🤖 AIコンシェルジュ')
st.markdown("あなたの読書履歴を分析して、Geminiがおすすめの本を提案します。")

genai.configure(api_key=api_key)
        
if st.button("✨ おすすめ本TOP5を聞く", type="primary"):
    with st.spinner('Gemini 2.5 Flash があなたの全読書データを分析中...'):
        try:
            # データの準備
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
            {fav_text}
            
            【既読リスト（絶対に提案しないでください）】
            {all_read_text}
            
            【依頼内容】
            上記を踏まえ、私がまだ読んでいなさそうで、かつ好みにドンピシャな本を5冊選んでください。
            出力はMarkdownの表形式（カラム：書籍名、著者名、推薦理由）でお願いします。
            """
            
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            
            st.success("分析完了！こちらがおすすめです👇")
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")