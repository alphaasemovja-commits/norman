import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

# ===================== НАСТРОЙКИ =====================
BOT_TOKEN = "8405148176:AAHzZ0Om_iksDl-2Xu74f3SAHtH-iYGAmVE"
ADMIN_ID = 7922305713          # Твой Telegram ID
SBER_CARD = "2202 2081 62869524"  # Номер карты Сбер
SBER_NAME = "Скрыто Hellstar"         # Имя получателя

PRICE_PER_BC = 1.77           # Рублей за 1 BC
MIN_ORDER_RUB = 30            # Минимальный заказ в рублях
# =====================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Готовые пакеты BC
PACKAGES = [
    {"bc": 20,  "price": 35},
    {"bc": 50,  "price": 89},
    {"bc": 100, "price": 177},
    {"bc": 200, "price": 354},
    {"bc": 500, "price": 885},
]


class OrderStates(StatesGroup):
    choosing_amount = State()
    entering_custom_bc = State()
    entering_nickname = State()
    entering_server = State()
    waiting_payment = State()
    waiting_screenshot = State()


def main_menu():
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Купить BC")],
        [KeyboardButton(text="📋 Информация"), KeyboardButton(text="❓ Поддержка")]
    ], resize_keyboard=True)
    return kb


def packages_keyboard():
    builder = InlineKeyboardBuilder()
    for p in PACKAGES:
        builder.button(
            text=f"💎 {p['bc']} BC — {p['price']}₽",
            callback_data=f"pkg_{p['bc']}_{p['price']}"
        )
    builder.button(text="✏️ Своя сумма", callback_data="custom_amount")
    builder.adjust(1)
    return builder.as_markup()


def confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Я оплатил — отправить чек", callback_data="paid")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def admin_keyboard(user_id, order_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Выдал BC", callback_data=f"done_{user_id}_{order_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_{user_id}_{order_id}")
    builder.adjust(2)
    return builder.as_markup()


# ===================== КОМАНДЫ =====================

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        f"👋 Добро пожаловать в донат-магазин <b>Black Russia</b>!\n\n"
        f"💰 Курс: <b>1 BC = {PRICE_PER_BC}₽</b>\n"
        f"📦 Минимальный заказ: <b>{MIN_ORDER_RUB}₽</b>\n\n"
        f"Выбери действие ниже 👇",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


@dp.message(F.text == "📋 Информация")
async def info_handler(message: types.Message):
    await message.answer(
        "📌 <b>Информация о магазине</b>\n\n"
        f"🎮 Игра: <b>Black Russia (GTA RP)</b>\n"
        f"💎 Валюта: <b>BC (Black Coins)</b>\n"
        f"💰 Курс: <b>1 BC = {PRICE_PER_BC}₽</b>\n"
        f"📦 Минимальный заказ: <b>{MIN_ORDER_RUB}₽</b>\n\n"
        f"💳 Оплата: Перевод на карту Сбербанк\n"
        f"⏱ Выдача: вручную, обычно в течение 5–15 минут\n\n"
        f"❗️ После оплаты обязательно пришли скриншот чека!",
        parse_mode="HTML"
    )


@dp.message(F.text == "❓ Поддержка")
async def support_handler(message: types.Message):
    await message.answer(
        "❓ <b>Поддержка</b>\n\n"
        "Если у тебя возникли проблемы — напиши администратору:\n"
        "👤 @admin_username\n\n"
        "Мы ответим в ближайшее время!",
        parse_mode="HTML"
    )


# ===================== ПОКУПКА =====================

@dp.message(F.text == "🛒 Купить BC")
async def buy_handler(message: types.Message, state: FSMContext):
    await state.set_state(OrderStates.choosing_amount)
    await message.answer(
        "💎 <b>Выбери пакет BC</b>\n\n"
        f"Курс: 1 BC = {PRICE_PER_BC}₽\n"
        f"Минимальный заказ: {MIN_ORDER_RUB}₽\n\n"
        "👇 Выбери готовый пакет или введи своё количество:",
        parse_mode="HTML",
        reply_markup=packages_keyboard()
    )


@dp.callback_query(F.data.startswith("pkg_"))
async def package_selected(callback: types.CallbackQuery, state: FSMContext):
    _, bc, price = callback.data.split("_")
    bc, price = int(bc), int(price)
    await state.update_data(bc=bc, price=price)
    await state.set_state(OrderStates.entering_nickname)
    await callback.message.edit_text(
        f"✅ Выбрано: <b>{bc} BC — {price}₽</b>\n\n"
        f"📝 Введи свой <b>ник в игре</b> (Black Russia):",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "custom_amount")
async def custom_amount(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.entering_custom_bc)
    await callback.message.edit_text(
        f"✏️ Введи желаемое количество <b>BC</b>:\n\n"
        f"Минимум: {int(MIN_ORDER_RUB / PRICE_PER_BC) + 1} BC ({MIN_ORDER_RUB}₽)",
        parse_mode="HTML"
    )


