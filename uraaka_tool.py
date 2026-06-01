import streamlit as st
from openai import OpenAI
import pandas as pd
from datetime import datetime
import io
import re
import random

st.set_page_config(
    page_title="裏垢女子変換ツール",
    page_icon="🎀",
    layout="wide"
)

st.title("🎀 裏垢女子ツイート → AI画像生成プロンプト変換ツール")

# ============================================================
# セッション状態の初期化
# ============================================================
if "tweets" not in st.session_state:
    st.session_state.tweets = None
if "prompts" not in st.session_state:
    st.session_state.prompts = None

# ============================================================
# サイドバー
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
        MODEL = st.selectbox("使用モデル", ["grok-4-1-fast-reasoning", "grok-4-1-fast-non-reasoning"], index=0)
        st.success("✓ 接続完了")
    else:
        st.error("APIキーが正しくありません")
        st.stop()
    
    st.divider()
    
    num_tweets = st.slider("ツイート数", 2, 6, 4)
    
    st.subheader("📏 文字数")
    length_option = st.select_slider("目安", options=["30-50文字", "50-80文字", "80-120文字"], value="50-80文字")
    
    st.subheader("🛡️ シャドウバン対策")
    safety = st.select_slider("レベル", options=["セーフ", "ライト", "ギリギリ"], value="ライト")
    
    safety_map = {
        "セーフ": "fully clothed, casual wear, completely safe",
        "ライト": "loungewear or underwear, no nudity, implied only",
        "ギリギリ": "lingerie, covering private areas, suggestive"
    }

# ============================================================
# メイン
# ============================================================
st.header("👤 キャラクター設定")

st.caption("例：22歳、Fカップ、彼氏いない歴22年、メガネ、ブサイク")

character = st.text_area(
    "特徴を書いてください",
    height=80,
    placeholder="例：22歳、Fカップ、彼氏いない歴22年、メガネ、ブサイク"
)

if not character:
    st.info("👆 特徴を入力してください")
    st.stop()

# ============================================================
# ツイート生成
# ============================================================
st.markdown("---")
st.header("📝 ツイート生成")

if st.button("✨ ツイートを生成する", type="primary", use_container_width=True):
    with st.spinner("生成中..."):
        random_seed = random.randint(1, 999999)
        
        prompt = f"""以下の特徴を持つ女性のツイートを{num_tweets}個作ってください。

特徴：{character}

ルール：
- 各ツイートは{length_option}
- 文の終わり（「。」「！」「？」）の後は改行する
- 「写真」「撮影」「カメラ」という言葉は使わない
- 全てのツイートを違う内容にする

では、{num_tweets}個のツイートを出力してください。
乱数シード: {random_seed}"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.4,
            max_tokens=1000
        )
        
        raw = response.choices[0].message.content
        
        # ツイート抽出
        tweets = []
        for line in raw.split('\n'):
            line = line.strip()
            if line and len(line) > 10 and not line.startswith('例'):
                tweets.append(line)
        
        tweets = tweets[:num_tweets]
        
        if not tweets:
            st.error("ツイートを生成できませんでした。もう一度お試しください。")
        else:
            st.session_state.tweets = tweets
            st.success(f"{len(tweets)}件のツイートを生成しました")

# ツイート表示
if st.session_state.tweets:
    st.subheader("✏️ ツイート（編集可能）")
    edited = []
    for i, t in enumerate(st.session_state.tweets):
        new_t = st.text_area(f"ツイート {i+1}", t, key=f"t_{i}", height=120)
        edited.append(new_t)
    st.session_state.tweets = edited

# ============================================================
# プロンプト変換
# ============================================================
if st.session_state.tweets:
    st.markdown("---")
    st.header("🎨 英語プロンプトに変換")
    
    if st.button("🔄 プロンプト変換", type="primary", use_container_width=True):
        prompts = []
        progress_bar = st.progress(0)
        
        for i, tweet in enumerate(st.session_state.tweets):
            p = f"""以下のツイートからAI画像生成用の英語プロンプトを1つ作成してください。

ツイート：{tweet}

キャラクター：{character}

必須要素：
- iPhone自撮り、手ブレ、ピンボケ
- 鏡に写るスマホ構図
- 下着や部屋着、家の中の散らかり
- 恥ずかしそうな表情、リアルな肌質

禁止ワード：cafe, studio, perfect, clean, explicit, porn, naked, genitals, beautiful, elegant

安全レベル：{safety_map[safety]}

英語のみ、80語以内、1行で出力してください。"""
            
            res = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": p}],
                temperature=0.9,
                max_tokens=400
            )
            prompts.append(res.choices[0].message.content.strip())
            progress_bar.progress((i + 1) / len(st.session_state.tweets))
        
        st.session_state.prompts = prompts
        st.success("変換完了")
    
    if st.session_state.prompts:
        st.subheader("✏️ プロンプト（編集可能）")
        edited_prompts = []
        for i, (t, p) in enumerate(zip(st.session_state.tweets, st.session_state.prompts)):
            with st.expander(f"ツイート{i+1}", expanded=False):
                st.caption(f"元：{t[:80]}...")
                new_p = st.text_area(f"プロンプト {i+1}", p, key=f"p_{i}", height=120)
                edited_prompts.append(new_p)
        st.session_state.prompts = edited_prompts

# ============================================================
# CSV出力
# ============================================================
if st.session_state.tweets and st.session_state.prompts:
    st.markdown("---")
    st.header("💾 データ出力")
    
    df = pd.DataFrame({
        "キャラクター": [character] * len(st.session_state.tweets),
        "ツイート": st.session_state.tweets,
        "プロンプト": st.session_state.prompts,
        "日時": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] * len(st.session_state.tweets)
    })
    
    st.dataframe(df, use_container_width=True)
    
    csv = io.StringIO()
    df.to_csv(csv, index=False, encoding="utf-8-sig")
    st.download_button("📥 CSVダウンロード", csv.getvalue(), f"uraaka_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv", use_container_width=True)

st.markdown("---")
st.caption("Grok API使用 | プロンプトをHiggsfield/ImageFXに貼り付けてください")
