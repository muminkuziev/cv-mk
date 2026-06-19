import os
import asyncio
import threading
import textwrap
import base64
import uuid
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.types import (
    Message, KeyboardButton, ReplyKeyboardMarkup,
    ReplyKeyboardRemove, FSInputFile,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cv_mk")

# ── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi! Render > Environment Variables ga qo'ying.")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Flask (health check) ─────────────────────────────────────────────────────
web = Flask(__name__)

@web.route("/")
def home():
    return "CV_MK Bot ishlayapti", 200

@web.route("/health")
def health():
    return "OK", 200

def run_flask():
    port = int(os.getenv("PORT", 10000))
    web.run(host="0.0.0.0", port=port, use_reloader=False)

# ── Bot / Dispatcher ──────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ── FSM States ───────────────────────────────────────────────────────────────
class CV(StatesGroup):
    lang           = State()
    design         = State()
    full_name      = State()
    job            = State()
    custom_job     = State()
    phone          = State()
    email          = State()
    address        = State()
    photo          = State()
    summary        = State()
    experience     = State()
    education      = State()
    custom_edu     = State()
    skills         = State()
    languages      = State()

# ── Static data ───────────────────────────────────────────────────────────────
LANG_BUTTONS = ["🇺🇿 O'zbek", "🇷🇺 Русский", "🇬🇧 English"]
LANG_MAP     = {"🇺🇿 O'zbek": "uz", "🇷🇺 Русский": "ru", "🇬🇧 English": "en"}

DESIGN_KEYS = ["⬜ Minimalist", "🏢 Corporate", "🎨 Modern", "💎 Premium"]
DESIGN_MAP  = {
    "⬜ Minimalist": "minimalist",
    "🏢 Corporate":  "corporate",
    "🎨 Modern":     "modern",
    "💎 Premium":    "premium",
}

JOBS = {
    "uz": ["🧱 Kafelchi","🔨 Quruvchi","🎨 Malyar","🧩 Gipsokartonchi",
           "⚡ Elektrik","🚰 Santexnik","🚗 Haydovchi","🚕 Taksi haydovchisi",
           "📦 Omborchi","👨‍🍳 Oshpaz","✏️ Boshqa kasb"],
    "ru": ["🧱 Плиточник","🔨 Строитель","🎨 Маляр","🧩 Гипсокартонщик",
           "⚡ Электрик","🚰 Сантехник","🚗 Водитель","🚕 Таксист",
           "📦 Складской работник","👨‍🍳 Повар","✏️ Другая профессия"],
    "en": ["🧱 Tiler","🔨 Builder","🎨 Painter","🧩 Drywall Worker",
           "⚡ Electrician","🚰 Plumber","🚗 Driver","🚕 Taxi Driver",
           "📦 Warehouse Worker","👨‍🍳 Cook","✏️ Other profession"],
}

EXPERIENCE = {
    "uz": ["🔹 Tajribasiz","🔹 1–3 yil","🔹 3–5 yil","🔹 5–10 yil","🔹 10+ yil"],
    "ru": ["🔹 Без опыта","🔹 1–3 года","🔹 3–5 лет","🔹 5–10 лет","🔹 10+ лет"],
    "en": ["🔹 No experience","🔹 1–3 years","🔹 3–5 years","🔹 5–10 years","🔹 10+ years"],
}

EDUCATION = {
    "uz": ["🏫 O'rta maktab","🏢 Kollej / Litsey","🎓 Bakalavr","🎓 Magistr","✏️ Boshqa"],
    "ru": ["🏫 Средняя школа","🏢 Колледж / Лицей","🎓 Бакалавр","🎓 Магистр","✏️ Другое"],
    "en": ["🏫 Secondary School","🏢 College / Lyceum","🎓 Bachelor","🎓 Master","✏️ Other"],
}

# ── Translations ──────────────────────────────────────────────────────────────
T = {
    "uz": {
        "welcome":      "👋 Salom! CV_MK botiga xush kelibsiz.\n\n🌍 Tilni tanlang:",
        "choose_design":"🎨 CV dizaynini tanlang:",
        "ask_name":     "👤 Ism va familiyangizni yozing:",
        "name_short":   "⚠️ Ism juda qisqa. Qaytadan yozing:",
        "ask_job":      "💼 Kasbingizni tanlang:",
        "ask_custom_job":"✏️ Kasbingizni yozing:",
        "ask_phone":    "📞 Telefon raqamingiz:",
        "ask_email":    "📧 Email manzilingiz:",
        "ask_address":  "📍 Manzilingiz (shahar, mamlakat):",
        "ask_photo":    "📷 Foto yuboring yoki «O'tkazib yuborish» tugmasini bosing:",
        "ask_summary":  "📝 O'zingiz haqingizda qisqacha yozing:",
        "ask_exp":      "🏢 Ish tajribangizni tanlang:",
        "ask_edu":      "🎓 Ta'lim darajangizni tanlang:",
        "ask_custom_edu":"✏️ Ta'limingizni yozing:",
        "ask_skills":   "🛠 Ko'nikmalaringizni yozing (vergul bilan):",
        "ask_langs":    "🌐 Qaysi tillarni bilasiz? (vergul bilan):",
        "creating":     "⏳ CV tayyorlanmoqda...",
        "pdf_ready":    "✅ PDF CV tayyor!",
        "html_ready":   "🌐 HTML CV tayyor! (Brauzerda ochish uchun yuklab oling)",
        "done":         "🔄 Yangi CV yaratish uchun /start bosing.",
        "cancelled":    "❌ Bekor qilindi. Boshlash uchun /start bosing.",
        "error":        "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring: /start",
        "skip":         "⏭ O'tkazib yuborish",
        "cancel":       "❌ Bekor qilish",
        "wrong_design": "⚠️ Iltimos, quyidagi tugmalardan birini tanlang:",
        "wrong_job":    "⚠️ Iltimos, quyidagi kasblardan birini tanlang:",
        "wrong_exp":    "⚠️ Iltimos, tajriba darajasini tanlang:",
        "wrong_edu":    "⚠️ Iltimos, ta'lim darajasini tanlang:",
        "footer":       "CV_MK Bot tomonidan yaratildi",
        "labels": {
            "summary":    "O'zim haqimda",
            "experience": "Ish tajribasi",
            "education":  "Ta'lim",
            "skills":     "Ko'nikmalar",
            "languages":  "Tillar",
            "phone":      "Telefon",
            "email":      "Email",
            "address":    "Manzil",
        },
    },
    "ru": {
        "welcome":      "👋 Привет! Добро пожаловать в CV_MK бот.\n\n🌍 Выберите язык:",
        "choose_design":"🎨 Выберите дизайн CV:",
        "ask_name":     "👤 Напишите имя и фамилию:",
        "name_short":   "⚠️ Имя слишком короткое. Напишите снова:",
        "ask_job":      "💼 Выберите профессию:",
        "ask_custom_job":"✏️ Напишите вашу профессию:",
        "ask_phone":    "📞 Ваш номер телефона:",
        "ask_email":    "📧 Ваш email:",
        "ask_address":  "📍 Ваш адрес (город, страна):",
        "ask_photo":    "📷 Отправьте фото или нажмите «Пропустить»:",
        "ask_summary":  "📝 Кратко напишите о себе:",
        "ask_exp":      "🏢 Выберите опыт работы:",
        "ask_edu":      "🎓 Выберите уровень образования:",
        "ask_custom_edu":"✏️ Напишите ваше образование:",
        "ask_skills":   "🛠 Напишите навыки (через запятую):",
        "ask_langs":    "🌐 Какие языки вы знаете? (через запятую):",
        "creating":     "⏳ CV создаётся...",
        "pdf_ready":    "✅ PDF CV готов!",
        "html_ready":   "🌐 HTML CV готов! (Скачайте, чтобы открыть в браузере)",
        "done":         "🔄 Чтобы создать новое CV, нажмите /start.",
        "cancelled":    "❌ Отменено. Нажмите /start для начала.",
        "error":        "❌ Произошла ошибка. Попробуйте снова: /start",
        "skip":         "⏭ Пропустить",
        "cancel":       "❌ Отмена",
        "wrong_design": "⚠️ Пожалуйста, выберите один из вариантов ниже:",
        "wrong_job":    "⚠️ Пожалуйста, выберите профессию из списка:",
        "wrong_exp":    "⚠️ Пожалуйста, выберите уровень опыта:",
        "wrong_edu":    "⚠️ Пожалуйста, выберите уровень образования:",
        "footer":       "Создано CV_MK Bot",
        "labels": {
            "summary":    "Обо мне",
            "experience": "Опыт работы",
            "education":  "Образование",
            "skills":     "Навыки",
            "languages":  "Языки",
            "phone":      "Телефон",
            "email":      "Email",
            "address":    "Адрес",
        },
    },
    "en": {
        "welcome":      "👋 Hello! Welcome to CV_MK bot.\n\n🌍 Choose your language:",
        "choose_design":"🎨 Choose a CV design:",
        "ask_name":     "👤 Enter your full name:",
        "name_short":   "⚠️ Name is too short. Please write again:",
        "ask_job":      "💼 Choose your profession:",
        "ask_custom_job":"✏️ Write your profession:",
        "ask_phone":    "📞 Your phone number:",
        "ask_email":    "📧 Your email address:",
        "ask_address":  "📍 Your address (city, country):",
        "ask_photo":    "📷 Send a photo or press «Skip»:",
        "ask_summary":  "📝 Write a short professional summary:",
        "ask_exp":      "🏢 Choose your work experience:",
        "ask_edu":      "🎓 Choose your education level:",
        "ask_custom_edu":"✏️ Write your education:",
        "ask_skills":   "🛠 Write your skills (comma-separated):",
        "ask_langs":    "🌐 Languages you know (comma-separated):",
        "creating":     "⏳ Creating your CV...",
        "pdf_ready":    "✅ PDF CV is ready!",
        "html_ready":   "🌐 HTML CV is ready! (Download to open in browser)",
        "done":         "🔄 Press /start to create another CV.",
        "cancelled":    "❌ Cancelled. Press /start to begin.",
        "error":        "❌ An error occurred. Please try again: /start",
        "skip":         "⏭ Skip",
        "cancel":       "❌ Cancel",
        "wrong_design": "⚠️ Please choose one of the options below:",
        "wrong_job":    "⚠️ Please choose a profession from the list:",
        "wrong_exp":    "⚠️ Please choose an experience level:",
        "wrong_edu":    "⚠️ Please choose an education level:",
        "footer":       "Created by CV_MK Bot",
        "labels": {
            "summary":    "Professional Summary",
            "experience": "Work Experience",
            "education":  "Education",
            "skills":     "Skills",
            "languages":  "Languages",
            "phone":      "Phone",
            "email":      "Email",
            "address":    "Address",
        },
    },
}

# ── Keyboard helpers ──────────────────────────────────────────────────────────
def kb(items: list[str], cols: int = 2) -> ReplyKeyboardMarkup:
    rows = []
    for i in range(0, len(items), cols):
        rows.append([KeyboardButton(text=x) for x in items[i:i + cols]])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)

