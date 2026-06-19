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
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cv_mk")


# ─── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Render Environment Variables ga BOT_TOKEN qo'ying.")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ─── Bot & App ────────────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
web = Flask(__name__)


@web.route("/")
def home():
    return "CV_MK Bot is running"


@web.route("/health")
def health():
    return "OK"


def run_web():
    port = int(os.getenv("PORT", 10000))
    web.run(host="0.0.0.0", port=port)


# ─── FSM States ───────────────────────────────────────────────────────────────
class CV(StatesGroup):
    lang = State()
    design = State()
    full_name = State()
    job = State()
    custom_job = State()
    phone = State()
    email = State()
    address = State()
    photo = State()
    summary = State()
    experience = State()
    education = State()
    custom_education = State()
    skills = State()
    languages = State()


# ─── Language map (duplicates removed) ────────────────────────────────────────
LANGS = {
    "🇺🇿 O'zbek": "uz",
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en",
}


# ─── Translations ─────────────────────────────────────────────────────────────
TXT = {
    "uz": {
        "start": "✅ CV_MK ishga tushdi.\n\n🌍 Tilni tanlang:",
        "design": "🎨 CV dizaynini tanlang:",
        "name": "👤 Ism familiyangizni yozing:",
        "job": "💼 Kasbingizni tanlang:",
        "custom_job": "✏️ Kasbingizni yozing:",
        "phone": "📞 Telefon raqamingiz:",
        "email": "📧 Email:",
        "address": "📍 Manzil:",
        "photo": "📷 Foto yuboring yoki «O'tkazib yuborish» tugmasini bosing:",
        "summary": "📝 O'zingiz haqingizda qisqa yozing:",
        "experience": "🏢 Ish tajribangizni tanlang:",
        "education": "🎓 Ta'lim darajangizni tanlang:",
        "custom_education": "✏️ Ta'limingizni yozing:",
        "skills": "🛠 Ko'nikmalaringizni yozing:",
        "languages": "🌐 Qaysi tillarni bilasiz?",
        "creating": "⏳ CV tayyorlanmoqda...",
        "ready_pdf": "✅ PDF CV tayyor!",
        "ready_html": "🌐 HTML CV tayyor! (Brauzerdа ochish uchun yuklab oling)",
        "again": "🔄 Yana CV yaratish uchun /start bosing.",
        "skip": "⏭ O'tkazib yuborish",
        "cancel": "❌ Bekor qilish",
        "cancelled": "❌ Bekor qilindi.\n\n🌍 Tilni tanlang:",
        "error": "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring: /start",
        "footer": "CV_MK Bot tomonidan yaratildi",
        "labels": {
            "summary": "O'zim haqimda",
            "experience": "Ish tajribasi",
            "education": "Ta'lim",
            "skills": "Ko'nikmalar",
            "languages": "Tillar",
            "phone": "Telefon",
            "email": "Email",
            "address": "Manzil",
        },
    },
    "ru": {
        "start": "✅ CV_MK запущен.\n\n🌍 Выберите язык:",
        "design": "🎨 Выберите дизайн CV:",
        "name": "👤 Имя и фамилия:",
        "job": "💼 Выберите профессию:",
        "custom_job": "✏️ Напишите профессию:",
        "phone": "📞 Телефон:",
        "email": "📧 Email:",
        "address": "📍 Адрес:",
        "photo": "📷 Отправьте фото или нажмите «Пропустить»:",
        "summary": "📝 Кратко напишите о себе:",
        "experience": "🏢 Выберите опыт работы:",
        "education": "🎓 Выберите образование:",
        "custom_education": "✏️ Напишите образование:",
        "skills": "🛠 Напишите навыки:",
        "languages": "🌐 Какие языки знаете?",
        "creating": "⏳ CV создаётся...",
        "ready_pdf": "✅ PDF CV готов!",
        "ready_html": "🌐 HTML CV готов! (Скачайте, чтобы открыть в браузере)",
        "again": "🔄 Чтобы создать ещё одно CV, нажмите /start.",
        "skip": "⏭ Пропустить",
        "cancel": "❌ Отмена",
        "cancelled": "❌ Отменено.\n\n🌍 Выберите язык:",
        "error": "❌ Произошла ошибка. Попробуйте снова: /start",
        "footer": "Создано CV_MK Bot",
        "labels": {
            "summary": "Обо мне",
            "experience": "Опыт работы",
            "education": "Образование",
            "skills": "Навыки",
            "languages": "Языки",
            "phone": "Телефон",
            "email": "Email",
            "address": "Адрес",
        },
    },
    "en": {
        "start": "✅ CV_MK is running.\n\n🌍 Choose language:",
        "design": "🎨 Choose CV design:",
        "name": "👤 Full name:",
        "job": "💼 Choose your profession:",
        "custom_job": "✏️ Write your profession:",
        "phone": "📞 Phone:",
        "email": "📧 Email:",
        "address": "📍 Address:",
        "photo": "📷 Send a photo or press «Skip»:",
        "summary": "📝 Write a short professional summary:",
        "experience": "🏢 Choose work experience:",
        "education": "🎓 Choose education level:",
        "custom_education": "✏️ Write your education:",
        "skills": "🛠 Write your skills:",
        "languages": "🌐 Languages you know:",
        "creating": "⏳ Creating your CV...",
        "ready_pdf": "✅ PDF CV is ready!",
        "ready_html": "🌐 HTML CV is ready! (Download to open in browser)",
        "again": "🔄 Press /start to create another CV.",
        "skip": "⏭ Skip",
        "cancel": "❌ Cancel",
        "cancelled": "❌ Cancelled.\n\n🌍 Choose language:",
        "error": "❌ An error occurred. Please try again: /start",
        "footer": "Created by CV_MK Bot",
        "labels": {
            "summary": "Professional Summary",
            "experience": "Work Experience",
            "education": "Education",
            "skills": "Skills",
            "languages": "Languages",
            "phone": "Phone",
            "email": "Email",
            "address": "Address",
        },
    },
}


