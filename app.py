import streamlit as st
import httpx
import pandas as pd
import json
import re
import time
import os
from io import BytesIO
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

TG_API = "https://api.telegram.org/bot{token}/{method}"
GROQ_MODEL = "llama-3.1-8b-instant"  # 500k TPD vs 100k у 70b — в 5 раз выше лимит

st.set_page_config(
    page_title="TG Channel Finder",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">

<style>
/* ── Base ── */
:root {
    --bg:        #F4F5FC;
    --card:      #FFFFFF;
    --card2:     #F8F8FE;
    --border:    #DDE0F0;
    --border2:   #ECEDF8;
    --primary:   #6D28D9;
    --primary2:  #8B5CF6;
    --gold:      #D97706;
    --success:   #059669;
    --danger:    #DC2626;
    --text:      #1A1240;
    --muted:     #717499;
    --mono:      'JetBrains Mono', monospace;
    --shadow-sm: 0 1px 3px rgba(26,18,64,0.05);
    --shadow:    0 2px 8px rgba(26,18,64,0.07), 0 1px 3px rgba(26,18,64,0.04);
    --shadow-md: 0 6px 20px rgba(26,18,64,0.10), 0 2px 6px rgba(26,18,64,0.05);
}

html, body, .stApp {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
}

#MainMenu, footer, header { visibility: hidden !important; }

/* ── Decorative background glow ── */
.stApp::before {
    content: '';
    position: fixed;
    top: -120px; right: -120px;
    width: 700px; height: 700px;
    background: radial-gradient(ellipse at center, rgba(139,92,246,0.08) 0%, transparent 65%);
    pointer-events: none;
    z-index: 0;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #EDEEF8 0%, #E6E7F4 100%) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div { padding-top: 1.5rem !important; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p { color: #5A5C7E !important; font-size: 0.82rem !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--primary) !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}

/* ── Inputs ── */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
    background: #FFFFFF !important;
    border: 1.5px solid #D8DCF0 !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.9rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    box-shadow: var(--shadow-sm) !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(109,40,217,0.12), var(--shadow-sm) !important;
    outline: none !important;
}
.stTextInput input[type="password"] { letter-spacing: 0.1em !important; }

/* ── Select ── */
[data-baseweb="select"] > div,
[data-baseweb="base-input"] > input {
    background: #FFFFFF !important;
    border-color: #D8DCF0 !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-baseweb="menu"] {
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    box-shadow: var(--shadow-md) !important;
}
[data-baseweb="option"] { color: var(--text) !important; }
[data-baseweb="option"]:hover { background: #F2EEFF !important; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--primary), #5B21B6) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.05em !important;
    padding: 0.5rem 1.2rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 12px rgba(109,40,217,0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(109,40,217,0.38) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--primary) 0%, #EC4899 100%) !important;
    font-size: 1rem !important;
    padding: 0.75rem 1.5rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    box-shadow: 0 4px 18px rgba(109,40,217,0.30) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 8px 30px rgba(139,92,246,0.45) !important;
}

/* Download buttons */
.stDownloadButton > button {
    background: #FFFFFF !important;
    border: 1.5px solid var(--border) !important;
    color: var(--primary) !important;
    border-radius: 10px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    transition: all 0.2s !important;
    box-shadow: var(--shadow-sm) !important;
}
.stDownloadButton > button:hover {
    background: #F5EFFF !important;
    border-color: var(--primary) !important;
    box-shadow: 0 4px 14px rgba(109,40,217,0.18) !important;
    transform: translateY(-1px) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #EBEBF5 !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    border-radius: 8px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.03em !important;
    padding: 6px 18px !important;
    transition: all 0.2s !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--primary), var(--primary2)) !important;
    color: #fff !important;
    box-shadow: 0 2px 8px rgba(109,40,217,0.28) !important;
}

/* ── Progress ── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--primary), #EC4899, var(--gold)) !important;
    border-radius: 100px !important;
    animation: pulse-bar 2s ease infinite !important;
}
@keyframes pulse-bar {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.85; }
}
.stProgress > div > div {
    background: #E0E3F2 !important;
    border-radius: 100px !important;
}

/* ── Slider ── */
[data-baseweb="slider"] [role="slider"] {
    background: var(--primary) !important;
    border-color: var(--primary2) !important;
    box-shadow: 0 0 10px rgba(109,40,217,0.4) !important;
}
[data-baseweb="slider"] div[class*="Track"] > div {
    background: linear-gradient(90deg, var(--primary), var(--primary2)) !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-top: 3px solid var(--primary2) !important;
    border-radius: 14px !important;
    padding: 1.1rem 1.2rem !important;
    transition: all 0.2s !important;
    box-shadow: var(--shadow) !important;
}
[data-testid="metric-container"]:hover {
    box-shadow: var(--shadow-md) !important;
    transform: translateY(-2px) !important;
}
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 0.75rem !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }
[data-testid="stMetricValue"] { color: var(--primary) !important; font-family: 'Outfit', sans-serif !important; font-weight: 700 !important; font-size: 1.15rem !important; }