def kb_lang()         : return kb(LANG_BUTTONS, cols=1)
def kb_design()       : return kb(DESIGN_KEYS,  cols=2)
def kb_jobs(l)        : return kb(JOBS[l],       cols=2)
def kb_exp(l)         : return kb(EXPERIENCE[l], cols=1)
def kb_edu(l)         : return kb(EDUCATION[l],  cols=1)
def kb_skip_cancel(l) : return kb([T[l]["skip"], T[l]["cancel"]], cols=2)
def kb_cancel(l)      : return kb([T[l]["cancel"]], cols=1)

# ── Text utilities ─────────────────────────────────────────────────────────────
def is_cancel(text: str, lang: str) -> bool:
    cancel_words = {"bekor", "отмена", "cancel", "❌"}
    t = (text or "").lower()
    return any(w in t for w in cancel_words) or text == T[lang]["cancel"]

def is_skip(text: str, lang: str) -> bool:
    skip_words = {"skip", "пропустить", "otkazib", "o'tkazib", "⏭"}
    t = (text or "").lower().replace("'","'").replace("ʻ","'")
    return any(w in t for w in skip_words) or text == T[lang]["skip"]

def clean_emoji(text: str) -> str:
    for e in ["🧱","🔨","🎨","🧩","⚡","🚰","🚗","🚕","📦","👨‍🍳",
              "🔹","🏫","🏢","🎓","✏️","⏭","⬜","💎"]:
        text = (text or "").replace(e, "")
    return text.strip()