DESIGNS = {
    "⬜ Minimalist": "minimalist",
    "🏢 Corporate": "corporate",
    "🎨 Modern": "modern",
    "💎 Premium": "premium",
}

JOBS = {
    "uz": [
        "🧱 Kafelchi", "🔨 Quruvchi", "🎨 Malyar", "🧩 Gipsokartonchi",
        "⚡ Elektrik", "🚰 Santexnik", "🚗 Haydovchi", "🚕 Taksi haydovchisi",
        "📦 Omborchi", "👨‍🍳 Oshpaz", "➕ Boshqa kasb",
    ],
    "ru": [
        "🧱 Плиточник", "🔨 Строитель", "🎨 Маляр", "🧩 Гипсокартонщик",
        "⚡ Электрик", "🚰 Сантехник", "🚗 Водитель", "🚕 Таксист",
        "📦 Складской работник", "👨‍🍳 Повар", "➕ Другая профессия",
    ],
    "en": [
        "🧱 Tiler", "🔨 Builder", "🎨 Painter", "🧩 Drywall Worker",
        "⚡ Electrician", "🚰 Plumber", "🚗 Driver", "🚕 Taxi Driver",
        "📦 Warehouse Worker", "👨‍🍳 Cook", "➕ Other profession",
    ],
}

EXPERIENCE = {
    "uz": ["🔹 Tajribasiz", "🔹 1–3 yil", "🔹 3–5 yil", "🔹 5–10 yil", "🔹 10+ yil"],
    "ru": ["🔹 Без опыта", "🔹 1–3 года", "🔹 3–5 лет", "🔹 5–10 лет", "🔹 10+ лет"],
    "en": ["🔹 No experience", "🔹 1–3 years", "🔹 3–5 years", "🔹 5–10 years", "🔹 10+ years"],
}

