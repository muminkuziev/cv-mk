import os
import asyncio
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    FSInputFile
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from jinja2 import Environment, FileSystemLoader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Render Environment Variables ga BOT_TOKEN qo‘ying.")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
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


class CVStates(StatesGroup):
    lang = State()
    template = State()
    full_name = State()
    profession = State()
    phone = State()
    email = State()
    address = State()
    photo = State()
    summary = State()
    experience = State()
    education = State()
    skills = State()
    languages = State()


TEXT = {
    "uz": {
        "start": "✅ CV_MK Bot ishga tushdi.\n\n🌍 Tilni tanlang:",
        "choose_template": "🎨 CV dizaynini tanlang:",
        "full_name": "👤 Ism va familiyangizni yozing:",
        "profession": "💼 Kasbingiz yoki lavozimingizni yozing:",
        "phone": "📞 Telefon raqamingizni yozing:",
        "email": "📧 Email manzilingizni yozing:",
        "address": "📍 Manzilingizni yozing:",
        "photo": "📷 Foto yuboring yoki “O‘tkazib yuborish” tugmasini bosing:",
        "summary": "📝 O‘zingiz haqingizda qisqa professional summary yozing:",
        "experience": "🏢 Ish tajribangizni yozing:",
        "education": "🎓 Ta’limingizni yozing:",
        "skills": "🛠 Ko‘nikmalaringizni yozing:",
        "languages": "🌐 Qaysi tillarni bilasiz?",
        "creating": "⏳ CV tayyorlanmoqda...",
        "pdf_ready": "✅ Sizning PDF CV tayyor.",
        "html_ready": "🌐 HTML CV fayli ham tayyor.",
        "again": "Yana CV yaratish uchun /start bosing.",
        "skip": "O‘tkazib yuborish",
        "cancel": "❌ Bekor qilish"
    },
    "ru": {
        "start": "✅ CV_MK Bot запущен.\n\n🌍 Выберите язык:",
        "choose_template": "🎨 Выберите дизайн CV:",
        "full_name": "👤 Напишите имя и фамилию:",
        "profession": "💼 Напишите профессию или должность:",
        "phone": "📞 Напишите номер телефона:",
        "email": "📧 Напишите e-mail:",
        "address": "📍 Напишите адрес:",
        "photo": "📷 Отправьте фото или нажмите “Пропустить”:",
        "summary": "📝 Напишите краткое профессиональное описание:",
        "experience": "🏢 Напишите опыт работы:",
        "education": "🎓 Напишите образование:",
        "skills": "🛠 Напишите навыки:",
        "languages": "🌐 Какие языки знаете?",
        "creating": "⏳ CV создаётся...",
        "pdf_ready": "✅ Ваш PDF CV готов.",
        "html_ready": "🌐 HTML CV тоже готов.",
        "again": "Чтобы создать ещё одно CV, нажмите /start.",
        "skip": "Пропустить",
        "cancel": "❌ Отмена"
    },
    "en": {
        "start": "✅ CV_MK Bot is running.\n\n🌍 Choose language:",
        "choose_template": "🎨 Choose CV design:",
        "full_name": "👤 Enter your full name:",
        "profession": "💼 Enter your profession or job title:",
        "phone": "📞 Enter your phone number:",
        "email": "📧 Enter your email:",
        "address": "📍 Enter your address:",
        "photo": "📷 Send a photo or press “Skip”:",
        "summary": "📝 Write a short professional summary:",
        "experience": "🏢 Enter your work experience:",
        "education": "🎓 Enter your education:",
        "skills": "🛠 Enter your skills:",
        "languages": "🌐 Which languages do you know?",
        "creating": "⏳ CV is being created...",
        "pdf_ready": "✅ Your PDF CV is ready.",
        "html_ready": "🌐 HTML CV is also ready.",
        "again": "Press /start to create another CV.",
        "skip": "Skip",
        "cancel": "❌ Cancel"
    }
}


LANG_MAP = {
    "🇺🇿 O‘zbek": "uz",
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en"
}

TEMPLATE_MAP = {
    "Minimalist": "minimalist.html",
    "Corporate": "corporate.html",
    "Modern": "modern.html",
    "Premium": "premium.html"
}


def lang_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O‘zbek")],
            [KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True
    )


def template_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Minimalist"), KeyboardButton(text="Corporate")],
            [KeyboardButton(text="Modern"), KeyboardButton(text="Premium")]
        ],
        resize_keyboard=True
    )


def skip_keyboard(lang):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TEXT[lang]["skip"])],
            [KeyboardButton(text=TEXT[lang]["cancel"])]
        ],
        resize_keyboard=True
    )


def cancel_keyboard(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=TEXT[lang]["cancel"])]],
        resize_keyboard=True
    )


def clean_filename(user_id):
    return f"cv_{user_id}_{int(datetime.now().timestamp())}"


def generate_html(data, user_id):
    template_file = data.get("template", "minimalist.html")

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template(template_file)

    html = template.render(
        full_name=data.get("full_name", ""),
        profession=data.get("profession", ""),
        phone=data.get("phone", ""),
        email=data.get("email", ""),
        address=data.get("address", ""),
        photo=data.get("photo", ""),
        summary=data.get("summary", ""),
        experience=data.get("experience", ""),
        education=data.get("education", ""),
        skills=data.get("skills", ""),
        languages=data.get("languages", ""),
        date=datetime.now().strftime("%d.%m.%Y")
    )

    html_path = OUTPUT_DIR / f"{clean_filename(user_id)}.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path


