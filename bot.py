"""CV_MK V2.0 — 20 Premium Professional Templates with Carousel Preview"""
import asyncio, base64, html as _html_mod, io, logging, os, re, textwrap, uuid
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile, CallbackQuery, FSInputFile,
    InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, KeyboardButton, Message,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from PIL import Image, ImageDraw

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("cv_mk")

TOKEN      = os.environ["BOT_TOKEN"]
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
WH_PATH    = f"/wh/{TOKEN[-10:]}"
OUT_DIR    = Path(__file__).parent / "output"
OUT_DIR.mkdir(exist_ok=True)

# ── Font ──────────────────────────────────────────────────────────────────────
def _load_font() -> str:
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]:
        if Path(p).exists():
            try:
                pdfmetrics.registerFont(TTFont("CF", p))
                log.info("Font: %s", p)
                return "CF"
            except Exception:
                pass
    return "Helvetica"

FONT = _load_font()
bot  = Bot(token=TOKEN)
dp   = Dispatcher(storage=MemoryStorage())

# ── FSM ───────────────────────────────────────────────────────────────────────
class CV(StatesGroup):
    lang             = State()
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
    certifications   = State()
    preview          = State()

# ── 20 Templates ──────────────────────────────────────────────────────────────
TEMPLATES = [
    {"id":"executive_black",      "name":"Executive Black",     "emoji":"⚫","layout":"dark_sidebar",   "bg":"#13161A","sb":"#1C2128","hd":"#1C2128","ac":"#C9A84C","tx":"#E8E0D0","st":"#8A7A60","fn":"Georgia,'Times New Roman',serif"},
    {"id":"premium_gold",         "name":"Premium Gold",        "emoji":"🥇","layout":"dark_banner",    "bg":"#141414","sb":"#1E1E1E","hd":"#0D0D0D","ac":"#D4AF37","tx":"#F0E8D0","st":"#9A9070","fn":"Georgia,serif"},
    {"id":"luxury_black_gold",    "name":"Luxury Black Gold",   "emoji":"✨","layout":"centered_dark",  "bg":"#0D0D0D","sb":"#181818","hd":"#0D0D0D","ac":"#BFA16A","tx":"#F0E8D8","st":"#8A7850","fn":"Georgia,serif"},
    {"id":"corporate_blue",       "name":"Corporate Blue",      "emoji":"🔵","layout":"banner_light",   "bg":"#FFFFFF","sb":"#EEF3FA","hd":"#1B3B6F","ac":"#1B3B6F","tx":"#0F1F3A","st":"#3A5878","fn":"Arial,sans-serif"},
    {"id":"ats_minimal_white",    "name":"ATS Minimal",         "emoji":"⬜","layout":"ats_clean",      "bg":"#FFFFFF","sb":"#F5F5F5","hd":"#FFFFFF","ac":"#2C2C2C","tx":"#1A1A1A","st":"#555555","fn":"Arial,sans-serif"},
    {"id":"europass_professional","name":"Europass Pro",        "emoji":"🇪🇺","layout":"europass",       "bg":"#FFFFFF","sb":"#F0F4FF","hd":"#003399","ac":"#003399","tx":"#1A1A1A","st":"#444444","fn":"Arial,sans-serif"},
    {"id":"silicon_valley_tech",  "name":"Silicon Valley",      "emoji":"💜","layout":"tech_cards",     "bg":"#FAFAFA","sb":"#F3F0FF","hd":"#7C3AED","ac":"#7C3AED","tx":"#1F2937","st":"#6B7280","fn":"'Segoe UI',sans-serif"},
    {"id":"cyber_security",       "name":"Cyber Security",      "emoji":"🔒","layout":"dark_sidebar",   "bg":"#0B0F14","sb":"#0F1820","hd":"#0F1820","ac":"#22E07A","tx":"#C8FFD4","st":"#4A8A60","fn":"'Courier New',monospace"},
    {"id":"software_engineer",    "name":"Software Engineer",   "emoji":"💻","layout":"light_sidebar",  "bg":"#F8FAFC","sb":"#E0F0FA","hd":"#0E8FCE","ac":"#0E8FCE","tx":"#0A2030","st":"#2A5070","fn":"'Segoe UI',sans-serif"},
    {"id":"startup_founder",      "name":"Startup Founder",     "emoji":"🚀","layout":"dark_metrics",   "bg":"#0D0D1A","sb":"#131328","hd":"#1A1A2E","ac":"#E94560","tx":"#E8E8F8","st":"#7878A8","fn":"'Segoe UI',sans-serif"},
    {"id":"creative_designer",    "name":"Creative Designer",   "emoji":"🎨","layout":"initials_side",  "bg":"#FFFFFF","sb":"#16121E","hd":"#16121E","ac":"#FF5757","tx":"#1A1A1A","st":"#555555","fn":"'Segoe UI',sans-serif"},
    {"id":"construction_manager", "name":"Construction Mgr",    "emoji":"🏗️","layout":"industrial",    "bg":"#FAF6F0","sb":"#F0E8DC","hd":"#2C2C2C","ac":"#E8631A","tx":"#2C2C2C","st":"#5C5C5C","fn":"Arial,sans-serif"},
    {"id":"welder_professional",  "name":"Welder Professional", "emoji":"🔧","layout":"dark_sidebar",   "bg":"#1C1C1C","sb":"#252525","hd":"#252525","ac":"#E8731B","tx":"#E8E0D0","st":"#8A7A60","fn":"Arial,sans-serif"},
    {"id":"driver_logistics",     "name":"Driver & Logistics",  "emoji":"🚗","layout":"banner_dashed",  "bg":"#F5F8FF","sb":"#EBF0FF","hd":"#1B2951","ac":"#1B2951","tx":"#0A1528","st":"#3A5068","fn":"Arial,sans-serif","ac2":"#FFD700"},
    {"id":"hotel_hospitality",    "name":"Hotel & Hospitality", "emoji":"🏨","layout":"warm_centered",  "bg":"#FDF8F0","sb":"#F5ECD8","hd":"#8B6914","ac":"#8B6914","tx":"#2C2010","st":"#7C6030","fn":"Georgia,serif"},
    {"id":"medical_doctor",       "name":"Medical Doctor",      "emoji":"🏥","layout":"light_sidebar",  "bg":"#F0FAFA","sb":"#E0F4F4","hd":"#0F766E","ac":"#0F766E","tx":"#0A2A28","st":"#2A5A58","fn":"Arial,sans-serif"},
    {"id":"teacher_academic",     "name":"Teacher Academic",    "emoji":"📚","layout":"centered_light", "bg":"#F5F7F0","sb":"#E8EEE0","hd":"#1B5E3A","ac":"#1B5E3A","tx":"#1A2A1A","st":"#4A6A4A","fn":"Georgia,serif"},
    {"id":"finance_banking",      "name":"Finance & Banking",   "emoji":"💰","layout":"banner_light",   "bg":"#FFFFFF","sb":"#EEF0F8","hd":"#1B2951","ac":"#1B2951","tx":"#0A1020","st":"#3A5060","fn":"Georgia,serif"},
    {"id":"modern_dark_blue",     "name":"Modern Dark Blue",    "emoji":"🌊","layout":"dark_sidebar",   "bg":"#0A1628","sb":"#0F2A47","hd":"#0F2A47","ac":"#1E6FB8","tx":"#D8E8F8","st":"#4878A8","fn":"'Segoe UI',sans-serif"},
    {"id":"sales_manager",        "name":"Sales Manager",       "emoji":"📈","layout":"dark_metrics",   "bg":"#100808","sb":"#1A1010","hd":"#200A0A","ac":"#C0202C","tx":"#F0E8E8","st":"#907070","fn":"Arial,sans-serif"},
]
TPL_BY_ID = {t["id"]: t for t in TEMPLATES}

# ── Static data ───────────────────────────────────────────────────────────────
LANG_BTNS = ["🇺🇿 O'zbek", "🇷🇺 Русский", "🇬🇧 English"]
LANG_MAP  = {"🇺🇿 O'zbek":"uz","🇷🇺 Русский":"ru","🇬🇧 English":"en"}

JOBS = {
    "uz": ["🧱 Kafelchi","🔨 Quruvchi","🎨 Malyar","🧩 Gipsokartonchi","⚡ Elektrik",
           "🚰 Santexnik","🚗 Haydovchi","🚕 Taksi haydovchisi","📦 Omborchi",
           "👨‍🍳 Oshpaz","🧹 Tozalovchi","💻 IT mutaxassisi","👷 Usta","✏️ Boshqa kasb"],
    "ru": ["🧱 Плиточник","🔨 Строитель","🎨 Маляр","🧩 Гипсокартонщик","⚡ Электрик",
           "🚰 Сантехник","🚗 Водитель","🚕 Таксист","📦 Складской работник",
           "👨‍🍳 Повар","🧹 Уборщик","💻 IT специалист","👷 Мастер","✏️ Другая профессия"],
    "en": ["🧱 Tiler","🔨 Builder","🎨 Painter","🧩 Drywall Worker","⚡ Electrician",
           "🚰 Plumber","🚗 Driver","🚕 Taxi Driver","📦 Warehouse Worker",
           "👨‍🍳 Cook","🧹 Cleaner","💻 IT Specialist","👷 Craftsman","✏️ Other profession"],
}
EXPERIENCE = {
    "uz": ["Tajribasiz","1–3 yil","3–5 yil","5–10 yil","10+ yil"],
    "ru": ["Без опыта","1–3 года","3–5 лет","5–10 лет","10+ лет"],
    "en": ["No experience","1–3 years","3–5 years","5–10 years","10+ years"],
}
EDUCATION = {
    "uz": ["🏫 Maktab","🏢 Kollej / Litsey","🎓 Bakalavr","🎓 Magistr","✏️ Boshqa"],
    "ru": ["🏫 Школа","🏢 Колледж / Лицей","🎓 Бакалавр","🎓 Магистр","✏️ Другое"],
    "en": ["🏫 School","🏢 College / Lyceum","🎓 Bachelor","🎓 Master","✏️ Other"],
}

