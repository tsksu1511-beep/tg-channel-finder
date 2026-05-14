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
GROQ_MODEL = "llama-3.3-70b-versatile"

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
    --bg:       #07071A;
    --card:     #0D0D2B;
    --card2:    #11113A;
    --border:   #1E1E50;
    --primary:  #7C3AED;
    --primary2: #A855F7;
    --gold:     #F59E0B;
    --success:  #10B981;
    --danger:   #EF4444;
    --text:     #F0F0FF;
    --muted:    #7070AA;
    --mono:     'JetBrains Mono', monospace;
}

html, body, .stApp {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
}

#MainMenu, footer, header { visibility: hidden !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #09091F !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div { padding-top: 1.5rem !important; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p { color: #AAAACE !important; font-size: 0.82rem !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--primary2) !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
}

/* ── Inputs ── */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
    background: #0A0A22 !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.9rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.18) !important;
    outline: none !important;
}
.stTextInput input[type="password"] { letter-spacing: 0.1em !important; }

/* ── Select ── */
[data-baseweb="select"] > div,
[data-baseweb="base-input"] > input {
    background: #0A0A22 !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
}
[data-baseweb="menu"] { background: #0F0F30 !important; }
[data-baseweb="option"] { color: var(--text) !important; }
[data-baseweb="option"]:hover { background: #1A1A50 !important; }

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
    box-shadow: 0 4px 15px rgba(124,58,237,0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(124,58,237,0.45) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--primary) 0%, #EC4899 100%) !important;
    font-size: 1rem !important;
    padding: 0.75rem 1.5rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    box-shadow: 0 4px 20px rgba(124,58,237,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 8px 35px rgba(168,85,247,0.55) !important;
}

/* Download buttons */
.stDownloadButton > button {
    background: #0F0F30 !important;
    border: 1px solid var(--border) !important;
    color: var(--primary2) !important;
    border-radius: 10px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    transition: all 0.2s !important;
}
.stDownloadButton > button:hover {
    background: #1A1A48 !important;
    border-color: var(--primary) !important;
    box-shadow: 0 4px 16px rgba(124,58,237,0.2) !important;
    transform: translateY(-1px) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #0A0A22 !important;
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
    background: #1A1A40 !important;
    border-radius: 100px !important;
}

/* ── Slider ── */
[data-baseweb="slider"] [role="slider"] {
    background: var(--primary) !important;
    border-color: var(--primary2) !important;
    box-shadow: 0 0 10px rgba(124,58,237,0.5) !important;
}
[data-baseweb="slider"] div[class*="Track"] > div {
    background: linear-gradient(90deg, var(--primary), var(--primary2)) !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 1.1rem 1.2rem !important;
    transition: border-color 0.2s !important;
}
[data-testid="metric-container"]:hover { border-color: var(--primary) !important; }
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 0.75rem !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }
[data-testid="stMetricValue"] { color: var(--primary2) !important; font-family: 'Outfit', sans-serif !important; font-weight: 700 !important; font-size: 1.15rem !important; }

/* ── Expanders ── */
details {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    margin-bottom: 0.5rem !important;
}
details summary {
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    padding: 0.9rem 1.1rem !important;
    cursor: pointer !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.02em !important;
}
details summary:hover { background: #111130 !important; }
details[open] summary { border-bottom: 1px solid var(--border) !important; }
details > div { padding: 1rem 1.1rem !important; }

/* ── Dataframe ── */
.stDataFrame {
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
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
    background: #0A0A22 !important;
    border: 1.5px dashed var(--border) !important;
    border-radius: 12px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--primary) !important; }

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1.5rem 0 !important; }

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
    transition: border-color 0.2s, box-shadow 0.2s;
}
.card:hover {
    border-color: var(--primary);
    box-shadow: 0 0 25px rgba(124,58,237,0.1);
}
.card-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--primary2);
    margin-bottom: 0.6rem;
}