def generate_pdf(data, user_id):
    pdf_path = OUTPUT_DIR / f"{clean_filename(user_id)}.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    y = height - 60

    def write_line(text, size=10, bold=False, indent=50):
        nonlocal y
        if y < 60:
            c.showPage()
            y = height - 60

        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)

        safe_text = str(text).replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
        c.drawString(indent, y, safe_text[:95])
        y -= size + 7

    def section(title, body):
        nonlocal y
        y -= 6
        write_line(title, 13, True)
        for line in str(body).split("\n"):
            write_line(line, 10, False, 65)
        y -= 6

    write_line(data.get("full_name", "CV"), 22, True)
    write_line(data.get("profession", ""), 12)

    section("Phone:", data.get("phone", ""))
    section("Email:", data.get("email", ""))
    section("Address:", data.get("address", ""))
    section("Professional Summary:", data.get("summary", ""))
    section("Work Experience:", data.get("experience", ""))
    section("Education:", data.get("education", ""))
    section("Skills:", data.get("skills", ""))
    section("Languages:", data.get("languages", ""))

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 35, f"Created by CV_MK Bot • {datetime.now().strftime('%d.%m.%Y')}")
    c.save()

    return pdf_path


@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CVStates.lang)
    await message.answer(TEXT["uz"]["start"], reply_markup=lang_keyboard())


@dp.message(CVStates.lang)
async def choose_lang(message: Message, state: FSMContext):
    if message.text not in LANG_MAP:
        await message.answer("🌍 Tilni tanlang / Выберите язык / Choose language:", reply_markup=lang_keyboard())
        return

    lang = LANG_MAP[message.text]
    await state.update_data(lang=lang)
    await state.set_state(CVStates.template)
    await message.answer(TEXT[lang]["choose_template"], reply_markup=template_keyboard())


@dp.message(CVStates.template)
async def choose_template(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    if message.text not in TEMPLATE_MAP:
        await message.answer(TEXT[lang]["choose_template"], reply_markup=template_keyboard())
        return

    await state.update_data(template=TEMPLATE_MAP[message.text])
    await state.set_state(CVStates.full_name)
    await message.answer(TEXT[lang]["full_name"], reply_markup=cancel_keyboard(lang))


@dp.message(F.text.in_(["❌ Bekor qilish", "❌ Отмена", "❌ Cancel"]))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi. / Отменено. / Cancelled.", reply_markup=lang_keyboard())


@dp.message(CVStates.full_name)
async def full_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(full_name=message.text)
    await state.set_state(CVStates.profession)
    await message.answer(TEXT[lang]["profession"])


@dp.message(CVStates.profession)
async def profession(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(profession=message.text)
    await state.set_state(CVStates.phone)
    await message.answer(TEXT[lang]["phone"])


@dp.message(CVStates.phone)
async def phone(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(phone=message.text)
    await state.set_state(CVStates.email)
    await message.answer(TEXT[lang]["email"])


@dp.message(CVStates.email)
async def email(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(email=message.text)
    await state.set_state(CVStates.address)
    await message.answer(TEXT[lang]["address"])


@dp.message(CVStates.address)
async def address(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(address=message.text)
    await state.set_state(CVStates.photo)
    await message.answer(TEXT[lang]["photo"], reply_markup=skip_keyboard(lang))


@dp.message(CVStates.photo)
async def photo(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    if message.text == TEXT[lang]["skip"]:
        await state.update_data(photo="")
    elif message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        photo_path = OUTPUT_DIR / f"photo_{message.from_user.id}.jpg"
        await bot.download_file(file.file_path, destination=photo_path)
        await state.update_data(photo=str(photo_path))
    else:
        await message.answer(TEXT[lang]["photo"], reply_markup=skip_keyboard(lang))
        return

    await state.set_state(CVStates.summary)
    await message.answer(TEXT[lang]["summary"], reply_markup=cancel_keyboard(lang))


@dp.message(CVStates.summary)
async def summary(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(summary=message.text)
    await state.set_state(CVStates.experience)
    await message.answer(TEXT[lang]["experience"])


@dp.message(CVStates.experience)
async def experience(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(experience=message.text)
    await state.set_state(CVStates.education)
    await message.answer(TEXT[lang]["education"])


@dp.message(CVStates.education)
async def education(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(education=message.text)
    await state.set_state(CVStates.skills)
    await message.answer(TEXT[lang]["skills"])


@dp.message(CVStates.skills)
async def skills(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await state.update_data(skills=message.text)
    await state.set_state(CVStates.languages)
    await message.answer(TEXT[lang]["languages"])


@dp.message(CVStates.languages)
async def languages(message: Message, state: FSMContext):
    await state.update_data(languages=message.text)
    data = await state.get_data()
    lang = data.get("lang", "uz")

    await message.answer(TEXT[lang]["creating"])

    try:
        pdf_path = generate_pdf(data, message.from_user.id)
        html_path = generate_html(data, message.from_user.id)

        await message.answer_document(FSInputFile(pdf_path), caption=TEXT[lang]["pdf_ready"])
        await message.answer_document(FSInputFile(html_path), caption=TEXT[lang]["html_ready"])
        await message.answer(TEXT[lang]["again"], reply_markup=lang_keyboard())

    except Exception as e:
        await message.answer(f"❌ Xatolik:\n{e}")

    await state.clear()


async def main():
    threading.Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