/* ── Expanders ── */
details {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    margin-bottom: 0.5rem !important;
    box-shadow: var(--shadow-sm) !important;
}
details summary {
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    padding: 0.9rem 1.1rem !important;
    cursor: pointer !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.02em !important;
    background: var(--card) !important;
}
details summary:hover { background: #F8F7FF !important; }
details[open] summary { border-bottom: 1px solid var(--border) !important; }
details > div { padding: 1rem 1.1rem !important; }

/* ── Dataframe ── */
.stDataFrame {
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    box-shadow: var(--shadow) !important;
}
.stDataFrame iframe { border-radius: 14px !important; }

/* ── Alerts ── */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    border-left-width: 4px !important;
    font-family: 'Outfit', sans-serif !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #FAFBFF !important;
    border: 1.5px dashed #C8CCE8 !important;
    border-radius: 12px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--primary) !important; }

/* ── Divider ── */
hr { border-color: var(--border2) !important; margin: 1.5rem 0 !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] > div { border-top-color: var(--primary) !important; }

/* ── Caption ── */
.stCaption { color: var(--muted) !important; font-size: 0.78rem !important; }

/* ── Custom cards ── */
.card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    transition: all 0.2s;
    box-shadow: var(--shadow);
}
.card:hover {
    border-color: #C4B5FD;
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
}
.card-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--primary);
    margin-bottom: 0.6rem;
}