EDUCATION = {
    "uz": ["🏫 O'rta maktab", "🏢 Kollej / Litsey", "🎓 Bakalavr", "🎓 Magistr", "➕ Boshqa"],
    "ru": ["🏫 Средняя школа", "🏢 Колледж / Лицей", "🎓 Бакалавр", "🎓 Магистр", "➕ Другое"],
    "en": ["🏫 Secondary School", "🏢 College / Lyceum", "🎓 Bachelor", "🎓 Master", "➕ Other"],
}


# ─── Keyboards ────────────────────────────────────────────────────────────────
def keyboard(items: list[str], row: int = 2) -> ReplyKeyboardMarkup:
    rows = []
    for i in range(0, len(items), row):
        rows.append([KeyboardButton(text=x) for x in items[i:i + row]])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)


def kb_lang():      return keyboard(list(LANGS.keys()), row=1)
def kb_design():    return keyboard(list(DESIGNS.keys()), row=2)
def kb_jobs(l):     return keyboard(JOBS[l], row=2)
def kb_exp(l):      return keyboard(EXPERIENCE[l], row=1)
def kb_edu(l):      return keyboard(EDUCATION[l], row=1)
def kb_skip(l):     return keyboard([TXT[l]["skip"], TXT[l]["cancel"]], row=2)
def kb_cancel(l):   return keyboard([TXT[l]["cancel"]], row=1)


# ─── Text helpers ─────────────────────────────────────────────────────────────
def is_cancel(text: str) -> bool:
    t = (text or "").lower()
    return "bekor" in t or "отмена" in t or "cancel" in t


def is_skip(text: str) -> bool:
    t = (text or "").lower().replace("'", "'").replace("'", "'").replace("ʻ", "'")
    return any(k in t for k in ["skip", "пропустить", "otkazib", "o'tkazib"])


EMOJI_CLEAN = ["🧱","🔨","🎨","🧩","⚡","🚰","🚗","🚕","📦","👨‍🍳","🔹","🏫","🏢","🎓","➕","⏭"]

def clean_choice(text: str) -> str:
    for e in EMOJI_CLEAN:
        text = (text or "").replace(e, "")
    return text.strip()


def safe(v) -> str:
    return str(v or "").strip()


def wrap_lines(text: str, width: int = 78) -> list[str]:
    lines = []
    for part in safe(text).split("\n"):
        lines.extend(textwrap.wrap(part, width=width) or [""])
    return lines


def file_uid() -> str:
    """UUID-based unique filename — no timestamp collision risk."""
    return uuid.uuid4().hex


def cleanup(*paths: Path):
    """Delete temp files after sending."""
    for p in paths:
        try:
            p.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Fayl o'chirilmadi: {p} — {e}")


# ─── Font ─────────────────────────────────────────────────────────────────────
def get_font() -> str:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont("CustomFont", path))
                logger.info(f"Font yuklandi: {path}")
                return "CustomFont"
            except Exception:
                continue
    logger.warning("Maxsus font topilmadi, Helvetica ishlatiladi.")
    return "Helvetica"


FONT = get_font()


# ─── Photo → base64 ───────────────────────────────────────────────────────────
def photo_to_base64(photo_path: str) -> str:
    """
    FIX: HTML ga lokal fayl yo'li emas, base64 data URI embed qilinadi.
    Shunda HTML fayl istalgan qurilmada to'g'ri ko'rinadi.
    """
    try:
        p = Path(photo_path)
        if p.exists():
            data = base64.b64encode(p.read_bytes()).decode()
            ext = p.suffix.lower().lstrip(".")
            mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "jpeg")
            return f"data:image/{mime};base64,{data}"
    except Exception as e:
        logger.warning(f"Foto base64 ga aylantirilmadi: {e}")
    return ""