/* ── Hero ── */
.hero {
    padding: 2rem 0 1.8rem;
    margin-bottom: 0.5rem;
}
.hero-badge {
    display: inline-block;
    background: linear-gradient(135deg, rgba(124,58,237,0.2), rgba(168,85,247,0.1));
    border: 1px solid rgba(124,58,237,0.4);
    border-radius: 100px;
    padding: 4px 14px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--primary2);
    margin-bottom: 1rem;
}
.hero-title {
    font-family: 'Anton', sans-serif;
    font-size: clamp(2.8rem, 5vw, 4.2rem);
    line-height: 0.95;
    letter-spacing: 0.04em;
    margin: 0 0 0.8rem 0;
    background: linear-gradient(135deg, #fff 0%, var(--primary2) 50%, var(--gold) 100%);
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
    background: #0F0F30;
    border: 1px solid var(--border);
    border-radius: 100px;
    padding: 3px 12px;
    font-size: 0.72rem;
    color: var(--muted);
    letter-spacing: 0.05em;
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
    background: linear-gradient(135deg, rgba(124,58,237,0.08), rgba(168,85,247,0.04));
    border: 1px solid rgba(124,58,237,0.3);
    border-radius: 16px;
    padding: 1.3rem 1.5rem;
    margin: 1rem 0;
}
.brief-box h4 {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--primary2);
    margin: 0 0 0.8rem 0;
}
.brief-row { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 0.6rem; }
.brief-item { }
.brief-key { font-size: 0.7rem; color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 2px; }
.brief-val { font-size: 0.95rem; color: var(--text); font-weight: 600; }

