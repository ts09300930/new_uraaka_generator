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
    2. **キャラクター設定**を簡潔に入力
    3. **ツイート生成** → 裏垢女子っぽいツイートが出力
    4. **プロンプト変換** → 画像生成用英語プロンプトを生成
    5. **CSV出力** → データを保存
    6. プロンプトを**HiggsfieldやImageFXに貼り付け**
    """)

# ============================================================
# サイドバー：API設定
# ============================================================
with st.sidebar:
    st.header("🔑 API設定")
    
    if "XAI_API_KEY" in st.secrets:
        api_key = st.secrets["XAI_API_KEY"]
        st.success("✓ APIキー読み込み完了")
    else:
        api_key = st.text_input("Grok APIキー (xai-で始まります)", type="password")
    
    if not api_key:
        st.warning("APIキーを入力してください")
        st.stop()
    
    if api_key.startswith("xai-"):
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        
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
    
    st.header("⚙️ 設定")
    num_tweets = st.slider("生成するツイート数", 2, 8, 4)
    
    st.subheader("📏 ツイートの長さ")
    tweet_length_option = st.select_slider(
        "文字数の目安",
        options=["短め（30〜50文字）", "普通（50〜80文字）", "長め（80〜120文字）"],
        value="普通（50〜80文字）"
    )
    
    length_map = {
        "短め（30〜50文字）": "30〜50文字",
        "普通（50〜80文字）": "50〜80文字",
        "長め（80〜120文字）": "80〜120文字"
    }
    target_length = length_map[tweet_length_option]
    
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
# メインエリア：キャラクター設定
# ============================================================
st.header("👤 キャラクター設定（簡潔でOK）")

st.caption("例：22歳、Fカップ、彼氏いない歴22年、メガネ、ブサイク")

character_input = st.text_area(
    "特徴を書いてください",
    height=100,
    placeholder="例：22歳、Fカップ、彼氏いない歴22年、メガネ、ブサイク"
)

if not character_input:
    st.info("👆 上の欄にキャラクター特徴を入力してください")
    st.stop()

full_character_traits = f"""
【ユーザー設定】
{character_input}
"""

# ============================================================
# ツイート生成関数（完全修正版）
# ============================================================
def generate_tweets():
    # システムプロンプト（厳格なルール）
    system_prompt = f"""あなたは日本語のツイート生成AIです。以下のルールを絶対に守ってください。

【必須ルール】
1. ツイートの長さは{target_length}にすること
2. 改行は「。」「！」「？」の直後に入れること。文章の途中で改行してはいけない
3. 句点ごとに改行すること。例：「○○です。△△です。□□です。」→ 3行に分ける
4. 「撮影」「写真」「iPhone」「カメラ」という単語を絶対に使わない
5. 「見られたく」「見せたい」という表現を絶対に使わない
6. すべてのツイートを異なる内容にする（同じパターンを繰り返さない）
7. 数字や箇条書き記号を絶対に使わない
8. 「」は使わない

【正しい出力例】
○○です。
△△です。
□□です。

【絶対にやってはいけない出力例】
○○です。△△です。□□です。（改行なし）
○○で
す。△△で
す。（途中改行）"""

    user_prompt = f"""以下の特徴を持つ裏垢女子のツイートを{num_tweets}個生成してください。

{full_character_traits}

以下の形式で出力してください：

ツイート1:
（本文）

ツイート2:
（本文）

ツイート3:
（本文）

ツイート4:
（本文）"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=1.3,
        max_tokens=1000
    )
    
    raw = response.choices[0].message.content
    
    # ツイート抽出
    tweets = []
    for line in raw.split('\n'):
        if re.match(r'^ツイート\d+:', line):
            tweet_text = re.sub(r'^ツイート\d+:', '', line).strip()
            if tweet_text:
                tweets.append(tweet_text)
        elif tweets and line.strip() and not line.strip().startswith('ツイート'):
            # 前のツイートに追記（複数行の場合）
            tweets[-1] = tweets[-1] + " " + line.strip()
    
    # 空のツイートを除去
    tweets = [t for t in tweets if t and len(t) > 10]
    
    # 指定数に調整
    if len(tweets) < num_tweets:
        # 足りない場合は補完
        for i in range(len(tweets), num_tweets):
            tweets.append(tweets[i % len(tweets)] if tweets else "さみしい。誰か来てほしい。")
    
    return tweets[:num_tweets]