# ── Translations ──────────────────────────────────────────────────────────────
T = {
    "uz": {
        "welcome":   "👋 Salom! <b>CV_MK V2.0</b> botiga xush kelibsiz.\n\n20 ta premium dizayn ichidan o'zingizga mosini tanlaysiz!\n\n🌍 Tilni tanlang:",
        "name":      "👤 Ism va familiyangizni yozing:",
        "name_short":"⚠️ Ism juda qisqa. Qaytadan yozing:",
        "job":       "💼 Kasbingizni tanlang:",
        "job_custom":"✏️ Kasbingizni yozing:",
        "phone":     "📞 Telefon raqamingiz:",
        "email":     "📧 Email manzilingiz:",
        "address":   "📍 Manzilingiz (shahar, mamlakat):",
        "photo":     "📸 Fotosuratingizni yuboring yoki o'tkazib yuboring:",
        "summary":   "📝 O'zingiz haqida qisqacha yozing (2–3 jumla):",
        "experience":"🏢 Ish tajribangizni tanlang:",
        "education": "🎓 Ta'lim darajangizni tanlang:",
        "edu_custom":"✏️ Ta'limingizni yozing:",
        "skills":    "🛠 Ko'nikmalaringizni yozing (vergul bilan):\nMasalan: Kafel, Suvoq, Gipsokarton",
        "langs":     "🌐 Qaysi tillarni bilasiz? (vergul bilan):\nMasalan: O'zbek, Rus",
        "certs":     "📜 Sertifikat yoki diplomlaringiz? (ixtiyoriy, ⏭ o'tkazib yuborish mumkin):\nMasalan: OSHA, ISO 9001",
        "preview_hdr":"🎨 <b>Dizayn tanlang!</b>\n\nQuyidagi tugmalar orqali 20 ta premium template ko'ring va o'zingizga mosini tanlang:",
        "creating":  "⏳ CV tayyorlanmoqda...",
        "pdf_ready": "✅ PDF CV tayyor!",
        "html_ready":"🌐 HTML CV (brauzerda ochiladi):",
        "png_ready": "🖼 PNG preview:",
        "done":      "✅ CV tayyor!\n\n🔄 Yangi CV yaratish uchun /start bosing.",
        "cancelled": "❌ Bekor qilindi.\n\n/start — qayta boshlash",
        "error":     "❌ Xatolik yuz berdi. Qaytadan urining: /start",
        "skip":      "⏭️ O'tkazib yuborish",
        "cancel":    "❌ Bekor qilish",
        "wrong":     "⚠️ Iltimos, tugmalardan birini tanlang:",
        "select_btn":"✅ Shu dizaynni tanlash",
        "help":      "ℹ️ <b>CV_MK V2.0</b> — 20 ta premium dizayn\n\n/start — Yangi CV\n/cancel — Bekor qilish\n/help — Yordam",
        "labels": {
            "summary":   "O'zim haqimda","experience":"Ish tajribasi",
            "education": "Ta'lim","skills":"Ko'nikmalar","languages":"Tillar",
            "certs":     "Sertifikatlar","phone":"Telefon","email":"Email",
            "address":   "Manzil","footer":"CV_MK V2.0 Bot tomonidan yaratildi",
        },
    },
    "ru": {
        "welcome":   "👋 Привет! <b>CV_MK V2.0</b> — 20 профессиональных шаблонов!\n\nВыберите язык:",
        "name":      "👤 Напишите имя и фамилию:",
        "name_short":"⚠️ Имя слишком короткое. Напишите снова:",
        "job":       "💼 Выберите профессию:",
        "job_custom":"✏️ Напишите вашу профессию:",
        "phone":     "📞 Ваш номер телефона:",
        "email":     "📧 Ваш email:",
        "address":   "📍 Ваш адрес (город, страна):",
        "photo":     "📸 Отправьте фото или пропустите:",
        "summary":   "📝 Кратко о себе (2–3 предложения):",
        "experience":"🏢 Выберите опыт работы:",
        "education": "🎓 Выберите уровень образования:",
        "edu_custom":"✏️ Напишите ваше образование:",
        "skills":    "🛠 Напишите навыки (через запятую):\nНапример: Плитка, Штукатурка",
        "langs":     "🌐 Какие языки знаете? (через запятую):\nНапример: Русский, Узбекский",
        "certs":     "📜 Сертификаты или дипломы? (необязательно, можно ⏭ пропустить):\nНапример: ISO 9001, OSHA",
        "preview_hdr":"🎨 <b>Выберите дизайн!</b>\n\nПросмотрите 20 премиум шаблонов и выберите лучший:",
        "creating":  "⏳ Создаём резюме...",
        "pdf_ready": "✅ PDF резюме готово!",
        "html_ready":"🌐 HTML резюме (открыть в браузере):",
        "png_ready": "🖼 PNG превью:",
        "done":      "✅ Резюме готово!\n\n🔄 Новое резюме — /start",
        "cancelled": "❌ Отменено.\n\n/start — начать заново",
        "error":     "❌ Произошла ошибка. Попробуйте снова: /start",
        "skip":      "⏭️ Пропустить",
        "cancel":    "❌ Отмена",
        "wrong":     "⚠️ Пожалуйста, выберите один из вариантов:",
        "select_btn":"✅ Выбрать этот дизайн",
        "help":      "ℹ️ <b>CV_MK V2.0</b> — 20 профессиональных шаблонов\n\n/start — Новое CV\n/cancel — Отмена\n/help — Помощь",
        "labels": {
            "summary":   "Обо мне","experience":"Опыт работы",
            "education": "Образование","skills":"Навыки","languages":"Языки",
            "certs":     "Сертификаты","phone":"Телефон","email":"Email",
            "address":   "Адрес","footer":"Создано CV_MK V2.0 Bot",
        },
    },
    "en": {
        "welcome":   "👋 Hello! <b>CV_MK V2.0</b> — 20 premium designs!\n\nChoose your language:",
        "name":      "👤 Enter your full name:",
        "name_short":"⚠️ Name is too short. Please write again:",
        "job":       "💼 Choose your profession:",
        "job_custom":"✏️ Write your profession:",
        "phone":     "📞 Your phone number:",
        "email":     "📧 Your email address:",
        "address":   "📍 Your address (city, country):",
        "photo":     "📸 Send a photo or skip:",
        "summary":   "📝 Write a short professional summary (2–3 sentences):",
        "experience":"🏢 Choose your work experience:",
        "education": "🎓 Choose your education level:",
        "edu_custom":"✏️ Write your education:",
        "skills":    "🛠 Write your skills (comma-separated):\nExample: Tiling, Plastering",
        "langs":     "🌐 Languages you know (comma-separated):\nExample: Uzbek, Russian",
        "certs":     "📜 Certifications or diplomas? (optional, ⏭ skip):\nExample: ISO 9001, OSHA",
        "preview_hdr":"🎨 <b>Choose your design!</b>\n\nBrowse 20 premium templates and pick your favourite:",
        "creating":  "⏳ Creating your CV...",
        "pdf_ready": "✅ PDF CV is ready!",
        "html_ready":"🌐 HTML CV (open in browser):",
        "png_ready": "🖼 PNG preview:",
        "done":      "✅ CV is ready!\n\n🔄 Press /start for a new CV.",
        "cancelled": "❌ Cancelled.\n\n/start — start over",
        "error":     "❌ An error occurred. Try again: /start",
        "skip":      "⏭️ Skip",
        "cancel":    "❌ Cancel",
        "wrong":     "⚠️ Please choose one of the options:",
        "select_btn":"✅ Select this design",
        "help":      "ℹ️ <b>CV_MK V2.0</b> — 20 premium templates\n\n/start — New CV\n/cancel — Cancel\n/help — Help",
        "labels": {
            "summary":   "About Me","experience":"Work Experience",
            "education": "Education","skills":"Skills","languages":"Languages",
            "certs":     "Certifications","phone":"Phone","email":"Email",
            "address":   "Address","footer":"Created by CV_MK V2.0 Bot",
        },
    },
}

# ── Keyboards ─────────────────────────────────────────────────────────────────
def _kb(items, cols=2):
    rows = [items[i:i+cols] for i in range(0, len(items), cols)]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in r] for r in rows],
        resize_keyboard=True, one_time_keyboard=True,
    )

