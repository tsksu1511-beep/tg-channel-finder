import streamlit as st
import httpx
import pandas as pd
import json
import time
import os
from io import BytesIO
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

TG_API = "https://api.telegram.org/bot{token}/{method}"
GROQ_MODEL = "llama-3.3-70b-versatile"


# ─── Groq AI ──────────────────────────────────────────────────────────────────

def get_client(api_key: str) -> Groq:
    return Groq(api_key=api_key)


def ask_json(client: Groq, prompt: str):
    """Ask Groq and return parsed JSON. Raises on failure."""
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


def generate_channels(brief: dict, reference_channels: list, client: Groq, count: int) -> list:
    ref_block = ""
    if reference_channels:
        ref_block = f"Каналы-ориентиры: {', '.join(reference_channels)}. Подбери похожие по аудитории.\n"

    prompt = f"""Ты медиабайер в Telegram. Подбери русскоязычные Telegram-каналы для рекламы.

Продукт: {brief.get("product", "")}
Ниша: {brief.get("niche", "")}
Целевая аудитория: {brief.get("target_audience", "")}
Пол: {brief.get("gender", "все")}
Возраст: {brief.get("age_range", "")}
{ref_block}
Требования:
- Только реально существующие публичные русскоязычные Telegram-каналы с username
- Аудитория соответствует описанию
- Разный охват: крупные (500к+), средние (50-500к), нишевые (10-50к)

Верни JSON объект с массивом из {count} username-ов (без @):
{{"channels": ["username1", "username2", ...]}}"""

    try:
        result = ask_json(client, prompt)
        items = result.get("channels", result) if isinstance(result, dict) else result
        if isinstance(items, list):
            return [str(u).lstrip("@").strip() for u in items if u]
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

Верни JSON объект с массивом оценок (0-100) для каждого канала:
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
        stat.text(f"📡 Проверяю @{uname} ({i+1}/{total})...")
        info = tg_get_chat(bot_token, uname)
        if info and info.get("type") in ("channel", "supergroup"):
            count = tg_get_member_count(bot_token, uname)
            results.append({
                "username": uname,
                "title": info.get("title", ""),
                "description": info.get("description", ""),
                "subscribers": count,
            })
        time.sleep(0.15)
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


# ─── UI ───────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="TG Channel Finder", page_icon="📡", layout="wide")

st.title("📡 Telegram Channel Finder")

def get_secret(key: str) -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, "")

with st.sidebar:
    st.header("🔧 Параметры")
    channel_count = st.slider("Каналов для подбора", 20, 100, 50)
    max_subs = st.number_input("Макс. подписчики (0 = без лимита)", min_value=0, value=0, step=10000)
    min_subs = 1000  # Telegram Ads: минимум 1000 подписчиков

    # Ключи — только для локальной разработки, на сервере берутся из secrets
    groq_key = get_secret("GROQ_API_KEY")
    bot_token = get_secret("TELEGRAM_BOT_TOKEN")
    if not groq_key or not bot_token:
        st.divider()
        st.caption("⚙️ Локальная разработка")
        if not groq_key:
            groq_key = st.text_input("Groq API Key", type="password",
                                     help="console.groq.com (бесплатно)")
        if not bot_token:
            bot_token = st.text_input("Telegram Bot Token", type="password")

col1, col2 = st.columns([1, 1], gap="large")
brief_text = ""

with col1:
    st.subheader("📋 Бриф проекта")
    tab_text, tab_pdf = st.tabs(["Текст", "PDF"])
    with tab_text:
        brief_text = st.text_area("Вставь текст брифа", height=220,
            placeholder="Продукт, целевая аудитория, цели рекламы, гео...")
    with tab_pdf:
        pdf_file = st.file_uploader("Загрузи PDF", type=["pdf"])
        if pdf_file:
            extracted = extract_pdf_text(pdf_file)
            if extracted:
                brief_text = extracted
                st.success(f"Прочитано {len(extracted)} символов")

with col2:
    st.subheader("🎯 Каналы-ориентиры (необязательно)")
    reference_raw = st.text_area("Конкуренты или каналы где реклама работала",
        height=120, placeholder="@channel1\n@channel2")
    st.subheader("➕ Свои каналы (необязательно)")
    manual_raw = st.text_area("Добавить вручную", height=80, placeholder="@mychannel")

st.divider()
run = st.button("🔍 Найти каналы", type="primary", use_container_width=True)

