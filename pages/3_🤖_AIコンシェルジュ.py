import streamlit as st
import pandas as pd
import google.generativeai as genai 
from datetime import datetime, timedelta

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
    if '13桁ISBN' in df.columns: df = df.rename(columns={'13桁ISBN': 'ISBN'})
    
    # ISBNのクリーニング
    if 'ISBN' in df.columns:
        df['ISBN'] = df['ISBN'].astype(str).str.replace(r'\.0$', '', regex=True)

    df = df.dropna(subset=['タイトル'])
    df['読了日'] = pd.to_datetime(df['読了日'], errors='coerce')
    
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
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

# ジャンル指定が選ばれた時だけ表示するサブメニュー
target_genre = ""
if "ジャンル指定" in mode:
    target_genre = st.selectbox(
        "どのジャンルの本を探しますか？",
        ["小説・フィクション", "ビジネス・経済", "実用書・自己啓発", "その他（科学、歴史、哲学など上記以外）"]
    )

st.markdown("---")

# --- 分析実行ボタン ---
if st.button("✨ この条件でおすすめを聞く", type="primary"):
    
    # 1. データの事前フィルタリング（モードごとのデータ準備）
    target_df = df.copy()
    
    # 「直近1年」モードの場合、データを最近のものに絞る
    if "直近" in mode:
        one_year_ago = datetime.now() - timedelta(days=365)
        target_df = target_df[target_df['読了日'] >= one_year_ago]
        if len(target_df) < 5:
            st.warning("⚠️ 直近1年の読書データが少なすぎるため、全期間のデータを使用します。")
            target_df = df.copy()

    # 高評価の本を抽出（AIへのインプット用）
    fav_books = target_df.sort_values('評価', ascending=False).head(30)
    fav_text = ""
    for index, row in fav_books.iterrows():
        fav_text += f"- {row['タイトル']} (著者: {row['著者']})\n"

    # 既読除外リスト（全期間から作成）
    all_read_titles = df['タイトル'].unique().tolist()
    all_read_text = ", ".join(map(str, all_read_titles))

    # 2. プロンプトの組み立て
    # ★ここに「Amazonリンクを作れ」という指示を追加しました
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

    # モード別の追加指示
    specific_instruction = ""
    
    if "王道" in mode:
        specific_instruction = """
        【依頼内容】
        私の好みを深く分析し、私が「これこれ、こういうのが読みたかった！」と膝を打つような、
        ドンピシャのおすすめ本を5冊選んでください。
        出力形式：Markdownの表（タイトル(リンク付き)、著者、推薦理由）
        """

    elif "直近" in mode:
        specific_instruction = """
        【依頼内容】
        これは私の「直近1年間」の読書記録です。今の私のブームや関心事を分析してください。
        「今の私」に刺さる、最新の関心に沿ったおすすめ本を5冊選んでください。
        出力形式：Markdownの表（タイトル(リンク付き)、著者、推薦理由）
        """

    elif "深掘りと冒険" in mode:
        specific_instruction = """
        【依頼内容】
        2つの方向性で合計10冊提案してください。

        1. **「深掘り」おすすめ（5冊）**
           私の好みのど真ん中で、外さない鉄板の5冊。
           
        2. **「世界を広げる」おすすめ（5冊）**
           あえて私の普段の傾向とは少し違うが、私の好みの文脈から推測すると「実はハマりそう」なジャンルや、
           食わず嫌いをしているかもしれない名著、あるいは全く新しい視点を与えてくれる本（Novelty）を選んでください。
           「こんな本もアリかも？」と思わせる提案をお願いします。

        出力形式：それぞれのカテゴリごとにMarkdownの表（タイトル(リンク付き)、著者、推薦理由）を作成してください。
        """

    elif "ジャンル指定" in mode:
        specific_instruction = f"""
        【依頼内容】
        私の好みの傾向を踏まえた上で、**「{target_genre}」** のジャンルの中からおすすめ本を5冊選んでください。
        
        ※もし「その他」が指定された場合は、小説やビジネス書以外の、科学・歴史・哲学・エッセイなどから選んでください。
        出力形式：Markdownの表（タイトル(リンク付き)、著者、推薦理由）
        """

    # 最終的なプロンプト
    final_prompt = base_prompt + "\n" + specific_instruction

    # 3. API呼び出し
    with st.spinner('Gemini 2.5 Flash があなたの好みを分析して選書中...'):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(final_prompt)
            
            st.success("分析完了！こちらが選書結果です📚")
            st.markdown(response.text)
            
        except Exception as e:
            if "429" in str(e):
                st.error("⚠️ アクセスが集中しています。少し待ってから再度お試しください。")
            else:
                st.error(f"エラーが発生しました: {e}")

# （...これより上のコードはそのままでOK...）

st.markdown("---")
st.subheader("🔖 読みたい本リストに追加")

# 入力フォーム（サイドバーではなくメイン画面に配置）
with st.container(border=True):
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        new_title = st.text_input("タイトル（必須）", placeholder="おすすめされた本のタイトル")
    with col_input2:
        new_author = st.text_input("著者名", placeholder="著者名")
    
    new_memo = st.text_area("メモ", placeholder="「AIのおすすめ」などのメモや、Amazonリンクなど")
    
    if st.button("＋ リストに追加保存"):
        if new_title:
            # 保存するためのデータを作成
            new_data = pd.DataFrame({
                "タイトル": [new_title],
                "著者": [new_author],
                "メモ": [new_memo],
                "登録日": [datetime.now().strftime('%Y-%m-%d')]
            })
            
            # CSVファイルに「追記モード(mode='a')」で保存
            csv_path = "wishlist.csv"
            
            # ファイルがなければヘッダー付きで新規作成、あればデータだけ追記
            if not os.path.exists(csv_path):
                new_data.to_csv(csv_path, index=False)
            else:
                new_data.to_csv(csv_path, mode='a', header=False, index=False)
            
            st.success(f"『{new_title}』をリストに追加しました！")
        else:
            st.error("タイトルは必須です")