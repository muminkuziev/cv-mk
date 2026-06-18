import os, asyncio, threading, textwrap, html
from datetime import datetime
from pathlib import Path

from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Render Environment Variables ga BOT_TOKEN qo‘ying.")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

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


class CV(StatesGroup):
    lang = State()
    design = State()
    full_name = State()
    job = State()
    phone = State()
    email = State()
    address = State()
    photo = State()
    summary = State()
    experience = State()
    education = State()
    skills = State()
    languages = State()


LANGS = {
    "🇺🇿 O‘zbek": "uz",
    "🇺🇿 O'zbek": "uz",
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en",
}

TXT = {
    "uz": {
        "start": "✅ CV_MK ishga tushdi.\n\n🌍 Tilni tanlang:",
        "design": "🎨 CV dizaynini tanlang:",
        "name": "👤 Ism familiyangizni yozing:",
        "job": "💼 Kasbingiz / lavozimingiz:",
        "phone": "📞 Telefon raqamingiz:",
        "email": "📧 Email:",
        "address": "📍 Manzil:",
        "photo": "📷 Foto yuboring yoki “O‘tkazib yuborish” tugmasini bosing:",
        "summary": "📝 O‘zingiz haqingizda qisqa professional summary yozing:",
        "experience": "🏢 Ish tajribangiz:",
        "education": "🎓 Ta’limingiz:",
        "skills": "🛠 Ko‘nikmalaringiz:",
        "languages": "🌐 Qaysi tillarni bilasiz?",
        "creating": "⏳ CV tayyorlanmoqda...",
        "ready_pdf": "✅ PDF CV tayyor.",
        "ready_html": "🌐 HTML CV ham tayyor.",
        "again": "Yana CV yaratish uchun /start bosing.",
        "skip": "O‘tkazib yuborish",
        "cancel": "❌ Bekor qilish",
    },
    "ru": {
        "start": "✅ CV_MK запущен.\n\n🌍 Выберите язык:",
        "design": "🎨 Выберите дизайн CV:",
        "name": "👤 Имя и фамилия:",
        "job": "💼 Профессия / должность:",
        "phone": "📞 Телефон:",
        "email": "📧 Email:",
        "address": "📍 Адрес:",
        "photo": "📷 Отправьте фото или нажмите “Пропустить”:",
        "summary": "📝 Краткое профессиональное описание:",
        "experience": "🏢 Опыт работы:",
        "education": "🎓 Образование:",
        "skills": "🛠 Навыки:",
        "languages": "🌐 Какие языки знаете?",
        "creating": "⏳ CV создаётся...",
        "ready_pdf": "✅ PDF CV готов.",
        "ready_html": "🌐 HTML CV готов.",
        "again": "Чтобы создать ещё одно CV, нажмите /start.",
        "skip": "Пропустить",
        "cancel": "❌ Отмена",
    },
    "en": {
        "start": "✅ CV_MK is running.\n\n🌍 Choose language:",
        "design": "🎨 Choose CV design:",
        "name": "👤 Full name:",
        "job": "💼 Profession / job title:",
        "phone": "📞 Phone:",
        "email": "📧 Email:",
        "address": "📍 Address:",
        "photo": "📷 Send a photo or press “Skip”:",
        "summary": "📝 Short professional summary:",
        "experience": "🏢 Work experience:",
        "education": "🎓 Education:",
        "skills": "🛠 Skills:",
        "languages": "🌐 Languages:",
        "creating": "⏳ Creating CV...",
        "ready_pdf": "✅ PDF CV is ready.",
        "ready_html": "🌐 HTML CV is ready.",
        "again": "Press /start to create another CV.",
        "skip": "Skip",
        "cancel": "❌ Cancel",
    },
}

DESIGNS = {
    "⬜ Minimalist": "minimalist",
    "🏢 Corporate": "corporate",
    "🎨 Modern": "modern",
    "💎 Premium": "premium",
}


