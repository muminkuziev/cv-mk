"""CV_MK — Professional CV Builder Telegram Bot (Webhook mode, Render-ready)"""
import asyncio
import base64
import io
import logging
import os
import re
import textwrap
import uuid
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    FSInputFile, KeyboardButton, Message,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("cv_mk")

# ── Config ────────────────────────────────────────────────────────────────────
TOKEN      = os.environ["BOT_TOKEN"]
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
WH_PATH    = f"/wh/{TOKEN[-10:]}"

OUT_DIR = Path(__file__).parent / "output"
OUT_DIR.mkdir(exist_ok=True)

# ── Font (installed via apt-get in build command) ─────────────────────────────
def _load_font() -> str:
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]:
        if Path(p).exists():
            try:
                pdfmetrics.registerFont(TTFont("CF", p))
                log.info("Font yuklandi: %s", p)
                return "CF"
            except Exception:
                pass
    log.warning("Font topilmadi — Helvetica ishlatiladi (Kirill ko'rinmasligi mumkin)")
    return "Helvetica"

FONT = _load_font()

# ── Bot / Dispatcher ──────────────────────────────────────────────────────────
bot = Bot(token=TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ── FSM States ────────────────────────────────────────────────────────────────
class CV(StatesGroup):
    lang             = State()
    design           = State()
    full_name        = State()
    job              = State()
    job_custom       = State()
    phone            = State()
    email            = State()
    address          = State()
    photo            = State()
    summary          = State()
    experience       = State()
    education        = State()
    education_custom = State()
    skills           = State()
    languages        = State()

# ── Static data ───────────────────────────────────────────────────────────────
LANG_BTNS = ["🇺🇿 O'zbek", "🇷🇺 Русский", "🇬🇧 English"]
LANG_MAP   = {"🇺🇿 O'zbek": "uz", "🇷🇺 Русский": "ru", "🇬🇧 English": "en"}

DESIGN_BTNS = ["⬜ Minimalist", "🏢 Corporate", "🎨 Modern", "💎 Premium"]
DESIGN_MAP  = {
    "⬜ Minimalist": "minimalist",
    "🏢 Corporate":  "corporate",
    "🎨 Modern":     "modern",
    "💎 Premium":    "premium",
}

JOBS = {
    "uz": ["🧱 Kafelchi", "🔨 Quruvchi", "🎨 Malyar", "🧩 Gipsokartonchi",
           "⚡ Elektrik", "🚰 Santexnik", "🚗 Haydovchi", "🚕 Taksi haydovchisi",
           "📦 Omborchi", "👨‍🍳 Oshpaz", "🧹 Tozalovchi", "💻 IT mutaxassisi",
           "👷 Usta", "✏️ Boshqa kasb"],
    "ru": ["🧱 Плиточник", "🔨 Строитель", "🎨 Маляр", "🧩 Гипсокартонщик",
           "⚡ Электрик", "🚰 Сантехник", "🚗 Водитель", "🚕 Таксист",
           "📦 Складской работник", "👨‍🍳 Повар", "🧹 Уборщик", "💻 IT специалист",
           "👷 Мастер", "✏️ Другая профессия"],
    "en": ["🧱 Tiler", "🔨 Builder", "🎨 Painter", "🧩 Drywall Worker",
           "⚡ Electrician", "🚰 Plumber", "🚗 Driver", "🚕 Taxi Driver",
           "📦 Warehouse Worker", "👨‍🍳 Cook", "🧹 Cleaner", "💻 IT Specialist",
           "👷 Craftsman", "✏️ Other profession"],
}

EXPERIENCE = {
    "uz": ["Tajribasiz", "1–3 yil", "3–5 yil", "5–10 yil", "10+ yil"],
    "ru": ["Без опыта", "1–3 года", "3–5 лет", "5–10 лет", "10+ лет"],
    "en": ["No experience", "1–3 years", "3–5 years", "5–10 years", "10+ years"],
}

EDUCATION = {
    "uz": ["🏫 Maktab", "🏢 Kollej / Litsey", "🎓 Bakalavr", "🎓 Magistr", "✏️ Boshqa"],
    "ru": ["🏫 Школа", "🏢 Колледж / Лицей", "🎓 Бакалавр", "🎓 Магистр", "✏️ Другое"],
    "en": ["🏫 School", "🏢 College / Lyceum", "🎓 Bachelor", "🎓 Master", "✏️ Other"],
}

# ── Translations ──────────────────────────────────────────────────────────────
T = {
    "uz": {
        "welcome":    "👋 Salom! <b>CV_MK</b> botiga xush kelibsiz.\n\nMen sizga professional CV yaratishga yordam beraman.\n\n🌍 Tilni tanlang:",
        "design":     "🎨 CV dizaynini tanlang:",
        "name":       "👤 Ism va familiyangizni yozing:",
        "name_short": "⚠️ Ism juda qisqa. Qaytadan yozing:",
        "job":        "💼 Kasbingizni tanlang:",
        "job_custom": "✏️ Kasbingizni yozing:",
        "phone":      "📞 Telefon raqamingiz:",
        "email":      "📧 Email manzilingiz:",
        "address":    "📍 Manzilingiz (shahar, mamlakat):",
        "photo":      "📸 Fotosuratingizni yuboring yoki o'tkazib yuboring:",
        "summary":    "📝 O'zingiz haqida qisqacha yozing (2–3 jumla):",
        "experience": "🏢 Ish tajribangizni tanlang:",
        "education":  "🎓 Ta'lim darajangizni tanlang:",
        "edu_custom": "✏️ Ta'limingizni yozing:",
        "skills":     "🛠 Ko'nikmalaringizni yozing (vergul bilan):\nMasalan: Kafel, Suvoq, Gipsokarton",
        "langs":      "🌐 Qaysi tillarni bilasiz? (vergul bilan):\nMasalan: O'zbek, Rus",
        "creating":   "⏳ CV tayyorlanmoqda...",
        "pdf_ready":  "✅ PDF CV tayyor!",
        "html_ready": "🌐 HTML CV tayyor! Brauzerda ochish uchun yuklab oling.",
        "done":       "✅ CV tayyor!\n\n🔄 Yangi CV yaratish uchun /start bosing.",
        "cancelled":  "❌ Bekor qilindi.\n\n/start — qayta boshlash",
        "error":      "❌ Xatolik yuz berdi. Qaytadan urining: /start",
        "skip":       "⏭️ O'tkazib yuborish",
        "cancel":     "❌ Bekor qilish",
        "wrong":      "⚠️ Iltimos, tugmalardan birini tanlang:",
        "help":       "ℹ️ <b>CV_MK Bot</b> — professional CV yaratish boti\n\n/start — Yangi CV boshlash\n/cancel — Bekor qilish\n/help — Yordam",
        "labels": {
            "summary":    "O'zim haqimda",
            "experience": "Ish tajribasi",
            "education":  "Ta'lim",
            "skills":     "Ko'nikmalar",
            "languages":  "Tillar",
            "phone":      "Telefon",
            "email":      "Email",
            "address":    "Manzil",
            "footer":     "CV_MK Bot tomonidan yaratildi",
        },
    },
    "ru": {
        "welcome":    "👋 Привет! Добро пожаловать в <b>CV_MK</b> бот.\n\nЯ помогу создать профессиональное резюме.\n\n🌍 Выберите язык:",
        "design":     "🎨 Выберите дизайн резюме:",
        "name":       "👤 Напишите имя и фамилию:",
        "name_short": "⚠️ Имя слишком короткое. Напишите снова:",
        "job":        "💼 Выберите профессию:",
        "job_custom": "✏️ Напишите вашу профессию:",
        "phone":      "📞 Ваш номер телефона:",
        "email":      "📧 Ваш email:",
        "address":    "📍 Ваш адрес (город, страна):",
        "photo":      "📸 Отправьте фото или пропустите:",
        "summary":    "📝 Кратко о себе (2–3 предложения):",
        "experience": "🏢 Выберите опыт работы:",
        "education":  "🎓 Выберите уровень образования:",
        "edu_custom": "✏️ Напишите ваше образование:",
        "skills":     "🛠 Напишите навыки (через запятую):\nНапример: Плитка, Штукатурка",
        "langs":      "🌐 Какие языки знаете? (через запятую):\nНапример: Русский, Узбекский",
        "creating":   "⏳ Создаём резюме...",
        "pdf_ready":  "✅ PDF резюме готово!",
        "html_ready": "🌐 HTML резюме готово! Скачайте, чтобы открыть в браузере.",
        "done":       "✅ Резюме готово!\n\n🔄 Новое резюме — /start",
        "cancelled":  "❌ Отменено.\n\n/start — начать заново",
        "error":      "❌ Произошла ошибка. Попробуйте снова: /start",
        "skip":       "⏭️ Пропустить",
        "cancel":     "❌ Отмена",
        "wrong":      "⚠️ Пожалуйста, выберите один из вариантов:",
        "help":       "ℹ️ <b>CV_MK Bot</b> — бот для создания резюме\n\n/start — Новое CV\n/cancel — Отмена\n/help — Помощь",
        "labels": {
            "summary":    "Обо мне",
            "experience": "Опыт работы",
            "education":  "Образование",
            "skills":     "Навыки",
            "languages":  "Языки",
            "phone":      "Телефон",
            "email":      "Email",
            "address":    "Адрес",
            "footer":     "Создано CV_MK Bot",
        },
    },
    "en": {
        "welcome":    "👋 Hello! Welcome to <b>CV_MK</b> bot.\n\nI'll help you create a professional CV.\n\n🌍 Choose your language:",
        "design":     "🎨 Choose a CV design:",
        "name":       "👤 Enter your full name:",
        "name_short": "⚠️ Name is too short. Please write again:",
        "job":        "💼 Choose your profession:",
        "job_custom": "✏️ Write your profession:",
        "phone":      "📞 Your phone number:",
        "email":      "📧 Your email address:",
        "address":    "📍 Your address (city, country):",
        "photo":      "📸 Send a photo or skip:",
        "summary":    "📝 Write a short professional summary (2–3 sentences):",
        "experience": "🏢 Choose your work experience:",
        "education":  "🎓 Choose your education level:",
        "edu_custom": "✏️ Write your education:",
        "skills":     "🛠 Write your skills (comma-separated):\nExample: Tiling, Plastering",
        "langs":      "🌐 Languages you know (comma-separated):\nExample: Uzbek, Russian",
        "creating":   "⏳ Creating your CV...",
        "pdf_ready":  "✅ PDF CV is ready!",
        "html_ready": "🌐 HTML CV is ready! Download to open in browser.",
        "done":       "✅ CV is ready!\n\n🔄 Press /start for a new CV.",
        "cancelled":  "❌ Cancelled.\n\n/start — start over",
        "error":      "❌ An error occurred. Try again: /start",
        "skip":       "⏭️ Skip",
        "cancel":     "❌ Cancel",
        "wrong":      "⚠️ Please choose one of the options:",
        "help":       "ℹ️ <b>CV_MK Bot</b> — professional CV builder\n\n/start — New CV\n/cancel — Cancel\n/help — Help",
        "labels": {
            "summary":    "About Me",
            "experience": "Work Experience",
            "education":  "Education",
            "skills":     "Skills",
            "languages":  "Languages",
            "phone":      "Phone",
            "email":      "Email",
            "address":    "Address",
            "footer":     "Created by CV_MK Bot",
        },
    },
}

# ── Keyboards ─────────────────────────────────────────────────────────────────
def _kb(items: list[str], cols: int = 2) -> ReplyKeyboardMarkup:
    rows = [items[i:i + cols] for i in range(0, len(items), cols)]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in rows],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def kb_lang():         return _kb(LANG_BTNS, cols=1)
