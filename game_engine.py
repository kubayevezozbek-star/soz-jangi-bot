import asyncio
import time
import random
import logging
from typing import Dict, List, Optional, Any
from vocab_manager import vocab_mgr
import database as db

logger = logging.getLogger(__name__)

class Player:
    def __init__(self, user_id: int, first_name: str, username: str = ""):
        self.user_id = user_id
        self.first_name = first_name
        self.username = username
        self.score = 0
        self.is_ready = False
        self.answered = False
        self.last_answer = None
        self.last_is_correct = None
        self.last_points = 0
        self.mistakes = []
        self.ws = None  # WebSocket connection if using Mini App

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "first_name": self.first_name,
            "username": self.username,
            "score": self.score,
            "is_ready": self.is_ready,
            "answered": self.answered,
            "last_is_correct": self.last_is_correct,
            "last_points": self.last_points
        }

class Room:
    def __init__(self, code: str, host_id: int, host_name: str, host_username: str, max_players: int = 2, day: int = 1):
        self.code = code
        self.host_id = host_id
        self.max_players = max_players
        self.day = day
        self.status = "lobby"  # 'lobby', 'playing', 'finished'
        self.created_at = time.time()
        
        self.players: Dict[int, Player] = {}
        self.add_player(host_id, host_name, host_username)
        # Host is automatically ready
        self.players[host_id].is_ready = True
        
        self.questions: List[Dict[str, Any]] = []
        self.current_q_index = 0
        self.q_start_time = 0.0
        self.timer_task: Optional[asyncio.Task] = None
        self.correct_order_count = 0
        self.on_state_change = None  # Callback for bot message updates

    def add_player(self, user_id: int, first_name: str, username: str = "") -> Optional[Player]:
        if user_id in self.players:
            return self.players[user_id]
        if len(self.players) >= self.max_players and self.max_players > 1:
            return None
        if self.status != "lobby":
            return None
        
        p = Player(user_id, first_name, username)
        self.players[user_id] = p
        return p

    def remove_player(self, user_id: int):
        if user_id in self.players:
            del self.players[user_id]
            if user_id == self.host_id and self.players:
                # Reassign host
                self.host_id = next(iter(self.players.keys()))

    def all_ready(self) -> bool:
        if not self.players:
            return False
        # If solo mode (1 player), always ready
        if self.max_players == 1:
            return True
        return all(p.is_ready for p in self.players.values())

    def start_game(self, bot=None):
        if self.status != "lobby":
            return False
        
        # Generate questions
        self.questions = vocab_mgr.generate_quiz(day=self.day, count=10, mix_written=True)
        self.current_q_index = 0
        self.status = "playing"
        for p in self.players.values():
            p.score = 0
            p.mistakes = []
        
        asyncio.create_task(self.run_question_loop(bot))
        return True

    async def broadcast_ws(self, message: dict):
        for p in list(self.players.values()):
            if p.ws:
                try:
                    await p.ws.send_json(message)
                except Exception:
                    p.ws = None

    async def run_question_loop(self, bot=None):
        """Runs the battle rounds step-by-step with real-time timers and fast advance"""
        while self.current_q_index < len(self.questions):
            q = self.questions[self.current_q_index]
            self.correct_order_count = 0
            for p in self.players.values():
                p.answered = False
                p.last_answer = None
                p.last_is_correct = None
                p.last_points = 0
            
            self.q_start_time = time.time()
            time_limit = q["time_limit"]

            # Broadcast new question
            payload = {
                "type": "new_question",
                "room": self.get_summary(),
                "question": {
                    "number": self.current_q_index + 1,
                    "total": len(self.questions),
                    "type": q["type"],
                    "en": q["en"],
                    "pron": q.get("pron", ""),
                    "options": q.get("options", []),
                    "time_limit": time_limit
                }
            }
            await self.broadcast_ws(payload)
            if self.on_state_change:
                await self.on_state_change(self, "new_question", q)

            # Wait for either all players to answer or timer to expire
            elapsed = 0.0
            step = 0.2
            while elapsed < time_limit:
                # Check if all players answered
                if all(p.answered for p in self.players.values()):
                    # Short pause of 1.2 seconds so players can see the feedback
                    await asyncio.sleep(1.2)
                    break
                await asyncio.sleep(step)
                elapsed += step

            # Time is up or everyone answered!
            # For anyone who didn't answer in time, mark as unanswered (-1 penalty for missing)
            for p in self.players.values():
                if not p.answered:
                    p.answered = True
                    p.last_is_correct = False
                    p.last_points = -1
                    p.score = max(0, p.score - 1)
                    p.mistakes.append({
                        "en": q["en"],
                        "pron": q.get("pron", ""),
                        "correct": q["uz"],
                        "user_answer": "Vaqt tugadi ⏳"
                    })

            # Broadcast round result
            round_result = {
                "type": "round_ended",
                "question_number": self.current_q_index + 1,
                "correct_answer": q["uz"],
                "correct_option_index": q.get("correct_index", -1),
                "players": [p.to_dict() for p in self.players.values()]
            }
            await self.broadcast_ws(round_result)
            if self.on_state_change:
                await self.on_state_change(self, "round_ended", q)

            # Short intermission (2.5 seconds) before next question
            await asyncio.sleep(2.5)
            self.current_q_index += 1

        # All questions finished! End game.
        await self.finish_game()

    async def submit_answer(self, user_id: int, answer: str) -> dict:
        """Handles answer submission from a player"""
        if self.status != "playing":
            return {"error": "O'yin faol emas"}
        if user_id not in self.players:
            return {"error": "O'yinchi topilmadi"}
        
        player = self.players[user_id]
        if player.answered:
            return {"error": "Siz allaqachon javob berdingiz"}
        
        q = self.questions[self.current_q_index]
        is_correct = False
        
        answer_clean = answer.strip().lower()
        if q["type"] == "choice":
            # Compare with correct answer
            if answer_clean == q["correct"].strip().lower() or (
                q.get("options") and answer in q["options"] and q["options"].index(answer) == q["correct_index"]
            ):
                is_correct = True
        else:
            # Written question: check valid answers
            valid = [v.lower() for v in q["valid_answers"]]
            # Also allow partial/relaxed match
            if any(answer_clean == v or (len(answer_clean) > 3 and answer_clean in v) for v in valid):
                is_correct = True

        player.answered = True
        player.last_answer = answer
        player.last_is_correct = is_correct

        points = 0
        if is_correct:
            self.correct_order_count += 1
            # 1-to'g'ri: 5 bal, 2-to'g'ri: 4 bal, 3-to'g'ri: 3 bal, 4-chi: 2 bal, 5-6: 1 bal
            points = max(1, 6 - self.correct_order_count)
            player.score += points
        else:
            # Noto'g'ri javobga -1 jarima
            points = -1
            player.score = max(0, player.score - 1)
            player.mistakes.append({
                "en": q["en"],
                "pron": q.get("pron", ""),
                "correct": q["uz"],
                "user_answer": answer
            })
        
        player.last_points = points

        result = {
            "type": "answer_result",
            "user_id": user_id,
            "is_correct": is_correct,
            "points": points,
            "correct_answer": q["uz"],
            "correct_option_index": q.get("correct_index", -1),
            "new_score": player.score
        }

        # Send individual feedback
        if player.ws:
            try:
                await player.ws.send_json(result)
            except Exception:
                player.ws = None

        # Broadcast updated player states
        await self.broadcast_ws({
            "type": "player_answered",
            "user_id": user_id,
            "first_name": player.first_name,
            "all_answered": all(p.answered for p in self.players.values())
        })

        if self.on_state_change:
            await self.on_state_change(self, "player_answered", player)

        return result

    async def finish_game(self):
        self.status = "finished"
        
        # Sort players by score descending
        sorted_players = sorted(self.players.values(), key=lambda p: p.score, reverse=True)
        
        # Record stats in database
        for rank, p in enumerate(sorted_players, start=1):
            is_win = (rank == 1 and len(sorted_players) > 1 and p.score > 0)
            correct_count = 10 - len(p.mistakes)
            wrong_count = len(p.mistakes)
            await db.update_user_stats(
                user_id=p.user_id,
                score_delta=p.score,
                is_win=is_win,
                correct_delta=correct_count,
                wrong_delta=wrong_count
            )
            await db.record_game(
                room_id=self.code,
                user_id=p.user_id,
                day=self.day,
                score=p.score,
                rank=rank
            )

        leaderboard = []
        for rank, p in enumerate(sorted_players, start=1):
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            leaderboard.append({
                "rank": rank,
                "medal": medal,
                "user_id": p.user_id,
                "name": p.first_name,
                "score": p.score,
                "mistakes_count": len(p.mistakes),
                "mistakes": p.mistakes
            })

        final_data = {
            "type": "game_over",
            "room_code": self.code,
            "day": self.day,
            "leaderboard": leaderboard
        }
        await self.broadcast_ws(final_data)
        if self.on_state_change:
            await self.on_state_change(self, "game_over", leaderboard)

    def get_summary(self):
        return {
            "code": self.code,
            "host_id": self.host_id,
            "max_players": self.max_players,
            "day": self.day,
            "status": self.status,
            "player_count": len(self.players),
            "players": [p.to_dict() for p in self.players.values()]
        }

class GameManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.user_to_room: Dict[int, str] = {}

    def create_room(self, host_id: int, host_name: str, host_username: str, max_players: int = 2, day: int = 1) -> Room:
        # Generate 6-digit room code
        while True:
            code = str(random.randint(100000, 999999))
            if code not in self.rooms:
                break
        
        room = Room(code, host_id, host_name, host_username, max_players, day)
        self.rooms[code] = room
        self.user_to_room[host_id] = code
        return room

    def get_room(self, code: str) -> Optional[Room]:
        return self.rooms.get(code)

    def get_user_room(self, user_id: int) -> Optional[Room]:
        code = self.user_to_room.get(user_id)
        if code:
            return self.rooms.get(code)
        return None

    def join_room(self, code: str, user_id: int, first_name: str, username: str = "") -> Optional[Room]:
        room = self.get_room(code)
        if not room:
            return None
        
        p = room.add_player(user_id, first_name, username)
        if p:
            self.user_to_room[user_id] = code
            return room
        return None

    def leave_room(self, user_id: int):
        code = self.user_to_room.pop(user_id, None)
        if code and code in self.rooms:
            room = self.rooms[code]
            room.remove_player(user_id)
            if not room.players:
                del self.rooms[code]

game_mgr = GameManager()