def safe(v) -> str:
    return str(v or "").strip()

def wrap(text: str, width: int = 78) -> list[str]:
    lines = []
    for part in safe(text).split("\n"):
        lines.extend(textwrap.wrap(part, width=width) or [""])
    return lines

def uid() -> str:
    return uuid.uuid4().hex

def cleanup(*paths: Path):
    for p in paths:
        try:
            if p:
                Path(p).unlink(missing_ok=True)
        except Exception as e:
            logger.warning("Fayl o'chirilmadi: %s — %s", p, e)

# ── Font ───────────────────────────────────────────────────────────────────────
def load_font() -> str:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont("CVFont", path))
                logger.info("Font yuklandi: %s", path)
                return "CVFont"
            except Exception:
                continue
    logger.warning("Maxsus font topilmadi, Helvetica ishlatiladi.")
    return "Helvetica"

FONT = load_font()

# ── Photo → base64 ────────────────────────────────────────────────────────────
def photo_b64(path: str) -> str:
    try:
        p = Path(path)
        if p.exists():
            data = base64.b64encode(p.read_bytes()).decode()
            ext  = p.suffix.lower().lstrip(".")
            mime = {"jpg":"jpeg","jpeg":"jpeg","png":"png","webp":"webp"}.get(ext,"jpeg")
            return f"data:image/{mime};base64,{data}"
    except Exception as e:
        logger.warning("Foto base64 xatosi: %s", e)
    return ""

