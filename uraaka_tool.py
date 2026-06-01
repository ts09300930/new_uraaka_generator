import streamlit as st
from openai import OpenAI
import pandas as pd
from datetime import datetime
import io
import re

st.set_page_config(
    page_title="裏垢女子変換ツール",
    page_icon="🎀",
    layout="wide"
)

# ============================================================
# タイトルと説明
# ============================================================
st.title("🎀 裏垢女子ツイート → AI画像生成プロンプト変換ツール")
st.markdown("---")

with st.expander("📖 使い方", expanded=False):
    st.markdown("""
    1. **Grok APIキー**を入力（サイドバー）
    2. **キャラクター設定**を簡潔に入力（例：32歳シングルマザー、Fカップ、小学生の娘）
    3. **ツイート生成** → 自動で裏垢女子っぽいツイートが出力
    4. **プロンプト変換** → 各ツイートから画像生成用英語プロンプトを生成
    5. **CSV出力** → データを保存
    6. プロンプトを**HiggsfieldやImageFXに貼り付け**
    """)

# ============================================================
# サイドバー：API設定
# ============================================================
with st.sidebar:
    st.header("🔑 API設定")
    
    # シークレットまたは直接入力
    if "XAI_API_KEY" in st.secrets:
        api_key = st.secrets["XAI_API_KEY"]
        st.success("✓ APIキー読み込み完了")
    else:
        api_key = st.text_input("Grok APIキー (xai-で始まります)", type="password")
    
    if not api_key:
        st.warning("APIキーを入力してください")
        st.stop()
    
    # Grok API設定
    if api_key.startswith("xai-"):
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        
        # モデル選択（あなたの環境で動いているもの）
        model_options = [
            "grok-4-1-fast-reasoning",
            "grok-4-1-fast-non-reasoning",
            "grok-4-fast-reasoning",
            "grok-4"
        ]
        MODEL = st.selectbox("使用モデル", model_options, index=0)
        
        st.success(f"✓ Grok API接続準備完了（{MODEL}）")
    else:
        st.error("APIキーは xai- で始まる必要があります")
        st.stop()
    
    st.divider()
    
    # 生成設定
    st.header("⚙️ 設定")
    num_tweets = st.slider("生成するツイート数", 2, 8, 4)
    
    # 文字数設定（追加）
    st.subheader("📏 ツイートの長さ")
    tweet_length_option = st.select_slider(
        "文字数の目安",
        options=["短め（30〜50文字）", "普通（50〜80文字）", "長め（80〜120文字）"],
        value="長め（80〜120文字）"
    )
    
    length_map = {
        "短め（30〜50文字）": "30〜50文字",
        "普通（50〜80文字）": "50〜80文字",
        "長め（80〜120文字）": "80〜120文字"
    }
    target_length = length_map[tweet_length_option]
    
    # シャドウバン対策レベル
    st.subheader("🛡️ シャドウバン対策")
    safety_level = st.select_slider(
        "露出セーフティレベル",
        options=["セーフ", "ライト", "ギリギリ"],
        value="ライト"
    )
    
    safety_map = {
        "セーフ": "fully clothed, casual wear, no skin below shoulders, completely Twitter safe, SFW",
        "ライト": "loungewear or underwear allowed, no nipples or genitals visible, implied only, Twitter safe",
        "ギリギリ": "lingerie allowed, covering private areas with hands/objects, suggestive but still platform safe"
    }

# ============================================================
# 自動補完される裏垢女子基本要素（ユーザーが書かなくていい）
# ============================================================
AUTO_IMPLICIT_TRAITS = """
【以下の特徴は自動的にツイートとプロンプトに反映されます】
- iPhoneで自撮りしている
- 写真は手ブレやピンボケがある（プロっぽくない）
- 鏡に写るスマホ構図をよく使う
- 露出は下着や部屋着程度まで
- 恥ずかしがりながらも誘ってしまうタイプ
- 肌は加工しすぎないリアルな質感
- 家の中は散らかっていることが多い
"""

