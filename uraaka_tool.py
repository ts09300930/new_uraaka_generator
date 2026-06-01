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

st.title("🎀 裏垢女子ツイート → AI画像生成プロンプト変換ツール")

# ============================================================
# サイドバー
# ============================================================
with st.sidebar:
    st.header("🔑 API設定")
    
    if "XAI_API_KEY" in st.secrets:
        api_key = st.secrets["XAI_API_KEY"]
    else:
        api_key = st.text_input("Grok APIキー", type="password")
    
    if not api_key:
        st.warning("APIキーを入力してください")
        st.stop()
    
    if api_key.startswith("xai-"):
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        MODEL = "grok-4-1-fast-reasoning"
        st.success("✓ 接続完了")
    else:
        st.error("xai-で始まるキーを入力してください")
        st.stop()
    
    st.divider()
    
    num_tweets = st.slider("ツイート数", 2, 6, 4)
    
    length_option = st.select_slider(
        "文字数",
        options=["30-50文字", "50-80文字", "80-120文字"],
        value="50-80文字"
    )
    
    safety = st.select_slider(
        "セーフティレベル",
        options=["セーフ", "ライト", "ギリギリ"],
        value="ライト"
    )
    
    safety_map = {
        "セーフ": "fully clothed, safe",
        "ライト": "loungewear, implied only",
        "ギリギリ": "lingerie, suggestive"
    }

# ============================================================
# メイン
# ============================================================
st.header("👤 キャラクター設定")
st.caption("例：22歳、Fカップ、彼氏いない歴22年、メガネ、ブサイク")

character = st.text_area(
    "特徴",
    height=80,
    placeholder="例：22歳、Fカップ、彼氏いない歴22年、メガネ、ブサイク"
)

if not character:
    st.info("特徴を入力してください")
    st.stop()

# ============================================================
# 文字数変換
# ============================================================
length_map = {
    "30-50文字": 40,
    "50-80文字": 65,
    "80-120文字": 100
}
target_length = length_map[length_option]

# ============================================================
# ツイート生成
# ============================================================
st.markdown("---")
st.header("📝 ツイート生成")

if st.button("✨ 生成する", type="primary", use_container_width=True):
    with st.spinner("生成中..."):
        prompt = f"""プロのツイートライターとして、以下の女性のツイートを{num_tweets}個書いてください。

【特徴】
{character}

【条件】
・1ツイート{target_length}文字程度
・句読点で改行すること
・「写真」「撮影」「カメラ」禁止
・全て異なる内容にすること

【例】
彼氏いない歴22年。そろそろ誰か来てくれないかな。毎晩一人で寝るのがつらい。

【出力形式】
1:（ツイート）
2:（ツイート）
3:（ツイート）
4:（ツイート）"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.3,
            max_tokens=800
        )
        
        raw = response.choices[0].message.content
        
        tweets = []
        for line in raw.split('\n'):
            line = line.strip()
            match = re.match(r'^\d+:', line)
            if match:
                tweet = line[match.end():].strip()
                if tweet and len(tweet) > 15:
                    tweets.append(tweet)
        
        tweets = tweets[:num_tweets]
        
        if not tweets:
            st.error("生成失敗しました。もう一度お試しください。")
        else:
            st.session_state.tweets = tweets
            st.success(f"{len(tweets)}件生成しました")

# ツイート表示
if st.session_state.get("tweets"):
    st.subheader("✏️ ツイート")
    edited = []
    for i, t in enumerate(st.session_state.tweets):
        new_t = st.text_area(f"No.{i+1}", t, key=f"t_{i}", height=100)
        edited.append(new_t)
    st.session_state.tweets = edited

# ============================================================
# プロンプト変換
# ============================================================
if st.session_state.get("tweets"):
    st.markdown("---")
    st.header("🎨 英語プロンプト変換")
    
    if st.button("🔄 変換する", type="primary", use_container_width=True):
        prompts = []
        prog = st.progress(0)
        
        for i, tweet in enumerate(st.session_state.tweets):
            p = f"""以下のツイートから画像生成プロンプトを作成。

ツイート：{tweet}
特徴：{character}

条件：iPhone自撮り、手ブレ、鏡構図、下着/部屋着、生活感、恥ずかしげ、リアル肌
禁止：cafe, studio, perfect, clean, porn, naked, beautiful
安全：{safety_map[safety]}

英語80語以内、1行で出力。"""

            res = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": p}],
                temperature=0.8,
                max_tokens=400
            )
            prompts.append(res.choices[0].message.content.strip())
            prog.progress((i + 1) / len(st.session_state.tweets))
        
        st.session_state.prompts = prompts
        st.success("変換完了")
    
    if st.session_state.get("prompts"):
        st.subheader("✏️ プロンプト")
        edited = []
        for i, (t, p) in enumerate(zip(st.session_state.tweets, st.session_state.prompts)):
            with st.expander(f"ツイート{i+1}", expanded=False):
                st.caption(f"元：{t[:60]}...")
                new_p = st.text_area(f"P{i+1}", p, key=f"p_{i}", height=100)
                edited.append(new_p)
        st.session_state.prompts = edited

# ============================================================
# CSV出力
# ============================================================
if st.session_state.get("tweets") and st.session_state.get("prompts"):
    st.markdown("---")
    st.header("💾 出力")
    
    df = pd.DataFrame({
        "特徴": [character] * len(st.session_state.tweets),
        "ツイート": st.session_state.tweets,
        "プロンプト": st.session_state.prompts,
        "日時": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] * len(st.session_state.tweets)
    })
    
    st.dataframe(df, use_container_width=True)
    
    csv = io.StringIO()
    df.to_csv(csv, index=False, encoding="utf-8-sig")
    st.download_button("📥 CSV", csv.getvalue(), f"uraaka_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")

st.markdown("---")
st.caption("Grok API | プロンプトをHiggsfield/ImageFXに貼り付け")
