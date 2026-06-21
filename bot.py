"""CV_MK V2.1 — HTML-first engine: WeasyPrint renders PDF from same HTML source"""
import asyncio, base64, html as _htm, io, logging, os, re, textwrap, uuid
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
from PIL import Image, ImageDraw

try:
    from weasyprint import HTML as WP_HTML
    HAS_WP = True
except ImportError:
    HAS_WP = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("cv_mk")
if not HAS_WP:
    log.warning("WeasyPrint not found — PDF unavailable until installed")

TOKEN      = os.environ["BOT_TOKEN"]
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
WH_PATH    = f"/wh/{TOKEN[-10:]}"
OUT_DIR    = Path(__file__).parent / "output"
OUT_DIR.mkdir(exist_ok=True)

bot = Bot(token=TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

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

# ── 25 Templates ──────────────────────────────────────────────────────────────
TEMPLATES = [
    {"id":"executive_black",      "name":"Executive Black",     "emoji":"⚫","layout":"dark_sidebar",   "bg":"#13161A","sb":"#1C2128","hd":"#1C2128","ac":"#C9A84C","tx":"#E8E0D0","st":"#8A7A60","fn":"Georgia,'Times New Roman',serif"},
    {"id":"premium_gold",         "name":"Premium Gold",        "emoji":"🥇","layout":"dark_banner",    "bg":"#141414","sb":"#1E1E1E","hd":"#0D0D0D","ac":"#D4AF37","tx":"#F0E8D0","st":"#9A9070","fn":"Georgia,serif"},
    {"id":"luxury_black_gold",    "name":"Luxury Black Gold",   "emoji":"✨","layout":"centered_dark",  "bg":"#0D0D0D","sb":"#181818","hd":"#0D0D0D","ac":"#BFA16A","tx":"#F0E8D8","st":"#8A7850","fn":"Georgia,serif"},
    {"id":"corporate_blue",       "name":"Corporate Blue",      "emoji":"🔵","layout":"banner_light",   "bg":"#FFFFFF","sb":"#EEF3FA","hd":"#1B3B6F","ac":"#1B3B6F","tx":"#0F1F3A","st":"#3A5878","fn":"Arial,sans-serif"},
    {"id":"ats_minimal_white",    "name":"ATS Minimal",         "emoji":"⬜","layout":"ats_clean",      "bg":"#FFFFFF","sb":"#F5F5F5","hd":"#FFFFFF","ac":"#2C2C2C","tx":"#1A1A1A","st":"#555555","fn":"Arial,sans-serif"},
    {"id":"europass_professional","name":"Europass Pro",        "emoji":"🇪🇺","layout":"europass",       "bg":"#FFFFFF","sb":"#F0F4FF","hd":"#003399","ac":"#003399","tx":"#1A1A1A","st":"#444444","fn":"Arial,sans-serif"},
    {"id":"silicon_valley_tech",  "name":"Silicon Valley",      "emoji":"💜","layout":"tech_cards",     "bg":"#FAFAFA","sb":"#F3F0FF","hd":"#7C3AED","ac":"#7C3AED","tx":"#1F2937","st":"#6B7280","fn":"'Segoe UI',Arial,sans-serif"},
    {"id":"cyber_security",       "name":"Cyber Security",      "emoji":"🔒","layout":"dark_sidebar",   "bg":"#0B0F14","sb":"#0F1820","hd":"#0F1820","ac":"#22E07A","tx":"#C8FFD4","st":"#4A8A60","fn":"'Courier New',Courier,monospace"},
    {"id":"software_engineer",    "name":"Software Engineer",   "emoji":"💻","layout":"light_sidebar",  "bg":"#F8FAFC","sb":"#E0F0FA","hd":"#0E8FCE","ac":"#0E8FCE","tx":"#0A2030","st":"#2A5070","fn":"'Segoe UI',Arial,sans-serif"},
    {"id":"startup_founder",      "name":"Startup Founder",     "emoji":"🚀","layout":"dark_metrics",   "bg":"#0D0D1A","sb":"#131328","hd":"#1A1A2E","ac":"#E94560","tx":"#E8E8F8","st":"#7878A8","fn":"'Segoe UI',Arial,sans-serif"},
    {"id":"creative_designer",    "name":"Creative Designer",   "emoji":"🎨","layout":"initials_side",  "bg":"#FFFFFF","sb":"#16121E","hd":"#16121E","ac":"#FF5757","tx":"#1A1A1A","st":"#555555","fn":"'Segoe UI',Arial,sans-serif"},
    {"id":"construction_manager", "name":"Construction Mgr",    "emoji":"🏗️","layout":"industrial",    "bg":"#FAF6F0","sb":"#F0E8DC","hd":"#2C2C2C","ac":"#E8631A","tx":"#2C2C2C","st":"#5C5C5C","fn":"Arial,sans-serif"},
    {"id":"welder_professional",  "name":"Welder Professional", "emoji":"🔧","layout":"dark_sidebar",   "bg":"#1C1C1C","sb":"#252525","hd":"#252525","ac":"#E8731B","tx":"#E8E0D0","st":"#8A7A60","fn":"Arial,sans-serif"},
    {"id":"driver_logistics",     "name":"Driver & Logistics",  "emoji":"🚗","layout":"banner_dashed",  "bg":"#F5F8FF","sb":"#EBF0FF","hd":"#1B2951","ac":"#1B2951","tx":"#0A1528","st":"#3A5068","fn":"Arial,sans-serif","ac2":"#FFD700"},
    {"id":"hotel_hospitality",    "name":"Hotel & Hospitality", "emoji":"🏨","layout":"warm_centered",  "bg":"#FDF8F0","sb":"#F5ECD8","hd":"#8B6914","ac":"#8B6914","tx":"#2C2010","st":"#7C6030","fn":"Georgia,serif"},
    {"id":"medical_doctor",       "name":"Medical Doctor",      "emoji":"🏥","layout":"light_sidebar",  "bg":"#F0FAFA","sb":"#E0F4F4","hd":"#0F766E","ac":"#0F766E","tx":"#0A2A28","st":"#2A5A58","fn":"Arial,sans-serif"},
    {"id":"teacher_academic",     "name":"Teacher Academic",    "emoji":"📚","layout":"centered_light", "bg":"#F5F7F0","sb":"#E8EEE0","hd":"#1B5E3A","ac":"#1B5E3A","tx":"#1A2A1A","st":"#4A6A4A","fn":"Georgia,serif"},
    {"id":"finance_banking",      "name":"Finance & Banking",   "emoji":"💰","layout":"banner_light",   "bg":"#FFFFFF","sb":"#EEF0F8","hd":"#1B2951","ac":"#1B2951","tx":"#0A1020","st":"#3A5060","fn":"Georgia,serif"},
    {"id":"modern_dark_blue",     "name":"Modern Dark Blue",    "emoji":"🌊","layout":"dark_sidebar",   "bg":"#0A1628","sb":"#0F2A47","hd":"#0F2A47","ac":"#1E6FB8","tx":"#D8E8F8","st":"#4878A8","fn":"'Segoe UI',Arial,sans-serif"},
    {"id":"sales_manager",        "name":"Sales Manager",       "emoji":"📈","layout":"dark_metrics",   "bg":"#100808","sb":"#1A1010","hd":"#200A0A","ac":"#C0202C","tx":"#F0E8E8","st":"#907070","fn":"Arial,sans-serif"},
    # ── Uzbek vocational templates (21-25) ─────────────────────────────────────
    {"id":"quruvchi",             "name":"Quruvchi-usta",        "emoji":"🧱","layout":"uzbek_sidebar",  "bg":"#FFFFFF","sb":"#2C333A","hd":"#2C333A","ac":"#E8631A","tx":"#22262B","st":"#888888","fn":"'Segoe UI',Arial,sans-serif"},
    {"id":"oshpaz",               "name":"Oshpaz",               "emoji":"👨‍🍳","layout":"uzbek_banner",  "bg":"#FFFFFF","sb":"#7A2E1E","hd":"#7A2E1E","ac":"#C0492B","tx":"#2A1714","st":"#888888","fn":"'Segoe UI',Arial,sans-serif"},
    {"id":"oshpaz_yordamchisi",   "name":"Oshpaz yordamchisi",  "emoji":"🍴","layout":"uzbek_sidebar",  "bg":"#FFFFFF","sb":"#2F6B33","hd":"#2F6B33","ac":"#3E8E41","tx":"#1C2B22","st":"#888888","fn":"'Segoe UI',Arial,sans-serif"},
    {"id":"tozalovchi",           "name":"Tozalovchi/Xizmatchi","emoji":"🧹","layout":"uzbek_sidebar",  "bg":"#FFFFFF","sb":"#0E7C72","hd":"#0E7C72","ac":"#0E9488","tx":"#13302C","st":"#888888","fn":"'Segoe UI',Arial,sans-serif"},
    {"id":"zavod_ishchisi",       "name":"Zavod ishchisi",       "emoji":"🏭","layout":"uzbek_banner",   "bg":"#FFFFFF","sb":"#16344F","hd":"#16344F","ac":"#1F6FB2","tx":"#16202B","st":"#888888","fn":"'Segoe UI',Arial,sans-serif"},
]
TPL_BY_ID = {t["id"]: t for t in TEMPLATES}

UZ_VOC_LABELS = {
    "summary":"Men haqimda","experience":"Ish tajribasi","education":"Ta'lim va kurslar",
    "skills":"Ko'nikmalar","qualities":"Shaxsiy fazilatlar","languages":"Tillar",
    "certs":"Sertifikatlar","phone":"Tel","email":"Email","address":"Manzil",
    "contact":"Aloqa","footer":"CV_MK V2.1",
}

# ── Static data ───────────────────────────────────────────────────────────────
LANG_BTNS = ["🇺🇿 O'zbek","🇷🇺 Русский","🇬🇧 English"]
LANG_MAP  = {"🇺🇿 O'zbek":"uz","🇷🇺 Русский":"ru","🇬🇧 English":"en"}
JOBS = {
    "uz":["🧱 Kafelchi","🔨 Quruvchi","🎨 Malyar","🧩 Gipsokartonchi","⚡ Elektrik",
          "🚰 Santexnik","🚗 Haydovchi","🚕 Taksi haydovchisi","📦 Omborchi",
          "👨‍🍳 Oshpaz","🧹 Tozalovchi","💻 IT mutaxassisi","👷 Usta","✏️ Boshqa kasb"],
    "ru":["🧱 Плиточник","🔨 Строитель","🎨 Маляр","🧩 Гипсокартонщик","⚡ Электрик",
          "🚰 Сантехник","🚗 Водитель","🚕 Таксист","📦 Складской работник",
          "👨‍🍳 Повар","🧹 Уборщик","💻 IT специалист","👷 Мастер","✏️ Другая профессия"],
    "en":["🧱 Tiler","🔨 Builder","🎨 Painter","🧩 Drywall Worker","⚡ Electrician",
          "🚰 Plumber","🚗 Driver","🚕 Taxi Driver","📦 Warehouse Worker",
          "👨‍🍳 Cook","🧹 Cleaner","💻 IT Specialist","👷 Craftsman","✏️ Other profession"],
}
EXPERIENCE = {"uz":["Tajribasiz","1–3 yil","3–5 yil","5–10 yil","10+ yil"],
               "ru":["Без опыта","1–3 года","3–5 лет","5–10 лет","10+ лет"],
               "en":["No experience","1–3 years","3–5 years","5–10 years","10+ years"]}
EDUCATION = {"uz":["🏫 Maktab","🏢 Kollej / Litsey","🎓 Bakalavr","🎓 Magistr","✏️ Boshqa"],
              "ru":["🏫 Школа","🏢 Колледж / Лицей","🎓 Бакалавр","🎓 Магистр","✏️ Другое"],
              "en":["🏫 School","🏢 College / Lyceum","🎓 Bachelor","🎓 Master","✏️ Other"]}

T = {
    "uz":{
        "welcome":"👋 Salom! <b>CV_MK V2.1</b> — 25 premium dizayn!\n\nHTML preview = PDF, bir xil sifat.\n\n🌍 Tilni tanlang:",
        "name":"👤 Ism va familiyangizni yozing:","name_short":"⚠️ Ism juda qisqa. Qaytadan yozing:",
        "job":"💼 Kasbingizni tanlang:","job_custom":"✏️ Kasbingizni yozing:",
        "phone":"📞 Telefon raqamingiz:","email":"📧 Email manzilingiz:",
        "address":"📍 Manzilingiz (shahar, mamlakat):","photo":"📸 Fotosuratingizni yuboring yoki o'tkazib yuboring:",
        "summary":"📝 O'zingiz haqida qisqacha (2–3 jumla):","experience":"🏢 Ish tajribangizni tanlang:",
        "education":"🎓 Ta'lim darajangizni tanlang:","edu_custom":"✏️ Ta'limingizni yozing:",
        "skills":"🛠 Ko'nikmalar (vergul bilan):\nMasalan: Kafel, Suvoq","langs":"🌐 Tillar (vergul bilan):\nMasalan: O'zbek, Rus",
        "certs":"📜 Sertifikatlar (ixtiyoriy, ⏭ o'tkazib yuborish):\nMasalan: ISO 9001",
        "preview_hdr":"🎨 <b>Dizayn tanlang</b> — 25 ta premium template!\n\n⬅️ ➡️ aylantiring, ✅ tanlang:",
        "creating":"⏳ CV yaratilmoqda...","pdf_ready":"✅ PDF tayyor! (A4, print-ready)",
        "html_ready":"🌐 HTML (brauzerda oching — PDF bilan bir xil ko'rinish):",
        "png_ready":"🖼 Preview:","done":"✅ CV tayyor!\n\n🔄 Yangi CV — /start",
        "cancelled":"❌ Bekor qilindi.\n\n/start — qayta boshlash","error":"❌ Xatolik. /start",
        "skip":"⏭️ O'tkazib yuborish","cancel":"❌ Bekor qilish","wrong":"⚠️ Tugmadan birini tanlang:",
        "select_btn":"✅ Shu dizaynni tanlash","help":"ℹ️ <b>CV_MK V2.1</b>\n\n/start — Yangi CV\n/cancel — Bekor\n/help — Yordam",
        "labels":{"summary":"O'zim haqimda","experience":"Ish tajribasi","education":"Ta'lim",
                  "skills":"Ko'nikmalar","languages":"Tillar","certs":"Sertifikatlar",
                  "phone":"Telefon","email":"Email","address":"Manzil","footer":"CV_MK V2.1"},
    },
    "ru":{
        "welcome":"👋 Привет! <b>CV_MK V2.1</b> — 25 премиум шаблонов!\n\nHTML = PDF, одинаковое качество.\n\n🌍 Выберите язык:",
        "name":"👤 Напишите имя и фамилию:","name_short":"⚠️ Имя слишком короткое. Напишите снова:",
        "job":"💼 Выберите профессию:","job_custom":"✏️ Напишите профессию:",
        "phone":"📞 Номер телефона:","email":"📧 Email:",
        "address":"📍 Адрес (город, страна):","photo":"📸 Отправьте фото или пропустите:",
        "summary":"📝 Кратко о себе (2–3 предложения):","experience":"🏢 Опыт работы:",
        "education":"🎓 Уровень образования:","edu_custom":"✏️ Напишите образование:",
        "skills":"🛠 Навыки (через запятую):\nНапример: Плитка, Штукатурка","langs":"🌐 Языки (через запятую):",
        "certs":"📜 Сертификаты (необязательно, ⏭ пропустить):",
        "preview_hdr":"🎨 <b>Выберите дизайн</b> — 25 премиум шаблонов!\n\n⬅️ ➡️ листайте, ✅ выбирайте:",
        "creating":"⏳ Создаём резюме...","pdf_ready":"✅ PDF готово! (A4, print-ready)",
        "html_ready":"🌐 HTML (открыть в браузере — тот же вид что PDF):",
        "png_ready":"🖼 Превью:","done":"✅ Резюме готово!\n\n🔄 Новое — /start",
        "cancelled":"❌ Отменено.\n\n/start — начать заново","error":"❌ Ошибка. /start",
        "skip":"⏭️ Пропустить","cancel":"❌ Отмена","wrong":"⚠️ Выберите один из вариантов:",
        "select_btn":"✅ Выбрать этот дизайн","help":"ℹ️ <b>CV_MK V2.1</b>\n\n/start — Новое CV\n/cancel — Отмена\n/help — Помощь",
        "labels":{"summary":"Обо мне","experience":"Опыт работы","education":"Образование",
                  "skills":"Навыки","languages":"Языки","certs":"Сертификаты",
                  "phone":"Телефон","email":"Email","address":"Адрес","footer":"CV_MK V2.1"},
    },
    "en":{
        "welcome":"👋 Hello! <b>CV_MK V2.1</b> — 25 premium designs!\n\nHTML = PDF, identical quality.\n\n🌍 Choose language:",
        "name":"👤 Enter your full name:","name_short":"⚠️ Name too short. Please write again:",
        "job":"💼 Choose your profession:","job_custom":"✏️ Write your profession:",
        "phone":"📞 Phone number:","email":"📧 Email:",
        "address":"📍 Address (city, country):","photo":"📸 Send a photo or skip:",
        "summary":"📝 Short professional summary (2–3 sentences):","experience":"🏢 Work experience:",
        "education":"🎓 Education level:","edu_custom":"✏️ Write your education:",
        "skills":"🛠 Skills (comma-separated):\nExample: Tiling, Plastering","langs":"🌐 Languages (comma-separated):",
        "certs":"📜 Certifications (optional, ⏭ skip):\nExample: ISO 9001",
        "preview_hdr":"🎨 <b>Choose your design</b> — 25 premium templates!\n\n⬅️ ➡️ browse, ✅ select:",
        "creating":"⏳ Creating your CV...","pdf_ready":"✅ PDF ready! (A4, print-ready)",
        "html_ready":"🌐 HTML (open in browser — same look as PDF):",
        "png_ready":"🖼 Preview:","done":"✅ CV ready!\n\n🔄 New CV — /start",
        "cancelled":"❌ Cancelled.\n\n/start — start over","error":"❌ Error. /start",
        "skip":"⏭️ Skip","cancel":"❌ Cancel","wrong":"⚠️ Please choose one of the options:",
        "select_btn":"✅ Select this design","help":"ℹ️ <b>CV_MK V2.1</b>\n\n/start — New CV\n/cancel — Cancel\n/help — Help",
        "labels":{"summary":"About Me","experience":"Work Experience","education":"Education",
                  "skills":"Skills","languages":"Languages","certs":"Certifications",
                  "phone":"Phone","email":"Email","address":"Address","footer":"CV_MK V2.1"},
    },
}

# ── Keyboards ─────────────────────────────────────────────────────────────────
def _kb(items, cols=2):
    rows = [items[i:i+cols] for i in range(0,len(items),cols)]
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=t) for t in r] for r in rows],
                               resize_keyboard=True, one_time_keyboard=True)