/* ── Hero ── */
.hero {
    padding: 2rem 0 1.8rem;
    margin-bottom: 0.5rem;
}
.hero-badge {
    display: inline-block;
    background: linear-gradient(135deg, rgba(109,40,217,0.10), rgba(139,92,246,0.06));
    border: 1px solid rgba(109,40,217,0.25);
    border-radius: 100px;
    padding: 4px 14px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--primary);
    margin-bottom: 1rem;
}
.hero-title {
    font-family: 'Anton', sans-serif;
    font-size: clamp(2.8rem, 5vw, 4.2rem);
    line-height: 0.95;
    letter-spacing: 0.04em;
    margin: 0 0 0.8rem 0;
    background: linear-gradient(135deg, #1A1240 0%, var(--primary) 55%, var(--gold) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-title em {
    font-style: normal;
    -webkit-text-fill-color: var(--gold);
    color: var(--gold);
}
.hero-sub {
    font-size: 0.95rem;
    color: var(--muted);
    font-weight: 400;
    margin: 0;
    letter-spacing: 0.01em;
}
.hero-chips {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-top: 1rem;
}
.chip {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 100px;
    padding: 4px 12px;
    font-size: 0.72rem;
    color: #5A5C7A;
    letter-spacing: 0.05em;
    box-shadow: var(--shadow-sm);
}

/* ── Section headers ── */
.section-title {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* ── Brief analysis box ── */
.brief-box {
    background: linear-gradient(135deg, rgba(109,40,217,0.04), rgba(139,92,246,0.02));
    border: 1px solid rgba(109,40,217,0.18);
    border-left: 3px solid var(--primary);
    border-radius: 16px;
    padding: 1.3rem 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 2px 12px rgba(109,40,217,0.06);
}
.brief-box h4 {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--primary);
    margin: 0 0 0.8rem 0;
}
.brief-row { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 0.6rem; }
.brief-item { }
.brief-key { font-size: 0.7rem; color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 2px; }
.brief-val { font-size: 0.95rem; color: var(--text); font-weight: 600; }

/* ── Status bar ── */
.status-bar {
    background: #F0FBF6;
    border: 1px solid #BBF7D0;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    font-family: var(--mono);
    font-size: 0.8rem;
    color: #065F46;
    margin: 0.5rem 0;
    letter-spacing: 0.03em;
}

/* ── Results header ── */
.results-header {
    display: flex;
    align-items: baseline;
    gap: 1rem;
    margin-bottom: 1rem;
}
.results-count {
    font-family: 'Anton', sans-serif;
    font-size: 2.5rem;
    letter-spacing: 0.04em;
    color: var(--primary);
    line-height: 1;
}
.results-label {
    font-size: 0.85rem;
    color: var(--muted);
    font-weight: 500;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #ECEDF5; }
::-webkit-scrollbar-thumb { background: #C2C4DC; border-radius: 100px; }
::-webkit-scrollbar-thumb:hover { background: var(--primary2); }
</style>
""", unsafe_allow_html=True)


# ─── Groq AI ──────────────────────────────────────────────────────────────────

def get_client(api_key: str) -> Groq:
    return Groq(api_key=api_key)


def ask_json(client: Groq, prompt: str, max_tokens: int = 4096) -> dict:
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(response.choices[0].message.content)


def analyze_brief(brief_text: str, client: Groq) -> dict:
    prompt = f"""Проанализируй рекламный бриф для Telegram-рекламы.

Бриф:
{brief_text[:3000]}

Верни JSON:
{{
  "product": "название продукта или услуги",
  "niche": "ниша",
  "target_audience": "описание целевой аудитории",
  "age_range": "возраст например 25-44",
  "gender": "все или мужчины или женщины",
  "geo": "Россия"
}}"""
    try:
        return ask_json(client, prompt)
    except Exception as e:
        st.error(f"Ошибка анализа брифа: {e}")
        return {}


_KW_STOPWORDS = {
    "лет", "года", "году", "рублей", "рубль", "рублях", "доход", "доходом",
    "месяц", "месяца", "месяцев", "более", "менее", "выше", "ниже",
    "среднего", "среднем", "тысяч", "миллион", "человек", "людей",
    "который", "которая", "которые", "также", "этого", "этой", "этот",
    "своей", "своего", "своих", "будет", "после", "перед", "между",
    "russia", "женщин", "мужчин", "россия", "россию", "российских",
}

def _clean_kws(kws: list) -> list:
    """Оставляет только слова пригодные для поиска каналов в Telemetr."""
    result = []
    for kw in kws:
        kw = kw.strip().lower()
        words = kw.split()
        if not words or len(words) > 2:
            continue
        # отбрасываем слова с цифрами или дефисом+цифра
        if any(c.isdigit() for c in kw):
            continue
        # отбрасываем стоп-слова
        if all(w in _KW_STOPWORDS for w in words):
            continue
        # минимум 4 буквы в каждом слове
        if any(len(w) < 4 for w in words):
            continue
        # отбрасываем слова в косвенных падежах с нехарактерными окончаниями
        if kw.endswith(("ью", "ови", "ями", "ами", "ого", "его", "ому", "ему")):
            continue
        if kw not in result:
            result.append(kw)
    return result


def extract_keywords(brief: dict, client: Groq, ref_channels_info: list = None) -> list:
    ref_block = ""
    if ref_channels_info:
        lines = [f"- @{ch['username']}: «{ch['title']}»" for ch in ref_channels_info[:4]]
        ref_block = f"Каналы-ориентиры (ищем похожие по аудитории):\n" + "\n".join(lines) + "\n"

    prompt = f"""Составь ключевые слова для поиска Telegram-каналов через Telemetr.

Правила — ОБЯЗАТЕЛЬНЫ:
- Только 1 слово (реже 2). Никаких фраз из 3+ слов!
- Слова должны реально встречаться в НАЗВАНИЯХ Telegram-каналов
- Хорошие примеры: бизнес, маркетинг, коучинг, продвижение, заработок, инвестиции, саморазвитие
- Плохие: "женщины-предпринимательницы", "30-55", "рублей", "доходом"

Продукт: {brief.get("product", "")[:100]}
Ниша: {brief.get("niche", "")[:80]}
ЦА: {brief.get("target_audience", "")[:100]}
Пол: {brief.get("gender", "")}
{ref_block}
Верни JSON с 14 словами (разные темы: продукт, интересы ЦА, смежные ниши):
{{"keywords": ["слово1", "слово2", ...]}}"""
    try:
        result = ask_json(client, prompt, max_tokens=512)
        kws = _clean_kws(result.get("keywords", []))
        if len(kws) < 6:
            # Фолбэк — только слова из product/niche, без target_audience
            for field in ["niche", "product"]:
                for word in brief.get(field, "").split():
                    w = word.strip(".,!?«»()-").lower()
                    if len(w) >= 4 and not any(c.isdigit() for c in w) and w not in _KW_STOPWORDS:
                        if w not in kws:
                            kws.append(w)
        return kws[:12]
    except Exception:
        # Жёсткий фолбэк — только product/niche
        words = []
        for field in ["niche", "product"]:
            for w in brief.get(field, "").split():
                w = w.strip(".,!?«»()-").lower()
                if len(w) >= 4 and not any(c.isdigit() for c in w) and w not in _KW_STOPWORDS:
                    words.append(w)
        return list(dict.fromkeys(words))[:10]


def search_duckduckgo(query: str) -> list:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query, "kl": "ru-ru", "ia": "web"},
            headers=headers,
            timeout=15,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return []
        found = re.findall(
            r't\.me/(?!joinchat|s/|\+|share/)([A-Za-z][A-Za-z0-9_]{3,31})(?=[^A-Za-z0-9_/]|$)',
            resp.text,
        )
        return list(dict.fromkeys(found))
    except Exception:
        return []



def telemetr_get_channel_id(api_key: str, username: str):
    """Получить internal_id канала по username через Telemetr."""
    try:
        resp = httpx.get(
            "https://api.telemetr.io/v1/channels/search",
            headers={"x-api-key": api_key},
            params={"term": username.lstrip("@"), "limit": 5},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, list):
            return None
        uname_clean = username.lstrip("@").lower()
        for ch in data:
            link = ch.get("link") or ""
            if uname_clean in link.lower():
                iid = ch.get("internal_id")
                return str(iid) if iid else None
    except Exception:
        pass
    return None


def telemetr_similar_channels(api_key: str, channel_id: str) -> list:
    """Найти похожие каналы по internal_id через Telemetr."""
    for endpoint in [
        f"https://api.telemetr.io/v1/channels/{channel_id}/similar",
        f"https://api.telemetr.io/v1/channels/similar",
    ]:
        try:
            params = {"limit": 50}
            if "similar" == endpoint.split("/")[-1]:
                params["id"] = channel_id
            resp = httpx.get(
                endpoint,
                headers={"x-api-key": api_key},
                params=params,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("channels", [])
                ids = []
                for ch in items:
                    iid = ch.get("internal_id")
                    if iid:
                        ids.append(str(iid))
                if ids:
                    return ids
        except Exception:
            continue
    return []


def search_telemetr(api_key: str, keywords: list, ref_usernames: list = None) -> list:
    """Поиск через Telemetr.io. Возвращает список словарей с данными каналов.

    Шаг 1: search по ключевым словам → internal_id + базовые поля (title, members_count)
    Шаг 2: info-batch по ID → получаем link (= t.me/username) и description
    """
    # internal_id → базовые данные из search (title, members_count)
    id_to_base = {}

    # Если есть ориентиры — ищем похожие через similar API
    if ref_usernames:
        for ref_u in ref_usernames[:3]:
            ref_id = telemetr_get_channel_id(api_key, ref_u)
            if ref_id and ref_id not in id_to_base:
                id_to_base[ref_id] = {}
                for sid in telemetr_similar_channels(api_key, ref_id):
                    if sid not in id_to_base:
                        id_to_base[sid] = {}
            time.sleep(0.3)

    for kw in keywords[:12]:
        try:
            resp = httpx.get(
                "https://api.telemetr.io/v1/channels/search",
                headers={"x-api-key": api_key},
                params={"term": kw, "limit": 25},
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            if not isinstance(data, list):
                continue
            for ch in data:
                if not isinstance(ch, dict):
                    continue
                iid = str(ch.get("internal_id", ""))
                if iid and iid not in id_to_base:
                    # search не возвращает username/link — сохраняем что есть
                    id_to_base[iid] = {
                        "title": ch.get("title") or ch.get("name") or "",
                        "subscribers": int(ch.get("members_count") or 0),
                    }
            time.sleep(0.5)
        except Exception:
            continue

    if not id_to_base:
        return []

    # Шаг 2: info-batch → получаем link (username) и description
    channels = []
    seen_usernames = set()
    all_ids = list(id_to_base.keys())

    for i in range(0, len(all_ids), 100):
        batch = all_ids[i:i + 100]
        try:
            resp = httpx.get(
                "https://api.telemetr.io/v1/channels/info-batch",
                headers={"x-api-key": api_key},
                params={"ids": ",".join(batch)},
                timeout=25,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            items = data.get("channels", data) if isinstance(data, dict) else data
            if not isinstance(items, list):
                continue
            for ch in items:
                # Извлекаем username из link
                link = ch.get("link") or ch.get("url") or ""
                uname = ""
                if "t.me/" in link:
                    uname = link.split("t.me/")[-1].strip("/")
                elif ch.get("username"):
                    uname = str(ch["username"]).lstrip("@")
                if not uname or uname.startswith("+") or uname.lower() in seen_usernames:
                    continue
                seen_usernames.add(uname.lower())
                iid = str(ch.get("internal_id", ""))
                base = id_to_base.get(iid, {})
                subs = (ch.get("members_count") or ch.get("subscribers") or
                        ch.get("participants_count") or base.get("subscribers") or 0)
                title = ch.get("title") or ch.get("name") or base.get("title") or uname
                desc = ch.get("about") or ch.get("description") or ch.get("bio") or ""
                channels.append({
                    "username": uname,
                    "title": str(title),
                    "description": str(desc)[:300],
                    "subscribers": int(subs) if subs else 0,
                    "source": "telemetr",
                })
        except Exception:
            continue

    return channels


def search_web_for_channels(brief: dict, client: Groq, target_count: int) -> list:
    keywords = extract_keywords(brief, client)
    if not keywords:
        return []
    all_usernames = []
    seen = set()
    for kw in keywords:
        found = search_duckduckgo(f"site:t.me {kw}")
        for u in found:
            if u.lower() not in seen:
                seen.add(u.lower())
                all_usernames.append(u)
        time.sleep(0.5)
        if len(all_usernames) >= target_count:
            break
    return all_usernames


def generate_channels(brief: dict, reference_channels: list, client: Groq, count: int, exclude: set = None) -> list:
    """Запрашиваем count каналов у AI. Используется только если Telemetr недоступен."""
    if exclude is None:
        exclude = set()
    count = min(count, 20)  # не больше 20 — иначе JSON не успевает сгенерироваться

    ref_block = f"Ориентиры: {', '.join(reference_channels[:5])}.\n" if reference_channels else ""

    prompt = f"""Telegram-каналы для рекламы (русскоязычные, публичные, реальные):

Продукт: {brief.get("product", "")[:80]}
Ниша: {brief.get("niche", "")[:60]}
ЦА: {brief.get("target_audience", "")[:100]}
Пол: {brief.get("gender", "все")} · Возраст: {brief.get("age_range", "")}
{ref_block}
Только реальные существующие каналы с username. От 5000 подписчиков.
Верни JSON: {{"channels": ["username1", "username2", ...]}} — ровно {count} штук."""

    try:
        result = ask_json(client, prompt, max_tokens=1024)
        items = result.get("channels", result) if isinstance(result, dict) else result
        if isinstance(items, list):
            return [str(u).lstrip("@").strip() for u in items if u and str(u).lstrip("@").strip() not in exclude]
        return []
    except Exception as e:
        st.warning(f"AI генерация недоступна: {e}")
        return []


def _score_batch(batch: list, brief: dict, client: Groq) -> dict:
    """Оценивает один батч каналов, возвращает {username: {score, reason}}."""
    summaries = [
        {
            "u": ch["username"],
            "t": ch.get("title", "")[:60],
            "d": ch.get("description", "")[:80],
        }
        for ch in batch
    ]
    prompt = f"""Оцени Telegram-каналы для рекламы. Критерий: совпадает ли АУДИТОРИЯ канала с ЦА.

Продукт: {brief.get("product", "")}
ЦА: {brief.get("target_audience", "")}
Пол: {brief.get("gender", "все")} · Возраст: {brief.get("age_range", "")}

70-100 = аудитория совпадает. 40-69 = частично. 0-39 = не совпадает.

Каналы (u=username, t=title, d=description):
{json.dumps(summaries, ensure_ascii=False)}

Верни JSON: {{"scores": [{{"u": "username", "s": 85, "r": "причина (1 предложение)"}}, ...]}}"""
    try:
        result = ask_json(client, prompt)
        scores = result.get("scores", [])
        return {s["u"]: {"score": int(s.get("s", 0)), "reason": s.get("r", "")} for s in scores if "u" in s}
    except Exception:
        return {}


def score_channels(channels: list, brief: dict, client: Groq) -> list:
    if not channels:
        return []

    score_map = {}
    batch_size = 20
    for i in range(0, len(channels), batch_size):
        batch = channels[i:i + batch_size]
        result = _score_batch(batch, brief, client)
        score_map.update(result)
        if i + batch_size < len(channels):
            time.sleep(1)  # небольшая пауза между батчами

    for ch in channels:
        s = score_map.get(ch["username"], {})
        ch["ai_score"] = s.get("score", 0)
        ch["ai_reason"] = s.get("reason", "")
    return sorted(channels, key=lambda x: x.get("ai_score", 0), reverse=True)


# ─── Telegram Bot API ─────────────────────────────────────────────────────────

def tg_get_chat(bot_token: str, username: str) -> dict:
    try:
        resp = httpx.get(
            TG_API.format(token=bot_token, method="getChat"),
            params={"chat_id": f"@{username.lstrip('@')}"},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return data["result"]
    except Exception:
        pass
    return {}


def tg_get_member_count(bot_token: str, username: str) -> int:
    try:
        resp = httpx.get(
            TG_API.format(token=bot_token, method="getChatMemberCount"),
            params={"chat_id": f"@{username.lstrip('@')}"},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return int(data["result"])
    except Exception:
        pass
    return 0


def enrich_channels(bot_token: str, usernames: list, prog, stat) -> list:
    results = []
    total = len(usernames)
    for i, uname in enumerate(usernames):
        stat.markdown(f'<div class="status-bar">📡 Проверяю @{uname} &nbsp;·&nbsp; {i+1} / {total} &nbsp;·&nbsp; найдено: {len(results)}</div>', unsafe_allow_html=True)
        info = tg_get_chat(bot_token, uname)
        if info and info.get("type") in ("channel", "supergroup"):
            count = tg_get_member_count(bot_token, uname)
            results.append({
                "username": uname,
                "title": info.get("title", ""),
                "description": info.get("description", ""),
                "subscribers": count,
            })
        time.sleep(0.05)
        prog.progress((i + 1) / total)
    return results


def extract_pdf_text(pdf_file) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(pdf_file) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        st.error(f"Ошибка PDF: {e}")
        return ""


def parse_handles(raw: str) -> list:
    out = []
    for line in raw.strip().splitlines():
        h = line.strip().replace("https://t.me/", "").strip("/").lstrip("@").strip()
        if h:
            out.append(h)
    return out


def fmt_subs(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}М"
    if n >= 1_000:
        return f"{n/1_000:.0f}К"
    return str(n)


def score_color(score: int) -> str:
    if score >= 80:
        return "#10B981"
    if score >= 60:
        return "#F59E0B"
    if score >= 40:
        return "#F97316"
    return "#EF4444"


def to_df(channels: list) -> pd.DataFrame:
    rows = []
    for ch in channels:
        uname = ch.get("username", "")
        rows.append({
            "Оценка": ch.get("ai_score", 0),
            "Канал": f"@{uname}",
            "Название": ch.get("title", ""),
            "Подписчики": ch.get("subscribers", 0),
            "Описание": ch.get("description", "")[:200],
            "Комментарий AI": ch.get("ai_reason", ""),
            "Ссылка": f"https://t.me/{uname}",
        })
    return pd.DataFrame(rows)


def get_secret(key: str) -> str:
    # st.secrets uses __getitem__, not .get() — must use try/except
    for k in [key, key.lower(), key.upper()]:
        try:
            val = st.secrets[k]
            if val:
                return str(val)
        except Exception:
            pass
    for k in [key, key.lower(), key.upper()]:
        val = os.getenv(k, "")
        if val:
            return val
    return ""


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🔧 Параметры")
    channel_count = st.slider("Каналов для подбора", 20, 100, 50)
    max_subs = st.number_input("Макс. подписчики (0 = без лимита)", min_value=0, value=0, step=10000)
    min_subs = 1000

    groq_key     = get_secret("GROQ_API_KEY")
    bot_token    = get_secret("TELEGRAM_BOT_TOKEN")
    telemetr_key = get_secret("TELEMETR_API_KEY")

    st.divider()
    st.markdown("### ⚙️ Ключи API")
    if not groq_key:
        groq_key = st.text_input("Groq API Key", type="password", help="console.groq.com")
        st.caption("Назови секрет: **GROQ_API_KEY**")
    else:
        st.caption("✅ Groq API Key")
    if not bot_token:
        bot_token = st.text_input("Telegram Bot Token", type="password")
        st.caption("Назови секрет: **TELEGRAM_BOT_TOKEN**")
    else:
        st.caption("✅ Telegram Bot Token")
    if not telemetr_key:
        telemetr_key = st.text_input("Telemetr API Key", type="password", help="@telemetrio_api_bot в Telegram")
        st.caption("Назови секрет: **TELEMETR_API_KEY**")
    else:
        st.caption("✅ Telemetr API Key")

    st.divider()
    st.markdown('<p style="font-size:0.7rem;color:#9496B8;letter-spacing:0.1em;text-align:center;text-transform:uppercase;">TG Channel Finder · AI Media Planning</p>', unsafe_allow_html=True)


# ─── HERO ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
    <div class="hero-badge">⚡ AI · POWERED · MEDIA PLANNING</div>
    <h1 class="hero-title">TG CHANNEL<br>FINDER</h1>
    <p class="hero-sub">Загрузи бриф → AI подберёт каналы → получи медиаплан</p>
    <div class="hero-chips">
        <span class="chip">🤖 Groq Llama 3.3</span>
        <span class="chip">📡 Telegram API</span>
        <span class="chip">📊 AI-скоринг</span>
        <span class="chip">📥 CSV / Excel</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── INPUT AREA ───────────────────────────────────────────────────────────────

col1, col2 = st.columns([3, 2], gap="large")
brief_text = ""

with col1:
    st.markdown('<div class="section-title">📋 Бриф проекта</div>', unsafe_allow_html=True)
    tab_text, tab_pdf = st.tabs(["✏️  Текст", "📄  PDF"])
    with tab_text:
        brief_text = st.text_area(
            "brief",
            height=200,
            placeholder="Опиши продукт и целевую аудиторию...\n\nНапример: онлайн-курс по инвестициям. ЦА — мужчины 25-40 лет, хотят научиться вкладывать деньги. Гео: Россия.",
            label_visibility="collapsed",
        )
    with tab_pdf:
        pdf_file = st.file_uploader("pdf", type=["pdf"], label_visibility="collapsed")
        if pdf_file:
            extracted = extract_pdf_text(pdf_file)
            if extracted:
                brief_text = extracted
                st.success(f"Прочитано {len(extracted):,} символов из PDF")

with col2:
    st.markdown('<div class="section-title">🎯 Ориентиры</div>', unsafe_allow_html=True)
    reference_raw = st.text_area(
        "ref",
        height=100,
        placeholder="Каналы конкурентов или где реклама уже работала:\n@channel1\n@channel2",
        label_visibility="collapsed",
    )
    st.markdown('<div class="section-title" style="margin-top:0.8rem">➕ Свои каналы</div>', unsafe_allow_html=True)
    manual_raw = st.text_area(
        "manual",
        height=70,
        placeholder="@mychannel",
        label_visibility="collapsed",
    )

st.divider()
run = st.button("⚡  НАЙТИ КАНАЛЫ", type="primary", use_container_width=True)

# ─── SEARCH FLOW ──────────────────────────────────────────────────────────────

if run:
    errors = []
    if not groq_key:    errors.append("Нет Groq API Key — добавь в боковой панели")
    if not bot_token:   errors.append("Нет Telegram Bot Token")
    if not brief_text:  errors.append("Введи бриф проекта")
    for e in errors:
        st.error(e)
    if errors:
        st.stop()

    client = get_client(groq_key)

    # 1. Анализ брифа
    with st.spinner("Анализирую бриф..."):
        brief = analyze_brief(brief_text, client)

    if not brief:
        st.error("Не удалось проанализировать бриф. Проверь Groq API Key.")
        st.stop()

    st.markdown(f"""
    <div class="brief-box">
        <h4>📊 AI понял бриф так</h4>
        <div class="brief-row">
            <div class="brief-item"><div class="brief-key">Продукт</div><div class="brief-val">{brief.get("product","—")}</div></div>
            <div class="brief-item"><div class="brief-key">Ниша</div><div class="brief-val">{brief.get("niche","—")}</div></div>
            <div class="brief-item"><div class="brief-key">Гео</div><div class="brief-val">{brief.get("geo","—")}</div></div>
            <div class="brief-item"><div class="brief-key">Пол</div><div class="brief-val">{brief.get("gender","—")}</div></div>
            <div class="brief-item"><div class="brief-key">Возраст</div><div class="brief-val">{brief.get("age_range","—")}</div></div>
        </div>
        <div class="brief-item"><div class="brief-key">Целевая аудитория</div><div class="brief-val" style="font-weight:400;font-size:0.9rem;color:var(--muted)">{brief.get("target_audience","—")}</div></div>
    </div>
    """, unsafe_allow_html=True)

    ref_handles = parse_handles(reference_raw)
    manual_handles = parse_handles(manual_raw)

    # 2. Получаем данные каналов-ориентиров через Bot API (для анализа аудитории)
    ref_channels_info = []
    if ref_handles:
        with st.spinner("🔍 Анализирую каналы-ориентиры..."):
            dummy_prog = st.empty()
            dummy_stat = st.empty()
            ref_channels_info = enrich_channels(bot_token, ref_handles[:5], dummy_prog, dummy_stat)
            dummy_prog.empty()
            dummy_stat.empty()

    # 3. Ключевые слова — с учётом ориентиров
    with st.spinner("🧠 Анализирую аудиторию и формирую запросы..."):
        keywords = extract_keywords(brief, client, ref_channels_info or None)
    if keywords:
        st.caption(f"Ключевые слова: {', '.join(keywords)}")

    # 4a. Telemetr → данные каналов напрямую (БЕЗ Bot API верификации)
    telemetr_channels = []
    if telemetr_key:
        with st.spinner("🔍 Ищу каналы через Telemetr.io..."):
            telemetr_channels = search_telemetr(telemetr_key, keywords, ref_handles or None)
        if telemetr_channels:
            st.info(f"📡 Telemetr.io: найдено {len(telemetr_channels)} каналов")
        else:
            st.warning("Telemetr.io не вернул каналов — использую AI генерацию")
    else:
        st.caption("Telemetr API не настроен — использую AI генерацию")

    telemetr_usernames = {c["username"].lower() for c in telemetr_channels}

    # 4b. AI генерация — только если Telemetr совсем ничего не нашёл
    # (AI каналы часто фейковые, Telemetr даёт реальные)
    ai_handles = []
    if not telemetr_channels:
        ai_needed = min(channel_count, 40)
        exclude_ai = {h.lower() for h in ref_handles + manual_handles}
        with st.spinner("🤖 AI подбирает каналы (Telemetr недоступен)..."):
            ai_handles = generate_channels(brief, ref_handles, client, ai_needed, exclude=exclude_ai)

    if not telemetr_channels and not ai_handles:
        st.error("Не удалось найти каналы. Попробуй переформулировать бриф.")
        st.stop()

    # 4c. Bot API верификация — только для AI и ручных каналов
    to_verify = list(dict.fromkeys(
        [h for h in ai_handles + ref_handles + manual_handles
         if h.lower() not in telemetr_usernames]
    ))
    verified_channels = []
    if to_verify:
        st.markdown(f'<div class="section-title" style="margin-top:1rem">📡 Проверяю AI-каналы через Telegram — {len(to_verify)}</div>', unsafe_allow_html=True)
        prog = st.progress(0)
        stat = st.empty()
        verified_channels = enrich_channels(bot_token, to_verify, prog, stat)
        stat.empty()
        prog.empty()

    # Объединяем: Telemetr (прямые данные) + верифицированные AI/ручные каналы
    seen_u = set()
    enriched = []
    for ch in telemetr_channels + verified_channels:
        k = ch["username"].lower()
        if k not in seen_u:
            seen_u.add(k)
            enriched.append(ch)

    found = len(enriched)
    verified_failed = len(to_verify) - len(verified_channels)

    if found == 0:
        st.error("Не удалось найти каналы. Возможно, Telemetr не вернул данных и AI-каналы приватные.")
        st.stop()

    msg = f"✅ Найдено **{found}** каналов"
    if verified_failed:
        msg += f"  ·  AI-каналов не прошло проверку: {verified_failed}"
    st.success(msg)

    with st.expander(f"👀 Все найденные каналы — {found} штук"):
        handles_text = "  ·  ".join(f"`@{c['username']}`" for c in enriched)
        st.markdown(f'<p style="font-family:var(--mono);font-size:0.78rem;color:#7070AA;line-height:2">{handles_text}</p>', unsafe_allow_html=True)

    # 3. Фильтры по подписчикам (0 = неизвестно, не фильтруем)
    filtered_channels = [
        c for c in enriched
        if c.get("subscribers", 0) == 0 or c.get("subscribers", 0) >= min_subs
    ]
    if max_subs > 0:
        filtered_channels = [
            c for c in filtered_channels
            if c.get("subscribers", 0) == 0 or c.get("subscribers", 0) <= max_subs
        ]

    if not filtered_channels:
        st.warning("После фильтрации ничего не осталось. Попробуй уменьшить фильтры подписчиков.")
        st.stop()

    # 5. Скоринг
    with st.spinner(f"🤖 AI оценивает {len(filtered_channels)} каналов..."):
        scored = score_channels(filtered_channels, brief, client)

    st.session_state["scored"] = scored
    st.session_state["brief"] = brief

# ─── RESULTS ──────────────────────────────────────────────────────────────────

if "scored" in st.session_state:
    scored = st.session_state["scored"]

    st.divider()
    st.markdown(f"""
    <div class="results-header">
        <span class="results-count">{len(scored)}</span>
        <span class="results-label">каналов найдено и оценено</span>
    </div>
    """, unsafe_allow_html=True)

    rf1, rf2 = st.columns([2, 1])
    with rf1:
        min_score_f = st.slider("Минимальная оценка AI", 0, 100, 30, key="score_f")
    with rf2:
        sort_by = st.selectbox("Сортировка", ["Оценка AI", "Подписчики"], key="sort_f")

    df = to_df(scored)
    result = df[df["Оценка"] >= min_score_f]
    sort_col = "Оценка" if sort_by == "Оценка AI" else "Подписчики"
    result = result.sort_values(sort_col, ascending=False)

    st.dataframe(
        result,
        use_container_width=True,
        height=500,
        column_config={
            "Оценка": st.column_config.ProgressColumn(
                "Оценка AI", min_value=0, max_value=100, format="%d"
            ),
            "Подписчики": st.column_config.NumberColumn("Подписчики", format="%d"),
            "Ссылка": st.column_config.LinkColumn("Открыть"),
        },
        hide_index=True,
    )

    st.caption(f"Показано {len(result)} из {len(df)} · мин. 1 000 подписчиков (требование Telegram Ads)")

    e1, e2 = st.columns(2)
    with e1:
        st.download_button(
            "📥 Скачать CSV",
            result.to_csv(index=False).encode("utf-8-sig"),
            "tg_channels.csv", "text/csv",
            use_container_width=True,
        )
    with e2:
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            result.to_excel(writer, index=False, sheet_name="Каналы")
        st.download_button(
            "📥 Скачать Excel",
            buf.getvalue(), "tg_channels.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