# ============================================================
# メインエリア：キャラクター設定
# ============================================================
st.header("👤 キャラクター設定（簡潔でOK）")

st.caption("例：32歳シングルマザー、Fカップ、小学生の娘がいる、性欲の捌け口がないのがコンプレックス")

character_input = st.text_area(
    "特徴を書いてください",
    height=100,
    placeholder="例：32歳シングルマザー、Fカップ、小学生の娘がいる、性欲の捌け口がないのがコンプレックス"
)

if not character_input:
    st.info("👆 上の欄にキャラクター特徴を入力してください")
    st.stop()

# ユーザー入力 + 自動補完を結合
full_character_traits = f"""
【ユーザー設定】
{character_input}

【自動適用（あなたが書かなくても常に追加）】
{AUTO_IMPLICIT_TRAITS}
"""

# ============================================================
# ツイート生成用プロンプト（修正版：文字数制御 + 具体性）
# ============================================================
def generate_tweets():
    prompt = f"""
あなたは以下の特徴を持つ「裏垢女子」です。

{full_character_traits}

【タスク】
{num_tweets}個の「ふと漏れた一言」のようなツイートを生成してください。

【厳守ルール】
1. **1ツイートあたり {target_length} を厳守**
2. **必ず2〜4回の改行を入れる**（文中でもどんどん改行して「息継ぎ」している感じを出す）
3. 改行の例：
   「手ブレ写真じゃなくて、
   本当の私を見てほしい。
   
   家の中ぐちゃぐちゃだけど、
   それでもいいって人、いない？」
   
   「Fカップ、
   邪魔でしかない。
   
   誰か来てくれないかな。
   おもちゃ散らかってるけど気にしないで。」

4. **「撮影している描写」を絶対に入れない**（×：iPhoneで撮った、自撮りした、写した）
5. **代わりに「その瞬間の感情・状況・欲求」を書く**
6. 説明文ではなく「独り言・ぼやき・誰かへの呼びかけ」の形式
7. 以下の要素を自然に含める：
   - 具体的な状況（家の様子・子供の存在・時間帯・散らかった部屋など）
   - 感情（寂しさ・欲求不満・罪悪感・照れ・自虐）
   - 誰かへの呼びかけや誘い

【具体例（この改行の感じを忠実に再現）】
「小学生女児の娘がいるママだけど、
会える男の人探してます。

結婚はしていません。
シングルマザーなので安心してください。

うちは娘のオモチャとかあって生活感があるけど、
それでも良ければ遊びに来てください。
お泊まりOKです。」

【絶対にやらないこと】
- 「今日は〜でした」という日記形式
- 「撮影した」「写した」「カメラ」「iPhoneで」などの撮影描写
- 同じパターンの繰り返し
- 過激な表現

【出力形式（細かい改行を必ず入れる）】
###1
1行目
2行目

3行目
4行目

###2
1行目
2行目

3行目

...（{num_tweets}個まで）
"""
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=1.3,
        max_tokens=1500
    )
    
    raw = response.choices[0].message.content
    
    # ツイートを抽出（改行を保持）
    tweets = []
    for block in raw.split("###"):
        block = block.strip()
        if block and not block.startswith(" "):
            tweets.append(block)
    
    return tweets[:num_tweets]


# ============================================================
# プロンプト変換用（裏垢女子っぽさ＋シャドウバン対策）
# ============================================================
def tweet_to_prompt(tweet, index):
    safety_instruction = safety_map[safety_level]
    
    prompt = f"""
以下の裏垢女子のツイートから、AI画像生成用の英語プロンプトを1つだけ作成してください。

【ツイート】
{tweet}

【キャラクター特徴】
{full_character_traits}

【必須要素（必ず入れる）】
- iPhoneで撮影した自撮り写真
- 手ブレやピンボケがある（完璧じゃない）
- 鏡に写るスマホ構図を意識
- 下着や部屋着程度の露出
- 家の中の生活感（散らかり、日常的な小物）
- 恥ずかしそうな表情や仕草
- リアルな肌質（肌荒れやクマも含めて自然）

【絶対に入れない要素（禁止ワード）】
- convenience store, cafe, coffee shop, studio, perfectly tidy
- explicit, porn, naked, genitals, hardcore, XXX
- beautiful, elegant, perfect, minimalist, clean

【シャドウバン対策】
{safety_instruction}

【出力ルール】
- 英語のみ
- 80語以内
- カンマで区切られた1行のプロンプト
- 禁止ワード絶対不使用
"""
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=400
    )
    
    return response.choices[0].message.content.strip()