def kb_lang():          return _kb(LANG_BTNS, 1)
def kb_jobs(l):         return _kb(JOBS[l], 2)
def kb_exp(l):          return _kb(EXPERIENCE[l], 1)
def kb_edu(l):          return _kb(EDUCATION[l], 1)
def kb_cancel(l):       return _kb([T[l]["cancel"]], 1)
def kb_skip_cancel(l):  return _kb([T[l]["skip"], T[l]["cancel"]], 2)

def kb_preview(idx: int, lang: str) -> InlineKeyboardMarkup:
    t = TEMPLATES[idx]
    total = len(TEMPLATES)
    prev_i = (idx - 1) % total
    next_i = (idx + 1) % total
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️", callback_data=f"nav:{prev_i}"),
            InlineKeyboardButton(text=f"{t['emoji']} {idx+1}/{total}", callback_data="noop"),
            InlineKeyboardButton(text="➡️", callback_data=f"nav:{next_i}"),
        ],
        [InlineKeyboardButton(text=T[lang]["select_btn"], callback_data=f"sel:{idx}")],
    ])

# ── Helpers ───────────────────────────────────────────────────────────────────
_EMOJI_RE = re.compile(r"[\U0001F000-\U0001FFFF\U00002600-\U000027FF\U0000FE00-\U0000FE0F]+", re.UNICODE)

def uid():           return uuid.uuid4().hex[:12]
def safe(v):         return str(v or "").strip()
def e(v):            return _html_mod.escape(safe(v))
def strip_emoji(s):  return _EMOJI_RE.sub("", s or "").strip(" –—-")
def is_cancel(t, l): return any(w in (t or "").lower() for w in ["bekor","отмена","cancel","❌"]) or t == T[l]["cancel"]
def is_skip(t, l):   return any(w in (t or "").lower() for w in ["skip","пропустить","otkazib","⏭"]) or t == T[l]["skip"]

def cleanup(*paths):
    for p in paths:
        try:
            if p: Path(p).unlink(missing_ok=True)
        except Exception: pass

def wraptext(text, width):
    result = []
    for line in safe(text).split("\n"):
        result.extend(textwrap.wrap(line, width) or [""])
    return result

def photo_b64(path):
    try:
        p = Path(path)
        if p.exists():
            ext = p.suffix.lower().lstrip(".")
            mime = {"jpg":"jpeg","jpeg":"jpeg","png":"png","webp":"webp"}.get(ext,"jpeg")
            return f"data:image/{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
    except Exception: pass
    return ""

def _tags(val, ac):
    items = [x.strip() for x in re.split(r"[,\n]", safe(val)) if x.strip()]
    return "".join(f'<span style="display:inline-block;background:{ac}22;color:{ac};border-radius:4px;padding:2px 8px;font-size:11px;margin:2px;font-weight:600">{e(x)}</span>' for x in items)

def _initials(name):
    parts = safe(name).split()
    return "".join(p[0].upper() for p in parts[:2]) if parts else "CV"

# ── Preview image (Pillow) ────────────────────────────────────────────────────
def _h2r(h):
    h = h.lstrip("#")
    if len(h) == 3: h = "".join(c*2 for c in h)
    return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

def _mix(c1, c2, t):
    return tuple(max(0,min(255,int(a+(b-a)*t))) for a,b in zip(c1,c2))

