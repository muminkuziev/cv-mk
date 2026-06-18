import os
import asyncio
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from jinja2 import Environment, FileSystemLoader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable topilmadi.")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

web = Flask(__name__)


@web.route("/")
def home():
    return "ZiyoCVBot is running"


@web.route("/health")
def health():
    return "OK"


def run_web():
    port = int(os.getenv("PORT", 10000))
    web.run(host="0.0.0.0", port=port)


class CVStates(StatesGroup):
    template = State()
    full_name = State()
    profession = State()
    phone = State()
    email = State()
    address = State()
    experience = State()
    education = State()
    skills = State()
    languages = State()


main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📄 CV yaratish")],
        [KeyboardButton(text="ℹ️ Yordam")]
    ],
    resize_keyboard=True
)

template_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Minimalist"), KeyboardButton(text="Corporate")],
        [KeyboardButton(text="Modern"), KeyboardButton(text="Premium")]
    ],
    resize_keyboard=True
)

TEMPLATE_MAP = {
    "Minimalist": "minimalist.html",
    "Corporate": "corporate.html",
    "Modern": "modern.html",
    "Premium": "premium.html"
}


def generate_html(data: dict, user_id: int) -> Path:
    template_file = data.get("template", "minimalist.html")

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template(template_file)

    html = template.render(
        full_name=data.get("full_name", ""),
        profession=data.get("profession", ""),
        phone=data.get("phone", ""),
        email=data.get("email", ""),
        address=data.get("address", ""),
        experience=data.get("experience", ""),
        education=data.get("education", ""),
        skills=data.get("skills", ""),
        languages=data.get("languages", ""),
        date=datetime.now().strftime("%d.%m.%Y")
    )

    html_path = OUTPUT_DIR / f"cv_{user_id}.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path


def generate_pdf(data: dict, user_id: int) -> Path:
    pdf_path = OUTPUT_DIR / f"cv_{user_id}.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    y = height - 60

    def new_page_if_needed():
        nonlocal y
        if y < 70:
            c.showPage()
            y = height - 60

    def draw_section(title, text):
        nonlocal y
        new_page_if_needed()
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, title)
        y -= 20

        c.setFont("Helvetica", 10)
        for line in str(text).split("\n"):
            new_page_if_needed()
            c.drawString(60, y, line[:95])
            y -= 14

        y -= 10

    c.setFont("Helvetica-Bold", 22)
    c.drawString(50, y, data.get("full_name", "CV"))
    y -= 28

    c.setFont("Helvetica", 12)
    c.drawString(50, y, data.get("profession", ""))
    y -= 30

    draw_section("Telefon:", data.get("phone", ""))
    draw_section("Email:", data.get("email", ""))
    draw_section("Manzil:", data.get("address", ""))
    draw_section("Ish tajribasi:", data.get("experience", ""))
    draw_section("Ta'lim:", data.get("education", ""))
    draw_section("Ko'nikmalar:", data.get("skills", ""))
    draw_section("Tillar:", data.get("languages", ""))

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 35, f"ZiyoCVBot orqali yaratildi • {datetime.now().strftime('%d.%m.%Y')}")

    c.save()
    return pdf_path


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "✅ ZiyoCVBot ishga tushdi.\n\n"
        "Men sizga professional CV yaratib beraman.\n\n"
        "Boshlash uchun pastdagi tugmani bosing:",
        reply_markup=main_keyboard
    )


@dp.message(F.text == "ℹ️ Yordam")
async def help_message(message: Message):
    await message.answer(
        "📌 Bot qanday ishlaydi:\n\n"
        "1. 📄 CV yaratish tugmasini bosing\n"
        "2. Dizayn tanlang\n"
        "3. Savollarga javob bering\n"
        "4. Bot sizga HTML va PDF CV yuboradi"
    )


@dp.message(F.text == "📄 CV yaratish")
async def create_cv(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CVStates.template)
    await message.answer(
        "🎨 CV dizaynini tanlang:",
        reply_markup=template_keyboard
    )


@dp.message(CVStates.template)
async def choose_template(message: Message, state: FSMContext):
    if message.text not in TEMPLATE_MAP:
        await message.answer("Iltimos, pastdagi tugmalardan birini tanlang.")
        return

    await state.update_data(template=TEMPLATE_MAP[message.text])
    await state.set_state(CVStates.full_name)

    await message.answer(
        "Ism va familiyangizni yozing:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
            resize_keyboard=True
        )
    )


@dp.message(F.text == "❌ Bekor qilish")
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_keyboard)


@dp.message(CVStates.full_name)
async def get_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(CVStates.profession)
    await message.answer("Kasbingiz yoki lavozimingizni yozing:")


@dp.message(CVStates.profession)
async def get_profession(message: Message, state: FSMContext):
    await state.update_data(profession=message.text)
    await state.set_state(CVStates.phone)
    await message.answer("Telefon raqamingizni yozing:")


@dp.message(CVStates.phone)
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(CVStates.email)
    await message.answer("Email manzilingizni yozing:")


@dp.message(CVStates.email)
async def get_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text)
    await state.set_state(CVStates.address)
    await message.answer("Yashash manzilingizni yozing:\nMasalan: Warsaw, Poland")


@dp.message(CVStates.address)
async def get_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(CVStates.experience)
    await message.answer("Ish tajribangizni yozing:")


@dp.message(CVStates.experience)
async def get_experience(message: Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await state.set_state(CVStates.education)
    await message.answer("Ta'limingizni yozing:")


@dp.message(CVStates.education)
async def get_education(message: Message, state: FSMContext):
    await state.update_data(education=message.text)
    await state.set_state(CVStates.skills)
    await message.answer("Ko‘nikmalaringizni yozing:")


@dp.message(CVStates.skills)
async def get_skills(message: Message, state: FSMContext):
    await state.update_data(skills=message.text)
    await state.set_state(CVStates.languages)
    await message.answer("Qaysi tillarni bilasiz?")


@dp.message(CVStates.languages)
async def get_languages(message: Message, state: FSMContext):
    await state.update_data(languages=message.text)

    data = await state.get_data()
    user_id = message.from_user.id

    await message.answer("⏳ CV tayyorlanmoqda...")

    try:
        html_path = generate_html(data, user_id)
        pdf_path = generate_pdf(data, user_id)

        await message.answer_document(
            FSInputFile(pdf_path),
            caption="✅ Sizning PDF CV tayyor."
        )

        await message.answer_document(
            FSInputFile(html_path),
            caption="🌐 HTML CV fayli ham tayyor."
        )

    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi:\n{e}")

    await state.clear()
    await message.answer("Yana CV yaratish uchun tugmani bosing.", reply_markup=main_keyboard)


async def main():
    threading.Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
