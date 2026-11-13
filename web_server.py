import json
import logging
from aiohttp import web, WSMsgType
from config import BASE_DIR
from game_engine import game_mgr
from vocab_manager import vocab_mgr
import database as db

logger = logging.getLogger(__name__)

async def handle_index(request):
    index_file = BASE_DIR / "web" / "templates" / "index.html"
    return web.FileResponse(index_file)

async def handle_css(request):
    css_file = BASE_DIR / "web" / "style.css"
    return web.FileResponse(css_file, headers={"Content-Type": "text/css"})

async def handle_js(request):
    js_file = BASE_DIR / "web" / "app.js"
    return web.FileResponse(js_file, headers={"Content-Type": "application/javascript"})

async def handle_create_room(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id"))
        first_name = data.get("first_name", "O'yinchi")
        username = data.get("username", "")
        max_players = int(data.get("max_players", 2))
        day = int(data.get("day", 1))
        q_mode = str(data.get("q_mode", "choice"))
        if q_mode not in ("choice", "written"):
            q_mode = "choice"
        time_limit = int(data.get("time_limit", 15))
        if time_limit not in (10, 15, 20, 25, 30):
            time_limit = 15

        await db.get_or_create_user(user_id, username, first_name)
        room = game_mgr.create_room(user_id, first_name, username, max_players, day, q_mode, time_limit)
        return web.json_response({"success": True, "code": room.code, "room": room.get_summary()})
    except Exception as e:
        logger.error(f"Error creating room: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=400)

async def handle_join_room(request):
    try:
        data = await request.json()
        code = str(data.get("code")).strip()
        user_id = int(data.get("user_id"))
        first_name = data.get("first_name", "O'yinchi")
        username = data.get("username", "")

        await db.get_or_create_user(user_id, username, first_name)
        room = game_mgr.join_room(code, user_id, first_name, username)
        if room:
            await room.broadcast_ws({
                "type": "room_update",
                "players": [p.to_dict() for p in room.players.values()]
            })
            return web.json_response({"success": True, "room": room.get_summary()})
        else:
            return web.json_response({"success": False, "error": "Xona topilmadi yoki to'lgan"}, status=404)
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=400)

async def handle_get_room(request):
    code = request.match_info.get("code")
    room = game_mgr.get_room(code)
    if room:
        return web.json_response({"success": True, "room": room.get_summary()})
    return web.json_response({"success": False, "error": "Xona topilmadi"}, status=404)

async def handle_get_user(request):
    user_id = int(request.match_info.get("user_id"))
    u = await db.get_user(user_id)
    if u:
        return web.json_response(u)
    return web.json_response({"user_id": user_id, "score": 0, "games_played": 0, "wins": 0})

async def handle_get_user_mistakes(request):
    user_id = int(request.match_info.get("user_id"))
    # Return random/recent sample of words to review
    sample_words = vocab_mgr.all_words[:12]
    return web.json_response(sample_words)

async def handle_get_leaderboard(request):
    top = await db.get_top_users(20)
    return web.json_response(top)

async def handle_vocab_summary(request):
    summary = []
    for day in vocab_mgr.get_available_days():
        words = vocab_mgr.get_day_words(day)
        sample = ", ".join(w["en"] for w in words[:3])
        if len(words) > 3:
            sample += "..."
        summary.append({
            "day": day,
            "count": len(words),
            "sample": sample
        })
    return web.json_response(summary)

async def handle_vocab_day(request):
    day = int(request.match_info.get("day", 1))
    words = vocab_mgr.get_day_words(day)
    return web.json_response(words)

async def handle_websocket(request):
    room_code = request.match_info.get("room_code")
    user_id = int(request.match_info.get("user_id"))

    room = game_mgr.get_room(room_code)
    if not room or user_id not in room.players:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_json({"type": "error", "message": "Xona topilmadi"})
        await ws.close()
        return ws

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    player = room.players[user_id]
    player.ws = ws

    logger.info(f"WebSocket connected: User {user_id} in Room {room_code}")

    await ws.send_json({
        "type": "room_update",
        "room": room.get_summary(),
        "players": [p.to_dict() for p in room.players.values()]
    })

    # If game is already active, immediately deliver current question
    if room.status == "playing" and room.current_q_index < len(room.questions):
        q = room.questions[room.current_q_index]
        import time as _t
        remaining = max(1.0, q["time_limit"] - (_t.time() - room.q_start_time))
        await ws.send_json({
            "type": "new_question",
            "room": room.get_summary(),
            "question": {
                "number": room.current_q_index + 1,
                "total": len(room.questions),
                "type": q["type"],
                "en": q["en"],
                "pron": q.get("pron", ""),
                "options": q.get("options", []),
                "time_limit": remaining
            }
        })

    await room.broadcast_ws({
        "type": "room_update",
        "players": [p.to_dict() for p in room.players.values()]
    })

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                mtype = data.get("type")

                if mtype == "start_game":
                    player.is_ready = True
                    if room.status == "lobby":
                        if user_id == room.host_id or room.all_ready():
                            room.start_game()
                        else:
                            await room.broadcast_ws({
                                "type": "room_update",
                                "players": [p.to_dict() for p in room.players.values()]
                            })

                elif mtype == "submit_answer":
                    answer = data.get("answer", "")
                    await room.submit_answer(user_id, answer)

            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                break
    finally:
        player.ws = None
        logger.info(f"WebSocket disconnected: User {user_id}")

    return ws

def create_web_app():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/style.css", handle_css)
    app.router.add_get("/app.js", handle_js)
    app.router.add_get("/ws/{room_code}/{user_id}", handle_websocket)
    app.router.add_post("/api/room/create", handle_create_room)
    app.router.add_post("/api/room/join", handle_join_room)
    app.router.add_get("/api/room/{code}", handle_get_room)
    app.router.add_get("/api/user/{user_id}", handle_get_user)
    app.router.add_get("/api/user/{user_id}/mistakes", handle_get_user_mistakes)
    app.router.add_get("/api/leaderboard", handle_get_leaderboard)
    app.router.add_get("/api/vocab/summary", handle_vocab_summary)
    app.router.add_get("/api/vocab/day/{day}", handle_vocab_day)

    static_dir = BASE_DIR / "web" / "static"
    if static_dir.exists():
        app.router.add_static("/static/", path=str(static_dir), name="static")

    return app