def kb_lang():         return _kb(LANG_BTNS,1)
def kb_jobs(l):        return _kb(JOBS[l],2)
def kb_exp(l):         return _kb(EXPERIENCE[l],1)
def kb_edu(l):         return _kb(EDUCATION[l],1)
def kb_cancel(l):      return _kb([T[l]["cancel"]],1)
def kb_skip_cancel(l): return _kb([T[l]["skip"],T[l]["cancel"]],2)

def kb_preview(idx:int, lang:str) -> InlineKeyboardMarkup:
    t = TEMPLATES[idx]; n = len(TEMPLATES)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️",callback_data=f"nav:{(idx-1)%n}"),
         InlineKeyboardButton(text=f"{t['emoji']} {idx+1}/{n}",callback_data="noop"),
         InlineKeyboardButton(text="➡️",callback_data=f"nav:{(idx+1)%n}")],
        [InlineKeyboardButton(text=T[lang]["select_btn"],callback_data=f"sel:{idx}")],
    ])

# ── Helpers ───────────────────────────────────────────────────────────────────
_EMOJI_RE = re.compile(r"[\U0001F000-\U0001FFFF\U00002600-\U000027FF\U0000FE00-\U0000FE0F]+",re.UNICODE)

def uid():            return uuid.uuid4().hex[:12]
def s(v):             return str(v or "").strip()
def e(v):             return _htm.escape(s(v))
def strip_emoji(x):   return _EMOJI_RE.sub("",x or "").strip(" –—-")
def is_cancel(t,l):   return any(w in (t or "").lower() for w in ["bekor","отмена","cancel","❌"]) or t==T[l]["cancel"]
def is_skip(t,l):     return any(w in (t or "").lower() for w in ["skip","пропустить","otkazib","⏭"]) or t==T[l]["skip"]

def cleanup(*paths):
    for p in paths:
        try: Path(p).unlink(missing_ok=True) if p else None
        except Exception: pass