def kb_design():       return _kb(DESIGN_BTNS, cols=2)
def kb_jobs(l):        return _kb(JOBS[l], cols=2)
def kb_exp(l):         return _kb(EXPERIENCE[l], cols=1)
def kb_edu(l):         return _kb(EDUCATION[l], cols=1)
def kb_cancel(l):      return _kb([T[l]["cancel"]], cols=1)
def kb_skip_cancel(l): return _kb([T[l]["skip"], T[l]["cancel"]], cols=2)

# ── Helpers ───────────────────────────────────────────────────────────────────
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FFFF\U00002600-\U000027FF\U0000FE00-\U0000FE0F\U0001FA00-\U0001FAFF]+",
    re.UNICODE,
)

def uid() -> str:
    return uuid.uuid4().hex[:12]

def safe(v) -> str:
    return str(v or "").strip()

def wraptext(text: str, width: int) -> list[str]:
    result = []
    for line in safe(text).split("\n"):
        result.extend(textwrap.wrap(line, width) or [""])
    return result

def is_cancel(text: str, lang: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ["bekor", "отмена", "cancel", "❌"]) or text == T[lang]["cancel"]

def is_skip(text: str, lang: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ["skip", "пропустить", "otkazib", "⏭"]) or text == T[lang]["skip"]

def strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text or "").strip(" –—-")