# ── HTML Generator ────────────────────────────────────────────────────────────
THEMES = {
    "minimalist": {"bg":"#ffffff","sidebar":"#f1f5f9","text":"#111827","accent":"#2563eb","card":"#f8fafc"},
    "corporate":  {"bg":"#f8fafc","sidebar":"#e2e8f0","text":"#0f172a","accent":"#1d4ed8","card":"#ffffff"},
    "modern":     {"bg":"#0f172a","sidebar":"#1e293b","text":"#f1f5f9","accent":"#ec4899","card":"#1e293b"},
    "premium":    {"bg":"#080b18","sidebar":"#0f1629","text":"#f5f0e8","accent":"#f59e0b","card":"#0f1629"},
}

def generate_html(data: dict, fid: str) -> Path:
    import html as hmod
    lang   = data.get("lang", "uz")
    lbl    = T[lang]["labels"]
    design = data.get("design", "minimalist")
    t      = THEMES.get(design, THEMES["minimalist"])

    def esc(v): return hmod.escape(safe(v))

    photo_tag = ""
    if data.get("photo_path"):
        src = photo_b64(data["photo_path"])
        if src:
            photo_tag = f'<img class="photo" src="{src}" alt="photo">'
    if not photo_tag:
        photo_tag = '<div class="photo-placeholder">👤</div>'

    def tags(text: str) -> str:
        parts = safe(text).replace(",", "\n").split("\n")
        return "".join(
            f'<span class="tag">{esc(s.strip())}</span>'
            for s in parts if s.strip()
        )

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data.get("full_name"))} — CV</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{t["bg"]};font-family:'Segoe UI',Arial,sans-serif;color:{t["text"]};min-height:100vh}}
.wrap{{max-width:860px;margin:32px auto;background:{t["bg"]};border-radius:20px;
  box-shadow:0 30px 80px rgba(0,0,0,.3);overflow:hidden;display:grid;grid-template-columns:260px 1fr}}
.side{{background:{t["sidebar"]};padding:36px 24px;display:flex;flex-direction:column;gap:24px}}
.photo{{width:120px;height:120px;border-radius:50%;object-fit:cover;border:4px solid {t["accent"]};display:block;margin:0 auto}}
.photo-placeholder{{width:120px;height:120px;border-radius:50%;background:{t["accent"]}22;
  border:3px dashed {t["accent"]};display:flex;align-items:center;justify-content:center;font-size:44px;margin:0 auto}}
.s-sec h3{{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:{t["accent"]};margin-bottom:8px;font-weight:700}}
.s-sec .val{{font-size:13px;line-height:1.8;opacity:.85;word-break:break-all}}
.tag{{display:inline-block;background:{t["accent"]}22;color:{t["accent"]};border-radius:8px;
  padding:3px 10px;font-size:12px;margin:2px;font-weight:500}}
