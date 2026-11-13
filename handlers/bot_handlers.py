import asyncio
import logging
import random
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import WEBAPP_URL, BOT_USERNAME, ADMIN_IDS
import database as db
from game_engine import game_mgr
from vocab_manager import vocab_mgr
import keyboards as kb

logger = logging.getLogger(__name__)
router = Router()

# Store active bot message IDs per user for clean updating: user_id -> message_id
user_active_msg = {}

RULES_TEXT = (
    "📜 <b>'SO'Z JANGI' O'YIN QOIDALARI:</b>\n\n"
    "1️⃣ <b>Ishtirokchilar:</b>\n"
    "• 1 kishi (Solo - o'zingiz bilan mashq)\n"
    "• 2, 3, 4, 5 yoki 6 kishilik xonalarda do'stlar bilan jonli bellashuv!\n\n"
    "2️⃣ <b>Savollar va Vaqt:</b>\n"
    "• <b>4 talik Test:</b> ⏱️ 10 soniya\n"
    "• <b>Yozma so'z kiritish:</b> ⏱️ 20 soniya\n"
    "• <i>Agar barcha ishtirokchilar javob berib bo'lsa, kutmasdan keyingi savolga o'tiladi!</i>\n\n"
    "3️⃣ <b>Ballar tizimi:</b>\n"
    "• 🥇 1-bo'lib to'g'ri topganga: <b>+5 ball</b>\n"
    "• 🥈 2-bo'lib to'g'ri topganga: <b>+4 ball</b>\n"
    "• 🥉 3-bo'lib to'g'ri topganga: <b>+3 ball</b>\n"
    "• 4-chiga: +2 ball, 5-6 chiga: +1 ball\n"
    "• ❌ Noto'g'ri javobga: <b>-1 ball jarima!</b>\n\n"
    "4️⃣ <b>Yakuniy natija:</b>\n"
    "• O'yin oxirida umumiy ballar va 1-, 2-, 3-o'rinlar shohsupasi aniqlanadi!\n"
    "• Qaysi so'zlarda adashganingiz va to'g'ri javoblari to'liq ko'rsatiladi."
)

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    stats = await db.get_total_stats()
    text = (
        "⚙️ <b>ADMIN PANELI:</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b> ta\n"
        f"🎮 Jami o'yinlar: <b>{stats['total_games']}</b> ta\n"
        f"🏠 Hozirgi faol xonalar: <b>{len(game_mgr.rooms)}</b> ta\n"
        f"📚 Bazadagi so'zlar: <b>{len(vocab_mgr.all_words)}</b> ta (96 kun)"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user = message.from_user
    await db.get_or_create_user(user.id, user.username or "", user.first_name or "")
    
    # Check for deep-linking (e.g. /start room_123456)
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("room_"):
        room_code = args[1].replace("room_", "").strip()
        room = game_mgr.join_room(room_code, user.id, user.first_name, user.username or "")
        if room:
            await show_room_lobby(bot, room, message.chat.id)
            return
        else:
            await message.answer("⚠️ Xona topilmadi yoki to'lib bo'lgan.", reply_markup=kb.get_main_keyboard(WEBAPP_URL))

    welcome_text = (
        f"👋 <b>Assalomu alaykum, {user.first_name}!</b>\n\n"
        f"⚔️ <b>'So'z Jangi'</b> multiplayer o'yiniga xush kelibsiz!\n"
        f"Bu yerda siz 96 kunlik ingliz tili lug'atlari bo'yicha do'stlaringiz bilan "
        f"jonli bellashishingiz yoki yolg'iz bilimingizni sinashingiz mumkin.\n\n"
        f"👇 O'yin rejimini tanlang:"
    )
    await message.answer(
        welcome_text,
        reply_markup=kb.get_main_keyboard(WEBAPP_URL),
        parse_mode="HTML"
    )

@router.message(F.text == "ℹ️ Qoidalar")
async def show_rules(message: Message):
    await message.answer(RULES_TEXT, parse_mode="HTML")

@router.message(F.text == "👤 Profilim")
async def show_profile(message: Message):
    user_id = message.from_user.id
    u = await db.get_user(user_id)
    if not u:
        u = await db.get_or_create_user(user_id, message.from_user.username or "", message.from_user.first_name)
    
    text = (
        f"👤 <b>Foydalanuvchi:</b> {u['first_name']}\n"
        f"⭐ <b>Jami ballar:</b> {u['score']} ball\n"
        f"🎮 <b>O'ynalgan o'yinlar:</b> {u['games_played']} ta\n"
        f"🏆 <b>G'alabalar soni:</b> {u['wins']} ta\n"
        f"✅ <b>To'g'ri topilgan so'zlar:</b> {u['correct_count']} ta\n"
        f"❌ <b>Xatolar soni:</b> {u['wrong_count']} ta"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "🏆 Reyting")
async def show_leaderboard(message: Message):
    top = await db.get_top_users(10)
    if not top:
        await message.answer("Hozircha reytingda hech kim yo'q. Birinchi bo'ling!")
        return

    text = "🏆 <b>TOP-10 ENG KUCHLI O'YINCHILAR:</b>\n\n"
    for i, u in enumerate(top, start=1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        name = u["first_name"] or u["username"] or "O'yinchi"
        text += f"{medal} <b>{name}</b> — <b>{u['score']}</b> ball ({u['wins']} g'alaba)\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📚 96 Kunlik Lug'at")
async def show_vocab_info(message: Message):
    text = (
        f"📚 <b>Lug'atlar bazasi:</b>\n"
        f"• Jami: <b>96 kun</b>\n"
        f"• So'zlar soni: <b>{len(vocab_mgr.all_words)} ta</b>\n\n"
        f"Har bir kun uchun alohida savollar to'plami tuzilgan. "
        f"Xona ochayotganda istalgan kunni tanlashingiz mumkin!"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "⚡ 1 O'zim o'ynash (Solo)")
async def start_solo_flow(message: Message, bot: Bot):
    user = message.from_user
    random_day = random.randint(1, 96)
    room = game_mgr.create_room(user.id, user.first_name, user.username or "", max_players=1, day=random_day, q_mode="choice", time_limit=15)
    attach_room_bot_listener(room, bot)
    await message.answer(
        f"⚡ <b>Solo rejim boshlanmoqda!</b>\nTanlangan kun: <b>{random_day}-kun</b>\nSavollar soni: 10 ta.",
        parse_mode="HTML"
    )
    room.start_game(bot)

@router.message(F.text == "⚔️ Do'stlar bilan jangi")
async def start_multiplayer_flow(message: Message):
    text = (
        "⚔️ <b>Do'stlar bilan bellashuv:</b>\n\n"
        "Xonangiz necha kishilik bo'lsin?"
    )
    await message.answer(text, reply_markup=kb.get_player_count_inline(), parse_mode="HTML")

@router.callback_query(F.data.startswith("setup_count_"))
async def cb_setup_count(call: CallbackQuery):
    parts = call.data.split("_")
    count = int(parts[2])
    day = int(parts[3])
    
    if count == 1:
        # Solo
        room = game_mgr.create_room(call.from_user.id, call.from_user.first_name, call.from_user.username or "", max_players=1, day=day, q_mode="choice", time_limit=15)
        attach_room_bot_listener(room, call.bot)
        await call.message.edit_text(f"⚡ <b>Solo rejim!</b> {day}-kun lug'ati bo'yicha boshlanmoqda...", parse_mode="HTML")
        room.start_game(call.bot)
        await call.answer()
        return

    # Choose day
    await call.message.edit_text(
        f"👥 Tanlandi: <b>{count} kishilik xona</b>\nEndi qaysi kun lug'atidan o'ynaymiz?",
        reply_markup=kb.get_day_select_inline(count=count, page=1),
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data.startswith("day_page_"))
async def cb_day_page(call: CallbackQuery):
    parts = call.data.split("_")
    page = int(parts[2])
    count = int(parts[3])
    await call.message.edit_reply_markup(reply_markup=kb.get_day_select_inline(count=count, page=page))
    await call.answer()

@router.callback_query(F.data.startswith("choose_day_"))
async def cb_choose_day(call: CallbackQuery, bot: Bot):
    parts = call.data.split("_")
    day_str = parts[2]
    count = int(parts[3])
    
    if day_str == "random":
        day = random.randint(1, 96)
    else:
        day = int(day_str)

    user = call.from_user
    room = game_mgr.create_room(user.id, user.first_name, user.username or "", max_players=count, day=day, q_mode="choice", time_limit=15)
    attach_room_bot_listener(room, bot)
    
    await call.message.delete()
    await show_room_lobby(bot, room, call.message.chat.id)
    await call.answer()

async def show_room_lobby(bot: Bot, room, chat_id: int):
    players_text = "\n".join([f"• <b>{p.first_name}</b> {'(Host 👑)' if p.user_id == room.host_id else ''}" for p in room.players.values()])
    
    text = (
        f"🎮 <b>XONA TAYYOR!</b>\n\n"
        f"🔑 Xona kodi: <code>{room.code}</code>\n"
        f"📅 Tanlangan kun: <b>{room.day}-kun lug'ati</b>\n"
        f"👥 Sig'imi: <b>{len(room.players)} / {room.max_players} kishi</b>\n\n"
        f"<b>Uланган ishtirokchilar:</b>\n{players_text}\n\n"
        f"👇 Do'stlaringizga taklif havolasini yuboring va hamma yig'ilgach 'O'yinni boshlash' tugmasini bosing!"
    )
    
    is_host = (chat_id == room.host_id)
    await bot.send_message(
        chat_id,
        text,
        reply_markup=kb.get_lobby_keyboard(room.code, is_host=is_host, webapp_url=WEBAPP_URL),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("start_room_"))
async def cb_start_room(call: CallbackQuery, bot: Bot):
    code = call.data.replace("start_room_", "").strip()
    room = game_mgr.get_room(code)
    if not room:
        await call.answer("Xona topilmadi!", show_alert=True)
        return
    if call.from_user.id != room.host_id:
        await call.answer("Faqat xona egasi boshlay oladi!", show_alert=True)
        return

    await call.answer("O'yin boshlanmoqda! 🚀")
    room.start_game(bot)

@router.callback_query(F.data.startswith("leave_room_"))
async def cb_leave_room(call: CallbackQuery):
    game_mgr.leave_room(call.from_user.id)
    await call.message.edit_text("Siz xonadan chiqdingiz.")
    await call.answer()

@router.callback_query(F.data.startswith("ans_"))
async def cb_answer(call: CallbackQuery):
    # Format: ans_{room_code}_{q_index}_{opt_index}
    parts = call.data.split("_")
    code = parts[1]
    q_index = int(parts[2])
    opt_index = int(parts[3])

    room = game_mgr.get_room(code)
    if not room or room.status != "playing":
        await call.answer("O'yin faol emas!", show_alert=True)
        return
    if room.current_q_index != q_index:
        await call.answer("Bu savol muddati tugagan!", show_alert=True)
        return

    q = room.questions[q_index]
    options = q.get("options", [])
    if opt_index >= len(options):
        await call.answer()
        return

    chosen_opt = options[opt_index]
    res = await room.submit_answer(call.from_user.id, chosen_opt)

    if res.get("is_correct"):
        await call.answer(f"✓ TO'G'RI! +{res['points']} ball! 🎉", show_alert=True)
    else:
        await call.answer(f"✗ NOTO'G'RI! -1 ball jarima.\nTo'g'ri javob: {res['correct_answer']}", show_alert=True)

@router.message(F.text)
async def handle_written_chat_answer(message: Message):
    # Check if user is in an active game and question is written
    user_id = message.from_user.id
    room = game_mgr.get_user_room(user_id)
    if not room or room.status != "playing":
        return
    
    if room.current_q_index < len(room.questions):
        q = room.questions[room.current_q_index]
        if q["type"] == "written":
            res = await room.submit_answer(user_id, message.text.strip())
            if res.get("is_correct"):
                await message.reply(f"✓ <b>TO'G'RI!</b> +{res['points']} ball! 🎉", parse_mode="HTML")
            else:
                await message.reply(f"❌ <b>NOTO'G'RI!</b> -1 ball jarima.\nTo'g'ri javob: <b>{res['correct_answer']}</b>", parse_mode="HTML")

# Broadcast callback connecting Game Engine to Telegram chat messages
def attach_room_bot_listener(room, bot: Bot):
    async def on_state_change(r, event_type, data):
        try:
            if event_type == "new_question":
                q = data
                q_num = r.current_q_index + 1
                q_total = len(r.questions)
                
                is_choice = (q["type"] == "choice")
                type_name = "4 talik Test (⏱️ 10 soniya)" if is_choice else "Yozma Savol (⏱️ 20 soniya)"
                pron_str = f" [{q['pron']}]" if q.get('pron') else ""

                text = (
                    f"⚔️ <b>SAVOL {q_num} / {q_total}</b> ({type_name})\n\n"
                    f"So'z: <b>{q['en']}</b>{pron_str}\n\n"
                )
                if is_choice:
                    text += "To'g'ri tarjimani tanlang:"
                    reply_markup = kb.get_question_inline(q["options"], r.code, r.current_q_index)
                else:
                    text += "✍️ <i>Ushbu so'zning o'zbekcha ma'nosini chatga yozib yuboring:</i>"
                    reply_markup = None

                for user_id in list(r.players.keys()):
                    try:
                        msg = await bot.send_message(user_id, text, reply_markup=reply_markup, parse_mode="HTML")
                        user_active_msg[user_id] = msg.message_id
                    except Exception:
                        pass

            elif event_type == "round_ended":
                q = data
                text = (
                    f"⏱️ <b>Savol yakunlandi!</b>\n"
                    f"So'z: <b>{q['en']}</b> ➔ To'g'ri javob: <b>{q['uz']}</b>\n\n"
                    f"<b>Hozirgi hisob:</b>\n"
                )
                for p in r.players.values():
                    text += f"• {p.first_name}: <b>{p.score} ball</b>\n"
                
                for user_id in list(r.players.keys()):
                    try:
                        await bot.send_message(user_id, text, parse_mode="HTML")
                    except Exception:
                        pass

            elif event_type == "game_over":
                leaderboard = data
                text = "🏁 <b>O'YIN YAKUNLANDI! G'OLIBLAR:</b>\n\n"
                for item in leaderboard:
                    text += f"{item['medal']} <b>{item['name']}</b> — <b>{item['score']} ball</b>\n"
                
                for user_id, p in r.players.items():
                    user_text = text
                    if p.mistakes:
                        user_text += "\n❌ <b>Sizning xatolaringiz:</b>\n"
                        for m in p.mistakes[:6]:
                            user_text += f"• {m['en']} ➔ To'g'ri: <i>{m['correct']}</i>\n"
                    
                    try:
                        await bot.send_message(
                            user_id,
                            user_text,
                            reply_markup=kb.get_main_keyboard(WEBAPP_URL),
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Error in on_state_change: {e}")

    room.on_state_change = on_state_change