def make_preview(tpl: dict, idx: int) -> bytes:
    W, H = 400, 566
    bg = _h2r(tpl["bg"]); sb = _h2r(tpl["sb"]); hd = _h2r(tpl["hd"])
    ac = _h2r(tpl["ac"]); tx = _h2r(tpl["tx"])
    layout = tpl.get("layout","dark_sidebar")
    WHITE = (255,255,255); BLACK = (0,0,0)

    img = Image.new("RGB", (W, H), bg)
    d   = ImageDraw.Draw(img)

    ac_dim   = _mix(bg, ac, 0.15)
    tx_dim   = _mix(bg, tx, 0.5)
    tx_light = _mix(bg, tx, 0.3)

    def text_lines(x0, ys, wds, big_col=None):
        for i,(y,w) in enumerate(zip(ys,wds)):
            col = big_col if (big_col and i==0) else (tx_dim if i>0 else _mix(bg,tx,0.8))
            h_bar = 7 if i==0 else 4
            d.rectangle([x0,y,x0+w,y+h_bar], fill=col)

    def sec_title(x, y, w=60):
        d.rectangle([x,y,x+w,y+4], fill=ac)
        d.line([x+w+6,y+2,W-14,y+2], fill=_mix(bg,ac,0.25), width=1)

    if layout in ("dark_sidebar","light_sidebar"):
        sbw = 110
        d.rectangle([0,0,sbw,H], fill=sb)
        d.line([sbw,0,sbw,H], fill=ac, width=1)
        # photo circle
        cx,cy,r = sbw//2, 68, 30
        d.ellipse([cx-r,cy-r,cx+r,cy+r], outline=ac, width=2, fill=_mix(sb,ac,0.1))
        # sidebar lines
        for i,y0 in enumerate(range(115,H-60,44)):
            d.rectangle([10,y0,sbw-10,y0+4], fill=_mix(sb,ac,0.7))
            d.rectangle([10,y0+10,sbw-16,y0+14], fill=_mix(sb,tx,0.3))
            d.rectangle([10,y0+20,sbw-22,y0+24], fill=_mix(sb,tx,0.2))
        # main content
        d.line([sbw+14,52,W-14,52], fill=ac, width=2)
        text_lines(sbw+14,[58,70],[160,90], big_col=_mix(bg,tx,0.9))
        sec_title(sbw+14,92); text_lines(sbw+14,[100,110,120],[140,110,90])
        sec_title(sbw+14,140); text_lines(sbw+14,[148,158,168],[130,100,80])
        sec_title(sbw+14,188); text_lines(sbw+14,[196,206],[120,90])

    elif layout in ("banner_light","banner_dashed"):
        # header banner
        d.rectangle([0,0,W,88], fill=hd)
        d.ellipse([14,12,74,72], fill=_mix(hd,WHITE,0.1), outline=_mix(hd,WHITE,0.4), width=2)
        d.rectangle([84,22,260,34], fill=_mix(hd,WHITE,0.9))
        d.rectangle([84,40,200,50], fill=_mix(hd,WHITE,0.5))
        if tpl.get("ac2"):
            ac2 = _h2r(tpl["ac2"])
            d.rectangle([0,88,W,92], fill=ac2)
        else:
            d.rectangle([0,88,W,92], fill=ac)
        x0=14
        sec_title(x0,104); text_lines(x0,[113,123,133],[180,140,110])
        sec_title(x0,153); text_lines(x0,[162,172,182],[200,160,130])
        sec_title(x0,202); text_lines(x0,[211,221],[170,130])
        if layout == "banner_dashed":
            d.rectangle([W-80,0,W,88], fill=_mix(hd,BLACK,0.15))

    elif layout in ("dark_banner","dark_metrics"):
        d.rectangle([0,0,W,76], fill=hd)
        metrics_bg = _mix(hd,ac,0.2)
        d.rectangle([0,76,W,106], fill=metrics_bg)
        for mx in (16,140,264):
            d.rectangle([mx,83,mx+100,96], fill=_mix(metrics_bg,ac,0.4))
        d.line([0,106,W,106], fill=ac, width=1)
        x0=14
        sec_title(x0,118); text_lines(x0,[127,137,147],[180,140,110])
        sec_title(x0,167); text_lines(x0,[176,186,196],[200,160,130])
        sec_title(x0,216); text_lines(x0,[225,235],[170,130])

    elif layout == "ats_clean":
        d.rectangle([0,0,W,3], fill=ac)
        d.rectangle([80,22,320,34], fill=_mix(bg,tx,0.85))
        d.rectangle([120,40,280,49], fill=_mix(bg,ac,0.6))
        d.rectangle([30,57,370,61], fill=_mix(bg,tx,0.25))
        d.line([20,70,W-20,70], fill=_mix(bg,tx,0.15), width=1)
        x0=20
        sec_title(x0,83,80); text_lines(x0,[95,105,115],[280,240,200])
        sec_title(x0,133,80); text_lines(x0,[145,155,165],[260,220,180])
        sec_title(x0,183,80); text_lines(x0,[195,205],[240,200])

    elif layout == "europass":
        d.rectangle([0,0,W,58], fill=hd)
        d.rectangle([0,58,W,62], fill=ac)
        d.rectangle([14,8,64,50], fill=_mix(hd,WHITE,0.1), outline=_mix(hd,WHITE,0.4), width=1)
        d.rectangle([74,16,240,28], fill=_mix(hd,WHITE,0.9))
        d.rectangle([74,34,180,43], fill=_mix(hd,WHITE,0.5))
        for y0 in range(76,H-20,30):
            d.rectangle([14,y0,90,y0+4], fill=_mix(bg,ac,0.5))
            d.rectangle([100,y0,340,y0+4], fill=_mix(bg,tx,0.4))
            d.line([14,y0+12,W-14,y0+12], fill=_mix(bg,tx,0.1), width=1)

    elif layout == "tech_cards":
        d.rectangle([0,0,W,54], fill=hd)
        for cy0 in (72,162,252,342):
            if cy0+75 > H-20: break
            d.rectangle([14,cy0,W-14,cy0+72], fill=_mix(bg,WHITE,0.6), outline=_mix(bg,ac,0.3), width=1)
            d.rectangle([24,cy0+10,180,cy0+19], fill=_mix(bg,tx,0.7))
            d.rectangle([24,cy0+26,230,cy0+31], fill=_mix(bg,tx,0.35))
            d.rectangle([24,cy0+40,190,cy0+45], fill=_mix(bg,tx,0.25))

    elif layout in ("centered_dark","centered_light","warm_centered"):
        if layout in ("centered_light","warm_centered"):
            d.rectangle([0,0,W,112], fill=hd)
        cx=W//2; r=40
        fill_c = _mix(hd if layout!="centered_dark" else bg, ac, 0.08)
        d.ellipse([cx-r,16,cx+r,96], fill=fill_c, outline=ac, width=3)
        d.rectangle([cx-120,106,cx+120,116], fill=_mix(bg,tx,0.8))
        d.rectangle([cx-80,120,cx+80,129], fill=_mix(bg,ac,0.5))
        d.line([30,136,W-30,136], fill=_mix(bg,ac,0.3), width=1)
        sec_title(W//2-60,150,60); text_lines(W//2-100,[162,172],[200,160])
        sec_title(W//2-60,192,60); text_lines(W//2-100,[204,214],[180,140])
        sec_title(W//2-60,234,60); text_lines(W//2-100,[246,256],[170,130])

    elif layout == "initials_side":
        sbw=110
        d.rectangle([0,0,sbw,H], fill=sb)
        d.line([sbw,0,sbw,H], fill=ac, width=2)
        cx,cy=sbw//2,65; r=36
        d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=_mix(sb,ac,0.2), outline=ac, width=2)
        for i,y0 in enumerate(range(118,H-40,42)):
            d.rectangle([10,y0,sbw-10,y0+4], fill=_mix(sb,ac,0.6))
            d.rectangle([10,y0+10,sbw-20,y0+14], fill=_mix(sb,tx,0.25))
        d.line([sbw+14,52,W-14,52], fill=ac, width=2)
        text_lines(sbw+14,[58,70],[150,80], big_col=_mix(bg,tx,0.9))
        sec_title(sbw+14,92); text_lines(sbw+14,[101,111,121],[140,110,85])
        sec_title(sbw+14,141); text_lines(sbw+14,[150,160],[125,95])

    elif layout == "industrial":
        d.rectangle([0,0,W,80], fill=hd)
        d.polygon([(W-90,0),(W,0),(W,80),(W-130,80)], fill=_mix(hd,ac,0.5))
        d.rectangle([0,80,W,84], fill=ac)
        x0=14
        sec_title(x0,96); text_lines(x0,[106,116,126],[190,150,120])
        sec_title(x0,148); text_lines(x0,[158,168,178],[200,160,130])
        sec_title(x0,198); text_lines(x0,[208,218],[170,130])

    else:  # fallback
        d.rectangle([0,0,W,65], fill=hd)
        d.rectangle([0,65,W,69], fill=ac)
        sec_title(14,82); text_lines(14,[92,102,112],[190,150,120])
        sec_title(14,132); text_lines(14,[142,152],[180,140])

    # Bottom bar with template info
    d.rectangle([0,H-36,W,H], fill=BLACK)
    d.rectangle([6,H-29,44,H-7], fill=ac)
    d.ellipse([W-18,6,W-6,18], fill=ac)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf.getvalue()

# ── HTML Generators ───────────────────────────────────────────────────────────
def _photo_tag(data, t):
    if data.get("photo_path"):
        b64 = photo_b64(data["photo_path"])
        if b64:
            return f'<img style="width:100px;height:100px;border-radius:50%;object-fit:cover;border:3px solid {t["ac"]};display:block;margin:0 auto" src="{b64}">'
    init = _initials(data.get("full_name","CV"))
    return (f'<div style="width:100px;height:100px;border-radius:50%;background:{t["ac"]}22;border:2px solid {t["ac"]};'
            f'display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:700;'
            f'color:{t["ac"]};margin:0 auto">{init}</div>')

def _certs_block(data, lbl, ac):
    c = safe(data.get("certifications",""))
    if not c: return ""
    items = [x.strip() for x in c.split(",") if x.strip()]
    badges = "".join(f'<span style="display:inline-block;background:{ac}22;color:{ac};border:1px solid {ac}44;border-radius:4px;padding:3px 10px;font-size:11px;margin:2px">{e(x)}</span>' for x in items)
    return f'<div style="margin-top:4px"><b style="font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:{ac}">{lbl["certs"]}</b><div style="margin-top:6px">{badges}</div></div>'

def _html_dark_sidebar(data, t, lbl):
    photo = _photo_tag(data, t)
    certs = _certs_block(data, lbl, t["ac"])
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{t['bg']};font-family:{t['fn']};color:{t['tx']};min-height:100vh}}
.wrap{{max-width:860px;margin:0 auto;display:grid;grid-template-columns:220px 1fr;min-height:100vh}}
.sb{{background:{t['sb']};padding:36px 18px;display:flex;flex-direction:column;gap:20px;border-right:1px solid {t['ac']}40}}
.sb h4{{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};margin-bottom:5px;font-weight:700}}
.sb .val{{font-size:11.5px;opacity:.8;line-height:1.6;word-break:break-all}}
.tag{{display:inline-block;background:{t['ac']}22;color:{t['ac']};border-radius:4px;padding:2px 8px;font-size:10.5px;margin:2px;font-weight:600}}
.main{{padding:40px 34px;display:flex;flex-direction:column;gap:20px}}
.hdr{{border-bottom:2px solid {t['ac']};padding-bottom:14px}}
.hdr h1{{font-size:25px;font-weight:800;color:{t['tx']}}}
.hdr .role{{font-size:13px;color:{t['ac']};font-weight:600;margin-top:5px}}
.sec h2{{font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};margin-bottom:9px;display:flex;align-items:center;gap:7px}}
.sec h2::after{{content:"";flex:1;height:1px;background:{t['ac']}40}}
.sec p{{font-size:12.5px;line-height:1.75;opacity:.9;white-space:pre-line}}
.foot{{font-size:9px;color:{t['st']};text-align:center;padding-top:14px;border-top:1px solid {t['ac']}20;margin-top:auto}}
@media print{{.wrap{{box-shadow:none}}}}
</style></head><body><div class="wrap">
<aside class="sb">
  <div style="text-align:center">{photo}</div>
  <div><h4>📞 {lbl['phone']}</h4><div class="val">{e(data.get('phone','—'))}</div></div>
  <div><h4>📧 {lbl['email']}</h4><div class="val">{e(data.get('email','—'))}</div></div>
  <div><h4>📍 {lbl['address']}</h4><div class="val">{e(data.get('address','—'))}</div></div>
  <div><h4>🌐 {lbl['languages']}</h4><div>{_tags(data.get('languages',''),t['ac'])}</div></div>
  <div><h4>🛠 {lbl['skills']}</h4><div>{_tags(data.get('skills',''),t['ac'])}</div></div>
  {"<div><h4>📜 "+lbl['certs']+"</h4><div class='val'>"+e(data.get('certifications',''))+"</div></div>" if data.get('certifications') else ""}
</aside>
<main class="main">
  <div class="hdr"><h1>{e(data.get('full_name','—'))}</h1><div class="role">{e(data.get('job','—'))}</div></div>
  <div class="sec"><h2>{lbl['summary']}</h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="sec"><h2>{lbl['experience']}</h2><p>{e(data.get('experience','—'))}</p></div>
  <div class="sec"><h2>{lbl['education']}</h2><p>{e(data.get('education','—'))}</p></div>
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</main></div></body></html>"""

def _html_banner(data, t, lbl, dashed=False):
    photo = _photo_tag(data, t)
    ac2 = t.get("ac2", t["ac"])
    stripe = f'border-left:5px dashed {ac2};padding-left:12px' if dashed else ''
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{t['bg']};font-family:{t['fn']};color:{t['tx']}}}
.hdr{{background:{t['hd']};padding:28px 36px;display:flex;align-items:center;gap:28px}}
.hdr img,.hdr .ph{{width:88px;height:88px;border-radius:50%;object-fit:cover;border:3px solid {ac2};flex-shrink:0}}
.hdr .ph{{display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:700;color:{ac2};background:{ac2}22}}
.hdr h1{{font-size:26px;font-weight:800;color:#fff;margin-bottom:4px}}
.hdr .role{{font-size:13px;color:{ac2};font-weight:600}}
.hdr .contact{{font-size:11px;color:#ffffff99;margin-top:6px;line-height:1.7}}
.stripe{{background:{t['hd']};height:4px;background:linear-gradient(90deg,{t['hd']},{ac2})}}
.body{{max-width:860px;margin:0 auto;padding:32px 36px;display:flex;flex-direction:column;gap:20px}}
.sec h2{{font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};margin-bottom:9px;display:flex;align-items:center;gap:8px;{stripe}}}
.sec h2::after{{content:"";flex:1;height:1px;background:{t['ac']}40}}
.sec p{{font-size:12.5px;line-height:1.75;opacity:.9;white-space:pre-line}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.tags span{{display:inline-block;background:{t['ac']}18;color:{t['ac']};border-radius:4px;padding:2px 9px;font-size:11px;margin:2px;font-weight:600}}
.foot{{font-size:9px;color:{t['st']};text-align:center;padding-top:12px;border-top:1px solid {t['ac']}20;margin-top:8px}}
@media print{{body{{background:{t['bg']}}}}}
</style></head><body>
<div class="hdr">
  {photo}
  <div>
    <h1>{e(data.get('full_name','—'))}</h1>
    <div class="role">{e(data.get('job','—'))}</div>
    <div class="contact">{e(data.get('phone',''))} &nbsp;|&nbsp; {e(data.get('email',''))} &nbsp;|&nbsp; {e(data.get('address',''))}</div>
  </div>
</div>
<div class="stripe"></div>
<div class="body">
  <div class="sec"><h2>{lbl['summary']}</h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="grid">
    <div class="sec"><h2>{lbl['experience']}</h2><p>{e(data.get('experience','—'))}</p></div>
    <div class="sec"><h2>{lbl['education']}</h2><p>{e(data.get('education','—'))}</p></div>
  </div>
  <div class="grid">
    <div class="sec"><h2>{lbl['skills']}</h2><div class="tags">{_tags(data.get('skills',''),t['ac'])}</div></div>
    <div class="sec"><h2>{lbl['languages']}</h2><div class="tags">{_tags(data.get('languages',''),t['ac'])}</div></div>
  </div>
  {"<div class='sec'><h2>"+lbl['certs']+"</h2><div class='tags'>"+_tags(data.get('certifications',''),t['ac'])+"</div></div>" if data.get('certifications') else ""}
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div></body></html>"""