def cleanup(*paths):
    for p in paths:
        try:
            if p:
                Path(p).unlink(missing_ok=True)
        except Exception:
            pass

def photo_b64(path: str) -> str:
    try:
        p = Path(path)
        if p.exists():
            ext  = p.suffix.lower().lstrip(".")
            mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "jpeg")
            return f"data:image/{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
    except Exception:
        pass
    return ""

# ── HTML Generator ────────────────────────────────────────────────────────────
THEMES = {
    "minimalist": {"bg": "#ffffff", "sidebar": "#f1f5f9", "text": "#111827", "accent": "#2563eb"},
    "corporate":  {"bg": "#f8fafc", "sidebar": "#e2e8f0", "text": "#0f172a", "accent": "#1d4ed8"},
    "modern":     {"bg": "#0f172a", "sidebar": "#1e293b", "text": "#f1f5f9", "accent": "#ec4899"},
    "premium":    {"bg": "#080b18", "sidebar": "#0f1629", "text": "#f5f0e8", "accent": "#f59e0b"},
}

def generate_html(data: dict, fid: str) -> Path:
    import html as h
    lang = data.get("lang", "uz")
    lbl  = T[lang]["labels"]
    th   = THEMES.get(data.get("design", "minimalist"), THEMES["minimalist"])

    def e(v): return h.escape(safe(v))
    def tags(v: str) -> str:
        return "".join(
            f'<span class="tag">{e(x.strip())}</span>'
            for x in safe(v).replace(",", "\n").split("\n") if x.strip()
        )

    photo_tag = ""
    if data.get("photo_path"):
        b64 = photo_b64(data["photo_path"])
        if b64:
            photo_tag = f'<img class="photo" src="{b64}" alt="photo">'
    photo_tag = photo_tag or '<div class="photo-ph">👤</div>'

    html_out = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(data.get("full_name"))} — CV</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{th["bg"]};font-family:'Segoe UI',Arial,sans-serif;color:{th["text"]};min-height:100vh}}