def kb_lang():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O‘zbek")],
            [KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇬🇧 English")],
        ],
        resize_keyboard=True,
    )


def kb_design():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬜ Minimalist"), KeyboardButton(text="🏢 Corporate")],
            [KeyboardButton(text="🎨 Modern"), KeyboardButton(text="💎 Premium")],
        ],
        resize_keyboard=True,
    )


def kb_skip(lang):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TXT[lang]["skip"])],
            [KeyboardButton(text=TXT[lang]["cancel"])],
        ],
        resize_keyboard=True,
    )


def kb_cancel(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=TXT[lang]["cancel"])]],
        resize_keyboard=True,
    )


def is_cancel(text):
    text = (text or "").lower()
    return "bekor" in text or "отмена" in text or "cancel" in text


def is_skip(text):
    text = (text or "").lower().replace("‘", "'").replace("’", "'").replace("ʻ", "'")
    return (
        "skip" in text
        or "пропустить" in text
        or "otkazib" in text
        or "o'tkazib" in text
        or "o‘tkazib" in text
        or "oʻtkazib" in text
    )


def get_font():
    try:
        path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        pdfmetrics.registerFont(TTFont("DejaVu", path))
        return "DejaVu"
    except Exception:
        return "Helvetica"


FONT = get_font()


def safe(v):
    return str(v or "").strip()


def wrap_lines(text, width=76):
    lines = []
    for part in safe(text).split("\n"):
        lines.extend(textwrap.wrap(part, width=width) or [""])
    return lines


def file_base(user_id):
    return f"cv_{user_id}_{int(datetime.now().timestamp())}"


def generate_html(data, user_id):
    design = data.get("design", "minimalist")
    colors = {
        "minimalist": ("#ffffff", "#111827", "#2563eb"),
        "corporate": ("#f8fafc", "#0f172a", "#1d4ed8"),
        "modern": ("#0f172a", "#f8fafc", "#ec4899"),
        "premium": ("#080b18", "#ffffff", "#f59e0b"),
    }
    bg, text, accent = colors.get(design, colors["minimalist"])

    photo_html = ""
    if data.get("photo"):
        photo_html = f'<img class="photo" src="{html.escape(data["photo"])}">'

    content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(data.get("full_name","CV"))}</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#d1d5db;font-family:Arial,sans-serif;color:{text}}}
.page{{max-width:850px;margin:30px auto;background:{bg};padding:38px;border-radius:22px;box-shadow:0 25px 70px rgba(0,0,0,.25)}}
.header{{display:flex;gap:22px;align-items:center;border-bottom:3px solid {accent};padding-bottom:20px}}
.photo{{width:110px;height:110px;border-radius:50%;object-fit:cover;border:4px solid {accent}}}
h1{{font-size:36px;margin:0;color:{text}}}
.job{{color:{accent};font-size:18px;margin-top:6px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:24px}}
.section{{margin-top:22px;padding:18px;border-radius:16px;background:rgba(128,128,128,.10)}}
h2{{font-size:17px;margin:0 0 10px;color:{accent}}}
p{{line-height:1.6;white-space:pre-line}}
.small{{font-size:14px;opacity:.9}}
.footer{{margin-top:25px;font-size:12px;opacity:.7;text-align:center}}
@media(max-width:700px){{.grid,.header{{display:block}}.photo{{margin-bottom:15px}}}}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    {photo_html}
    <div>
      <h1>{html.escape(safe(data.get("full_name")))}</h1>
      <div class="job">{html.escape(safe(data.get("job")))}</div>
      <div class="small">📞 {html.escape(safe(data.get("phone")))} · 📧 {html.escape(safe(data.get("email")))} · 📍 {html.escape(safe(data.get("address")))}</div>
    </div>
  </div>

  <div class="section"><h2>Professional Summary</h2><p>{html.escape(safe(data.get("summary")))}</p></div>
  <div class="section"><h2>Work Experience</h2><p>{html.escape(safe(data.get("experience")))}</p></div>

  <div class="grid">
    <div class="section"><h2>Education</h2><p>{html.escape(safe(data.get("education")))}</p></div>
    <div class="section"><h2>Skills</h2><p>{html.escape(safe(data.get("skills")))}</p></div>
  </div>

  <div class="section"><h2>Languages</h2><p>{html.escape(safe(data.get("languages")))}</p></div>
  <div class="footer">Created by CV_MK Bot • {datetime.now().strftime("%d.%m.%Y")}</div>
