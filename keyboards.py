from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
)
from config import WEBAPP_URL, BOT_USERNAME

def get_main_keyboard(webapp_url: str = "") -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="⚡ 1 O'zim o'ynash (Solo)"), KeyboardButton(text="⚔️ Do'stlar bilan jangi")],
    ]
    if webapp_url:
        buttons.append([KeyboardButton(text="🎮 O'yinni ochish (Mini App)", web_app=WebAppInfo(url=webapp_url))])
    
    buttons.extend([
        [KeyboardButton(text="🏆 Reyting"), KeyboardButton(text="👤 Profilim")],
        [KeyboardButton(text="📚 96 Kunlik Lug'at"), KeyboardButton(text="ℹ️ Qoidalar")]
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

def get_player_count_inline(day: int = 1) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 1 o'zim (Solo)", callback_data=f"setup_count_1_{day}"),
            InlineKeyboardButton(text="👥 2 kishi", callback_data=f"setup_count_2_{day}")
        ],
        [
            InlineKeyboardButton(text="👥 3 kishi", callback_data=f"setup_count_3_{day}"),
            InlineKeyboardButton(text="👥 4 kishi", callback_data=f"setup_count_4_{day}")
        ],
        [
            InlineKeyboardButton(text="👥 5 kishi", callback_data=f"setup_count_5_{day}"),
            InlineKeyboardButton(text="👥 6 kishi", callback_data=f"setup_count_6_{day}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="back_to_menu")
        ]
    ])

def get_day_select_inline(count: int = 2, page: int = 1) -> InlineKeyboardMarkup:
    # 96 days, 12 per page
    items_per_page = 12
    start_day = (page - 1) * items_per_page + 1
    end_day = min(96, start_day + items_per_page - 1)

    keyboard = []
    row = []
    for d in range(start_day, end_day + 1):
        row.append(InlineKeyboardButton(text=f"{d}-kun", callback_data=f"choose_day_{d}_{count}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Navigation buttons
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"day_page_{page-1}_{count}"))
    if end_day < 96:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"day_page_{page+1}_{count}"))
    
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton(text="🎲 Tasodifiy kun", callback_data=f"choose_day_random_{count}"),
        InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_to_setup")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_lobby_keyboard(room_code: str, is_host: bool = False, webapp_url: str = "") -> InlineKeyboardMarkup:
    share_text = f"🎮 Kel, 'So'z Jangi'da bellashamiz!\nXona kodi: {room_code}\nUlanish: https://t.me/{BOT_USERNAME}?start=room_{room_code}"
    
    rows = []
    # Share button
    rows.append([
        InlineKeyboardButton(
            text="📲 Do'stlarni taklif qilish",
            url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}?start=room_{room_code}&text={share_text}"
        )
    ])
    
    if webapp_url:
        room_webapp_url = f"{webapp_url}?room={room_code}"
        rows.append([
            InlineKeyboardButton(text="🎮 Mini Appda o'ynash", web_app=WebAppInfo(url=room_webapp_url))
        ])

    action_row = []
    if is_host:
        action_row.append(InlineKeyboardButton(text="🚀 O'yinni boshlash", callback_data=f"start_room_{room_code}"))
    else:
        action_row.append(InlineKeyboardButton(text="✅ Tayyorman", callback_data=f"ready_room_{room_code}"))
    
    action_row.append(InlineKeyboardButton(text="🚪 Chiqish", callback_data=f"leave_room_{room_code}"))
    rows.append(action_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_question_inline(options: list, room_code: str, q_index: int) -> InlineKeyboardMarkup:
    keyboard = []
    for idx, opt in enumerate(options):
        letter = chr(65 + idx)
        btn_text = f"{letter}) {opt}"
        keyboard.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"ans_{room_code}_{q_index}_{idx}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