# ============================================================
# UI: ステップ1 ツイート生成
# ============================================================
st.markdown("---")
st.header("📝 ステップ1：ツイート生成")

if st.button("✨ ツイートを生成する", type="primary", use_container_width=True):
    with st.spinner("Grok APIでツイート生成中..."):
        tweets = generate_tweets()
        st.session_state.tweets = tweets
        st.success(f"{len(tweets)}件のツイートを生成しました")

# ツイート表示・編集
if "tweets" in st.session_state:
    st.subheader("✏️ 生成されたツイート（編集可能）")
    edited_tweets = []
    for i, tweet in enumerate(st.session_state.tweets):
        edited = st.text_area(f"ツイート {i+1}", tweet, key=f"tweet_edit_{i}", height=100)
        edited_tweets.append(edited)
    st.session_state.tweets = edited_tweets

# ============================================================
# UI: ステップ2 プロンプト変換
# ============================================================
if "tweets" in st.session_state and st.session_state.tweets:
    st.markdown("---")
    st.header("🎨 ステップ2：英語プロンプトに変換")
    st.caption("各ツイートから、Higgsfield/ImageFXに貼り付ける用の英語プロンプトを生成します")
    
    if st.button("🔄 プロンプトに変換する", type="primary", use_container_width=True):
        prompts = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, tweet in enumerate(st.session_state.tweets):
            status_text.text(f"変換中... ({i+1}/{len(st.session_state.tweets)})")
            prompt = tweet_to_prompt(tweet, i)
            prompts.append(prompt)
            progress_bar.progress((i + 1) / len(st.session_state.tweets))
        
        status_text.text("完了！")
        st.session_state.prompts = prompts
        st.success(f"{len(prompts)}件のプロンプトを生成しました")
    
    # プロンプト表示・編集
    if "prompts" in st.session_state:
        st.subheader("✏️ 生成された英語プロンプト（編集可能）")
        edited_prompts = []
        for i, (tweet, prompt) in enumerate(zip(st.session_state.tweets, st.session_state.prompts)):
            with st.expander(f"ツイート{i+1} → プロンプト", expanded=False):
                st.caption(f"元ツイート: {tweet}")
                edited = st.text_area(f"プロンプト {i+1}", prompt, key=f"prompt_edit_{i}", height=100)
                edited_prompts.append(edited)
        st.session_state.prompts = edited_prompts

# ============================================================
# CSV出力
# ============================================================
if "tweets" in st.session_state and "prompts" in st.session_state:
    st.markdown("---")
    st.header("💾 ステップ3：データ出力")
    
    # データフレーム作成
    df = pd.DataFrame({
        "キャラクター設定": [character_input] * len(st.session_state.tweets),
        "ツイート本文": st.session_state.tweets,
        "英語プロンプト": st.session_state.prompts,
        "セーフティレベル": [safety_level] * len(st.session_state.tweets),
        "生成日時": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] * len(st.session_state.tweets)
    })
    
    st.dataframe(df, use_container_width=True)
    
    # CSVダウンロード
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv_buffer.getvalue(),
            file_name=f"uraaka_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    # プロンプトだけをコピーしやすい形で表示
    with col2:
        st.markdown("**📋 Higgsfield貼り付け用**")
        for i, prompt in enumerate(st.session_state.prompts):
            st.code(f"【{i+1}】\n{prompt}", language="text")

# ============================================================
# フッター
# ============================================================
st.markdown("---")
st.caption("💡 このツールはGrok APIを使用しています。生成したプロンプトはHiggsfieldやImageFXに貼り付けてお使いください。")