.main{{padding:40px 36px;display:flex;flex-direction:column;gap:22px}}
.hdr{{border-bottom:3px solid {t["accent"]};padding-bottom:18px}}
.hdr h1{{font-size:30px;font-weight:800;letter-spacing:-.5px}}
.hdr .role{{color:{t["accent"]};font-size:16px;font-weight:600;margin-top:6px}}
.sec h2{{font-size:13px;letter-spacing:.10em;text-transform:uppercase;color:{t["accent"]};
  font-weight:700;margin-bottom:10px;display:flex;align-items:center;gap:8px}}
.sec h2::after{{content:"";flex:1;height:1px;background:{t["accent"]}44}}
.sec p{{font-size:14px;line-height:1.75;white-space:pre-line;opacity:.9}}
.foot{{text-align:center;font-size:11px;opacity:.4;padding:14px 0 0;border-top:1px solid {t["accent"]}22}}
@media(max-width:680px){{.wrap{{grid-template-columns:1fr}}.side{{padding:24px 18px}}.main{{padding:24px 18px}}}}
@media print{{body{{background:white}}.wrap{{box-shadow:none;margin:0;border-radius:0}}}}
</style>
</head>
<body>
<div class="wrap">
<aside class="side">
  {photo_tag}
  <div class="s-sec"><h3>📞 {lbl["phone"]}</h3><div class="val">{esc(data.get("phone","—"))}</div></div>
  <div class="s-sec"><h3>📧 {lbl["email"]}</h3><div class="val">{esc(data.get("email","—"))}</div></div>
  <div class="s-sec"><h3>📍 {lbl["address"]}</h3><div class="val">{esc(data.get("address","—"))}</div></div>
  <div class="s-sec"><h3>🌐 {lbl["languages"]}</h3><div>{tags(data.get("languages",""))}</div></div>
  <div class="s-sec"><h3>🛠 {lbl["skills"]}</h3><div>{tags(data.get("skills",""))}</div></div>
</aside>
<main class="main">
  <div class="hdr">
    <h1>{esc(data.get("full_name","—"))}</h1>
    <div class="role">{esc(data.get("job","—"))}</div>
  </div>
  <div class="sec"><h2>{lbl["summary"]}</h2><p>{esc(data.get("summary","—"))}</p></div>
  <div class="sec"><h2>{lbl["experience"]}</h2><p>{esc(data.get("experience","—"))}</p></div>
  <div class="sec"><h2>{lbl["education"]}</h2><p>{esc(data.get("education","—"))}</p></div>
  <div class="foot">{T[lang]["footer"]} • {datetime.now().strftime("%d.%m.%Y")}</div>