# ─── HTML Generator ───────────────────────────────────────────────────────────
def generate_html(data: dict, uid: str) -> Path:
    import html as html_mod

    lang = data.get("lang", "uz")
    labels = TXT[lang]["labels"]
    design = data.get("design", "minimalist")

    themes = {
        "minimalist": {
            "bg": "#ffffff", "sidebar": "#f1f5f9", "text": "#111827",
            "accent": "#2563eb", "accent2": "#1d4ed8", "card": "#f8fafc",
        },
        "corporate": {
            "bg": "#f8fafc", "sidebar": "#e2e8f0", "text": "#0f172a",
            "accent": "#1d4ed8", "accent2": "#1e40af", "card": "#ffffff",
        },
        "modern": {
            "bg": "#0f172a", "sidebar": "#1e293b", "text": "#f1f5f9",
            "accent": "#ec4899", "accent2": "#db2777", "card": "#1e293b",
        },
        "premium": {
            "bg": "#080b18", "sidebar": "#0f1629", "text": "#f5f0e8",
            "accent": "#f59e0b", "accent2": "#d97706", "card": "#0f1629",
        },
    }

    t = themes.get(design, themes["minimalist"])

    photo_html = ""
    if data.get("photo_path"):
        src = photo_to_base64(data["photo_path"])
        if src:
            photo_html = f'<img class="photo" src="{src}" alt="Photo">'

    def esc(v): return html_mod.escape(safe(v))

    content = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data.get("full_name"))} — CV</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: {t["bg"]};
    font-family: 'Segoe UI', Arial, sans-serif;
    color: {t["text"]};
    min-height: 100vh;
  }}
  .wrapper {{
    max-width: 860px;
    margin: 32px auto;
    background: {t["bg"]};
    border-radius: 20px;
    box-shadow: 0 30px 80px rgba(0,0,0,.30);
    overflow: hidden;
    display: grid;
    grid-template-columns: 260px 1fr;
  }}
  /* ── Sidebar ── */
  .sidebar {{
    background: {t["sidebar"]};
    padding: 36px 24px;
    display: flex;
    flex-direction: column;
    gap: 28px;
  }}
  .photo {{
    width: 120px; height: 120px;
    border-radius: 50%;
    object-fit: cover;
    border: 4px solid {t["accent"]};
    display: block;
    margin: 0 auto 4px;
  }}
  .photo-placeholder {{
    width: 120px; height: 120px;
    border-radius: 50%;
    background: {t["accent"]}22;
    border: 3px dashed {t["accent"]};
    display: flex; align-items: center; justify-content: center;
    font-size: 44px;
    margin: 0 auto 4px;
  }}
  .sidebar-section h3 {{
    font-size: 11px;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: {t["accent"]};
    margin-bottom: 10px;
    font-weight: 700;
  }}
  .contact-item {{
    font-size: 13px;
    line-height: 1.8;
    opacity: .85;
    word-break: break-all;
  }}
  .contact-item span {{
    font-weight: 600;
    color: {t["accent"]};
  }}
  .tag {{
    display: inline-block;
    background: {t["accent"]}22;
    color: {t["accent"]};
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 12px;
    margin: 3px 2px;
    font-weight: 500;
  }}
  /* ── Main ── */
  .main {{
    padding: 40px 36px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }}
  .header {{ border-bottom: 3px solid {t["accent"]}; padding-bottom: 20px; }}
  .header h1 {{ font-size: 32px; font-weight: 800; letter-spacing: -.5px; }}
  .header .role {{
    color: {t["accent"]};
    font-size: 17px;
    font-weight: 600;
    margin-top: 6px;
  }}
  .section h2 {{
    font-size: 14px;
    letter-spacing: .10em;
    text-transform: uppercase;
    color: {t["accent"]};
    font-weight: 700;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .section h2::after {{
    content: "";
    flex: 1;
    height: 1px;
    background: {t["accent"]}44;
  }}
  .section p {{
    font-size: 14px;
    line-height: 1.75;
    white-space: pre-line;
    opacity: .9;
  }}
  .footer {{
    text-align: center;
    font-size: 11px;
    opacity: .45;
    padding: 16px 0 0;
    border-top: 1px solid {t["accent"]}22;
  }}
  @media (max-width: 680px) {{
    .wrapper {{ grid-template-columns: 1fr; }}
    .sidebar {{ padding: 28px 20px; }}
    .main {{ padding: 28px 20px; }}
  }}
  @media print {{
    body {{ background: white; }}
    .wrapper {{ box-shadow: none; margin: 0; border-radius: 0; }}
  }}
</style>
</head>
<body>
<div class="wrapper">

  <aside class="sidebar">
    {"" if not photo_html else photo_html}
    {"" if photo_html else '<div class="photo-placeholder">👤</div>'}

    <div class="sidebar-section">
      <h3>📞 {labels["phone"]}</h3>
      <div class="contact-item">{esc(data.get("phone", "—"))}</div>
    </div>

    <div class="sidebar-section">
      <h3>📧 {labels["email"]}</h3>
      <div class="contact-item">{esc(data.get("email", "—"))}</div>
    </div>

    <div class="sidebar-section">
      <h3>📍 {labels["address"]}</h3>
      <div class="contact-item">{esc(data.get("address", "—"))}</div>
    </div>

    <div class="sidebar-section">
      <h3>🌐 {labels["languages"]}</h3>
      <div>
        {"".join(f'<span class="tag">{esc(lang_item.strip())}</span>'
          for lang_item in safe(data.get("languages","")).replace(",","\n").split("\n") if lang_item.strip())}
      </div>
    </div>

    <div class="sidebar-section">
      <h3>🛠 {labels["skills"]}</h3>
      <div>
        {"".join(f'<span class="tag">{esc(s.strip())}</span>'
          for s in safe(data.get("skills","")).replace(",","\n").split("\n") if s.strip())}
      </div>
    </div>
  </aside>

  <main class="main">
    <div class="header">
      <h1>{esc(data.get("full_name", "—"))}</h1>
      <div class="role">{esc(data.get("job", "—"))}</div>
    </div>

    <div class="section">
      <h2>{labels["summary"]}</h2>
      <p>{esc(data.get("summary", "—"))}</p>
    </div>

    <div class="section">
      <h2>{labels["experience"]}</h2>
      <p>{esc(data.get("experience", "—"))}</p>
    </div>

    <div class="section">
      <h2>{labels["education"]}</h2>
      <p>{esc(data.get("education", "—"))}</p>
    </div>

    <div class="footer">
      {TXT[lang]["footer"]} • {datetime.now().strftime("%d.%m.%Y")}
    </div>
  </main>

</div>
</body>
</html>"""

    path = OUTPUT_DIR / f"cv_{uid}.html"
    path.write_text(content, encoding="utf-8")
    return path


# ─── PDF Generator ────────────────────────────────────────────────────────────
def generate_pdf(data: dict, uid: str) -> Path:
    path = OUTPUT_DIR / f"cv_{uid}.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    W, H = A4

    lang = data.get("lang", "uz")
    labels = TXT[lang]["labels"]
    design = data.get("design", "minimalist")

    palettes = {
        "minimalist": {"accent": (0.15, 0.39, 0.92), "dark": False},
        "corporate":  {"accent": (0.05, 0.20, 0.45), "dark": False},
        "modern":     {"accent": (0.90, 0.20, 0.55), "dark": True},
        "premium":    {"accent": (0.96, 0.62, 0.04), "dark": True},
    }
    pal = palettes.get(design, palettes["minimalist"])
    accent = pal["accent"]
    dark = pal["dark"]

    BG   = (0.04, 0.06, 0.12) if dark else (1.0, 1.0, 1.0)
    TEXT = (0.95, 0.95, 0.95) if dark else (0.07, 0.07, 0.12)

    # Background
    c.setFillColorRGB(*BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Accent header bar
    c.setFillColorRGB(*accent)
    c.rect(0, H - 38, W, 38, fill=1, stroke=0)

    # Sidebar strip
    sidebar_w = 200
    sidebar_bg = tuple(max(0, x - 0.05) for x in BG) if dark else (0.945, 0.953, 0.965)
    c.setFillColorRGB(*sidebar_bg)
    c.rect(0, 0, sidebar_w, H - 38, fill=1, stroke=0)

    # ── Header bar text ──
    c.setFillColorRGB(1, 1, 1)
    c.setFont(FONT, 11)
    c.drawString(18, H - 24, "CV_MK BOT")

    y_main = H - 70  # main content Y

    # ── Name & Job ──
    c.setFillColorRGB(*TEXT)
    c.setFont(FONT, 22)
    name = safe(data.get("full_name"))[:40]
    c.drawString(sidebar_w + 20, y_main, name)
    y_main -= 26

    c.setFillColorRGB(*accent)
    c.setFont(FONT, 13)
    c.drawString(sidebar_w + 20, y_main, safe(data.get("job"))[:55])
    y_main -= 24

    # Divider
    c.setStrokeColorRGB(*accent)
    c.setLineWidth(1.5)
    c.line(sidebar_w + 20, y_main, W - 30, y_main)
    y_main -= 16

    # ── Main sections ──
    def main_section(title: str, body: str):
        nonlocal y_main
        if y_main < 80:
            c.showPage()
            # Re-draw sidebar on new page
            c.setFillColorRGB(*sidebar_bg)
            c.rect(0, 0, sidebar_w, H, fill=1, stroke=0)
            y_main = H - 40

        c.setFillColorRGB(*accent)
        c.setFont(FONT, 12)
        c.drawString(sidebar_w + 20, y_main, title.upper())
        y_main -= 4
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(0.5)
        c.line(sidebar_w + 20, y_main, W - 30, y_main)
        y_main -= 14

        c.setFillColorRGB(*TEXT)
        c.setFont(FONT, 10)
        for line in wrap_lines(body, 65):
            if y_main < 60:
                c.showPage()
                c.setFillColorRGB(*sidebar_bg)
                c.rect(0, 0, sidebar_w, H, fill=1, stroke=0)
                y_main = H - 40
                c.setFillColorRGB(*TEXT)
                c.setFont(FONT, 10)
            c.drawString(sidebar_w + 24, y_main, line)
            y_main -= 15
        y_main -= 8

    main_section(labels["summary"],    safe(data.get("summary")))
    main_section(labels["experience"], safe(data.get("experience")))
    main_section(labels["education"],  safe(data.get("education")))

    # ── Sidebar content ──
    y_side = H - 70

    def side_label(title: str):
        nonlocal y_side
        if y_side < 60:
            return
        c.setFillColorRGB(*accent)
        c.setFont(FONT, 9)
        c.drawString(12, y_side, title.upper())
        y_side -= 14

    def side_text(text: str, wrap_w: int = 26):
        nonlocal y_side
        c.setFillColorRGB(*TEXT)
        c.setFont(FONT, 9)
        for line in wrap_lines(text, wrap_w):
            if y_side < 55:
                break
            c.drawString(12, y_side, line)
            y_side -= 13

    # Photo circle placeholder on sidebar
    photo_cx, photo_cy, photo_r = 100, y_side + 2, 42
    c.setFillColorRGB(*accent)
    c.circle(photo_cx, photo_cy, photo_r + 3, fill=1, stroke=0)
    c.setFillColorRGB(*sidebar_bg)
    c.circle(photo_cx, photo_cy, photo_r, fill=1, stroke=0)

    # If real photo exists — embed it
    photo_path = data.get("photo_path", "")
    if photo_path and Path(photo_path).exists():
        try:
            from reportlab.lib.utils import ImageReader
            from PIL import Image as PILImage
            import io
            img = PILImage.open(photo_path).convert("RGB")
            # Crop to square
            s = min(img.size)
            left = (img.width - s) // 2
            top  = (img.height - s) // 2
            img = img.crop((left, top, left + s, top + s)).resize((120, 120))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            buf.seek(0)
            c.drawImage(
                ImageReader(buf),
                photo_cx - photo_r, photo_cy - photo_r,
                width=photo_r * 2, height=photo_r * 2,
                mask="auto",
            )
        except Exception as e:
            logger.warning(f"PDF fotosi chizilmadi: {e}")
            c.setFillColorRGB(*TEXT)
            c.setFont(FONT, 22)
            c.drawCentredString(photo_cx, photo_cy - 8, "👤")

    y_side -= photo_r * 2 + 18

    side_label(labels["phone"])
    side_text(safe(data.get("phone")))
    y_side -= 4

    side_label(labels["email"])
    side_text(safe(data.get("email")))
    y_side -= 4

    side_label(labels["address"])
    side_text(safe(data.get("address")))
    y_side -= 4

    side_label(labels["languages"])
    side_text(safe(data.get("languages")))
    y_side -= 4

    side_label(labels["skills"])
    side_text(safe(data.get("skills")))

    # Footer
    c.setFillColorRGB(*accent)
    c.setFont(FONT, 7)
    c.drawString(12, 20, f"{TXT[lang]['footer']} • {datetime.now().strftime('%d.%m.%Y')}")

    c.save()
    return path


# ─── Finalize ─────────────────────────────────────────────────────────────────
async def finalize_cv(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    uid  = file_uid()

    await message.answer(TXT[lang]["creating"])

    pdf_path  = None
    html_path = None

    try:
        pdf_path  = generate_pdf(data, uid)
        html_path = generate_html(data, uid)

        await message.answer_document(
            FSInputFile(pdf_path),
            caption=TXT[lang]["ready_pdf"],
        )
        await message.answer_document(
            FSInputFile(html_path),
            caption=TXT[lang]["ready_html"],
        )
        await message.answer(TXT[lang]["again"], reply_markup=kb_lang())

    except Exception as e:
        logger.exception(f"CV yaratishda xatolik: {e}")
        await message.answer(TXT[lang]["error"])

    finally:
        # FIX: Temp fayllarni tozalash — disk to'lib ketmasin
        files_to_clean = [f for f in [pdf_path, html_path] if f is not None]
        if data.get("photo_path"):
            files_to_clean.append(Path(data["photo_path"]))
        cleanup(*files_to_clean)

        await state.clear()
        await state.set_state(CV.lang)


# ─── Handlers ─────────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CV.lang)
    await message.answer(TXT["uz"]["start"], reply_markup=kb_lang())


# FIX: StateFilter(CV.lang) qo'shildi — o'rta jarayonda til o'zgartirishdan himoya
@dp.message(StateFilter(CV.lang), F.text.in_(list(LANGS.keys())))
async def choose_lang(message: Message, state: FSMContext):
    lang = LANGS[message.text]
    await state.update_data(lang=lang)
    await state.set_state(CV.design)
    await message.answer(TXT[lang]["design"], reply_markup=kb_design())


# Photo handler
@dp.message(StateFilter(CV.photo), F.photo)
async def photo_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    try:
        file      = await bot.get_file(message.photo[-1].file_id)
        photo_path = OUTPUT_DIR / f"photo_{file_uid()}.jpg"
        await bot.download_file(file.file_path, destination=photo_path)
        await state.update_data(photo_path=str(photo_path))
        logger.info(f"Foto saqlandi: {photo_path}")
    except Exception as e:
        logger.warning(f"Foto yuklanmadi: {e}")
        await state.update_data(photo_path="")

    await state.set_state(CV.summary)
    await message.answer(TXT[lang]["summary"], reply_markup=kb_cancel(lang))


# Universal text router
@dp.message(F.text)
async def router(message: Message, state: FSMContext):
    text    = message.text or ""
    current = await state.get_state()
    data    = await state.get_data()
    lang    = data.get("lang", "uz")

    # Cancel — istalgan joydan
    if is_cancel(text):
        await state.clear()
        await state.set_state(CV.lang)
        await message.answer(TXT[lang]["cancelled"], reply_markup=kb_lang())
        return

    # ── State machine ──
    match current:

        case CV.lang.state:
            await message.answer(TXT["uz"]["start"], reply_markup=kb_lang())

        case CV.design.state:
            if text not in DESIGNS:
                await message.answer(TXT[lang]["design"], reply_markup=kb_design())
                return
            await state.update_data(design=DESIGNS[text])
            await state.set_state(CV.full_name)
            await message.answer(TXT[lang]["name"], reply_markup=kb_cancel(lang))

        case CV.full_name.state:
            if len(text) < 2:
                await message.answer("⚠️ Ism familiya juda qisqa. Qaytadan yozing:")
                return
            await state.update_data(full_name=text)
            await state.set_state(CV.job)
            await message.answer(TXT[lang]["job"], reply_markup=kb_jobs(lang))

        case CV.job.state:
            tl = text.lower()
            if "boshqa" in tl or "другая" in tl or "other" in tl:
                await state.set_state(CV.custom_job)
                await message.answer(TXT[lang]["custom_job"], reply_markup=kb_cancel(lang))
                return
            await state.update_data(job=clean_choice(text))
            await state.set_state(CV.phone)
            await message.answer(TXT[lang]["phone"], reply_markup=kb_cancel(lang))

        case CV.custom_job.state:
            await state.update_data(job=text)
            await state.set_state(CV.phone)
            await message.answer(TXT[lang]["phone"], reply_markup=kb_cancel(lang))

        case CV.phone.state:
            await state.update_data(phone=text)
            await state.set_state(CV.email)
            await message.answer(TXT[lang]["email"], reply_markup=kb_cancel(lang))

        case CV.email.state:
            await state.update_data(email=text)
            await state.set_state(CV.address)
            await message.answer(TXT[lang]["address"], reply_markup=kb_cancel(lang))

        case CV.address.state:
            await state.update_data(address=text)
            await state.set_state(CV.photo)
            await message.answer(TXT[lang]["photo"], reply_markup=kb_skip(lang))

        case CV.photo.state:
            if is_skip(text):
                await state.update_data(photo_path="")
                await state.set_state(CV.summary)
                await message.answer(TXT[lang]["summary"], reply_markup=kb_cancel(lang))
                return
            await message.answer(TXT[lang]["photo"], reply_markup=kb_skip(lang))

        case CV.summary.state:
            await state.update_data(summary=text)
            await state.set_state(CV.experience)
            await message.answer(TXT[lang]["experience"], reply_markup=kb_exp(lang))

        case CV.experience.state:
            await state.update_data(experience=clean_choice(text))
            await state.set_state(CV.education)
            await message.answer(TXT[lang]["education"], reply_markup=kb_edu(lang))

        case CV.education.state:
            tl = text.lower()
            if "boshqa" in tl or "другое" in tl or "other" in tl:
                await state.set_state(CV.custom_education)
                await message.answer(TXT[lang]["custom_education"], reply_markup=kb_cancel(lang))
                return
            await state.update_data(education=clean_choice(text))
            await state.set_state(CV.skills)
            await message.answer(TXT[lang]["skills"], reply_markup=kb_cancel(lang))

        case CV.custom_education.state:
            await state.update_data(education=text)
            await state.set_state(CV.skills)
            await message.answer(TXT[lang]["skills"], reply_markup=kb_cancel(lang))

        case CV.skills.state:
            await state.update_data(skills=text)
            await state.set_state(CV.languages)
            await message.answer(TXT[lang]["languages"], reply_markup=kb_cancel(lang))

        case CV.languages.state:
            await state.update_data(languages=text)
            await finalize_cv(message, state)

        case _:
            await state.clear()
            await state.set_state(CV.lang)
            await message.answer(TXT[lang]["start"], reply_markup=kb_lang())


@dp.message()
async def fallback(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.clear()
    await state.set_state(CV.lang)
    await message.answer(TXT[lang]["start"], reply_markup=kb_lang())


# ─── Entry point ──────────────────────────────────────────────────────────────
async def main():
    logger.info("CV_MK Bot ishga tushmoqda...")
    threading.Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot, allowed_updates=["message"])


if __name__ == "__main__":
    asyncio.run(main())