.wrap{{max-width:860px;margin:32px auto;background:{th["bg"]};border-radius:16px;
  box-shadow:0 20px 60px rgba(0,0,0,.25);overflow:hidden;display:grid;grid-template-columns:250px 1fr}}
.side{{background:{th["sidebar"]};padding:32px 20px;display:flex;flex-direction:column;gap:20px}}
.photo{{width:110px;height:110px;border-radius:50%;object-fit:cover;
  border:3px solid {th["accent"]};display:block;margin:0 auto}}
.photo-ph{{width:110px;height:110px;border-radius:50%;background:{th["accent"]}20;
  border:2px dashed {th["accent"]};display:flex;align-items:center;justify-content:center;
  font-size:40px;margin:0 auto}}
.sb h3{{font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  color:{th["accent"]};margin-bottom:6px;font-weight:700}}
.sb .val{{font-size:12px;line-height:1.7;opacity:.85;word-break:break-all}}
.tag{{display:inline-block;background:{th["accent"]}20;color:{th["accent"]};
  border-radius:6px;padding:2px 8px;font-size:11px;margin:2px;font-weight:500}}
.main{{padding:36px 32px;display:flex;flex-direction:column;gap:20px}}
.hdr{{border-bottom:2px solid {th["accent"]};padding-bottom:16px}}
.hdr h1{{font-size:26px;font-weight:800}}
.hdr .role{{color:{th["accent"]};font-size:14px;font-weight:600;margin-top:4px}}
.sec h2{{font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:{th["accent"]};font-weight:700;margin-bottom:8px;
  display:flex;align-items:center;gap:6px}}