# ============================================================
# プロンプト変換関数
# ============================================================
def tweet_to_prompt(tweet):
    safety_instruction = safety_map[safety_level]
    
    prompt = f"""以下のツイートから、AI画像生成用の英語プロンプトを1つ作成してください。

【ツイート】
{tweet}

【キャラクター】
{character_input}

【必須要素】
- iPhoneで撮影した自撮り、手ブレやピンボケ、鏡に写るスマホ構図
- 下着や部屋着程度の露出、家の中の生活感（散らかり）
- 恥ずかしそうな表情、リアルな肌質（加工なし）

【禁止ワード】
convenience store, cafe, coffee shop, studio, perfectly tidy, explicit, porn, naked, genitals, hardcore, beautiful, elegant, perfect, minimalist, clean

【シャドウバン対策】
{safety_instruction}

【出力】英語のみ、80語以内、カンマ区切り1行、禁止ワード不使用"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=400
    )
    
    return response.choices[0].message.content.strip()

# ============================================================
# UI: ステップ1
# ============================================================
st.markdown("---")
st.header("📝 ステップ1：ツイート生成")

if st.button("✨ ツイートを生成する", type="primary", use_container_width=True):
    with st.spinner("生成中..."):
        tweets = generate_tweets()
        st.session_state.tweets = tweets
        st.success(f"{len(tweets)}件のツイートを生成しました")

if "tweets" in st.session_state:
    st.subheader("✏️ 生成されたツイート（編集可能）")
    edited_tweets = []
    cols = st.columns(2)
    
    for i, tweet in enumerate(st.session_state.tweets):
        col_idx = i % 2
        with cols[col_idx]:
            edited = st.text_area(
                f"ツイート {i+1}",
                tweet,
                key=f"tweet_edit_{i}",
                height=150
            )
            edited_tweets.append(edited)
    
    st.session_state.tweets = edited_tweets

# ============================================================
# UI: ステップ2
# ============================================================
if "tweets" in st.session_state and st.session_state.tweets:
    st.markdown("---")
    st.header("🎨 ステップ2：英語プロンプトに変換")
    
    if st.button("🔄 プロンプトに変換する", type="primary", use_container_width=True):
        prompts = []
        progress_bar = st.progress(0)
        
        for i, tweet in enumerate(st.session_state.tweets):
            prompt = tweet_to_prompt(tweet)
            prompts.append(prompt)
            progress_bar.progress((i + 1) / len(st.session_state.tweets))
        
        st.session_state.prompts = prompts
        st.success(f"{len(prompts)}件のプロンプトを生成しました")
    
    if "prompts" in st.session_state:
        st.subheader("✏️ 生成された英語プロンプト（編集可能）")
        edited_prompts = []
        cols = st.columns(2)
        
        for i, (tweet, prompt) in enumerate(zip(st.session_state.tweets, st.session_state.prompts)):
            col_idx = i % 2
            with cols[col_idx]:
                with st.expander(f"ツイート{i+1}", expanded=False):
                    st.caption(f"元: {tweet[:80]}...")
                    edited = st.text_area(
                        f"プロンプト {i+1}",
                        prompt,
                        key=f"prompt_edit_{i}",
                        height=150
                    )
                    edited_prompts.append(edited)
        
        st.session_state.prompts = edited_prompts

# ============================================================
# CSV出力
# ============================================================
if "tweets" in st.session_state and "prompts" in st.session_state:
    st.markdown("---")
    st.header("💾 ステップ3：データ出力")
    
    df = pd.DataFrame({
        "キャラクター設定": [character_input] * len(st.session_state.tweets),
        "ツイート本文": st.session_state.tweets,
        "英語プロンプト": st.session_state.prompts,
        "セーフティレベル": [safety_level] * len(st.session_state.tweets),
        "生成日時": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] * len(st.session_state.tweets)
    })
    
    st.dataframe(df, use_container_width=True)
    
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
    
    with col2:
        st.markdown("**📋 Higgsfield貼り付け用**")
        for i, prompt in enumerate(st.session_state.prompts):
            st.code(f"【{i+1}】\n{prompt}", language="text")

st.markdown("---")
st.caption("💡 Grok API使用。生成したプロンプトをHiggsfieldやImageFXに貼り付けてください。")