if run:
    errors = []
    if not groq_key:
        errors.append("Нет Groq API Key")
    if not bot_token:
        errors.append("Нет Telegram Bot Token")
    if not brief_text:
        errors.append("Введи бриф")
    for e in errors:
        st.error(e)
    if errors:
        st.stop()

    client = get_client(groq_key)

    # 1. Анализ брифа
    with st.spinner("🤖 Анализирую бриф..."):
        brief = analyze_brief(brief_text, client)

    if not brief:
        st.error("Не удалось проанализировать бриф. Проверь Groq API Key.")
        st.stop()

    with st.expander("📊 Как AI понял бриф", expanded=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Продукт", brief.get("product", "—"))
        c2.metric("Ниша", brief.get("niche", "—"))
        c3.metric("Гео", brief.get("geo", "—"))
        st.write("**ЦА:**", brief.get("target_audience", "—"))
        st.write("**Пол / Возраст:**", brief.get("gender", "—"), "/", brief.get("age_range", "—"))

    ref_handles = parse_handles(reference_raw)
    manual_handles = parse_handles(manual_raw)

    # 2. Генерация каналов
    with st.spinner(f"🤖 AI подбирает {channel_count} каналов..."):
        ai_handles = generate_channels(brief, ref_handles, client, channel_count)

    if not ai_handles:
        st.error("AI не вернул список каналов. Попробуй переформулировать бриф.")
        st.stop()

    with st.expander(f"👀 Что предложил AI — {len(ai_handles)} каналов"):
        st.write(", ".join(f"@{h}" for h in ai_handles))

    all_handles = list(dict.fromkeys(ai_handles + ref_handles + manual_handles))

    # 3. Проверка через Telegram
    st.write(f"**Проверяю {len(all_handles)} каналов через Telegram...**")
    prog = st.progress(0)
    stat = st.empty()
    enriched = enrich_channels(bot_token, all_handles, prog, stat)
    stat.empty()
    prog.empty()

    found = len(enriched)
    not_found = len(all_handles) - found
    if found == 0:
        st.error("Ни один канал не прошёл проверку Telegram. Возможно каналы приватные или бот заблокирован.")
        st.stop()

    st.success(f"Найдено: **{found}** каналов" + (f" | не найдено/приватных: {not_found}" if not_found else ""))

    # 4. Фильтры
    filtered_channels = enriched
    if min_subs > 0:
        filtered_channels = [c for c in filtered_channels if c.get("subscribers", 0) >= min_subs]
    if max_subs > 0:
        filtered_channels = [c for c in filtered_channels if c.get("subscribers", 0) <= max_subs]

    if not filtered_channels:
        st.warning("После фильтрации ничего не осталось — убери ограничения по подписчикам.")
        st.stop()

    # 5. Скоринг
    with st.spinner(f"🤖 Оцениваю {len(filtered_channels)} каналов..."):
        scored = score_channels(filtered_channels, brief, client)

    st.session_state["scored"] = scored
    st.session_state["brief"] = brief

# ── Результаты ──
if "scored" in st.session_state:
    scored = st.session_state["scored"]

    st.subheader(f"✅ Результаты — {len(scored)} каналов")

    rf1, rf2 = st.columns(2)
    with rf1:
        min_score_f = st.slider("Мин. оценка AI", 0, 100, 30, key="score_f")
    with rf2:
        sort_by = st.selectbox("Сортировка", ["Оценка AI", "Подписчики"], key="sort_f")

    df = to_df(scored)
    result = df[df["Оценка"] >= min_score_f]
    sort_col = "Оценка" if sort_by == "Оценка AI" else "Подписчики"
    result = result.sort_values(sort_col, ascending=False)

    st.dataframe(
        result,
        use_container_width=True,
        height=520,
        column_config={
            "Оценка": st.column_config.ProgressColumn("Оценка AI", min_value=0, max_value=100, format="%d"),
            "Подписчики": st.column_config.NumberColumn("Подписчики", format="%d"),
            "Ссылка": st.column_config.LinkColumn("Открыть"),
        },
        hide_index=True,
    )
    st.caption(f"Показано {len(result)} из {len(df)}")

    e1, e2 = st.columns(2)
    with e1:
        st.download_button("📥 CSV", result.to_csv(index=False).encode("utf-8-sig"),
                           "tg_channels.csv", "text/csv", use_container_width=True)
    with e2:
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            result.to_excel(writer, index=False, sheet_name="Каналы")
        st.download_button("📥 Excel", buf.getvalue(), "tg_channels.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