.sec h2::after{{content:"";flex:1;height:1px;background:{th["accent"]}40}}
.sec p{{font-size:13px;line-height:1.7;white-space:pre-line;opacity:.9}}
.foot{{text-align:center;font-size:10px;opacity:.4;
  padding:12px 0 0;border-top:1px solid {th["accent"]}20}}
@media(max-width:640px){{.wrap{{grid-template-columns:1fr}}}}
@media print{{body{{background:#fff}}.wrap{{box-shadow:none;margin:0;border-radius:0}}}}
</style></head>
<body><div class="wrap">
<aside class="side">
  {photo_tag}
  <div class="sb"><h3>📞 {lbl["phone"]}</h3><div class="val">{e(data.get("phone","—"))}</div></div>
  <div class="sb"><h3>📧 {lbl["email"]}</h3><div class="val">{e(data.get("email","—"))}</div></div>
  <div class="sb"><h3>📍 {lbl["address"]}</h3><div class="val">{e(data.get("address","—"))}</div></div>
  <div class="sb"><h3>🌐 {lbl["languages"]}</h3><div>{tags(data.get("languages",""))}</div></div>
  <div class="sb"><h3>🛠 {lbl["skills"]}</h3><div>{tags(data.get("skills",""))}</div></div>
</aside>
<main class="main">
  <div class="hdr">
    <h1>{e(data.get("full_name","—"))}</h1>
    <div class="role">{e(data.get("job","—"))}</div>
  </div>
  <div class="sec"><h2>{lbl["summary"]}</h2><p>{e(data.get("summary","—"))}</p></div>
  <div class="sec"><h2>{lbl["experience"]}</h2><p>{e(data.get("experience","—"))}</p></div>
  <div class="sec"><h2>{lbl["education"]}</h2><p>{e(data.get("education","—"))}</p></div>
  <div class="foot">{lbl["footer"]} • {datetime.now().strftime("%d.%m.%Y")}</div>
</main></div></body></html>"""

    out = OUT_DIR / f"cv_{fid}.html"
    out.write_text(html_out, encoding="utf-8")
    return out

# ── PDF Generator ─────────────────────────────────────────────────────────────
PDF_PAL = {
    "minimalist": {"accent": (0.15, 0.39, 0.92), "dark": False},
    "corporate":  {"accent": (0.05, 0.20, 0.45), "dark": False},
    "modern":     {"accent": (0.90, 0.20, 0.55), "dark": True},
    "premium":    {"accent": (0.96, 0.62, 0.04), "dark": True},
}

def generate_pdf(data: dict, fid: str) -> Path:
    out  = OUT_DIR / f"cv_{fid}.pdf"
    c    = canvas.Canvas(str(out), pagesize=A4)
    W, H = A4
    lang = data.get("lang", "uz")
    lbl  = T[lang]["labels"]
    pal  = PDF_PAL.get(data.get("design", "minimalist"), PDF_PAL["minimalist"])
    acc  = pal["accent"]
    dark = pal["dark"]

    BG  = (0.04, 0.06, 0.12) if dark else (1.0, 1.0, 1.0)
    TXT = (0.95, 0.95, 0.95) if dark else (0.07, 0.07, 0.12)
    SBG = tuple(max(0, x - 0.06) for x in BG) if dark else (0.945, 0.953, 0.965)
    SW  = 195

    def fill_bg():
        c.setFillColorRGB(*BG);  c.rect(0, 0, W, H, fill=1, stroke=0)
        c.setFillColorRGB(*SBG); c.rect(0, 0, SW, H, fill=1, stroke=0)

    # Page 1 base
    fill_bg()
    c.setFillColorRGB(*acc); c.rect(0, H - 40, W, 40, fill=1, stroke=0)
    c.setFillColorRGB(*SBG); c.rect(0, 0, SW, H - 40, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1); c.setFont(FONT, 11)
    c.drawString(14, H - 26, "CV_MK BOT")

    # ── Main content area ─────────────────────────────────────────────────────
    y = H - 68
    c.setFillColorRGB(*TXT);  c.setFont(FONT, 20)
    c.drawString(SW + 14, y, safe(data.get("full_name"))[:40]); y -= 22
    c.setFillColorRGB(*acc);  c.setFont(FONT, 12)
    c.drawString(SW + 14, y, safe(data.get("job"))[:50]); y -= 16
    c.setStrokeColorRGB(*acc); c.setLineWidth(1.2)
    c.line(SW + 14, y, W - 20, y); y -= 14

    def new_page():
        nonlocal y
        c.showPage()
        fill_bg()
        y = H - 40

    def section(title: str, body: str):
        nonlocal y
        if y < 90:
            new_page()
        c.setFillColorRGB(*acc);   c.setFont(FONT, 10)
        c.drawString(SW + 14, y, title.upper()); y -= 4
        c.setStrokeColorRGB(*acc); c.setLineWidth(0.4)
        c.line(SW + 14, y, W - 20, y); y -= 13
        c.setFillColorRGB(*TXT);   c.setFont(FONT, 9)
        for line in wraptext(body, 66):
            if y < 50:
                new_page()
                c.setFillColorRGB(*TXT); c.setFont(FONT, 9)
            c.drawString(SW + 18, y, line); y -= 13
        y -= 8

    section(lbl["summary"],    safe(data.get("summary")))
    section(lbl["experience"], safe(data.get("experience")))
    section(lbl["education"],  safe(data.get("education")))

    # ── Sidebar ───────────────────────────────────────────────────────────────
    sy = H - 98       # photo circle center (top = sy+41 = H-57, below header H-40)
    px = SW // 2
    pr = 38

    c.setFillColorRGB(*acc); c.circle(px, sy, pr + 3, fill=1, stroke=0)
    c.setFillColorRGB(*SBG); c.circle(px, sy, pr, fill=1, stroke=0)

    photo_path = data.get("photo_path", "")
    if photo_path and Path(photo_path).exists():
        try:
            from PIL import Image as PILImage
            from reportlab.lib.utils import ImageReader
            img = PILImage.open(photo_path).convert("RGB")
            sz  = min(img.size)
            lf  = (img.width - sz) // 2
            tp  = (img.height - sz) // 2
            img = img.crop((lf, tp, lf + sz, tp + sz)).resize((84, 84))
            buf = io.BytesIO(); img.save(buf, format="JPEG"); buf.seek(0)
            c.drawImage(ImageReader(buf), px - pr, sy - pr,
                        width=pr * 2, height=pr * 2, mask="auto")
        except Exception as e:
            log.warning("PDF foto xatosi: %s", e)

    sy -= pr + 18

    def st(title: str):
        nonlocal sy
        if sy < 50:
            return
        c.setFillColorRGB(*acc); c.setFont(FONT, 8)
        c.drawString(8, sy, title.upper()); sy -= 13

    def sv(text: str):
        nonlocal sy
        c.setFillColorRGB(*TXT); c.setFont(FONT, 8)
        for line in wraptext(text, 28):
            if sy < 45:
                break
            c.drawString(8, sy, line); sy -= 11

    st(lbl["phone"]);     sv(safe(data.get("phone")));     sy -= 4
    st(lbl["email"]);     sv(safe(data.get("email")));     sy -= 4
    st(lbl["address"]);   sv(safe(data.get("address")));   sy -= 4
    st(lbl["languages"]); sv(safe(data.get("languages"))); sy -= 4
    st(lbl["skills"]);    sv(safe(data.get("skills")))

    c.setFillColorRGB(*acc); c.setFont(FONT, 7)
    c.drawString(8, 14, f"{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}")
    c.save()
    return out

# ── Finalize: CV yuborish ─────────────────────────────────────────────────────
async def finalize(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    fid  = uid()
    pdf_path = html_path = None

    await msg.answer(T[lang]["creating"], reply_markup=ReplyKeyboardRemove())
    try:
        pdf_path  = generate_pdf(data, fid)
        html_path = generate_html(data, fid)
        await msg.answer_document(FSInputFile(pdf_path),  caption=T[lang]["pdf_ready"])
        await msg.answer_document(FSInputFile(html_path), caption=T[lang]["html_ready"])
        await msg.answer(T[lang]["done"], reply_markup=kb_lang(), parse_mode="HTML")
    except Exception as e:
        log.exception("CV yaratishda xatolik: %s", e)
        await msg.answer(T[lang]["error"], reply_markup=kb_lang())
    finally:
        to_del = [p for p in [pdf_path, html_path] if p]
        if data.get("photo_path"):
            to_del.append(Path(data["photo_path"]))
        cleanup(*to_del)
        await state.clear()
        await state.set_state(CV.lang)

# ── Cancel helper ─────────────────────────────────────────────────────────────
async def do_cancel(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.clear()
    await state.set_state(CV.lang)
    await msg.answer(T[lang]["cancelled"], reply_markup=kb_lang())

# ── Commands ──────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CV.lang)
    await msg.answer(T["uz"]["welcome"], reply_markup=kb_lang(), parse_mode="HTML")
    log.info("/start user=%s", msg.from_user.id if msg.from_user else "?")

@dp.message(Command("cancel"))
async def cmd_cancel(msg: Message, state: FSMContext):
    await do_cancel(msg, state)

@dp.message(Command("help"))
async def cmd_help(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await msg.answer(T[lang]["help"], parse_mode="HTML")

# ── FSM: Til ──────────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.lang), F.text.in_(LANG_BTNS))
async def h_lang(msg: Message, state: FSMContext):
    lang = LANG_MAP[msg.text]
    await state.update_data(lang=lang)
    await state.set_state(CV.design)
    await msg.answer(T[lang]["design"], reply_markup=kb_design())

# ── FSM: Dizayn ───────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.design), F.text.in_(DESIGN_BTNS))
async def h_design(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    await state.update_data(design=DESIGN_MAP[msg.text])
    await state.set_state(CV.full_name)
    await msg.answer(T[lang]["name"], reply_markup=kb_cancel(lang))

# ── FSM: Ism ──────────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.full_name), F.text)
async def h_name(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    if len(msg.text.strip()) < 3:
        return await msg.answer(T[lang]["name_short"], reply_markup=kb_cancel(lang))
    await state.update_data(full_name=msg.text.strip())
    await state.set_state(CV.job)
    await msg.answer(T[lang]["job"], reply_markup=kb_jobs(lang))

# ── FSM: Kasb ─────────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.job), F.text)
async def h_job(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    if msg.text not in JOBS[lang]:
        return await msg.answer(T[lang]["wrong"], reply_markup=kb_jobs(lang))
    if any(w in msg.text.lower() for w in ["boshqa", "другая", "other", "✏"]):
        await state.set_state(CV.job_custom)
        return await msg.answer(T[lang]["job_custom"], reply_markup=kb_cancel(lang))
    await state.update_data(job=strip_emoji(msg.text))
    await state.set_state(CV.phone)
    await msg.answer(T[lang]["phone"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.job_custom), F.text)
async def h_job_custom(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(job=msg.text.strip())
    await state.set_state(CV.phone)
    await msg.answer(T[lang]["phone"], reply_markup=kb_cancel(lang))

# ── FSM: Telefon → Email → Manzil ────────────────────────────────────────────
@dp.message(StateFilter(CV.phone), F.text)
async def h_phone(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(phone=msg.text.strip())
    await state.set_state(CV.email)
    await msg.answer(T[lang]["email"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.email), F.text)
async def h_email(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(email=msg.text.strip())
    await state.set_state(CV.address)
    await msg.answer(T[lang]["address"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.address), F.text)
async def h_address(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(address=msg.text.strip())
    await state.set_state(CV.photo)
    await msg.answer(T[lang]["photo"], reply_markup=kb_skip_cancel(lang))

# ── FSM: Foto ─────────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.photo), F.photo)
async def h_photo(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    try:
        file = await bot.get_file(msg.photo[-1].file_id)
        path = OUT_DIR / f"p_{uid()}.jpg"
        await bot.download_file(file.file_path, destination=path)
        await state.update_data(photo_path=str(path))
    except Exception as e:
        log.warning("Foto yuklashda xatolik: %s", e)
        await state.update_data(photo_path="")
    await state.set_state(CV.summary)
    await msg.answer(T[lang]["summary"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.photo), F.text)
async def h_photo_text(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    if is_skip(msg.text, lang):
        await state.update_data(photo_path="")
        await state.set_state(CV.summary)
        return await msg.answer(T[lang]["summary"], reply_markup=kb_cancel(lang))
    await msg.answer(T[lang]["photo"], reply_markup=kb_skip_cancel(lang))

# ── FSM: Summary → Tajriba → Ta'lim → Ko'nikmalar → Tillar ──────────────────
@dp.message(StateFilter(CV.summary), F.text)
async def h_summary(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(summary=msg.text.strip())
    await state.set_state(CV.experience)
    await msg.answer(T[lang]["experience"], reply_markup=kb_exp(lang))

@dp.message(StateFilter(CV.experience), F.text)
async def h_experience(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    if msg.text not in EXPERIENCE[lang]:
        return await msg.answer(T[lang]["wrong"], reply_markup=kb_exp(lang))
    await state.update_data(experience=msg.text)
    await state.set_state(CV.education)
    await msg.answer(T[lang]["education"], reply_markup=kb_edu(lang))

@dp.message(StateFilter(CV.education), F.text)
async def h_education(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    if msg.text not in EDUCATION[lang]:
        return await msg.answer(T[lang]["wrong"], reply_markup=kb_edu(lang))
    if any(w in msg.text.lower() for w in ["boshqa", "другое", "other", "✏"]):
        await state.set_state(CV.education_custom)
        return await msg.answer(T[lang]["edu_custom"], reply_markup=kb_cancel(lang))
    await state.update_data(education=strip_emoji(msg.text))
    await state.set_state(CV.skills)
    await msg.answer(T[lang]["skills"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.education_custom), F.text)
async def h_edu_custom(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(education=msg.text.strip())
    await state.set_state(CV.skills)
    await msg.answer(T[lang]["skills"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.skills), F.text)
async def h_skills(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(skills=msg.text.strip())
    await state.set_state(CV.languages)
    await msg.answer(T[lang]["langs"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.languages), F.text)
async def h_languages(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(languages=msg.text.strip())
    await finalize(msg, state)

# ── Catch-all ─────────────────────────────────────────────────────────────────
@dp.message()
async def catch_all(msg: Message, state: FSMContext):
    data    = await state.get_data()
    lang    = data.get("lang", "uz")
    current = await state.get_state()

    if not current or current == CV.lang.state:
        await state.clear()
        await state.set_state(CV.lang)
        await msg.answer(T[lang]["welcome"], reply_markup=kb_lang(), parse_mode="HTML")
    elif current == CV.design.state:
        await msg.answer(T[lang]["wrong"], reply_markup=kb_design())
    elif current == CV.photo.state:
        await msg.answer(T[lang]["photo"], reply_markup=kb_skip_cancel(lang))
    else:
        await msg.answer(T[lang]["wrong"])

# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    log.info("CV_MK Bot ishga tushmoqda...")
    try:
        me = await bot.get_me()
        log.info("Bot: @%s (id=%s)", me.username, me.id)
    except Exception as e:
        log.critical("BOT_TOKEN xato: %s", e)
        raise

    if RENDER_URL:
        # ── Webhook mode (Render production) ──────────────────────────────────
        from aiohttp import web as aio_web
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

        webhook_url = f"{RENDER_URL}{WH_PATH}"
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        log.info("Webhook: %s", webhook_url)

        app = aio_web.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WH_PATH)
        setup_application(app, dp, bot=bot)

        async def health(_): return aio_web.Response(text="OK")
        app.router.add_get("/", health)
        app.router.add_get("/health", health)

        runner = aio_web.AppRunner(app)
        await runner.setup()
        port = int(os.getenv("PORT", 10000))
        await aio_web.TCPSite(runner, "0.0.0.0", port).start()
        log.info("Webhook server port=%s", port)
        await asyncio.Event().wait()
    else:
        # ── Polling mode (local dev) ───────────────────────────────────────────
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("Polling (local dev)...")
        await dp.start_polling(bot, allowed_updates=["message"])

if __name__ == "__main__":
    asyncio.run(main())