def _html_dark_metrics(data, t, lbl):
    photo = _photo_tag(data, t)
    exp = safe(data.get('experience',''))
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{t['bg']};font-family:{t['fn']};color:{t['tx']}}}
.hdr{{background:{t['hd']};padding:28px 36px;display:flex;align-items:center;gap:28px}}
.hdr .ph{{width:80px;height:80px;border-radius:50%;background:{t['ac']}22;border:2px solid {t['ac']};display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:700;color:{t['ac']};flex-shrink:0}}
.hdr h1{{font-size:24px;font-weight:800;color:{t['tx']};margin-bottom:4px}}
.hdr .role{{font-size:13px;color:{t['ac']};font-weight:600}}
.metrics{{display:flex;gap:0;border-top:1px solid {t['ac']}40;border-bottom:1px solid {t['ac']}40}}
.metric{{flex:1;text-align:center;padding:14px 8px;border-right:1px solid {t['ac']}20}}
.metric:last-child{{border-right:none}}
.metric .val{{font-size:18px;font-weight:800;color:{t['ac']}}}
.metric .lbl{{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:{t['st']};margin-top:2px}}
.body{{max-width:860px;margin:0 auto;padding:30px 36px;display:flex;flex-direction:column;gap:20px}}
.sec h2{{font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};margin-bottom:9px;display:flex;align-items:center;gap:8px}}
.sec h2::after{{content:"";flex:1;height:1px;background:{t['ac']}40}}
.sec p{{font-size:12.5px;line-height:1.75;opacity:.9;white-space:pre-line}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.tags span{{display:inline-block;background:{t['ac']}22;color:{t['ac']};border-radius:4px;padding:2px 9px;font-size:11px;margin:2px;font-weight:600}}
.foot{{font-size:9px;color:{t['st']};text-align:center;padding-top:12px;border-top:1px solid {t['ac']}20;margin-top:8px}}
</style></head><body>
<div class="hdr">{photo}<div><h1>{e(data.get('full_name','—'))}</h1><div class="role">{e(data.get('job','—'))}</div></div></div>
<div class="metrics">
  <div class="metric"><div class="val">{exp}</div><div class="lbl">{lbl['experience']}</div></div>
  <div class="metric"><div class="val">{e(data.get('address','—'))}</div><div class="lbl">{lbl['address']}</div></div>
  <div class="metric"><div class="val">{e(data.get('phone','—'))}</div><div class="lbl">{lbl['phone']}</div></div>
</div>
<div class="body">
  <div class="sec"><h2>{lbl['summary']}</h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="grid">
    <div class="sec"><h2>{lbl['education']}</h2><p>{e(data.get('education','—'))}</p></div>
    <div><div class="sec"><h2>{lbl['skills']}</h2><div class="tags">{_tags(data.get('skills',''),t['ac'])}</div></div>
    <div class="sec" style="margin-top:16px"><h2>{lbl['languages']}</h2><div class="tags">{_tags(data.get('languages',''),t['ac'])}</div></div></div>
  </div>
  {"<div class='sec'><h2>"+lbl['certs']+"</h2><div class='tags'>"+_tags(data.get('certifications',''),t['ac'])+"</div></div>" if data.get('certifications') else ""}
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div></body></html>"""

def _html_ats_clean(data, t, lbl):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#fff;font-family:Arial,sans-serif;color:#1A1A1A;max-width:800px;margin:40px auto;padding:0 40px}}
h1{{font-size:26px;text-align:center;font-weight:700;color:#111;margin-bottom:4px}}
.role{{text-align:center;font-size:14px;color:#333;font-weight:600;margin-bottom:8px}}
.contact{{text-align:center;font-size:11.5px;color:#555;margin-bottom:14px;line-height:1.8}}
hr{{border:none;border-top:1.5px solid #CCC;margin:12px 0}}
h2{{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#111;margin:14px 0 6px}}
p{{font-size:12.5px;line-height:1.75;color:#333;white-space:pre-line}}
.tags span{{display:inline-block;border:1px solid #888;border-radius:3px;padding:2px 8px;font-size:11px;margin:2px;color:#333}}
.foot{{font-size:9px;color:#999;text-align:center;margin-top:20px;padding-top:10px;border-top:1px solid #EEE}}
</style></head><body>
<h1>{e(data.get('full_name','—'))}</h1>
<div class="role">{e(data.get('job','—'))}</div>
<div class="contact">{e(data.get('phone',''))} | {e(data.get('email',''))} | {e(data.get('address',''))}</div>
<hr>
<h2>{lbl['summary']}</h2><p>{e(data.get('summary','—'))}</p>
<hr>
<h2>{lbl['experience']}</h2><p>{e(data.get('experience','—'))}</p>
<hr>
<h2>{lbl['education']}</h2><p>{e(data.get('education','—'))}</p>
<hr>
<h2>{lbl['skills']}</h2><div class="tags">{_tags(data.get('skills',''),'#333')}</div>
<hr>
<h2>{lbl['languages']}</h2><div class="tags">{_tags(data.get('languages',''),'#333')}</div>
{"<hr><h2>"+lbl['certs']+"</h2><p>"+e(data.get('certifications',''))+"</p>" if data.get('certifications') else ""}
<div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</body></html>"""

def _html_europass(data, t, lbl):
    def row(label, val, is_tags=False):
        v = _tags(val, t['ac']) if is_tags else f'<span style="font-size:12px;color:{t["tx"]};opacity:.9">{e(val)}</span>'
        return f'<tr><td style="padding:10px 16px 10px 0;vertical-align:top;min-width:140px;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:{t["ac"]};border-bottom:1px solid {t["ac"]}18">{label}</td><td style="padding:10px 0;border-bottom:1px solid {t["ac"]}18">{v}</td></tr>'

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{t['bg']};font-family:{t['fn']};color:{t['tx']}}}
.hdr{{background:{t['hd']};padding:24px 36px;display:flex;align-items:center;gap:24px}}
.hdr h1{{font-size:24px;font-weight:800;color:#fff;margin-bottom:3px}}
.hdr .role{{font-size:12px;color:#ffffff99;font-weight:600}}
.flag{{background:#003399;color:#fff;font-size:9px;padding:2px 8px;letter-spacing:.1em;text-transform:uppercase;display:inline-block;margin-bottom:8px}}
.body{{max-width:860px;margin:0 auto;padding:28px 36px}}
.foot{{font-size:9px;color:{t['st']};padding-top:12px;border-top:1px solid {t['ac']}20;margin-top:12px}}
</style></head><body>
<div class="hdr">
  <div><div class="flag">CURRICULUM VITAE</div><h1>{e(data.get('full_name','—'))}</h1><div class="role">{e(data.get('job','—'))}</div></div>
</div>
<div class="body">
<table style="width:100%;border-collapse:collapse">
  {row(lbl['phone'], data.get('phone','—'))}
  {row(lbl['email'], data.get('email','—'))}
  {row(lbl['address'], data.get('address','—'))}
  {row(lbl['summary'], data.get('summary','—'))}
  {row(lbl['experience'], data.get('experience','—'))}
  {row(lbl['education'], data.get('education','—'))}
  {row(lbl['skills'], data.get('skills',''), is_tags=True)}
  {row(lbl['languages'], data.get('languages',''), is_tags=True)}
  {row(lbl['certs'], data.get('certifications','')) if data.get('certifications') else ''}
</table>
<div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div></body></html>"""

def _html_tech_cards(data, t, lbl):
    def card(title, content, tags=False):
        inner = _tags(content, t['ac']) if tags else f'<p style="font-size:12.5px;line-height:1.75;color:{t["tx"]};opacity:.85;white-space:pre-line">{e(content)}</p>'
        return f"""<div style="background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 2px 12px {t['ac']}18;margin-bottom:14px">
<h3 style="font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};font-weight:700;margin-bottom:10px">{title}</h3>
{inner}</div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{t['bg']};font-family:{t['fn']};color:{t['tx']}}}
.hdr{{background:linear-gradient(135deg,{t['hd']},{t['hd']}dd);padding:32px 36px;color:#fff}}
.hdr h1{{font-size:26px;font-weight:800;margin-bottom:4px}}
.hdr .role{{font-size:13px;color:{t['ac']}cc;font-weight:600;margin-bottom:8px}}
.hdr .info{{font-size:11px;opacity:.7;line-height:1.8}}
.body{{max-width:800px;margin:0 auto;padding:28px 28px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.foot{{font-size:9px;color:{t['st']};text-align:center;padding-top:10px;margin-top:8px}}
</style></head><body>
<div class="hdr">
  <h1>{e(data.get('full_name','—'))}</h1>
  <div class="role">{e(data.get('job','—'))}</div>
  <div class="info">{e(data.get('phone',''))} &nbsp;·&nbsp; {e(data.get('email',''))} &nbsp;·&nbsp; {e(data.get('address',''))}</div>
</div>
<div class="body">
  {card(lbl['summary'], data.get('summary','—'))}
  <div class="grid">
    {card(lbl['experience'], data.get('experience','—'))}
    {card(lbl['education'], data.get('education','—'))}
  </div>
  <div class="grid">
    {card(lbl['skills'], data.get('skills',''), tags=True)}
    {card(lbl['languages'], data.get('languages',''), tags=True)}
  </div>
  {card(lbl['certs'], data.get('certifications',''), tags=True) if data.get('certifications') else ''}
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div></body></html>"""

def _html_centered(data, t, lbl, dark=False):
    photo = _photo_tag(data, t)
    hdr_bg = t['hd'] if not dark else t['bg']
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{t['bg']};font-family:{t['fn']};color:{t['tx']}}}
.hdr{{background:{hdr_bg};text-align:center;padding:36px 40px 28px}}
.hdr h1{{font-size:26px;font-weight:800;color:{'#fff' if not dark else t['tx']};margin:14px 0 4px}}
.hdr .role{{font-size:13px;color:{t['ac']};font-weight:600;margin-bottom:10px}}
.hdr .info{{font-size:11px;color:{"#ffffff99" if not dark else t['st']};line-height:1.8}}
.divider{{height:3px;background:linear-gradient(90deg,{t['bg']},{t['ac']},{t['bg']})}}
.body{{max-width:860px;margin:0 auto;padding:32px 36px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.sec h2{{font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};margin-bottom:9px;display:flex;align-items:center;gap:8px}}
.sec h2::after{{content:"";flex:1;height:1px;background:{t['ac']}40}}
.sec p{{font-size:12.5px;line-height:1.75;opacity:.9;white-space:pre-line}}
.tags span{{display:inline-block;background:{t['ac']}22;color:{t['ac']};border-radius:4px;padding:2px 9px;font-size:11px;margin:2px;font-weight:600}}
.foot{{font-size:9px;color:{t['st']};text-align:center;padding-top:12px;border-top:1px solid {t['ac']}20;margin-top:8px}}
</style></head><body>
<div class="hdr">
  {photo}
  <h1>{e(data.get('full_name','—'))}</h1>
  <div class="role">{e(data.get('job','—'))}</div>
  <div class="info">{e(data.get('phone',''))} &nbsp;|&nbsp; {e(data.get('email',''))} &nbsp;|&nbsp; {e(data.get('address',''))}</div>
</div>
<div class="divider"></div>
<div class="body">
  <div class="sec" style="margin-bottom:20px"><h2>{lbl['summary']}</h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="grid">
    <div class="sec"><h2>{lbl['experience']}</h2><p>{e(data.get('experience','—'))}</p></div>
    <div class="sec"><h2>{lbl['education']}</h2><p>{e(data.get('education','—'))}</p></div>
  </div>
  <div class="grid" style="margin-top:20px">
    <div class="sec"><h2>{lbl['skills']}</h2><div class="tags">{_tags(data.get('skills',''),t['ac'])}</div></div>
    <div class="sec"><h2>{lbl['languages']}</h2><div class="tags">{_tags(data.get('languages',''),t['ac'])}</div></div>
  </div>
  {"<div class='sec' style='margin-top:20px'><h2>"+lbl['certs']+"</h2><div class='tags'>"+_tags(data.get('certifications',''),t['ac'])+"</div></div>" if data.get('certifications') else ""}
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div></body></html>"""

def _html_initials_side(data, t, lbl):
    init = _initials(data.get("full_name","CV"))
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{t['bg']};font-family:{t['fn']};color:{t['tx']}}}
.wrap{{max-width:860px;margin:0 auto;display:grid;grid-template-columns:220px 1fr;min-height:100vh}}
.sb{{background:{t['sb']};padding:36px 18px;display:flex;flex-direction:column;gap:20px;align-items:center}}
.initials{{width:110px;height:110px;border-radius:50%;background:{t['ac']}33;border:2px solid {t['ac']};display:flex;align-items:center;justify-content:center;font-size:38px;font-weight:900;color:{t['ac']};margin-bottom:8px;font-family:Georgia,serif}}
.sb h4{{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};margin-bottom:4px;font-weight:700;align-self:flex-start}}
.sb .val{{font-size:11px;color:#ffffff99;line-height:1.6;word-break:break-all;align-self:flex-start}}
.main{{padding:40px 34px;display:flex;flex-direction:column;gap:20px;border-left:2px solid {t['ac']}}}
.hdr h1{{font-size:25px;font-weight:800;color:{t['tx']}}}
.hdr .role{{font-size:13px;color:{t['ac']};font-weight:600;margin-top:5px}}
.sec h2{{font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};margin-bottom:9px;display:flex;align-items:center;gap:7px}}
.sec h2::after{{content:"";flex:1;height:1px;background:{t['ac']}40}}
.sec p{{font-size:12.5px;line-height:1.75;color:{t['tx']};opacity:.9;white-space:pre-line}}
.tags span{{display:inline-block;background:{t['ac']}22;color:{t['ac']};border-radius:4px;padding:2px 9px;font-size:11px;margin:2px}}
.foot{{font-size:9px;color:{t['st']};text-align:center;padding-top:12px;border-top:1px solid {t['ac']}20;margin-top:auto}}
</style></head><body><div class="wrap">
<aside class="sb">
  <div class="initials">{init}</div>
  <div><h4>📞 {lbl['phone']}</h4><div class="val">{e(data.get('phone','—'))}</div></div>
  <div><h4>📧 {lbl['email']}</h4><div class="val">{e(data.get('email','—'))}</div></div>
  <div><h4>📍 {lbl['address']}</h4><div class="val">{e(data.get('address','—'))}</div></div>
  <div><h4>🌐 {lbl['languages']}</h4><div>{_tags(data.get('languages',''),t['ac'])}</div></div>
  <div><h4>🛠 {lbl['skills']}</h4><div>{_tags(data.get('skills',''),t['ac'])}</div></div>
</aside>
<main class="main">
  <div class="hdr"><h1>{e(data.get('full_name','—'))}</h1><div class="role">{e(data.get('job','—'))}</div></div>
  <div class="sec"><h2>{lbl['summary']}</h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="sec"><h2>{lbl['experience']}</h2><p>{e(data.get('experience','—'))}</p></div>
  <div class="sec"><h2>{lbl['education']}</h2><p>{e(data.get('education','—'))}</p></div>
  {"<div class='sec'><h2>"+lbl['certs']+"</h2><div class='tags'>"+_tags(data.get('certifications',''),t['ac'])+"</div></div>" if data.get('certifications') else ""}
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</main></div></body></html>"""

def _html_industrial(data, t, lbl):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{t['bg']};font-family:{t['fn']};color:{t['tx']}}}
.hdr{{background:{t['hd']};padding:28px 36px;position:relative;overflow:hidden}}
.hdr::after{{content:"";position:absolute;right:0;top:0;width:0;height:0;border-style:solid;border-width:0 140px 88px 0;border-color:transparent {t['ac']} transparent transparent;opacity:.7}}
.hdr h1{{font-size:26px;font-weight:900;color:#fff;margin-bottom:4px}}
.hdr .role{{font-size:13px;color:{t['ac']};font-weight:700}}
.stripe{{height:4px;background:{t['ac']}}}
.body{{max-width:860px;margin:0 auto;padding:30px 36px;display:flex;flex-direction:column;gap:18px}}
.contact{{display:flex;gap:24px;flex-wrap:wrap;padding:14px 20px;background:{t['sb']};border-radius:6px;border-left:4px solid {t['ac']}}}
.contact span{{font-size:11.5px;color:{t['tx']};opacity:.85}}
.sec h2{{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};font-weight:700;margin-bottom:9px;display:flex;align-items:center;gap:8px}}
.sec h2::after{{content:"";flex:1;height:1px;background:{t['ac']}40}}
.sec p{{font-size:12.5px;line-height:1.75;opacity:.9;white-space:pre-line}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.tags span{{display:inline-block;background:{t['ac']}22;color:{t['ac']};border-radius:4px;padding:2px 9px;font-size:11px;margin:2px;font-weight:600}}
.foot{{font-size:9px;color:{t['st']};text-align:center;padding-top:12px;border-top:1px solid {t['ac']}30;margin-top:4px}}
</style></head><body>
<div class="hdr">
  <h1>{e(data.get('full_name','—'))}</h1>
  <div class="role">{e(data.get('job','—'))}</div>
</div>
<div class="stripe"></div>
<div class="body">
  <div class="contact">
    <span>📞 {e(data.get('phone','—'))}</span>
    <span>📧 {e(data.get('email','—'))}</span>
    <span>📍 {e(data.get('address','—'))}</span>
  </div>
  <div class="sec"><h2>{lbl['summary']}</h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="grid">
    <div class="sec"><h2>{lbl['experience']}</h2><p>{e(data.get('experience','—'))}</p></div>
    <div class="sec"><h2>{lbl['education']}</h2><p>{e(data.get('education','—'))}</p></div>
  </div>
  <div class="grid">
    <div class="sec"><h2>{lbl['skills']}</h2><div class="tags">{_tags(data.get('skills',''),t['ac'])}</div></div>
    <div class="sec"><h2>{lbl['languages']}</h2><div class="tags">{_tags(data.get('languages',''),t['ac'])}</div></div>
  </div>
  {"<div class='sec'><h2>"+lbl['certs']+"</h2><div class='tags'>"+_tags(data.get('certifications',''),t['ac'])+"</div></div>" if data.get('certifications') else ""}
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div></body></html>"""

# ── Main HTML dispatcher ──────────────────────────────────────────────────────
def generate_html(data: dict, fid: str, tpl_id: str) -> Path:
    t    = TPL_BY_ID.get(tpl_id, TEMPLATES[0])
    lang = data.get("lang","uz")
    lbl  = T[lang]["labels"]
    layout = t.get("layout","dark_sidebar")

    if layout in ("dark_sidebar","light_sidebar"):
        html = _html_dark_sidebar(data, t, lbl)
    elif layout in ("banner_light","banner_dashed"):
        html = _html_banner(data, t, lbl, dashed=(layout=="banner_dashed"))
    elif layout in ("dark_banner","dark_metrics"):
        html = _html_dark_metrics(data, t, lbl)
    elif layout == "ats_clean":
        html = _html_ats_clean(data, t, lbl)
    elif layout == "europass":
        html = _html_europass(data, t, lbl)
    elif layout == "tech_cards":
        html = _html_tech_cards(data, t, lbl)
    elif layout in ("centered_dark","centered_light","warm_centered"):
        html = _html_centered(data, t, lbl, dark=(layout=="centered_dark"))
    elif layout == "initials_side":
        html = _html_initials_side(data, t, lbl)
    elif layout == "industrial":
        html = _html_industrial(data, t, lbl)
    else:
        html = _html_dark_sidebar(data, t, lbl)

    out = OUT_DIR / f"cv_{fid}.html"
    out.write_text(html, encoding="utf-8")
    return out

# ── PDF Generator ─────────────────────────────────────────────────────────────
def generate_pdf(data: dict, fid: str, tpl_id: str) -> Path:
    t    = TPL_BY_ID.get(tpl_id, TEMPLATES[0])
    out  = OUT_DIR / f"cv_{fid}.pdf"
    lang = data.get("lang","uz")
    lbl  = T[lang]["labels"]

    def _rgb(h):
        h = h.lstrip("#")
        if len(h)==3: h="".join(c*2 for c in h)
        return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))

    bg_c  = _rgb(t["bg"])
    sb_c  = _rgb(t["sb"])
    ac_c  = _rgb(t["ac"])
    tx_c  = _rgb(t["tx"])
    hd_c  = _rgb(t["hd"])

    cnv = rl_canvas.Canvas(str(out), pagesize=A4)
    W, H = A4
    SW = 200

    # Background
    cnv.setFillColorRGB(*bg_c); cnv.rect(0,0,W,H,fill=1,stroke=0)
    # Sidebar
    cnv.setFillColorRGB(*sb_c); cnv.rect(0,0,SW,H,fill=1,stroke=0)
    # Header bar
    cnv.setFillColorRGB(*hd_c); cnv.rect(0,H-44,W,44,fill=1,stroke=0)
    # Accent line
    cnv.setFillColorRGB(*ac_c); cnv.rect(SW,H-44,2,44,fill=1,stroke=0)
    # Brand
    cnv.setFillColorRGB(1,1,1); cnv.setFont(FONT,10)
    cnv.drawString(14,H-28,"CV_MK V2.0")

    # Photo circle in sidebar
    px, py, pr = int(SW//2), int(H-100), 35
    cnv.setFillColorRGB(*ac_c); cnv.circle(px,py,pr+2,fill=1,stroke=0)
    cnv.setFillColorRGB(*sb_c); cnv.circle(px,py,pr,fill=1,stroke=0)

    photo_path = data.get("photo_path","")
    if photo_path and Path(photo_path).exists():
        try:
            from PIL import Image as PILImg
            from reportlab.lib.utils import ImageReader
            img = PILImg.open(photo_path).convert("RGB")
            sz  = min(img.size)
            img = img.crop(((img.width-sz)//2,(img.height-sz)//2,(img.width+sz)//2,(img.height+sz)//2)).resize((pr*2,pr*2))
            buf = io.BytesIO(); img.save(buf,"JPEG"); buf.seek(0)
            cnv.drawImage(ImageReader(buf), px-pr, py-pr, pr*2, pr*2, mask="auto")
        except Exception: pass

    sy = py - pr - 20

    def st(title):
        nonlocal sy
        if sy < 50: return
        cnv.setFillColorRGB(*ac_c); cnv.setFont(FONT,7)
        cnv.drawString(8,sy,title.upper()); sy -= 12

    def sv(text):
        nonlocal sy
        cnv.setFillColorRGB(*tx_c); cnv.setFont(FONT,8)
        for line in textwrap.wrap(safe(text),26):
            if sy < 40: break
            cnv.drawString(8,sy,line); sy -= 11

    st(lbl["phone"]);    sv(safe(data.get("phone"))); sy -= 4
    st(lbl["email"]);    sv(safe(data.get("email"))); sy -= 4
    st(lbl["address"]);  sv(safe(data.get("address"))); sy -= 4
    st(lbl["languages"]);sv(safe(data.get("languages"))); sy -= 4
    st(lbl["skills"]);   sv(safe(data.get("skills")))
    if data.get("certifications"):
        sy -= 4; st(lbl["certs"]); sv(safe(data.get("certifications")))

    cnv.setFillColorRGB(*ac_c); cnv.setFont(FONT,6)
    cnv.drawString(8,14,f"{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}")

    # Main content
    my = H - 66
    cnv.setFillColorRGB(*tx_c); cnv.setFont(FONT,18)
    cnv.drawString(SW+14, my, safe(data.get("full_name",""))[:42]); my -= 20
    cnv.setFillColorRGB(*ac_c); cnv.setFont(FONT,11)
    cnv.drawString(SW+14, my, safe(data.get("job",""))[:50]); my -= 14
    cnv.setStrokeColorRGB(*ac_c); cnv.setLineWidth(1.2)
    cnv.line(SW+14, my, W-18, my); my -= 16

    def section(title, body):
        nonlocal my
        if my < 80:
            cnv.showPage()
            cnv.setFillColorRGB(*bg_c); cnv.rect(0,0,W,H,fill=1,stroke=0)
            cnv.setFillColorRGB(*sb_c); cnv.rect(0,0,SW,H,fill=1,stroke=0)
            my = H-40
        cnv.setFillColorRGB(*ac_c); cnv.setFont(FONT,9)
        cnv.drawString(SW+14, my, title.upper()); my -= 5
        cnv.setStrokeColorRGB(*ac_c); cnv.setLineWidth(0.4)
        cnv.line(SW+14, my, W-18, my); my -= 13
        cnv.setFillColorRGB(*tx_c); cnv.setFont(FONT,8.5)
        for line in textwrap.wrap(safe(body), 64) or [" "]:
            if my < 45:
                cnv.showPage()
                cnv.setFillColorRGB(*bg_c); cnv.rect(0,0,W,H,fill=1,stroke=0)
                cnv.setFillColorRGB(*sb_c); cnv.rect(0,0,SW,H,fill=1,stroke=0)
                my = H-40
                cnv.setFillColorRGB(*tx_c); cnv.setFont(FONT,8.5)
            cnv.drawString(SW+18, my, line); my -= 12
        my -= 8

    section(lbl["summary"],    safe(data.get("summary")))
    section(lbl["experience"], safe(data.get("experience")))
    section(lbl["education"],  safe(data.get("education")))
    if data.get("certifications"):
        section(lbl["certs"], safe(data.get("certifications")))

    cnv.save()
    return out

# ── Commands ──────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CV.lang)
    await msg.answer(T["uz"]["welcome"], reply_markup=kb_lang(), parse_mode="HTML")

@dp.message(Command("cancel"))
async def cmd_cancel(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang","uz")
    await state.clear(); await state.set_state(CV.lang)
    await msg.answer(T[lang]["cancelled"], reply_markup=kb_lang())

@dp.message(Command("help"))
async def cmd_help(msg: Message, state: FSMContext):
    data = await state.get_data()
    await msg.answer(T[data.get("lang","uz")]["help"], parse_mode="HTML")

# ── FSM handlers ──────────────────────────────────────────────────────────────
async def _cancel(msg, state):
    data = await state.get_data(); lang = data.get("lang","uz")
    await state.clear(); await state.set_state(CV.lang)
    await msg.answer(T[lang]["cancelled"], reply_markup=kb_lang())

@dp.message(StateFilter(CV.lang), F.text.in_(LANG_BTNS))
async def h_lang(msg: Message, state: FSMContext):
    lang = LANG_MAP[msg.text]
    await state.update_data(lang=lang)
    await state.set_state(CV.full_name)
    await msg.answer(T[lang]["name"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.full_name), F.text)
async def h_name(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    if len(msg.text.strip()) < 3:
        return await msg.answer(T[lang]["name_short"], reply_markup=kb_cancel(lang))
    await state.update_data(full_name=msg.text.strip())
    await state.set_state(CV.job)
    await msg.answer(T[lang]["job"], reply_markup=kb_jobs(lang))

@dp.message(StateFilter(CV.job), F.text)
async def h_job(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    if msg.text not in JOBS[lang]:
        return await msg.answer(T[lang]["wrong"], reply_markup=kb_jobs(lang))
    if any(w in msg.text.lower() for w in ["boshqa","другая","other","✏"]):
        await state.set_state(CV.job_custom)
        return await msg.answer(T[lang]["job_custom"], reply_markup=kb_cancel(lang))
    await state.update_data(job=strip_emoji(msg.text))
    await state.set_state(CV.phone)
    await msg.answer(T[lang]["phone"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.job_custom), F.text)
async def h_job_custom(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    await state.update_data(job=msg.text.strip())
    await state.set_state(CV.phone)
    await msg.answer(T[lang]["phone"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.phone), F.text)
async def h_phone(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    await state.update_data(phone=msg.text.strip())
    await state.set_state(CV.email)
    await msg.answer(T[lang]["email"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.email), F.text)
async def h_email(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    await state.update_data(email=msg.text.strip())
    await state.set_state(CV.address)
    await msg.answer(T[lang]["address"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.address), F.text)
async def h_address(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    await state.update_data(address=msg.text.strip())
    await state.set_state(CV.photo)
    await msg.answer(T[lang]["photo"], reply_markup=kb_skip_cancel(lang))

@dp.message(StateFilter(CV.photo), F.photo)
async def h_photo(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    try:
        file = await bot.get_file(msg.photo[-1].file_id)
        path = OUT_DIR / f"p_{uid()}.jpg"
        await bot.download_file(file.file_path, destination=path)
        await state.update_data(photo_path=str(path))
    except Exception as ex:
        log.warning("Photo error: %s", ex)
        await state.update_data(photo_path="")
    await state.set_state(CV.summary)
    await msg.answer(T[lang]["summary"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.photo), F.text)
async def h_photo_text(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    if is_skip(msg.text, lang):
        await state.update_data(photo_path="")
        await state.set_state(CV.summary)
        return await msg.answer(T[lang]["summary"], reply_markup=kb_cancel(lang))
    await msg.answer(T[lang]["photo"], reply_markup=kb_skip_cancel(lang))

@dp.message(StateFilter(CV.summary), F.text)
async def h_summary(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    await state.update_data(summary=msg.text.strip())
    await state.set_state(CV.experience)
    await msg.answer(T[lang]["experience"], reply_markup=kb_exp(lang))

@dp.message(StateFilter(CV.experience), F.text)
async def h_experience(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    if msg.text not in EXPERIENCE[lang]:
        return await msg.answer(T[lang]["wrong"], reply_markup=kb_exp(lang))
    await state.update_data(experience=msg.text)
    await state.set_state(CV.education)
    await msg.answer(T[lang]["education"], reply_markup=kb_edu(lang))

@dp.message(StateFilter(CV.education), F.text)
async def h_education(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    if msg.text not in EDUCATION[lang]:
        return await msg.answer(T[lang]["wrong"], reply_markup=kb_edu(lang))
    if any(w in msg.text.lower() for w in ["boshqa","другое","other","✏"]):
        await state.set_state(CV.education_custom)
        return await msg.answer(T[lang]["edu_custom"], reply_markup=kb_cancel(lang))
    await state.update_data(education=strip_emoji(msg.text))
    await state.set_state(CV.skills)
    await msg.answer(T[lang]["skills"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.education_custom), F.text)
async def h_edu_custom(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    await state.update_data(education=msg.text.strip())
    await state.set_state(CV.skills)
    await msg.answer(T[lang]["skills"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.skills), F.text)
async def h_skills(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    await state.update_data(skills=msg.text.strip())
    await state.set_state(CV.languages)
    await msg.answer(T[lang]["langs"], reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.languages), F.text)
async def h_languages(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    await state.update_data(languages=msg.text.strip())
    await state.set_state(CV.certifications)
    await msg.answer(T[lang]["certs"], reply_markup=kb_skip_cancel(lang))

@dp.message(StateFilter(CV.certifications), F.text)
async def h_certifications(msg: Message, state: FSMContext):
    data = await state.get_data(); lang = data.get("lang","uz")
    if is_cancel(msg.text, lang): return await _cancel(msg, state)
    if not is_skip(msg.text, lang):
        await state.update_data(certifications=msg.text.strip())
    await _start_preview(msg, state)

async def _start_preview(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang","uz")
    await state.set_state(CV.preview)
    await state.update_data(template_idx=0)
    await msg.answer(T[lang]["preview_hdr"], parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    idx = 0
    tpl = TEMPLATES[idx]
    img = make_preview(tpl, idx)
    caption = f"{tpl['emoji']} <b>{tpl['name']}</b>  ({idx+1}/{len(TEMPLATES)})"
    await msg.answer_photo(
        photo=BufferedInputFile(img, filename="preview.jpg"),
        caption=caption,
        parse_mode="HTML",
        reply_markup=kb_preview(idx, lang),
    )

# ── Carousel callback handlers ─────────────────────────────────────────────────
@dp.callback_query(StateFilter(CV.preview), F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()

@dp.callback_query(StateFilter(CV.preview), F.data.startswith("nav:"))
async def cb_navigate(callback: CallbackQuery, state: FSMContext):
    idx  = int(callback.data.split(":")[1])
    data = await state.get_data()
    lang = data.get("lang","uz")
    await state.update_data(template_idx=idx)
    tpl = TEMPLATES[idx]
    img = make_preview(tpl, idx)
    caption = f"{tpl['emoji']} <b>{tpl['name']}</b>  ({idx+1}/{len(TEMPLATES)})"
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=BufferedInputFile(img, filename="preview.jpg"),
                caption=caption,
                parse_mode="HTML",
            ),
            reply_markup=kb_preview(idx, lang),
        )
    except Exception as ex:
        log.warning("edit_media error: %s", ex)
    await callback.answer()

@dp.callback_query(StateFilter(CV.preview), F.data.startswith("sel:"))
async def cb_select(callback: CallbackQuery, state: FSMContext):
    idx  = int(callback.data.split(":")[1])
    data = await state.get_data()
    lang = data.get("lang","uz")
    tpl  = TEMPLATES[idx]

    await callback.answer(f"✅ {tpl['name']}")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception: pass

    wait = await callback.message.answer(T[lang]["creating"])
    fid  = uid()
    html_path = pdf_path = None
    try:
        html_path = generate_html(data, fid, tpl["id"])
        pdf_path  = generate_pdf(data, fid, tpl["id"])
        # PNG — high-res preview
        png_bytes = make_preview(tpl, idx)

        await callback.message.answer_document(FSInputFile(pdf_path),  caption=T[lang]["pdf_ready"])
        await callback.message.answer_document(FSInputFile(html_path), caption=T[lang]["html_ready"])
        await callback.message.answer_photo(
            photo=BufferedInputFile(png_bytes, "cv_preview.jpg"),
            caption=T[lang]["png_ready"],
        )
        await callback.message.answer(T[lang]["done"], reply_markup=kb_lang(), parse_mode="HTML")
    except Exception as ex:
        log.exception("CV generate error: %s", ex)
        await callback.message.answer(T[lang]["error"], reply_markup=kb_lang())
    finally:
        try: await wait.delete()
        except Exception: pass
        cleanup(html_path, pdf_path, data.get("photo_path",""))
        await state.clear()
        await state.set_state(CV.lang)

# ── Catch-all ─────────────────────────────────────────────────────────────────
@dp.message()
async def catch_all(msg: Message, state: FSMContext):
    data    = await state.get_data()
    lang    = data.get("lang","uz")
    current = await state.get_state()
    if not current or current == CV.lang.state:
        await state.clear(); await state.set_state(CV.lang)
        await msg.answer(T["uz"]["welcome"], reply_markup=kb_lang(), parse_mode="HTML")
    elif current == CV.photo.state:
        await msg.answer(T[lang]["photo"], reply_markup=kb_skip_cancel(lang))
    else:
        await msg.answer(T[lang]["wrong"])

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    log.info("CV_MK V2.0 ishga tushmoqda...")
    try:
        me = await bot.get_me()
        log.info("Bot: @%s (id=%s)", me.username, me.id)
    except Exception as ex:
        log.critical("BOT_TOKEN xato: %s", ex); raise

    if RENDER_URL:
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
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("Polling (local dev)...")
        await dp.start_polling(bot, allowed_updates=["message","callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