@dp.message(OrderStates.entering_custom_bc)
async def custom_bc_entered(message: types.Message, state: FSMContext):
    try:
        bc = int(message.text.strip())
        price = round(bc * PRICE_PER_BC, 2)
        if price < MIN_ORDER_RUB:
            await message.answer(
                f"❌ Минимальный заказ — <b>{MIN_ORDER_RUB}₽</b>.\n"
                f"Введи не менее <b>{int(MIN_ORDER_RUB / PRICE_PER_BC) + 1} BC</b>.",
                parse_mode="HTML"
            )
            return
        await state.update_data(bc=bc, price=price)
        await state.set_state(OrderStates.entering_nickname)
        await message.answer(
            f"✅ Итого: <b>{bc} BC — {price}₽</b>\n\n"
            f"📝 Введи свой <b>ник в игре</b> (Black Russia):",
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ Введи число, например: <b>100</b>", parse_mode="HTML")


@dp.message(OrderStates.entering_nickname)
async def nickname_entered(message: types.Message, state: FSMContext):
    await state.update_data(nickname=message.text.strip())
    await state.set_state(OrderStates.entering_server)
    await message.answer(
        "🌐 На каком <b>сервере</b> играешь?\n\n"
        "Например: Сервер 1, Сервер 2 и т.д.",
        parse_mode="HTML"
    )


@dp.message(OrderStates.entering_server)
async def server_entered(message: types.Message, state: FSMContext):
    await state.update_data(server=message.text.strip())
    data = await state.get_data()
    bc = data['bc']
    price = data['price']
    nickname = data['nickname']
    server = data['server']

    await state.set_state(OrderStates.waiting_payment)
    await message.answer(
        f"🧾 <b>Твой заказ:</b>\n\n"
        f"🎮 Ник: <b>{nickname}</b>\n"
        f"🌐 Сервер: <b>{server}</b>\n"
        f"💎 Количество: <b>{bc} BC</b>\n"
        f"💰 Сумма: <b>{price}₽</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Реквизиты для оплаты:</b>\n\n"
        f"🏦 Сбербанк\n"
        f"💳 Карта: <code>{SBER_CARD}</code>\n"
        f"👤 Получатель: <b>{SBER_NAME}</b>\n"
        f"💵 Сумма: <b>{price}₽</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ После оплаты нажми кнопку ниже и пришли <b>скриншот чека</b>!",
        parse_mode="HTML",
        reply_markup=confirm_keyboard()
    )


@dp.callback_query(F.data == "paid")
async def paid_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.waiting_screenshot)
    await callback.message.edit_text(
        "📸 Отлично! Теперь пришли <b>скриншот чека</b> об оплате:",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "cancel")
async def cancel_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Заказ отменён.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu())


@dp.message(OrderStates.waiting_screenshot, F.photo)
async def screenshot_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    bc = data['bc']
    price = data['price']
    nickname = data['nickname']
    server = data['server']
    user = message.from_user
    order_id = message.message_id

    # Уведомление клиенту
    await message.answer(
        "✅ <b>Чек получен!</b>\n\n"
        "Твой заказ передан администратору.\n"
        "⏱ Ожидай выдачу BC в течение 5–15 минут.\n\n"
        "Спасибо за покупку! 🎮",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    # Уведомление админу
    await bot.send_photo(
        ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=(
            f"🔔 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n"
            f"👤 Клиент: {user.full_name} (@{user.username or 'нет'})\n"
            f"🆔 ID: <code>{user.id}</code>\n\n"
            f"🎮 Ник в игре: <b>{nickname}</b>\n"
            f"🌐 Сервер: <b>{server}</b>\n"
            f"💎 Количество: <b>{bc} BC</b>\n"
            f"💰 Сумма: <b>{price}₽</b>\n\n"
            f"👇 После выдачи нажми кнопку:"
        ),
        parse_mode="HTML",
        reply_markup=admin_keyboard(user.id, order_id)
    )

    await state.clear()


@dp.message(OrderStates.waiting_screenshot)
async def wrong_screenshot(message: types.Message):
    await message.answer("📸 Пожалуйста, пришли именно <b>скриншот</b> (фото чека).", parse_mode="HTML")


# ===================== АДМИН =====================

@dp.callback_query(F.data.startswith("done_"))
async def admin_done(callback: types.CallbackQuery):
    _, user_id, order_id = callback.data.split("_")
    await bot.send_message(
        int(user_id),
        "✅ <b>BC успешно выданы!</b>\n\n"
        "Проверь свой баланс в игре 🎮\n"
        "Спасибо за покупку! Возвращайся ещё 💎",
        parse_mode="HTML"
    )
    await callback.message.edit_caption(
        callback.message.caption + "\n\n✅ <b>ВЫДАНО</b>",
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("reject_"))
async def admin_reject(callback: types.CallbackQuery):
    _, user_id, order_id = callback.data.split("_")
    await bot.send_message(
        int(user_id),
        "❌ <b>Заказ отклонён.</b>\n\n"
        "Возможно, чек не прошёл проверку.\n"
        "Если считаешь это ошибкой — обратись в поддержку: @admin_username",
        parse_mode="HTML"
    )
    await callback.message.edit_caption(
        callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>",
        parse_mode="HTML"
    )


# Команда для админа — статистика
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "👑 <b>Панель администратора</b>\n\n"
        "Все заказы приходят сюда автоматически.\n"
        "После выдачи BC нажимай ✅ под заказом.",
        parse_mode="HTML"
    )


async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