</main>
</div>
</body>
</html>"""

    path = OUTPUT_DIR / f"cv_{fid}.html"
    path.write_text(html, encoding="utf-8")
    return path

# ── PDF Generator ─────────────────────────────────────────────────────────────
PDF_PAL = {
    "minimalist": {"accent":(0.15,0.39,0.92), "dark":False},
    "corporate":  {"accent":(0.05,0.20,0.45), "dark":False},
    "modern":     {"accent":(0.90,0.20,0.55), "dark":True},
    "premium":    {"accent":(0.96,0.62,0.04), "dark":True},
}

def generate_pdf(data: dict, fid: str) -> Path:
    path = OUTPUT_DIR / f"cv_{fid}.pdf"
    c    = canvas.Canvas(str(path), pagesize=A4)
    W, H = A4

    lang   = data.get("lang", "uz")
    lbl    = T[lang]["labels"]
    design = data.get("design", "minimalist")
    pal    = PDF_PAL.get(design, PDF_PAL["minimalist"])
    accent = pal["accent"]
    dark   = pal["dark"]

    BG   = (0.04, 0.06, 0.12) if dark else (1.0,  1.0,  1.0 )
    TXT_ = (0.95, 0.95, 0.95) if dark else (0.07, 0.07, 0.12)

    sidebar_w  = 200
    sidebar_bg = tuple(max(0, x - 0.05) for x in BG) if dark else (0.945, 0.953, 0.965)

    # Background
    c.setFillColorRGB(*BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Accent header bar
    c.setFillColorRGB(*accent)
    c.rect(0, H - 36, W, 36, fill=1, stroke=0)

    # Sidebar
    c.setFillColorRGB(*sidebar_bg)
    c.rect(0, 0, sidebar_w, H - 36, fill=1, stroke=0)

    # Header bar label
    c.setFillColorRGB(1, 1, 1)
    c.setFont(FONT, 10)
    c.drawString(16, H - 23, "CV_MK BOT")

    y_main = H - 66

    # Name
    c.setFillColorRGB(*TXT_)
    c.setFont(FONT, 20)
    c.drawString(sidebar_w + 18, y_main, safe(data.get("full_name"))[:42])
    y_main -= 24

    # Job / role
    c.setFillColorRGB(*accent)
    c.setFont(FONT, 12)
    c.drawString(sidebar_w + 18, y_main, safe(data.get("job"))[:55])
    y_main -= 20

    # Divider
    c.setStrokeColorRGB(*accent)
    c.setLineWidth(1.2)
    c.line(sidebar_w + 18, y_main, W - 28, y_main)
    y_main -= 14

    def new_page():
        nonlocal y_main
        c.showPage()
        c.setFillColorRGB(*BG)
        c.rect(0, 0, W, H, fill=1, stroke=0)
        c.setFillColorRGB(*sidebar_bg)
        c.rect(0, 0, sidebar_w, H, fill=1, stroke=0)
        y_main = H - 40

    def main_section(title: str, body: str):
        nonlocal y_main
        if y_main < 90:
            new_page()
        c.setFillColorRGB(*accent)
        c.setFont(FONT, 11)
        c.drawString(sidebar_w + 18, y_main, title.upper())
        y_main -= 4
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(0.4)
        c.line(sidebar_w + 18, y_main, W - 28, y_main)
        y_main -= 13
        c.setFillColorRGB(*TXT_)
        c.setFont(FONT, 9)
        for line in wrap(body, 68):
            if y_main < 55:
                new_page()
                c.setFillColorRGB(*TXT_)
                c.setFont(FONT, 9)
            c.drawString(sidebar_w + 22, y_main, line)
            y_main -= 13
        y_main -= 8

    main_section(lbl["summary"],    safe(data.get("summary")))
    main_section(lbl["experience"], safe(data.get("experience")))
    main_section(lbl["education"],  safe(data.get("education")))

    # ── Sidebar content ────────────────────────────────────────────────────────
    y_side = H - 66

    def side_title(title: str):
        nonlocal y_side
        if y_side < 55:
            return
        c.setFillColorRGB(*accent)
        c.setFont(FONT, 8)
        c.drawString(10, y_side, title.upper())
        y_side -= 13

    def side_text(text: str, w: int = 26):
        nonlocal y_side
        c.setFillColorRGB(*TXT_)
        c.setFont(FONT, 8)
        for line in wrap(text, w):
            if y_side < 50:
                break
            c.drawString(10, y_side, line)
            y_side -= 12

    # Photo circle
    px, py, pr = 100, y_side, 40
    c.setFillColorRGB(*accent)
    c.circle(px, py, pr + 3, fill=1, stroke=0)
    c.setFillColorRGB(*sidebar_bg)
    c.circle(px, py, pr, fill=1, stroke=0)

    photo_path = data.get("photo_path", "")
    if photo_path and Path(photo_path).exists():
        try:
            from reportlab.lib.utils import ImageReader
            from PIL import Image as PILImage
            import io
            img = PILImage.open(photo_path).convert("RGB")
            s   = min(img.size)
            lft = (img.width  - s) // 2
            top = (img.height - s) // 2
            img = img.crop((lft, top, lft + s, top + s)).resize((100, 100))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            buf.seek(0)
            c.drawImage(ImageReader(buf), px - pr, py - pr,
                        width=pr*2, height=pr*2, mask="auto")
        except Exception as e:
            logger.warning("PDF foto xatosi: %s", e)
            c.setFillColorRGB(*TXT_)
            c.setFont(FONT, 20)
            c.drawCentredString(px, py - 7, "👤")
    else:
        c.setFillColorRGB(*TXT_)
        c.setFont(FONT, 20)
        c.drawCentredString(px, py - 7, "👤")

    y_side -= pr * 2 + 16

    side_title(lbl["phone"]);     side_text(safe(data.get("phone")));    y_side -= 4
    side_title(lbl["email"]);     side_text(safe(data.get("email")));    y_side -= 4
    side_title(lbl["address"]);   side_text(safe(data.get("address"))); y_side -= 4
    side_title(lbl["languages"]); side_text(safe(data.get("languages"))); y_side -= 4
    side_title(lbl["skills"]);    side_text(safe(data.get("skills")))

    # Footer
    c.setFillColorRGB(*accent)
    c.setFont(FONT, 7)
    c.drawString(10, 18, f"{T[lang]['footer']} • {datetime.now().strftime('%d.%m.%Y')}")

    c.save()
    return path

# ── CV finalize ───────────────────────────────────────────────────────────────
async def finalize(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    fid  = uid()

    await msg.answer(T[lang]["creating"], reply_markup=ReplyKeyboardRemove())

    pdf_path  = None
    html_path = None
    try:
        pdf_path  = generate_pdf(data, fid)
        html_path = generate_html(data, fid)

        await msg.answer_document(FSInputFile(pdf_path),  caption=T[lang]["pdf_ready"])
        await msg.answer_document(FSInputFile(html_path), caption=T[lang]["html_ready"])
        await msg.answer(T[lang]["done"], reply_markup=kb_lang())
    except Exception as e:
        logger.exception("CV yaratishda xatolik: %s", e)
        await msg.answer(T[lang]["error"], reply_markup=kb_lang())
    finally:
        to_clean = [p for p in [pdf_path, html_path] if p]
        if data.get("photo_path"):
            to_clean.append(Path(data["photo_path"]))
        cleanup(*to_clean)
        await state.clear()
        await state.set_state(CV.lang)

# ── /start ────────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CV.lang)
    await msg.answer(T["uz"]["welcome"], reply_markup=kb_lang())

# ── Til tanlash ───────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.lang), F.text.in_(LANG_BUTTONS))
async def step_lang(msg: Message, state: FSMContext):
    lang = LANG_MAP[msg.text]
    await state.update_data(lang=lang)
    await state.set_state(CV.design)
    await msg.answer(T[lang]["choose_design"], reply_markup=kb_design())

# ── Dizayn tanlash ────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.design), F.text.in_(DESIGN_KEYS))
async def step_design(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    await state.update_data(design=DESIGN_MAP[msg.text])
    await state.set_state(CV.full_name)
    await msg.answer(T[lang]["ask_name"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.design))
async def step_design_wrong(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text or "", lang): return await do_cancel(msg, state)
    await msg.answer(T[lang]["wrong_design"], reply_markup=kb_design())

# ── Ism familiya ─────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.full_name), F.text)
async def step_name(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    if len(msg.text.strip()) < 2:
        return await msg.answer(T[lang]["name_short"], reply_markup=kb_cancel(lang))
    await state.update_data(full_name=msg.text.strip())
    await state.set_state(CV.job)
    await msg.answer(T[lang]["ask_job"], reply_markup=kb_jobs(lang))

# ── Kasb tanlash ─────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.job), F.text)
async def step_job(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    tl = (msg.text or "").lower()
    if any(w in tl for w in ["boshqa", "другая", "other", "✏️"]):
        await state.set_state(CV.custom_job)
        return await msg.answer(T[lang]["ask_custom_job"], reply_markup=kb_cancel(lang))
    if msg.text not in JOBS[lang]:
        return await msg.answer(T[lang]["wrong_job"], reply_markup=kb_jobs(lang))
    await state.update_data(job=clean_emoji(msg.text))
    await state.set_state(CV.phone)
    await msg.answer(T[lang]["ask_phone"], reply_markup=kb_cancel(lang))

# ── Boshqa kasb ──────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.custom_job), F.text)
async def step_custom_job(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(job=msg.text.strip())
    await state.set_state(CV.phone)
    await msg.answer(T[lang]["ask_phone"], reply_markup=kb_cancel(lang))

# ── Telefon ───────────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.phone), F.text)
async def step_phone(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(phone=msg.text.strip())
    await state.set_state(CV.email)
    await msg.answer(T[lang]["ask_email"], reply_markup=kb_cancel(lang))

# ── Email ─────────────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.email), F.text)
async def step_email(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(email=msg.text.strip())
    await state.set_state(CV.address)
    await msg.answer(T[lang]["ask_address"], reply_markup=kb_cancel(lang))

# ── Manzil ────────────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.address), F.text)
async def step_address(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(address=msg.text.strip())
    await state.set_state(CV.photo)
    await msg.answer(T[lang]["ask_photo"], reply_markup=kb_skip_cancel(lang))

# ── Foto: rasm ────────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.photo), F.photo)
async def step_photo_img(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    try:
        file       = await bot.get_file(msg.photo[-1].file_id)
        photo_path = OUTPUT_DIR / f"photo_{uid()}.jpg"
        await bot.download_file(file.file_path, destination=photo_path)
        await state.update_data(photo_path=str(photo_path))
        logger.info("Foto saqlandi: %s", photo_path)
    except Exception as e:
        logger.warning("Foto yuklab bo'lmadi: %s", e)
        await state.update_data(photo_path="")
    await state.set_state(CV.summary)
    await msg.answer(T[lang]["ask_summary"], reply_markup=kb_cancel(lang))

# ── Foto: matn (skip / cancel) ────────────────────────────────────────────────
@dp.message(StateFilter(CV.photo), F.text)
async def step_photo_text(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    if is_skip(msg.text, lang):
        await state.update_data(photo_path="")
        await state.set_state(CV.summary)
        return await msg.answer(T[lang]["ask_summary"], reply_markup=kb_cancel(lang))
    await msg.answer(T[lang]["ask_photo"], reply_markup=kb_skip_cancel(lang))

# ── Summary ───────────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.summary), F.text)
async def step_summary(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(summary=msg.text.strip())
    await state.set_state(CV.experience)
    await msg.answer(T[lang]["ask_exp"], reply_markup=kb_exp(lang))

# ── Tajriba ───────────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.experience), F.text)
async def step_exp(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    if msg.text not in EXPERIENCE[lang]:
        return await msg.answer(T[lang]["wrong_exp"], reply_markup=kb_exp(lang))
    await state.update_data(experience=clean_emoji(msg.text))
    await state.set_state(CV.education)
    await msg.answer(T[lang]["ask_edu"], reply_markup=kb_edu(lang))

# ── Ta'lim ────────────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.education), F.text)
async def step_edu(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    tl = (msg.text or "").lower()
    if any(w in tl for w in ["boshqa", "другое", "other", "✏️"]):
        await state.set_state(CV.custom_edu)
        return await msg.answer(T[lang]["ask_custom_edu"], reply_markup=kb_cancel(lang))
    if msg.text not in EDUCATION[lang]:
        return await msg.answer(T[lang]["wrong_edu"], reply_markup=kb_edu(lang))
    await state.update_data(education=clean_emoji(msg.text))
    await state.set_state(CV.skills)
    await msg.answer(T[lang]["ask_skills"], reply_markup=kb_cancel(lang))

# ── Boshqa ta'lim ─────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.custom_edu), F.text)
async def step_custom_edu(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(education=msg.text.strip())
    await state.set_state(CV.skills)
    await msg.answer(T[lang]["ask_skills"], reply_markup=kb_cancel(lang))

# ── Ko'nikmalar ───────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.skills), F.text)
async def step_skills(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(skills=msg.text.strip())
    await state.set_state(CV.languages)
    await msg.answer(T[lang]["ask_langs"], reply_markup=kb_cancel(lang))

# ── Tillar → finalize ─────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.languages), F.text)
async def step_langs(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang", "uz")
    if is_cancel(msg.text, lang): return await do_cancel(msg, state)
    await state.update_data(languages=msg.text.strip())
    await finalize(msg, state)

# ── Cancel helper ─────────────────────────────────────────────────────────────
async def do_cancel(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.clear()
    await state.set_state(CV.lang)
    await msg.answer(T[lang]["cancelled"], reply_markup=kb_lang())

# ── Catch-all: boshqa xabarlar ────────────────────────────────────────────────
@dp.message()
async def catch_all(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    current = await state.get_state()

    # Noto'g'ri state — qayta boshlash
    if current is None or current == CV.lang.state:
        await state.clear()
        await state.set_state(CV.lang)
        await msg.answer(T[lang]["welcome"], reply_markup=kb_lang())
        return

    # Foto kutilayotgan bo'lsa ammo boshqa narsa keldi
    if current == CV.photo.state:
        await msg.answer(T[lang]["ask_photo"], reply_markup=kb_skip_cancel(lang))
        return

    # Boshqa holatlarda qayta boshlash
    await state.clear()
    await state.set_state(CV.lang)
    await msg.answer(T[lang]["welcome"], reply_markup=kb_lang())

# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    logger.info("CV_MK Bot ishga tushmoqda...")
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot, allowed_updates=["message"])

if __name__ == "__main__":
    asyncio.run(main())