</div>
</body>
</html>"""

    path = OUTPUT_DIR / f"{file_base(user_id)}.html"
    path.write_text(content, encoding="utf-8")
    return path


def draw_wrapped(c, text, x, y, width_chars=76, size=10):
    c.setFont(FONT, size)
    for line in wrap_lines(text, width_chars):
        if y < 70:
            c.showPage()
            y = A4[1] - 60
            c.setFont(FONT, size)
        c.drawString(x, y, line)
        y -= size + 6
    return y


def generate_pdf(data, user_id):
    path = OUTPUT_DIR / f"{file_base(user_id)}.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    design = data.get("design", "minimalist")

    accent = {
        "minimalist": (0.15, 0.38, 0.92),
        "corporate": (0.05, 0.20, 0.45),
        "modern": (0.90, 0.20, 0.55),
        "premium": (0.95, 0.60, 0.08),
    }.get(design, (0.15, 0.38, 0.92))

    if design in ["modern", "premium"]:
        c.setFillColorRGB(0.04, 0.06, 0.12)
        c.rect(0, 0, w, h, fill=1, stroke=0)
        text_color = (1, 1, 1)
    else:
        text_color = (0.05, 0.05, 0.05)

    y = h - 60
    c.setFillColorRGB(*accent)
    c.rect(0, h - 32, w, 32, fill=1, stroke=0)

    c.setFillColorRGB(*text_color)
    c.setFont(FONT, 24)
    c.drawString(50, y, safe(data.get("full_name"))[:42])
    y -= 28

    c.setFillColorRGB(*accent)
    c.setFont(FONT, 14)
    c.drawString(50, y, safe(data.get("job"))[:60])
    y -= 25

    c.setFillColorRGB(*text_color)
    c.setFont(FONT, 10)
    c.drawString(50, y, f"Phone: {safe(data.get('phone'))}")
    y -= 16
    c.drawString(50, y, f"Email: {safe(data.get('email'))}")
    y -= 16
    c.drawString(50, y, f"Address: {safe(data.get('address'))}")
    y -= 20

    def section(title, body):
        nonlocal y
        y -= 8
        c.setFillColorRGB(*accent)
        c.setFont(FONT, 15)
        c.drawString(50, y, title)
        y -= 18
        c.setFillColorRGB(*text_color)
        y = draw_wrapped(c, body, 60, y, 82, 10)

    section("Professional Summary", data.get("summary"))
    section("Work Experience", data.get("experience"))
    section("Education", data.get("education"))
    section("Skills", data.get("skills"))
    section("Languages", data.get("languages"))

    c.setFont(FONT, 8)
    c.setFillColorRGB(*accent)
    c.drawString(50, 35, f"Created by CV_MK Bot • {datetime.now().strftime('%d.%m.%Y')}")
    c.save()
    return path


async def ask(message, state, next_state, key, text_key):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(**{key: message.text})
    await state.set_state(next_state)
    await message.answer(TXT[lang][text_key], reply_markup=kb_cancel(lang))


@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CV.lang)
    await message.answer(TXT["uz"]["start"], reply_markup=kb_lang())


@dp.message(F.text.in_(list(LANGS.keys())))
async def choose_lang_any(message: Message, state: FSMContext):
    lang = LANGS[message.text]
    await state.update_data(lang=lang)
    await state.set_state(CV.design)
    await message.answer(TXT[lang]["design"], reply_markup=kb_design())


@dp.message(F.text)
async def global_text_router(message: Message, state: FSMContext):
    text = message.text or ""
    data = await state.get_data()
    lang = data.get("lang", "uz")
    current = await state.get_state()

    if is_cancel(text):
        await state.clear()
        await state.set_state(CV.lang)
        await message.answer("Bekor qilindi. / Отменено. / Cancelled.\n\n🌍 Tilni tanlang:", reply_markup=kb_lang())
        return

    if current == CV.lang.state:
        await message.answer(TXT["uz"]["start"], reply_markup=kb_lang())
        return

    if current == CV.design.state:
        if text not in DESIGNS:
            await message.answer(TXT[lang]["design"], reply_markup=kb_design())
            return
        await state.update_data(design=DESIGNS[text])
        await state.set_state(CV.full_name)
        await message.answer(TXT[lang]["name"], reply_markup=kb_cancel(lang))
        return

    if current == CV.full_name.state:
        await ask(message, state, CV.job, "full_name", "job")
        return

    if current == CV.job.state:
        await ask(message, state, CV.phone, "job", "phone")
        return

    if current == CV.phone.state:
        await ask(message, state, CV.email, "phone", "email")
        return

    if current == CV.email.state:
        await ask(message, state, CV.address, "email", "address")
        return

    if current == CV.address.state:
        await state.update_data(address=text)
        await state.set_state(CV.photo)
        await message.answer(TXT[lang]["photo"], reply_markup=kb_skip(lang))
        return

    if current == CV.photo.state:
        if is_skip(text):
            await state.update_data(photo="")
            await state.set_state(CV.summary)
            await message.answer(TXT[lang]["summary"], reply_markup=kb_cancel(lang))
            return
        await message.answer(TXT[lang]["photo"], reply_markup=kb_skip(lang))
        return

    if current == CV.summary.state:
        await ask(message, state, CV.experience, "summary", "experience")
        return

    if current == CV.experience.state:
        await ask(message, state, CV.education, "experience", "education")
        return

    if current == CV.education.state:
        await ask(message, state, CV.skills, "education", "skills")
        return

    if current == CV.skills.state:
        await ask(message, state, CV.languages, "skills", "languages")
        return

    if current == CV.languages.state:
        await state.update_data(languages=text)
        data = await state.get_data()
        lang = data.get("lang", "uz")
        await message.answer(TXT[lang]["creating"])

        try:
            pdf = generate_pdf(data, message.from_user.id)
            html_file = generate_html(data, message.from_user.id)

            await message.answer_document(FSInputFile(pdf), caption=TXT[lang]["ready_pdf"])
            await message.answer_document(FSInputFile(html_file), caption=TXT[lang]["ready_html"])
            await message.answer(TXT[lang]["again"], reply_markup=kb_lang())
        except Exception as e:
            await message.answer(f"❌ Xatolik: {e}")

        await state.clear()
        await state.set_state(CV.lang)
        return

    await state.set_state(CV.lang)
    await message.answer(TXT["uz"]["start"], reply_markup=kb_lang())


@dp.message(CV.photo, F.photo)
async def photo_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    try:
        file = await bot.get_file(message.photo[-1].file_id)
        photo_path = OUTPUT_DIR / f"photo_{message.from_user.id}_{int(datetime.now().timestamp())}.jpg"
        await bot.download_file(file.file_path, destination=photo_path)
        await state.update_data(photo=str(photo_path))
    except Exception:
        await state.update_data(photo="")

    await state.set_state(CV.summary)
    await message.answer(TXT[lang]["summary"], reply_markup=kb_cancel(lang))


@dp.message()
async def fallback(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    current = await state.get_state()

    if not current:
        await state.set_state(CV.lang)
        await message.answer(TXT["uz"]["start"], reply_markup=kb_lang())
    else:
        await message.answer("Iltimos, matn yuboring yoki /start bosing.", reply_markup=kb_cancel(lang))


async def main():
    threading.Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