# ── Circular photo processing ─────────────────────────────────────────────────
def _circular_photo_src(path: str, border_color: str) -> str:
    """Returns data URL of circular-cropped photo PNG with colored border ring."""
    try:
        p = Path(path)
        if not p.exists():
            return ""
        img = Image.open(p).convert("RGBA")
        # Square crop
        sz = min(img.size)
        img = img.crop(((img.width-sz)//2,(img.height-sz)//2,(img.width+sz)//2,(img.height+sz)//2))
        SIZE, BORDER = 300, 10
        img = img.resize((SIZE,SIZE), Image.LANCZOS)
        # Circular mask on photo
        mask = Image.new("L",(SIZE,SIZE),0)
        ImageDraw.Draw(mask).ellipse([0,0,SIZE-1,SIZE-1],fill=255)
        img.putalpha(mask)
        # Border ring canvas
        total = SIZE + BORDER*2
        canvas = Image.new("RGBA",(total,total),(0,0,0,0))
        bc = tuple(int(border_color.lstrip("#")[i:i+2],16) for i in (0,2,4))
        ImageDraw.Draw(canvas).ellipse([0,0,total-1,total-1],fill=(*bc,255))
        canvas.paste(img,(BORDER,BORDER),img)
        buf = io.BytesIO()
        canvas.save(buf,format="PNG")
        buf.seek(0)
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    except Exception as ex:
        log.warning("Photo circular error: %s", ex)
        return ""

def _photo_html(data:dict, t:dict, size_mm:int=28) -> str:
    src = _circular_photo_src(data.get("photo_path",""), t["ac"])
    if src:
        return f'<img src="{src}" style="width:{size_mm}mm;height:{size_mm}mm;display:block;margin:0 auto">'
    init = "".join(w[0].upper() for w in s(data.get("full_name","CV")).split()[:2]) or "CV"
    return (f'<div style="width:{size_mm}mm;height:{size_mm}mm;border-radius:50%;'
            f'background:{t["ac"]}22;border:0.6mm solid {t["ac"]};'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:14pt;font-weight:700;color:{t["ac"]};margin:0 auto">{init}</div>')

# ── Shared HTML helpers ────────────────────────────────────────────────────────
def _tags_html(val:str, ac:str) -> str:
    items = [x.strip() for x in re.split(r"[,\n]",s(val)) if x.strip()]
    return "".join(
        f'<span style="display:inline-block;background:{ac}22;color:{ac};'
        f'border:0.3mm solid {ac}44;padding:0.5mm 2mm;font-size:7.5pt;'
        f'margin:0.3mm;font-weight:600">{e(x)}</span>'
        for x in items
    )

def _certs_section(data:dict, lbl:dict, ac:str) -> str:
    c = s(data.get("certifications",""))
    if not c: return ""
    return (f'<div class="section">'
            f'<h2 style="font-size:7pt;letter-spacing:.12em;text-transform:uppercase;'
            f'color:{ac};font-weight:700;margin-bottom:1.5mm">📜 {lbl["certs"]}</h2>'
            f'<div>{_tags_html(c,ac)}</div></div>')

# Shared CSS reset + @page + viewer shell
def _page_css(t:dict) -> str:
    return f"""
@page {{size:210mm 297mm;margin:0}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact}}
body{{background:#D0D0D0;display:flex;justify-content:center;padding:16px;font-family:{t['fn']}}}
.page{{width:210mm;min-height:297mm;background:{t['bg']};overflow:hidden;position:relative}}
@media print{{body{{background:{t['bg']};padding:0;display:block}}
.page{{width:210mm;height:297mm;min-height:unset}}}}"""

def _section(title:str, body:str, t:dict, tags:bool=False) -> str:
    inner = _tags_html(body,t['ac']) if tags else f'<p style="font-size:9.5pt;line-height:1.65;color:{t["tx"]};opacity:.9;white-space:pre-line">{e(body)}</p>'
    return f"""<div class="section" style="margin-bottom:3.5mm">
<h2 style="font-size:7pt;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};
font-weight:700;margin-bottom:1.5mm;display:flex;align-items:center;gap:2mm">
{title}<span style="flex:1;height:0.2mm;background:{t['ac']}40;display:inline-block"></span></h2>
{inner}</div>"""

# ── HTML Layout renderers ─────────────────────────────────────────────────────

def _tpl_sidebar(data:dict, t:dict, lbl:dict, dark:bool) -> str:
    """dark_sidebar / light_sidebar — left 68mm sidebar, right 142mm main."""
    sb_tx = t['tx'] if dark else t['tx']
    photo = _photo_html(data, t, size_mm=26)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
{_page_css(t)}
.wrap{{display:flex;width:210mm;min-height:297mm}}
.sb{{width:68mm;min-height:297mm;background:{t['sb']};padding:8mm 5mm 8mm 5mm;
display:flex;flex-direction:column;gap:3.5mm;border-right:0.3mm solid {t['ac']}40}}
.sb-item h4{{font-size:6.5pt;letter-spacing:.12em;text-transform:uppercase;
color:{t['ac']};font-weight:700;margin-bottom:1mm}}
.sb-item .val{{font-size:8.5pt;color:{t['tx']};opacity:.82;line-height:1.45;word-break:break-all}}
.mn{{flex:1;padding:8mm 7mm 8mm 6mm;display:flex;flex-direction:column}}
.hdr{{border-bottom:0.4mm solid {t['ac']};padding-bottom:3mm;margin-bottom:3.5mm}}
.hdr h1{{font-size:19pt;font-weight:800;color:{t['tx']};line-height:1.1}}
.hdr .role{{font-size:10.5pt;color:{t['ac']};font-weight:600;margin-top:1.2mm}}
.foot{{margin-top:auto;padding-top:2.5mm;border-top:0.2mm solid {t['ac']}20;
font-size:6.5pt;color:{t['st']};text-align:center}}
</style></head><body><div class="page"><div class="wrap">
<aside class="sb">
  <div style="text-align:center;margin-bottom:1mm">{photo}</div>
  <div class="sb-item"><h4>📞 {lbl['phone']}</h4><div class="val">{e(data.get('phone','—'))}</div></div>
  <div class="sb-item"><h4>📧 {lbl['email']}</h4><div class="val">{e(data.get('email','—'))}</div></div>
  <div class="sb-item"><h4>📍 {lbl['address']}</h4><div class="val">{e(data.get('address','—'))}</div></div>
  <div class="sb-item"><h4>🌐 {lbl['languages']}</h4><div>{_tags_html(data.get('languages',''),t['ac'])}</div></div>
  <div class="sb-item"><h4>🛠 {lbl['skills']}</h4><div>{_tags_html(data.get('skills',''),t['ac'])}</div></div>
  {"<div class='sb-item'><h4>📜 "+lbl['certs']+"</h4><div class='val'>"+e(data.get('certifications',''))+"</div></div>" if data.get('certifications') else ""}
</aside>
<main class="mn">
  <div class="hdr"><h1>{e(data.get('full_name','—'))}</h1><div class="role">{e(data.get('job','—'))}</div></div>
  {_section(lbl['summary'],    data.get('summary','—'),    t)}
  {_section(lbl['experience'], data.get('experience','—'), t)}
  {_section(lbl['education'],  data.get('education','—'),  t)}
  {_certs_section(data, lbl, t['ac'])}
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</main>
</div></div></body></html>"""

def _tpl_banner(data:dict, t:dict, lbl:dict, dashed:bool=False) -> str:
    """banner_light / banner_dashed — full-width dark header, content below."""
    ac2 = t.get("ac2", t["ac"])
    photo = _photo_html(data, t, size_mm=24)
    accent_stripe = f'border-left:1mm solid {ac2};padding-left:3mm' if dashed else ''
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
{_page_css(t)}
.hdr{{background:{t['hd']};padding:7mm 8mm;display:flex;align-items:center;gap:6mm}}
.hdr-info h1{{font-size:18pt;font-weight:800;color:#fff;line-height:1.1}}
.hdr-info .role{{font-size:10pt;color:{ac2};font-weight:600;margin-top:1mm}}
.hdr-info .contact{{font-size:7.5pt;color:#ffffff88;margin-top:1.5mm;line-height:1.5}}
.stripe{{height:1mm;background:linear-gradient(90deg,{t['hd']},{ac2})}}
.body{{padding:5mm 8mm 5mm 8mm}}
.grid{{display:flex;gap:5mm}}
.col{{flex:1}}
.section{{margin-bottom:3.5mm}}
.section h2{{font-size:7pt;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};
font-weight:700;margin-bottom:1.5mm;{accent_stripe};display:flex;align-items:center;gap:2mm}}
.section h2 span{{flex:1;height:0.2mm;background:{t['ac']}40;display:inline-block}}
.section p{{font-size:9.5pt;line-height:1.65;color:{t['tx']};opacity:.9;white-space:pre-line}}
.foot{{margin-top:3mm;padding-top:2mm;border-top:0.2mm solid {t['ac']}20;
font-size:6.5pt;color:{t['st']};text-align:center}}
</style></head><body><div class="page">
<div class="hdr">
  {photo}
  <div class="hdr-info">
    <h1>{e(data.get('full_name','—'))}</h1>
    <div class="role">{e(data.get('job','—'))}</div>
    <div class="contact">{e(data.get('phone',''))} &nbsp;|&nbsp; {e(data.get('email',''))} &nbsp;|&nbsp; {e(data.get('address',''))}</div>
  </div>
</div>
<div class="stripe"></div>
<div class="body">
  <div class="section"><h2>{lbl['summary']}<span></span></h2>
    <p>{e(data.get('summary','—'))}</p></div>
  <div class="grid">
    <div class="col">
      <div class="section"><h2>{lbl['experience']}<span></span></h2><p>{e(data.get('experience','—'))}</p></div>
      <div class="section"><h2>{lbl['education']}<span></span></h2><p>{e(data.get('education','—'))}</p></div>
    </div>
    <div class="col">
      <div class="section"><h2>{lbl['skills']}<span></span></h2><div>{_tags_html(data.get('skills',''),t['ac'])}</div></div>
      <div class="section"><h2>{lbl['languages']}<span></span></h2><div>{_tags_html(data.get('languages',''),t['ac'])}</div></div>
      {"<div class='section'><h2>"+lbl['certs']+"<span></span></h2><div>"+_tags_html(data.get('certifications',''),t['ac'])+"</div></div>" if data.get('certifications') else ""}
    </div>
  </div>
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div>
</div></body></html>"""

def _tpl_dark_metrics(data:dict, t:dict, lbl:dict) -> str:
    """dark_metrics — dark header + metrics bar + two-column content."""
    photo = _photo_html(data, t, size_mm=22)
    exp = s(data.get('experience','—'))
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
{_page_css(t)}
.hdr{{background:{t['hd']};padding:6mm 8mm;display:flex;align-items:center;gap:6mm}}
.hdr h1{{font-size:18pt;font-weight:800;color:{t['tx']};line-height:1.1}}
.hdr .role{{font-size:10pt;color:{t['ac']};font-weight:600;margin-top:1mm}}
.metrics{{display:flex;background:{t['sb']};border-bottom:0.3mm solid {t['ac']}40}}
.metric{{flex:1;text-align:center;padding:3mm 2mm;border-right:0.2mm solid {t['ac']}20}}
.metric:last-child{{border-right:none}}
.metric .mv{{font-size:9pt;font-weight:800;color:{t['ac']}}}
.metric .ml{{font-size:6pt;text-transform:uppercase;letter-spacing:.08em;color:{t['st']};margin-top:0.5mm}}
.body{{padding:5mm 8mm}}
.grid{{display:flex;gap:5mm}}
.col{{flex:1}}
.section{{margin-bottom:3.5mm}}
.section h2{{font-size:7pt;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};
font-weight:700;margin-bottom:1.5mm;display:flex;align-items:center;gap:2mm}}
.section h2 span{{flex:1;height:0.2mm;background:{t['ac']}40;display:inline-block}}
.section p{{font-size:9.5pt;line-height:1.65;color:{t['tx']};opacity:.9;white-space:pre-line}}
.foot{{margin-top:3mm;padding-top:2mm;border-top:0.2mm solid {t['ac']}20;
font-size:6.5pt;color:{t['st']};text-align:center}}
</style></head><body><div class="page">
<div class="hdr">{photo}
  <div><h1>{e(data.get('full_name','—'))}</h1><div class="role">{e(data.get('job','—'))}</div></div>
</div>
<div class="metrics">
  <div class="metric"><div class="mv">{e(exp)}</div><div class="ml">{lbl['experience']}</div></div>
  <div class="metric"><div class="mv">{e(data.get('phone','—'))}</div><div class="ml">{lbl['phone']}</div></div>
  <div class="metric"><div class="mv">{e(data.get('address','—'))}</div><div class="ml">{lbl['address']}</div></div>
</div>
<div class="body">
  <div class="section"><h2>{lbl['summary']}<span></span></h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="grid">
    <div class="col">
      <div class="section"><h2>{lbl['education']}<span></span></h2><p>{e(data.get('education','—'))}</p></div>
      {"<div class='section'><h2>"+lbl['certs']+"<span></span></h2><div>"+_tags_html(data.get('certifications',''),t['ac'])+"</div></div>" if data.get('certifications') else ""}
    </div>
    <div class="col">
      <div class="section"><h2>{lbl['skills']}<span></span></h2><div>{_tags_html(data.get('skills',''),t['ac'])}</div></div>
      <div class="section"><h2>{lbl['languages']}<span></span></h2><div>{_tags_html(data.get('languages',''),t['ac'])}</div></div>
    </div>
  </div>
  <div class="section" style="margin-top:1mm"><h2>📧 {lbl['email']}<span></span></h2>
    <p style="font-size:9pt">{e(data.get('email','—'))}</p></div>
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div>
</div></body></html>"""

def _tpl_ats_clean(data:dict, t:dict, lbl:dict) -> str:
    """ats_clean — single column, ATS-friendly, no colors."""
    def sec(title, body, tags=False):
        inner = _tags_html(body,'#333') if tags else f'<p style="font-size:9.5pt;line-height:1.7;color:#333;white-space:pre-line">{e(body)}</p>'
        return f'<div style="margin-bottom:4mm"><h2 style="font-size:8pt;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#111;border-bottom:0.3mm solid #CCC;padding-bottom:1mm;margin-bottom:2mm">{title}</h2>{inner}</div>'

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
@page{{size:210mm 297mm;margin:0}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact}}
body{{background:#F0F0F0;display:flex;justify-content:center;padding:16px;font-family:Arial,sans-serif}}
.page{{width:210mm;min-height:297mm;background:#fff;padding:12mm 14mm;position:relative}}
@media print{{body{{background:#fff;padding:0;display:block}}.page{{width:210mm;height:297mm;padding:15mm 18mm}}}}
h1{{font-size:20pt;font-weight:700;text-align:center;color:#111;margin-bottom:1mm}}
.role{{font-size:11pt;text-align:center;color:#333;font-weight:600;margin-bottom:2mm}}
.contact{{text-align:center;font-size:8.5pt;color:#555;margin-bottom:4mm;line-height:1.7}}
.foot{{margin-top:5mm;padding-top:2mm;border-top:0.3mm solid #EEE;font-size:6.5pt;color:#999;text-align:center}}
</style></head><body><div class="page">
<h1>{e(data.get('full_name','—'))}</h1>
<div class="role">{e(data.get('job','—'))}</div>
<div class="contact">{e(data.get('phone',''))} &nbsp;|&nbsp; {e(data.get('email',''))} &nbsp;|&nbsp; {e(data.get('address',''))}</div>
{sec(lbl['summary'],    data.get('summary','—'))}
{sec(lbl['experience'], data.get('experience','—'))}
{sec(lbl['education'],  data.get('education','—'))}
{sec(lbl['skills'],     data.get('skills',''),     tags=True)}
{sec(lbl['languages'],  data.get('languages',''),  tags=True)}
{sec(lbl['certs'],      data.get('certifications','')) if data.get('certifications') else ''}
<div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div></body></html>"""

def _tpl_europass(data:dict, t:dict, lbl:dict) -> str:
    def row(label, val, tags=False):
        v = _tags_html(val,t['ac']) if tags else f'<span style="font-size:9.5pt;color:{t["tx"]}">{e(val)}</span>'
        return f'<tr><td style="padding:2.5mm 4mm 2.5mm 0;min-width:36mm;vertical-align:top;font-size:7pt;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:{t["ac"]};border-bottom:0.2mm solid {t["ac"]}18">{label}</td><td style="padding:2.5mm 0;border-bottom:0.2mm solid {t["ac"]}18">{v}</td></tr>'

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
{_page_css(t)}
.hdr{{background:{t['hd']};padding:6mm 8mm;display:flex;align-items:center;gap:6mm}}
.hdr h1{{font-size:18pt;font-weight:800;color:#fff;line-height:1.1}}
.hdr .role{{font-size:10pt;color:#ffffff99;font-weight:600;margin-top:1mm}}
.eu-badge{{background:#fff;color:{t['hd']};font-size:6.5pt;font-weight:700;letter-spacing:.12em;padding:1mm 2mm;margin-bottom:2mm;display:inline-block}}
.stripe{{height:0.8mm;background:{t['ac']}}}
.body{{padding:5mm 8mm}}
table{{width:100%;border-collapse:collapse}}
.foot{{margin-top:4mm;padding-top:2mm;border-top:0.2mm solid {t['ac']}20;font-size:6.5pt;color:{t['st']};text-align:center}}
</style></head><body><div class="page">
<div class="hdr">
  {_photo_html(data,t,22)}
  <div><div class="eu-badge">CURRICULUM VITAE</div>
    <h1>{e(data.get('full_name','—'))}</h1><div class="role">{e(data.get('job','—'))}</div></div>
</div>
<div class="stripe"></div>
<div class="body">
<table>
  {row(lbl['phone'],    data.get('phone','—'))}
  {row(lbl['email'],    data.get('email','—'))}
  {row(lbl['address'],  data.get('address','—'))}
  {row(lbl['summary'],  data.get('summary','—'))}
  {row(lbl['experience'],data.get('experience','—'))}
  {row(lbl['education'],data.get('education','—'))}
  {row(lbl['skills'],   data.get('skills',''),    tags=True)}
  {row(lbl['languages'],data.get('languages',''), tags=True)}
  {row(lbl['certs'],    data.get('certifications','')) if data.get('certifications') else ''}
</table>
<div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div></div></body></html>"""

def _tpl_tech_cards(data:dict, t:dict, lbl:dict) -> str:
    def card(title, body, tags=False):
        inner = _tags_html(body,t['ac']) if tags else f'<p style="font-size:9pt;line-height:1.65;color:{t["tx"]};opacity:.85;white-space:pre-line">{e(body)}</p>'
        return f'<div style="background:#fff;border-radius:2mm;padding:3.5mm 4mm;margin-bottom:3mm;border-left:0.6mm solid {t["ac"]}"><h3 style="font-size:7pt;letter-spacing:.1em;text-transform:uppercase;color:{t["ac"]};font-weight:700;margin-bottom:1.5mm">{title}</h3>{inner}</div>'

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
{_page_css(t)}
.hdr{{background:{t['hd']};padding:6.5mm 8mm;color:#fff}}
.hdr h1{{font-size:18pt;font-weight:800;margin-bottom:1mm;line-height:1.1}}
.hdr .role{{font-size:10pt;color:{t['ac']};font-weight:600;margin-bottom:1.5mm}}
.hdr .info{{font-size:7.5pt;color:#ffffff88;line-height:1.5}}
.body{{padding:5mm 8mm}}
.grid{{display:flex;gap:4mm}}
.col{{flex:1}}
.foot{{margin-top:2mm;padding-top:2mm;border-top:0.2mm solid {t['ac']}30;font-size:6.5pt;color:{t['st']};text-align:center}}
</style></head><body><div class="page">
<div class="hdr">
  <h1>{e(data.get('full_name','—'))}</h1>
  <div class="role">{e(data.get('job','—'))}</div>
  <div class="info">{e(data.get('phone',''))} &nbsp;·&nbsp; {e(data.get('email',''))} &nbsp;·&nbsp; {e(data.get('address',''))}</div>
</div>
<div class="body">
  {card(lbl['summary'],    data.get('summary','—'))}
  <div class="grid">
    <div class="col">{card(lbl['experience'],data.get('experience','—'))}{card(lbl['education'],data.get('education','—'))}</div>
    <div class="col">{card(lbl['skills'],data.get('skills',''),tags=True)}{card(lbl['languages'],data.get('languages',''),tags=True)}{"" if not data.get('certifications') else card(lbl['certs'],data.get('certifications',''),tags=True)}</div>
  </div>
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div>
</div></body></html>"""

def _tpl_centered(data:dict, t:dict, lbl:dict, dark:bool) -> str:
    """centered_dark / centered_light / warm_centered — centered photo+name at top."""
    hdr_bg = t['hd'] if not dark else t['bg']
    name_col = "#fff" if not dark else t['tx']
    photo = _photo_html(data, t, size_mm=28)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
{_page_css(t)}
.hdr{{background:{hdr_bg};text-align:center;padding:7mm 10mm 5mm}}
.hdr h1{{font-size:19pt;font-weight:800;color:{name_col};margin:2.5mm 0 1mm;line-height:1.1}}
.hdr .role{{font-size:10.5pt;color:{t['ac']};font-weight:600;margin-bottom:1.5mm}}
.hdr .contact{{font-size:7.5pt;color:{"#ffffff88" if not dark else t['st']};line-height:1.5}}
.divider{{height:0.8mm;background:linear-gradient(90deg,{t['bg']},{t['ac']},{t['bg']})}}
.body{{padding:5mm 8mm}}
.grid{{display:flex;gap:5mm}}
.col{{flex:1}}
.section{{margin-bottom:3.5mm}}
.section h2{{font-size:7pt;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};
font-weight:700;margin-bottom:1.5mm;display:flex;align-items:center;gap:2mm}}
.section h2 span{{flex:1;height:0.2mm;background:{t['ac']}40;display:inline-block}}
.section p{{font-size:9.5pt;line-height:1.65;color:{t['tx']};opacity:.9;white-space:pre-line}}
.foot{{margin-top:3mm;padding-top:2mm;border-top:0.2mm solid {t['ac']}20;font-size:6.5pt;color:{t['st']};text-align:center}}
</style></head><body><div class="page">
<div class="hdr">
  {photo}
  <h1>{e(data.get('full_name','—'))}</h1>
  <div class="role">{e(data.get('job','—'))}</div>
  <div class="contact">{e(data.get('phone',''))} &nbsp;|&nbsp; {e(data.get('email',''))} &nbsp;|&nbsp; {e(data.get('address',''))}</div>
</div>
<div class="divider"></div>
<div class="body">
  <div class="section"><h2>{lbl['summary']}<span></span></h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="grid">
    <div class="col">
      <div class="section"><h2>{lbl['experience']}<span></span></h2><p>{e(data.get('experience','—'))}</p></div>
      <div class="section"><h2>{lbl['education']}<span></span></h2><p>{e(data.get('education','—'))}</p></div>
    </div>
    <div class="col">
      <div class="section"><h2>{lbl['skills']}<span></span></h2><div>{_tags_html(data.get('skills',''),t['ac'])}</div></div>
      <div class="section"><h2>{lbl['languages']}<span></span></h2><div>{_tags_html(data.get('languages',''),t['ac'])}</div></div>
      {"<div class='section'><h2>"+lbl['certs']+"<span></span></h2><div>"+_tags_html(data.get('certifications',''),t['ac'])+"</div></div>" if data.get('certifications') else ""}
    </div>
  </div>
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div>
</div></body></html>"""

def _tpl_initials_side(data:dict, t:dict, lbl:dict) -> str:
    """initials_side — dark sidebar with big initial letter instead of photo."""
    init = "".join(w[0].upper() for w in s(data.get("full_name","CV")).split()[:2]) or "CV"
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
{_page_css(t)}
.page{{background:{t['bg']}}}
.wrap{{display:flex;width:210mm;min-height:297mm}}
.sb{{width:68mm;min-height:297mm;background:{t['sb']};padding:8mm 5mm;
display:flex;flex-direction:column;gap:3.5mm;border-right:0.5mm solid {t['ac']}}}
.initial{{width:28mm;height:28mm;border-radius:50%;background:{t['ac']}2A;
border:0.5mm solid {t['ac']};display:flex;align-items:center;justify-content:center;
font-size:16pt;font-weight:900;color:{t['ac']};margin:0 auto 2mm;font-family:Georgia,serif}}
.sb h4{{font-size:6.5pt;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};font-weight:700;margin-bottom:1mm}}
.sb .val{{font-size:8.5pt;color:#ffffff99;line-height:1.45;word-break:break-all}}
.mn{{flex:1;padding:8mm 7mm 8mm 6mm;display:flex;flex-direction:column;background:{t['bg']}}}
.hdr h1{{font-size:19pt;font-weight:800;color:{t['tx']};line-height:1.1}}
.hdr .role{{font-size:10.5pt;color:{t['ac']};font-weight:600;margin-top:1.2mm;margin-bottom:3mm}}
.hdr .line{{height:0.4mm;background:{t['ac']};margin-bottom:3mm}}
.section{{margin-bottom:3.5mm}}
.section h2{{font-size:7pt;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};
font-weight:700;margin-bottom:1.5mm;display:flex;align-items:center;gap:2mm}}
.section h2 span{{flex:1;height:0.2mm;background:{t['ac']}40;display:inline-block}}
.section p{{font-size:9.5pt;line-height:1.65;color:{t['tx']};opacity:.9;white-space:pre-line}}
.foot{{margin-top:auto;padding-top:2.5mm;border-top:0.2mm solid {t['ac']}20;font-size:6.5pt;color:{t['st']};text-align:center}}
</style></head><body><div class="page"><div class="wrap">
<aside class="sb">
  <div class="initial">{init}</div>
  <div><h4>💼 {lbl['experience']}</h4><div class="val">{e(data.get('experience','—'))}</div></div>
  <div><h4>📞 {lbl['phone']}</h4><div class="val">{e(data.get('phone','—'))}</div></div>
  <div><h4>📧 {lbl['email']}</h4><div class="val">{e(data.get('email','—'))}</div></div>
  <div><h4>📍 {lbl['address']}</h4><div class="val">{e(data.get('address','—'))}</div></div>
  <div><h4>🌐 {lbl['languages']}</h4><div>{_tags_html(data.get('languages',''),t['ac'])}</div></div>
  <div><h4>🛠 {lbl['skills']}</h4><div>{_tags_html(data.get('skills',''),t['ac'])}</div></div>
</aside>
<main class="mn">
  <div class="hdr">
    <h1>{e(data.get('full_name','—'))}</h1>
    <div class="role">{e(data.get('job','—'))}</div>
    <div class="line"></div>
  </div>
  <div class="section"><h2>{lbl['summary']}<span></span></h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="section"><h2>{lbl['education']}<span></span></h2><p>{e(data.get('education','—'))}</p></div>
  {_certs_section(data, lbl, t['ac'])}
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</main>
</div></div></body></html>"""

def _tpl_industrial(data:dict, t:dict, lbl:dict) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
{_page_css(t)}
.hdr{{background:{t['hd']};padding:6.5mm 8mm;position:relative;overflow:hidden}}
.hdr-tri{{position:absolute;right:0;top:0;width:0;height:0;
border-style:solid;border-width:0 35mm 22mm 0;border-color:transparent {t['ac']} transparent transparent;opacity:.8}}
.hdr h1{{font-size:19pt;font-weight:900;color:#fff;line-height:1.1}}
.hdr .role{{font-size:10.5pt;color:{t['ac']};font-weight:700;margin-top:1mm}}
.stripe{{height:1mm;background:{t['ac']}}}
.body{{padding:5mm 8mm}}
.contact-bar{{display:flex;gap:5mm;padding:2.5mm 3.5mm;background:{t['sb']};
border-left:1mm solid {t['ac']};margin-bottom:4mm}}
.contact-bar span{{font-size:8.5pt;color:{t['tx']};opacity:.85}}
.grid{{display:flex;gap:5mm}}
.col{{flex:1}}
.section{{margin-bottom:3.5mm}}
.section h2{{font-size:7pt;letter-spacing:.12em;text-transform:uppercase;color:{t['ac']};
font-weight:700;margin-bottom:1.5mm;display:flex;align-items:center;gap:2mm}}
.section h2 span{{flex:1;height:0.2mm;background:{t['ac']}40;display:inline-block}}
.section p{{font-size:9.5pt;line-height:1.65;color:{t['tx']};opacity:.9;white-space:pre-line}}
.foot{{margin-top:3mm;padding-top:2mm;border-top:0.2mm solid {t['ac']}30;font-size:6.5pt;color:{t['st']};text-align:center}}
</style></head><body><div class="page">
<div class="hdr">
  <div class="hdr-tri"></div>
  <h1>{e(data.get('full_name','—'))}</h1>
  <div class="role">{e(data.get('job','—'))}</div>
</div>
<div class="stripe"></div>
<div class="body">
  <div class="contact-bar">
    <span>📞 {e(data.get('phone','—'))}</span>
    <span>📧 {e(data.get('email','—'))}</span>
    <span>📍 {e(data.get('address','—'))}</span>
  </div>
  <div class="section"><h2>{lbl['summary']}<span></span></h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="grid">
    <div class="col">
      <div class="section"><h2>{lbl['experience']}<span></span></h2><p>{e(data.get('experience','—'))}</p></div>
      <div class="section"><h2>{lbl['education']}<span></span></h2><p>{e(data.get('education','—'))}</p></div>
    </div>
    <div class="col">
      <div class="section"><h2>{lbl['skills']}<span></span></h2><div>{_tags_html(data.get('skills',''),t['ac'])}</div></div>
      <div class="section"><h2>{lbl['languages']}<span></span></h2><div>{_tags_html(data.get('languages',''),t['ac'])}</div></div>
      {"<div class='section'><h2>"+lbl['certs']+"<span></span></h2><div>"+_tags_html(data.get('certifications',''),t['ac'])+"</div></div>" if data.get('certifications') else ""}
    </div>
  </div>
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div>
</div></body></html>"""

# ── Uzbek vocational layouts ──────────────────────────────────────────────────

def _tpl_uzbek_sidebar(data: dict, t: dict) -> str:
    lbl = UZ_VOC_LABELS
    init = "".join(w[0].upper() for w in s(data.get("full_name","CV")).split()[:2]) or "CV"
    skill_chips = "".join(
        f'<span style="display:inline-block;font-size:6.5pt;padding:0.5mm 1.5mm;margin:0.3mm;'
        f'background:rgba(255,255,255,.16);color:#fff;border-radius:1mm">{e(x.strip())}</span>'
        for x in re.split(r"[,\n]",s(data.get("skills",""))) if x.strip()
    )
    qual_rows = "".join(
        f'<div style="font-size:7.5pt;padding:0.4mm 0 0.4mm 3.5mm;position:relative;color:rgba(255,255,255,.9)">'
        f'<span style="position:absolute;left:0;color:#fff;font-size:7pt">✔</span>{e(x.strip())}</div>'
        for x in re.split(r"[,\n]",s(data.get("certifications",""))) if x.strip()
    )
    lang_rows = "".join(
        f'<div style="font-size:7.5pt;color:rgba(255,255,255,.88);line-height:1.4">{e(x.strip())}</div>'
        for x in re.split(r"[,\n]",s(data.get("languages",""))) if x.strip()
    )
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
@page{{size:210mm 297mm;margin:0}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact}}
body{{background:#D0D0D0;display:flex;justify-content:center;padding:16px;font-family:{t['fn']}}}
.page{{width:210mm;min-height:297mm;background:linear-gradient(to right,{t['sb']} 0,{t['sb']} 66mm,#fff 66mm,#fff 100%);overflow:hidden;position:relative}}
@media print{{body{{background:#D0D0D0;padding:0;display:block}}.page{{width:210mm;height:297mm;min-height:unset}}}}
.layout{{display:table;width:210mm;min-height:297mm}}
.col-side{{display:table-cell;width:66mm;vertical-align:top;padding:8mm 5mm;color:#fff}}
.col-main{{display:table-cell;vertical-align:top;padding:8mm 7mm 8mm 6mm;background:#fff}}
.avatar{{width:22mm;height:22mm;border-radius:50%;background:#fff;color:{t['ac']};font-size:10pt;font-weight:800;text-align:center;line-height:22mm;margin:0 auto 3mm;display:block}}
.s-name{{font-size:11pt;font-weight:800;text-align:center;line-height:1.2;margin-bottom:1mm}}
.s-title{{font-size:6.5pt;text-align:center;letter-spacing:.06em;text-transform:uppercase;color:rgba(255,255,255,.85);margin-bottom:3.5mm}}
.sb-sec h4{{font-size:6pt;letter-spacing:.1em;text-transform:uppercase;color:#fff;font-weight:700;border-bottom:0.2mm solid rgba(255,255,255,.25);padding-bottom:1mm;margin-bottom:1.5mm;margin-top:3mm}}
.sb-sec .val{{font-size:7.5pt;color:rgba(255,255,255,.88);line-height:1.4;word-break:break-word}}
.main-head h1{{font-size:16pt;font-weight:800;color:{t['tx']};line-height:1.1;margin-bottom:0.5mm}}
.main-head .m-title{{font-size:8pt;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:{t['ac']};margin-bottom:2mm}}
.main-head{{border-bottom:0.4mm solid {t['ac']};padding-bottom:2mm;margin-bottom:3mm}}
.sec{{margin-bottom:3mm}}
.sec h2{{font-size:7pt;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:{t['ac']};border-bottom:0.2mm solid {t['ac']}40;padding-bottom:1mm;margin-bottom:1.5mm}}
.sec p{{font-size:9pt;line-height:1.65;color:{t['tx']};opacity:.9;white-space:pre-line}}
.foot{{font-size:6pt;color:#aaa;text-align:center;margin-top:3mm;padding-top:1.5mm;border-top:0.2mm solid #eee}}
</style></head><body><div class="page"><div class="layout">
<div class="col-side">
  <div class="avatar">{init}</div>
  <div class="s-name">{e(data.get('full_name','—'))}</div>
  <div class="s-title">{e(data.get('job','—'))}</div>
  <div class="sb-sec"><h4>{lbl['contact']}</h4>
    <div class="val">{e(data.get('phone','—'))}</div>
    <div class="val">{e(data.get('address','—'))}</div>
  </div>
  <div class="sb-sec"><h4>{lbl['skills']}</h4><div>{skill_chips}</div></div>
  {'<div class="sb-sec"><h4>'+lbl['qualities']+'</h4>'+qual_rows+'</div>' if data.get('certifications') else ''}
  <div class="sb-sec"><h4>{lbl['languages']}</h4><div>{lang_rows}</div></div>
</div>
<div class="col-main">
  <div class="main-head"><h1>{e(data.get('full_name','—'))}</h1><div class="m-title">{e(data.get('job','—'))}</div></div>
  <div class="sec"><h2>{lbl['summary']}</h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="sec"><h2>{lbl['experience']}</h2><p>{e(data.get('experience','—'))}</p></div>
  <div class="sec"><h2>{lbl['education']}</h2><p>{e(data.get('education','—'))}</p></div>
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div>
</div></div></body></html>"""


def _tpl_uzbek_banner(data: dict, t: dict) -> str:
    lbl = UZ_VOC_LABELS
    init = "".join(w[0].upper() for w in s(data.get("full_name","CV")).split()[:2]) or "CV"
    skill_chips = "".join(
        f'<span style="display:inline-block;font-size:8pt;padding:1mm 2.5mm;margin:0.5mm;'
        f'background:{t["ac"]}22;color:{t["ac"]};border-radius:1.5mm;font-weight:600">{e(x.strip())}</span>'
        for x in re.split(r"[,\n]",s(data.get("skills",""))) if x.strip()
    )
    qual_rows = "".join(
        f'<div style="font-size:8.5pt;padding:0.8mm 0 0.8mm 4mm;position:relative;color:{t["tx"]};opacity:.9">'
        f'<span style="position:absolute;left:0;color:{t["ac"]}">✔</span>{e(x.strip())}</div>'
        for x in re.split(r"[,\n]",s(data.get("certifications",""))) if x.strip()
    )
    lang_rows = "".join(
        f'<p style="font-size:9pt;color:{t["tx"]};opacity:.85">{e(x.strip())}</p>'
        for x in re.split(r"[,\n]",s(data.get("languages",""))) if x.strip()
    )
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{e(data.get('full_name',''))} — CV</title><style>
@page{{size:210mm 297mm;margin:0}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact}}
body{{background:#D0D0D0;display:flex;justify-content:center;padding:16px;font-family:{t['fn']}}}
.page{{width:210mm;min-height:297mm;background:#fff;overflow:hidden;position:relative}}
@media print{{body{{background:#D0D0D0;padding:0;display:block}}.page{{width:210mm;height:297mm;min-height:unset}}}}
.band{{background:{t['hd']};color:#fff;padding:7mm 9mm;display:flex;align-items:center;gap:5mm}}
.avatar{{width:22mm;height:22mm;border-radius:50%;background:#fff;color:{t['ac']};font-size:10pt;font-weight:800;text-align:center;line-height:22mm;flex-shrink:0}}
.band-txt h1{{font-size:17pt;font-weight:800;color:#fff;line-height:1.1}}
.band-txt .b-title{{font-size:8.5pt;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:rgba(255,255,255,.9);margin-top:1mm}}
.band-txt .b-contact{{font-size:7.5pt;color:rgba(255,255,255,.8);margin-top:1.5mm;line-height:1.5}}
.body{{padding:5mm 9mm}}
.sec{{margin-bottom:3mm}}
.sec h2{{font-size:7pt;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:{t['ac']};border-bottom:0.2mm solid {t['ac']}40;padding-bottom:1mm;margin-bottom:1.5mm}}
.sec p{{font-size:9pt;line-height:1.65;color:{t['tx']};opacity:.9;white-space:pre-line}}
.two{{display:flex;gap:5mm}}
.col{{flex:1}}
.foot{{font-size:6pt;color:#aaa;text-align:center;margin-top:3mm;padding-top:1.5mm;border-top:0.2mm solid #eee}}
</style></head><body><div class="page">
<div class="band">
  <div class="avatar">{init}</div>
  <div class="band-txt">
    <h1>{e(data.get('full_name','—'))}</h1>
    <div class="b-title">{e(data.get('job','—'))}</div>
    <div class="b-contact">{e(data.get('phone',''))} &nbsp;·&nbsp; {e(data.get('address',''))}</div>
  </div>
</div>
<div class="body">
  <div class="sec"><h2>{lbl['summary']}</h2><p>{e(data.get('summary','—'))}</p></div>
  <div class="sec"><h2>{lbl['experience']}</h2><p>{e(data.get('experience','—'))}</p></div>
  <div class="two">
    <div class="col"><div class="sec"><h2>{lbl['skills']}</h2><div>{skill_chips}</div></div></div>
    <div class="col">{'<div class="sec"><h2>'+lbl['qualities']+'</h2>'+qual_rows+'</div>' if data.get('certifications') else ''}</div>
  </div>
  <div class="two">
    <div class="col"><div class="sec"><h2>{lbl['education']}</h2><p>{e(data.get('education','—'))}</p></div></div>
    <div class="col"><div class="sec"><h2>{lbl['languages']}</h2>{lang_rows}</div></div>
  </div>
  <div class="foot">{lbl['footer']} • {datetime.now().strftime('%d.%m.%Y')}</div>
</div>
</div></body></html>"""


# ── HTML dispatch ──────────────────────────────────────────────────────────────
def generate_html(data:dict, fid:str, tpl_id:str) -> Path:
    t    = TPL_BY_ID.get(tpl_id, TEMPLATES[0])
    lang = data.get("lang","uz")
    lbl  = T[lang]["labels"]
    layout = t.get("layout","dark_sidebar")

    if layout in ("dark_sidebar","light_sidebar"):
        html = _tpl_sidebar(data, t, lbl, dark=(layout=="dark_sidebar"))
    elif layout in ("banner_light","banner_dashed"):
        html = _tpl_banner(data, t, lbl, dashed=(layout=="banner_dashed"))
    elif layout in ("dark_banner","dark_metrics"):
        html = _tpl_dark_metrics(data, t, lbl)
    elif layout == "ats_clean":
        html = _tpl_ats_clean(data, t, lbl)
    elif layout == "europass":
        html = _tpl_europass(data, t, lbl)
    elif layout == "tech_cards":
        html = _tpl_tech_cards(data, t, lbl)
    elif layout in ("centered_dark","centered_light","warm_centered"):
        html = _tpl_centered(data, t, lbl, dark=(layout=="centered_dark"))
    elif layout == "initials_side":
        html = _tpl_initials_side(data, t, lbl)
    elif layout == "industrial":
        html = _tpl_industrial(data, t, lbl)
    elif layout == "uzbek_sidebar":
        html = _tpl_uzbek_sidebar(data, t)
    elif layout == "uzbek_banner":
        html = _tpl_uzbek_banner(data, t)
    else:
        html = _tpl_sidebar(data, t, lbl, dark=True)

    out = OUT_DIR / f"cv_{fid}.html"
    out.write_text(html, encoding="utf-8")
    return out

# ── PDF via WeasyPrint ────────────────────────────────────────────────────────
def generate_pdf(data:dict, fid:str, tpl_id:str) -> Path:
    if not HAS_WP:
        raise RuntimeError("WeasyPrint not installed")
    html_tmp = generate_html(data, f"{fid}_tmp", tpl_id)
    out = OUT_DIR / f"cv_{fid}.pdf"
    WP_HTML(filename=str(html_tmp)).write_pdf(str(out))
    html_tmp.unlink(missing_ok=True)
    return out

# ── Pillow preview (carousel thumbnails) ──────────────────────────────────────
def _h2r(h):
    h=h.lstrip("#")
    if len(h)==3: h="".join(c*2 for c in h)
    return (int(h[0:2],16),int(h[2:4],16),int(h[4:6],16))

def _mix(c1,c2,t):
    return tuple(max(0,min(255,int(a+(b-a)*t))) for a,b in zip(c1,c2))

def make_preview(tpl:dict, idx:int) -> bytes:
    W,H = 400,566
    bg=_h2r(tpl["bg"]); sb=_h2r(tpl["sb"]); hd=_h2r(tpl["hd"])
    ac=_h2r(tpl["ac"]); tx=_h2r(tpl["tx"])
    layout=tpl.get("layout","dark_sidebar")
    img=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(img)

    def tlines(x0,ys,ws,title_col=None):
        for i,(y,w) in enumerate(zip(ys,ws)):
            col=title_col if(title_col and i==0) else(_mix(bg,tx,0.75) if i==0 else _mix(bg,tx,0.4))
            d.rectangle([x0,y,x0+w,y+(7 if i==0 else 4)],fill=col)

    def stitle(x,y,w=55):
        d.rectangle([x,y,x+w,y+4],fill=ac)
        d.line([x+w+5,y+2,W-12,y+2],fill=_mix(bg,ac,0.25),width=1)

    if layout in ("dark_sidebar","light_sidebar"):
        sw=108; d.rectangle([0,0,sw,H],fill=sb); d.line([sw,0,sw,H],fill=ac,width=1)
        cx,cy,r=sw//2,68,30; d.ellipse([cx-r,cy-r,cx+r,cy+r],outline=ac,width=2,fill=_mix(sb,ac,0.1))
        for i,y0 in enumerate(range(112,H-50,44)):
            d.rectangle([10,y0,sw-10,y0+4],fill=_mix(sb,ac,0.7))
            d.rectangle([10,y0+10,sw-16,y0+14],fill=_mix(sb,tx,0.3))
            d.rectangle([10,y0+20,sw-22,y0+24],fill=_mix(sb,tx,0.2))
        d.line([sw+14,52,W-14,52],fill=ac,width=2)
        tlines(sw+14,[58,70],[160,90],title_col=_mix(bg,tx,0.9))
        stitle(sw+14,92); tlines(sw+14,[100,110,120],[140,110,90])
        stitle(sw+14,140); tlines(sw+14,[148,158,168],[130,100,80])
        stitle(sw+14,188); tlines(sw+14,[196,206],[120,90])
    elif layout in ("banner_light","banner_dashed","europass"):
        d.rectangle([0,0,W,86],fill=hd)
        d.ellipse([14,12,74,72],fill=_mix(hd,(255,255,255),0.1),outline=_mix(hd,(255,255,255),0.4),width=2)
        d.rectangle([84,22,260,33],fill=_mix(hd,(255,255,255),0.9))
        d.rectangle([84,40,200,49],fill=_mix(hd,(255,255,255),0.5))
        d.rectangle([0,86,W,90],fill=tpl.get("ac2",None) and _h2r(tpl["ac2"]) or ac)
        x0=14
        stitle(x0,104); tlines(x0,[113,123,133],[180,140,110])
        stitle(x0,153); tlines(x0,[162,172,182],[200,160,130])
        stitle(x0,202); tlines(x0,[211,221],[170,130])
    elif layout in ("dark_banner","dark_metrics"):
        d.rectangle([0,0,W,76],fill=hd); mb=_mix(hd,ac,0.2); d.rectangle([0,76,W,106],fill=mb)
        for mx in(16,140,264): d.rectangle([mx,83,mx+100,96],fill=_mix(mb,ac,0.4))
        d.line([0,106,W,106],fill=ac,width=1)
        x0=14; stitle(x0,118); tlines(x0,[127,137,147],[180,140,110])
        stitle(x0,167); tlines(x0,[176,186,196],[200,160,130])
        stitle(x0,216); tlines(x0,[225,235],[170,130])
    elif layout=="ats_clean":
        d.rectangle([0,0,W,3],fill=ac); d.rectangle([80,22,320,33],fill=_mix(bg,tx,0.85))
        d.rectangle([120,40,280,49],fill=_mix(bg,ac,0.6)); d.rectangle([30,57,370,61],fill=_mix(bg,tx,0.25))
        d.line([20,70,W-20,70],fill=_mix(bg,tx,0.15),width=1)
        x0=20; stitle(x0,83,80); tlines(x0,[95,105,115],[280,240,200])
        stitle(x0,133,80); tlines(x0,[145,155,165],[260,220,180])
    elif layout=="tech_cards":
        d.rectangle([0,0,W,54],fill=hd)
        for cy0 in(72,162,252,342):
            if cy0+75>H-20: break
            d.rectangle([14,cy0,W-14,cy0+72],fill=_mix(bg,(255,255,255),0.6),outline=_mix(bg,ac,0.3),width=1)
            d.rectangle([24,cy0+10,180,cy0+19],fill=_mix(bg,tx,0.7))
            d.rectangle([24,cy0+26,230,cy0+31],fill=_mix(bg,tx,0.35))
    elif layout in("centered_dark","centered_light","warm_centered"):
        if layout!="centered_dark": d.rectangle([0,0,W,112],fill=hd)
        cx=W//2; r=40; d.ellipse([cx-r,16,cx+r,96],fill=_mix(hd if layout!="centered_dark" else bg,ac,0.08),outline=ac,width=3)
        d.rectangle([cx-120,106,cx+120,116],fill=_mix(bg,tx,0.8))
        d.rectangle([cx-80,120,cx+80,129],fill=_mix(bg,ac,0.5))
        d.line([30,136,W-30,136],fill=_mix(bg,ac,0.3),width=1)
        stitle(W//2-55,150,55); tlines(W//2-100,[162,172],[200,160])
        stitle(W//2-55,192,55); tlines(W//2-100,[204,214],[180,140])
    elif layout=="initials_side":
        sw=108; d.rectangle([0,0,sw,H],fill=sb); d.line([sw,0,sw,H],fill=ac,width=2)
        cx,cy=sw//2,65; r=36; d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=_mix(sb,ac,0.2),outline=ac,width=2)
        for i,y0 in enumerate(range(118,H-40,42)):
            d.rectangle([10,y0,sw-10,y0+4],fill=_mix(sb,ac,0.6))
            d.rectangle([10,y0+10,sw-20,y0+14],fill=_mix(sb,tx,0.25))
        d.line([sw+14,52,W-14,52],fill=ac,width=2)
        tlines(sw+14,[58,70],[150,80],title_col=_mix(bg,tx,0.9))
        stitle(sw+14,92); tlines(sw+14,[101,111,121],[140,110,85])
        stitle(sw+14,141); tlines(sw+14,[150,160],[125,95])
    elif layout=="industrial":
        d.rectangle([0,0,W,80],fill=hd); d.polygon([(W-90,0),(W,0),(W,80),(W-130,80)],fill=_mix(hd,ac,0.5))
        d.rectangle([0,80,W,84],fill=ac); x0=14
        stitle(x0,96); tlines(x0,[106,116,126],[190,150,120])
        stitle(x0,148); tlines(x0,[158,168,178],[200,160,130])
    elif layout=="uzbek_sidebar":
        sw=108; d.rectangle([0,0,sw,H],fill=sb); d.line([sw,0,sw,H],fill=ac,width=1)
        cx,cy,r=sw//2,68,30; d.ellipse([cx-r,cy-r,cx+r,cy+r],outline=ac,width=2,fill=_mix(sb,ac,0.1))
        for i,y0 in enumerate(range(112,H-50,44)):
            d.rectangle([10,y0,sw-10,y0+4],fill=_mix(sb,ac,0.7))
            d.rectangle([10,y0+10,sw-16,y0+14],fill=_mix(sb,tx,0.3))
            d.rectangle([10,y0+20,sw-22,y0+24],fill=_mix(sb,tx,0.2))
        d.line([sw+14,52,W-14,52],fill=ac,width=2)
        tlines(sw+14,[58,70],[160,90],title_col=_mix(bg,tx,0.9))
        stitle(sw+14,92); tlines(sw+14,[100,110,120],[140,110,90])
        stitle(sw+14,140); tlines(sw+14,[148,158,168],[130,100,80])
        stitle(sw+14,188); tlines(sw+14,[196,206],[120,90])
    elif layout=="uzbek_banner":
        d.rectangle([0,0,W,86],fill=hd)
        d.ellipse([14,12,74,72],fill=_mix(hd,(255,255,255),0.1),outline=_mix(hd,(255,255,255),0.4),width=2)
        d.rectangle([84,22,260,33],fill=_mix(hd,(255,255,255),0.9))
        d.rectangle([84,40,200,49],fill=_mix(hd,(255,255,255),0.5))
        d.rectangle([0,86,W,90],fill=ac)
        x0=14
        stitle(x0,104); tlines(x0,[113,123,133],[180,140,110])
        stitle(x0,153); tlines(x0,[162,172,182],[200,160,130])
        stitle(x0,202); tlines(x0,[211,221],[170,130])
    else:
        d.rectangle([0,0,W,65],fill=hd); d.rectangle([0,65,W,69],fill=ac)
        stitle(14,82); tlines(14,[92,102,112],[190,150,120])

    d.rectangle([0,H-34,W,H],fill=(0,0,0)); d.rectangle([6,H-27,42,H-9],fill=ac)
    d.ellipse([W-18,6,W-6,18],fill=ac)
    buf=io.BytesIO(); img.save(buf,format="JPEG",quality=90); buf.seek(0)
    return buf.getvalue()

# ── Commands ──────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(msg:Message,state:FSMContext):
    await state.clear(); await state.set_state(CV.lang)
    await msg.answer(T["uz"]["welcome"],reply_markup=kb_lang(),parse_mode="HTML")

@dp.message(Command("cancel"))
async def cmd_cancel(msg:Message,state:FSMContext):
    data=await state.get_data(); lang=data.get("lang","uz")
    await state.clear(); await state.set_state(CV.lang)
    await msg.answer(T[lang]["cancelled"],reply_markup=kb_lang())

@dp.message(Command("help"))
async def cmd_help(msg:Message,state:FSMContext):
    data=await state.get_data()
    await msg.answer(T[data.get("lang","uz")]["help"],parse_mode="HTML")

# ── FSM helpers ───────────────────────────────────────────────────────────────
async def _cancel(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    await state.clear(); await state.set_state(CV.lang)
    await msg.answer(T[lang]["cancelled"],reply_markup=kb_lang())

# ── FSM handlers ──────────────────────────────────────────────────────────────
@dp.message(StateFilter(CV.lang),F.text.in_(LANG_BTNS))
async def h_lang(msg,state):
    lang=LANG_MAP[msg.text]; await state.update_data(lang=lang)
    await state.set_state(CV.full_name); await msg.answer(T[lang]["name"],reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.full_name),F.text)
async def h_name(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    if len(msg.text.strip())<3: return await msg.answer(T[lang]["name_short"],reply_markup=kb_cancel(lang))
    await state.update_data(full_name=msg.text.strip()); await state.set_state(CV.job)
    await msg.answer(T[lang]["job"],reply_markup=kb_jobs(lang))

@dp.message(StateFilter(CV.job),F.text)
async def h_job(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    if msg.text not in JOBS[lang]: return await msg.answer(T[lang]["wrong"],reply_markup=kb_jobs(lang))
    if any(w in msg.text.lower() for w in ["boshqa","другая","other","✏"]):
        await state.set_state(CV.job_custom); return await msg.answer(T[lang]["job_custom"],reply_markup=kb_cancel(lang))
    await state.update_data(job=strip_emoji(msg.text)); await state.set_state(CV.phone)
    await msg.answer(T[lang]["phone"],reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.job_custom),F.text)
async def h_job_custom(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    await state.update_data(job=msg.text.strip()); await state.set_state(CV.phone)
    await msg.answer(T[lang]["phone"],reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.phone),F.text)
async def h_phone(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    await state.update_data(phone=msg.text.strip()); await state.set_state(CV.email)
    await msg.answer(T[lang]["email"],reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.email),F.text)
async def h_email(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    await state.update_data(email=msg.text.strip()); await state.set_state(CV.address)
    await msg.answer(T[lang]["address"],reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.address),F.text)
async def h_address(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    await state.update_data(address=msg.text.strip()); await state.set_state(CV.photo)
    await msg.answer(T[lang]["photo"],reply_markup=kb_skip_cancel(lang))

@dp.message(StateFilter(CV.photo),F.photo)
async def h_photo(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    try:
        file=await bot.get_file(msg.photo[-1].file_id)
        path=OUT_DIR/f"p_{uid()}.jpg"
        await bot.download_file(file.file_path,destination=path)
        await state.update_data(photo_path=str(path))
    except Exception as ex:
        log.warning("Photo download error: %s",ex); await state.update_data(photo_path="")
    await state.set_state(CV.summary)
    await msg.answer(T[lang]["summary"],reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.photo),F.text)
async def h_photo_text(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    if is_skip(msg.text,lang):
        await state.update_data(photo_path=""); await state.set_state(CV.summary)
        return await msg.answer(T[lang]["summary"],reply_markup=kb_cancel(lang))
    await msg.answer(T[lang]["photo"],reply_markup=kb_skip_cancel(lang))

@dp.message(StateFilter(CV.summary),F.text)
async def h_summary(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    await state.update_data(summary=msg.text.strip()); await state.set_state(CV.experience)
    await msg.answer(T[lang]["experience"],reply_markup=kb_exp(lang))

@dp.message(StateFilter(CV.experience),F.text)
async def h_experience(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    if msg.text not in EXPERIENCE[lang]: return await msg.answer(T[lang]["wrong"],reply_markup=kb_exp(lang))
    await state.update_data(experience=msg.text); await state.set_state(CV.education)
    await msg.answer(T[lang]["education"],reply_markup=kb_edu(lang))

@dp.message(StateFilter(CV.education),F.text)
async def h_education(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    if msg.text not in EDUCATION[lang]: return await msg.answer(T[lang]["wrong"],reply_markup=kb_edu(lang))
    if any(w in msg.text.lower() for w in ["boshqa","другое","other","✏"]):
        await state.set_state(CV.education_custom); return await msg.answer(T[lang]["edu_custom"],reply_markup=kb_cancel(lang))
    await state.update_data(education=strip_emoji(msg.text)); await state.set_state(CV.skills)
    await msg.answer(T[lang]["skills"],reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.education_custom),F.text)
async def h_edu_custom(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    await state.update_data(education=msg.text.strip()); await state.set_state(CV.skills)
    await msg.answer(T[lang]["skills"],reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.skills),F.text)
async def h_skills(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    await state.update_data(skills=msg.text.strip()); await state.set_state(CV.languages)
    await msg.answer(T[lang]["langs"],reply_markup=kb_cancel(lang))

@dp.message(StateFilter(CV.languages),F.text)
async def h_languages(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    await state.update_data(languages=msg.text.strip()); await state.set_state(CV.certifications)
    await msg.answer(T[lang]["certs"],reply_markup=kb_skip_cancel(lang))

@dp.message(StateFilter(CV.certifications),F.text)
async def h_certs(msg,state):
    data=await state.get_data(); lang=data.get("lang","uz")
    if is_cancel(msg.text,lang): return await _cancel(msg,state)
    if not is_skip(msg.text,lang): await state.update_data(certifications=msg.text.strip())
    await _start_preview(msg,state)

async def _start_preview(msg:Message,state:FSMContext):
    data=await state.get_data(); lang=data.get("lang","uz")
    await state.set_state(CV.preview); await state.update_data(template_idx=0)
    await msg.answer(T[lang]["preview_hdr"],parse_mode="HTML",reply_markup=ReplyKeyboardRemove())
    tpl=TEMPLATES[0]
    img=make_preview(tpl,0)
    caption=f"{tpl['emoji']} <b>{tpl['name']}</b>  (1/{len(TEMPLATES)})"
    await msg.answer_photo(photo=BufferedInputFile(img,"preview.jpg"),caption=caption,
                           parse_mode="HTML",reply_markup=kb_preview(0,lang))

# ── Callbacks ─────────────────────────────────────────────────────────────────
@dp.callback_query(StateFilter(CV.preview),F.data=="noop")
async def cb_noop(cb:CallbackQuery): await cb.answer()

@dp.callback_query(StateFilter(CV.preview),F.data.startswith("nav:"))
async def cb_nav(cb:CallbackQuery,state:FSMContext):
    idx=int(cb.data.split(":")[1]); data=await state.get_data(); lang=data.get("lang","uz")
    await state.update_data(template_idx=idx); tpl=TEMPLATES[idx]
    img=make_preview(tpl,idx)
    caption=f"{tpl['emoji']} <b>{tpl['name']}</b>  ({idx+1}/{len(TEMPLATES)})"
    try:
        await cb.message.edit_media(
            media=InputMediaPhoto(media=BufferedInputFile(img,"preview.jpg"),caption=caption,parse_mode="HTML"),
            reply_markup=kb_preview(idx,lang))
    except Exception as ex: log.warning("edit_media: %s",ex)
    await cb.answer()

@dp.callback_query(StateFilter(CV.preview),F.data.startswith("sel:"))
async def cb_select(cb:CallbackQuery,state:FSMContext):
    idx=int(cb.data.split(":")[1]); data=await state.get_data()
    lang=data.get("lang","uz"); tpl=TEMPLATES[idx]
    await cb.answer(f"✅ {tpl['name']}")
    try: await cb.message.edit_reply_markup(reply_markup=None)
    except Exception: pass
    wait=await cb.message.answer(T[lang]["creating"])
    fid=uid(); html_path=pdf_path=None
    try:
        html_path=generate_html(data,fid,tpl["id"])
        pdf_path=generate_pdf(data,fid,tpl["id"])
        png_bytes=make_preview(tpl,idx)
        await cb.message.answer_document(FSInputFile(pdf_path), caption=T[lang]["pdf_ready"])
        await cb.message.answer_document(FSInputFile(html_path),caption=T[lang]["html_ready"])
        await cb.message.answer_photo(photo=BufferedInputFile(png_bytes,"cv_preview.jpg"),caption=T[lang]["png_ready"])
        await cb.message.answer(T[lang]["done"],reply_markup=kb_lang(),parse_mode="HTML")
    except Exception as ex:
        log.exception("Generate error: %s",ex)
        await cb.message.answer(T[lang]["error"],reply_markup=kb_lang())
    finally:
        try: await wait.delete()
        except Exception: pass
        cleanup(html_path,pdf_path,data.get("photo_path",""))
        await state.clear(); await state.set_state(CV.lang)

@dp.message()
async def catch_all(msg:Message,state:FSMContext):
    data=await state.get_data(); lang=data.get("lang","uz"); cur=await state.get_state()
    if not cur or cur==CV.lang.state:
        await state.clear(); await state.set_state(CV.lang)
        await msg.answer(T["uz"]["welcome"],reply_markup=kb_lang(),parse_mode="HTML")
    elif cur==CV.photo.state:
        await msg.answer(T[lang]["photo"],reply_markup=kb_skip_cancel(lang))
    else:
        await msg.answer(T[lang]["wrong"])

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    log.info("CV_MK V2.1 — HTML-first engine")
    log.info("WeasyPrint: %s", "✅" if HAS_WP else "❌ not installed")
    try:
        me=await bot.get_me(); log.info("Bot: @%s",me.username)
    except Exception as ex:
        log.critical("BOT_TOKEN error: %s",ex); raise

    if RENDER_URL:
        from aiohttp import web as aio_web
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler,setup_application
        webhook_url=f"{RENDER_URL}{WH_PATH}"
        await bot.set_webhook(webhook_url,drop_pending_updates=True)
        log.info("Webhook: %s",webhook_url)
        app=aio_web.Application()
        SimpleRequestHandler(dispatcher=dp,bot=bot).register(app,path=WH_PATH)
        setup_application(app,dp,bot=bot)
        async def health(_): return aio_web.Response(text="OK")
        app.router.add_get("/",health); app.router.add_get("/health",health)
        runner=aio_web.AppRunner(app); await runner.setup()
        port=int(os.getenv("PORT",10000))
        await aio_web.TCPSite(runner,"0.0.0.0",port).start()
        log.info("Server port=%s",port); await asyncio.Event().wait()
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("Polling (local dev)...")
        await dp.start_polling(bot,allowed_updates=["message","callback_query"])

if __name__=="__main__":
    asyncio.run(main())
