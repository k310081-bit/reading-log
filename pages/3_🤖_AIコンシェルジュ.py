import streamlit as st
import pandas as pd
# --- 追加：GSheets用のインポート ---
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai 
from datetime import datetime, timedelta

st.set_page_config(page_title="AIコンシェルジュ", layout="wide")

# --- 設定 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("secrets.toml に GEMINI_API_KEY が設定されていません")
    st.stop()

# --- 1. スプレッドシート接続設定 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- データ読み込み (過去の読書履歴) ---
try:
    col_names = ["サービスID", "アイテムID", "13桁ISBN", "カテゴリ", "評価", "読書状況", "レビュー", "タグ", "読書メモ(非公開)", "登録日時", "読了日", "タイトル", "作者名", "出版社名", "発行年", "タイプ", "ページ数"]
    # 履歴データは引き続きローカルCSVを参照（分析用）
    df = pd.read_csv('reading_log.csv', encoding='cp932', header=None, names=col_names, dtype={'13桁ISBN': str})
    if '作者名' in df.columns: df = df.rename(columns={'作者名': '著者'})
    if '13桁ISBN' in df.columns: df = df.rename(columns={'13桁ISBN': 'ISBN'})
    
    if 'ISBN' in df.columns:
        df['ISBN'] = df['ISBN'].astype(str).str.replace(r'\.0$', '', regex=True)

    df = df.dropna(subset=['タイトル'])
    df['読了日'] = pd.to_datetime(df['読了日'], errors='coerce')
    
except Exception as e:
    st.error(f"過去のデータ読み込みエラー: {e}")
    st.stop()

# --- メイン表示 ---
st.title('🤖 AIコンシェルジュ')
st.markdown("あなたの読書データをもとに、Geminiが最適な本を提案します。")

genai.configure(api_key=api_key)

# --- 🎯 モード選択UI ---
st.markdown("### どのような提案をご希望ですか？")

mode = st.radio(
    "コースを選択してください",
    [
        "👑 王道のTOP5（全履歴から）",
        "🔥 直近の関心TOP5（ここ1年の履歴から）",
        "🌌 深掘りと冒険（好きなおすすめ5選 ＋ 世界を広げる5選）",
        "📚 ジャンル指定おすすめ（特定のジャンルに絞る）"
    ],
    index=0
)

target_genre = ""
if "ジャンル指定" in mode:
    target_genre = st.selectbox(
        "どのジャンルの本を探しますか？",
        ["小説・フィクション", "ビジネス・経済", "実用書・自己啓発", "その他（科学、歴史、哲学など上記以外）"]
    )

st.markdown("---")

# --- 分析実行ボタン ---
if st.button("✨ この条件でおすすめを聞く", type="primary"):
    target_df = df.copy()
    if "直近" in mode:
        one_year_ago = datetime.now() - timedelta(days=365)
        target_df = target_df[target_df['読了日'] >= one_year_ago]
        if len(target_df) < 5:
            st.warning("⚠️ 直近1年の読書データが少なすぎるため、全期間のデータを使用します。")
            target_df = df.copy()

    fav_books = target_df.sort_values('評価', ascending=False).head(30)
    fav_text = ""
    for index, row in fav_books.iterrows():
        fav_text += f"- {row['タイトル']} (著者: {row['著者']})\n"

    all_read_titles = df['タイトル'].unique().tolist()
    all_read_text = ", ".join(map(str, all_read_titles))

    base_prompt = f"""
    あなたは熟練のブックコンシェルジュです。
    私の読書データを分析し、次に読むべき本を提案してください。

    【重要：リンク生成のルール】
    提案する本のタイトルは、必ず以下のMarkdown形式で「Amazon検索結果へのリンク」にしてください。
    形式： [書籍タイトル](https://www.amazon.co.jp/s?k=書籍タイトル+著者名)
    ※URL内のスペースは + に置き換えること。

    【私の読書傾向（高評価の本）】
    {fav_text}

    【既読リスト（提案から除外すること）】
    {all_read_text}
    """

    specific_instruction = ""
    if "王道" in mode:
        specific_instruction = "【依頼内容】好みのど真ん中5冊を提案。表形式で出力。"
    elif "直近" in mode:
        specific_instruction = "【依頼内容】直近1年の傾向から5冊を提案。表形式で出力。"
    elif "深掘りと冒険" in mode:
        specific_instruction = "【依頼内容】「深掘り」5冊と「世界を広げる」5冊、計10冊を提案。表形式で出力。"
    elif "ジャンル指定" in mode:
        specific_instruction = f"【依頼内容】「{target_genre}」のジャンルから5冊を提案。表形式で出力。"

    final_prompt = base_prompt + "\n" + specific_instruction

    with st.spinner('Gemini 2.5 Flash が選書中...'):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(final_prompt)
            st.success("分析完了！")
            st.markdown(response.text)
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

# --- 2. 読みたい本リストへの追加機能 (スプレッドシート連携) ---
st.markdown("---")
st.subheader("🔖 読みたい本リストに追加")

with st.container(border=True):
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        new_title = st.text_input("タイトル（必須）", key="title_input")
    with col_input2:
        new_author = st.text_input("著者名", key="author_input")
    
    new_memo = st.text_area("メモ", placeholder="AIおすすめ理由など")
    
    if st.button("＋ スプレッドシートに保存"):
        if new_title:
            with st.spinner("保存中..."):
                try:
                    # 最新のシートデータを読み込み
                    df_wish = conn.read(ttl=0)
                except:
                    df_wish = pd.DataFrame(columns=["タイトル", "著者", "メモ", "登録日"])
                
                # 新しい行を作成
                new_row = pd.DataFrame([{
                    "タイトル": new_title,
                    "著者": new_author,
                    "メモ": new_memo,
                    "登録日": datetime.now().strftime('%Y/%m/%d')
                }])
                
                # 更新して書き込み
                updated_df = pd.concat([df_wish, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"『{new_title}』を保存しました！")
                st.rerun()
        else:
            st.error("タイトルは必須です")

# --- 3. 現在のリストを表示 (同期確認用) ---
st.markdown("### 📋 現在の「読みたい本」同期中データ")
try:
    current_wish = conn.read(ttl=0)
    if not current_wish.empty:
        # 登録日の新しい順に表示
        current_wish["登録日"] = pd.to_datetime(current_wish["登録日"])
        st.dataframe(current_wish.sort_values("登録日", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("リストは現在空っぽです。")
except:
    st.warning("リストの読み込みに失敗しました。")