/* ── Status bar ── */
.status-bar {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.7rem 1rem;
    font-family: var(--mono);
    font-size: 0.8rem;
    color: var(--success);
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
    color: var(--gold);
    line-height: 1;
}
.results-label {
    font-size: 0.85rem;
    color: var(--muted);
    font-weight: 500;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: #2A2A60; border-radius: 100px; }
::-webkit-scrollbar-thumb:hover { background: var(--primary); }
</style>
""", unsafe_allow_html=True)


# ─── Groq AI ──────────────────────────────────────────────────────────────────

def get_client(api_key: str) -> Groq:
    return Groq(api_key=api_key)


def ask_json(client: Groq, prompt: str):
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(response.choices[0].message.content)


def analyze_brief(brief_text: str, client: Groq) -> dict:
    prompt = f"""Проанализируй рекламный бриф для Telegram-рекламы.

Бриф:
{brief_text}

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


def extract_keywords(brief: dict, client: Groq) -> list:
    prompt = f"""Составь поисковые запросы для поиска Telegram-каналов по рекламному брифу.

Продукт: {brief.get("product", "")}
Ниша: {brief.get("niche", "")}
ЦА: {brief.get("target_audience", "")}

Верни JSON с 8 ключевыми словами/фразами на русском (тематика каналов, не название продукта):
{{"keywords": ["слово1", "фраза два", ...]}}"""
    try:
        result = ask_json(client, prompt)
        return result.get("keywords", [])[:8]
    except Exception:
        return []


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


def search_via_mtproto(session: str, keywords: list) -> list:
    """Поиск реальных каналов через Telegram MTProto."""
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.tl.functions.contacts import SearchRequest
    except ImportError:
        st.warning("MTProto: telethon не установлен")
        return []

    import asyncio
    import concurrent.futures

    keywords = keywords[:10]

    async def _run():
        client = TelegramClient(
            StringSession(session), 2040, "b18441a1ff607e10a989891a5462e627"
        )
        await client.connect()
        authorized = await client.is_user_authorized()
        if not authorized:
            await client.disconnect()
            return "__NOT_AUTHORIZED__", []
        found = {}
        for kw in keywords:
            try:
                res = await client(SearchRequest(q=kw, limit=50))
                for ch in res.chats:
                    uname = getattr(ch, "username", None)
                    if uname and uname not in found:
                        found[uname] = uname
                await asyncio.sleep(2)
            except Exception as e:
                await asyncio.sleep(10 if "FLOOD" in str(e).upper() else 3)
        await client.disconnect()
        return "ok", list(found.keys())

    def _thread_run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            status, channels = ex.submit(_thread_run).result(timeout=120)
        if status == "__NOT_AUTHORIZED__":
            st.warning("MTProto: сессия устарела — нужно обновить TELEGRAM_SESSION в secrets")
            return []
        return channels
    except concurrent.futures.TimeoutError:
        st.warning("MTProto: таймаут соединения с Telegram")
        return []
    except Exception as e:
        st.warning(f"MTProto ошибка: {e}")
        return []


def search_telemetr(api_key: str, keywords: list, limit_per_kw: int = 50) -> list:
    """Поиск каналов через Telemetr.io API по ключевым словам."""
    internal_ids = {}

    # Шаг 1: поиск по ключевым словам → internal_id (макс 25 на бесплатном тарифе)
    for kw in keywords[:8]:
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
                iid = ch.get("internal_id")
                if iid and iid not in internal_ids:
                    internal_ids[iid] = True
            time.sleep(0.5)
        except Exception:
            continue

    if not internal_ids:
        return []

    # Шаг 2: батч-запрос для получения username через поле link
    usernames = []
    all_ids = list(internal_ids.keys())
    for i in range(0, len(all_ids), 100):
        batch = all_ids[i:i + 100]
        try:
            resp = httpx.get(
                "https://api.telemetr.io/v1/channels/info-batch",
                headers={"x-api-key": api_key},
                params={"ids": ",".join(batch)},
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            channels = data.get("channels", data) if isinstance(data, dict) else data
            for ch in channels:
                link = ch.get("link") or ""
                if "t.me/" in link:
                    uname = link.split("t.me/")[-1].strip("/")
                    if uname and not uname.startswith("+"):
                        usernames.append(uname)
        except Exception:
            continue

    return usernames


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
    """Запрашиваем count каналов у AI. exclude — уже проверенные username-ы."""
    if exclude is None:
        exclude = set()
    count = min(count, 40)  # Groq JSON mode не осиливает больше 40 за раз

    ref_block = ""
    if reference_channels:
        ref_block = f"Каналы-ориентиры: {', '.join(reference_channels)}. Подбери похожие по аудитории.\n"

    exclude_block = ""
    if exclude:
        sample = list(exclude)[:30]
        exclude_block = f"НЕ включай эти каналы — они уже проверены: {', '.join(sample)}\n"

    prompt = f"""Ты опытный медиабайер в Telegram. Подбери русскоязычные Telegram-каналы для рекламы.

Продукт: {brief.get("product", "")}
Ниша: {brief.get("niche", "")}
Целевая аудитория: {brief.get("target_audience", "")}
Пол: {brief.get("gender", "все")}
Возраст: {brief.get("age_range", "")}
{ref_block}{exclude_block}
ВАЖНО — требования к каналам:
- Только ПУБЛИЧНЫЕ русскоязычные Telegram-каналы с реальным username
- Каналы должны быть ПОПУЛЯРНЫМИ и СУЩЕСТВУЮЩИМИ прямо сейчас (2024-2025)
- Приоритет: каналы с аудиторией от 5 000 подписчиков
- Тематика строго соответствует ЦА
- Разный охват: крупные (500к+), средние (50-500к), нишевые (5-50к)
- НЕ придумывай username — указывай только те каналы, в существовании которых уверен

Верни JSON объект с массивом из {count} username-ов (без @):
{{"channels": ["username1", "username2", ...]}}"""

    try:
        result = ask_json(client, prompt)
        items = result.get("channels", result) if isinstance(result, dict) else result
        if isinstance(items, list):
            return [str(u).lstrip("@").strip() for u in items if u and str(u).lstrip("@").strip() not in exclude]
        return []
    except Exception as e:
        st.error(f"Ошибка генерации каналов: {e}")
        return []


def score_channels(channels: list, brief: dict, client: Groq) -> list:
    if not channels:
        return []

    summaries = [
        {
            "username": ch["username"],
            "title": ch.get("title", ""),
            "description": ch.get("description", "")[:120],
            "subscribers": ch.get("subscribers", 0),
        }
        for ch in channels
    ]

    prompt = f"""Оцени Telegram-каналы для рекламы.

Продукт: {brief.get("product", "")}
ЦА: {brief.get("target_audience", "")}
Ниша: {brief.get("niche", "")}

Каналы:
{json.dumps(summaries, ensure_ascii=False)}

Верни JSON объект с массивом оценок (0-100):
{{"scores": [{{"username": "...", "score": 85, "reason": "почему подходит или нет"}}, ...]}}"""

    try:
        result = ask_json(client, prompt)
        scores = result.get("scores", result) if isinstance(result, dict) else result
        if not isinstance(scores, list):
            raise ValueError("не список")
        score_map = {s["username"]: s for s in scores}
        for ch in channels:
            s = score_map.get(ch["username"], {})
            ch["ai_score"] = int(s.get("score", 0))
            ch["ai_reason"] = s.get("reason", "")
        return sorted(channels, key=lambda x: x.get("ai_score", 0), reverse=True)
    except Exception as e:
        st.warning(f"Ошибка скоринга: {e}")
        for ch in channels:
            ch.setdefault("ai_score", 0)
            ch.setdefault("ai_reason", "")
        return channels


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
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, "")


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
    else:
        st.caption("✅ Groq API Key")
    if not bot_token:
        bot_token = st.text_input("Telegram Bot Token", type="password")
    else:
        st.caption("✅ Telegram Bot Token")
    if not telemetr_key:
        telemetr_key = st.text_input("Telemetr API Key", type="password", help="@telemetrio_api_bot в Telegram")
    else:
        st.caption("✅ Telemetr API Key")

    st.divider()
    st.markdown('<p style="font-size:0.7rem;color:#44446A;letter-spacing:0.1em;text-align:center;text-transform:uppercase;">TG Channel Finder · AI Media Planning</p>', unsafe_allow_html=True)


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
        <div class="brief-item"><div class="brief-key">Целевая аудитория</div><div class="brief-val" style="font-weight:400;font-size:0.9rem;color:#AAAACE">{brief.get("target_audience","—")}</div></div>
    </div>
    """, unsafe_allow_html=True)

    ref_handles = parse_handles(reference_raw)
    manual_handles = parse_handles(manual_raw)

    # 2. Поиск каналов
    ask_count = channel_count * 3
    mtproto_handles = []

    # Извлекаем ключевые слова из брифа
    with st.spinner("🧠 Извлекаю ключевые слова из брифа..."):
        keywords = extract_keywords(brief, client)
    if keywords:
        st.caption(f"Ключевые слова: {', '.join(keywords)}")

    # Поиск через Telemetr.io
    if telemetr_key:
        with st.spinner("🔍 Ищу каналы через Telemetr.io..."):
            mtproto_handles = search_telemetr(telemetr_key, keywords)
        if mtproto_handles:
            st.info(f"📡 Telemetr.io: найдено {len(mtproto_handles)} каналов")
        else:
            st.warning("Telemetr.io не вернул каналов — использую AI генерацию")
    else:
        st.caption("Telemetr API не настроен — использую AI генерацию")

    # 2б. AI генерация батчами по 40 (Groq не осиливает больше за раз)
    ai_needed = max(channel_count * 2 - len(mtproto_handles), channel_count)
    batches = max(1, min((ai_needed + 39) // 40, 4))
    ai_handles = []
    exclude_ai = set(mtproto_handles + ref_handles + manual_handles)
    for i in range(batches):
        with st.spinner(f"🤖 AI подбирает каналы (партия {i+1} из {batches})..."):
            batch = generate_channels(brief, ref_handles, client, 40,
                                      exclude=exclude_ai | set(ai_handles))
            ai_handles.extend(batch)
        if len(ai_handles) >= ai_needed:
            break

    if not mtproto_handles and not ai_handles:
        st.error("Не удалось найти каналы. Попробуй переформулировать бриф.")
        st.stop()

    all_handles = list(dict.fromkeys(mtproto_handles + ai_handles + ref_handles + manual_handles))
    tried = set(all_handles)

    # 3. Проверка раунд 1
    st.markdown(f'<div class="section-title" style="margin-top:1rem">📡 Проверка через Telegram — {len(all_handles)} каналов</div>', unsafe_allow_html=True)
    prog = st.progress(0)
    stat = st.empty()
    enriched = enrich_channels(bot_token, all_handles, prog, stat)
    stat.empty()
    prog.empty()

    # Если нашли меньше нужного — второй раунд
    if len(enriched) < channel_count:
        still_need = (channel_count - len(enriched)) * 3
        stat.markdown(f'<div class="status-bar">🔄 Найдено {len(enriched)} из {channel_count} — запускаю раунд 2...</div>', unsafe_allow_html=True)
        with st.spinner("🔍 Ищу ещё каналы (раунд 2)..."):
            ai_handles_2 = generate_channels(brief, ref_handles, client, still_need, exclude=tried)
        new_handles = [h for h in ai_handles_2 if h not in tried]
        tried.update(new_handles)
        if new_handles:
            st.markdown(f'<div class="section-title" style="margin-top:0.5rem">📡 Проверка раунд 2 — {len(new_handles)} каналов</div>', unsafe_allow_html=True)
            prog2 = st.progress(0)
            stat2 = st.empty()
            enriched2 = enrich_channels(bot_token, new_handles, prog2, stat2)
            stat2.empty()
            prog2.empty()
            enriched = enriched + enriched2
        stat.empty()

    found = len(enriched)
    not_found = len(tried) - found

    if found == 0:
        st.error("Ни один канал не прошёл проверку. Возможно, каналы приватные.")
        st.stop()

    st.success(f"✅ Найдено **{found}** каналов" + (f"  ·  не прошли проверку: {not_found}" if not_found else ""))

    with st.expander(f"👀 Все найденные каналы — {found} штук"):
        handles_text = "  ·  ".join(f"`@{c['username']}`" for c in enriched)
        st.markdown(f'<p style="font-family:var(--mono);font-size:0.78rem;color:#7070AA;line-height:2">{handles_text}</p>', unsafe_allow_html=True)

    # 4. Фильтры
    filtered_channels = [c for c in enriched if c.get("subscribers", 0) >= min_subs]
    if max_subs > 0:
        filtered_channels = [c for c in filtered_channels if c.get("subscribers", 0) <= max_subs]

    if not filtered_channels:
        st.warning("После фильтрации ничего не осталось.")
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
