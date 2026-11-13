import json
import random
from config import WORDS_FILE

class VocabManager:
    def __init__(self):
        self.days_data = {}
        self.all_words = []
        self.total_days = 96
        self.load_words()

    def load_words(self):
        with open(WORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.days_data = {int(k): v for k, v in data.get("days", {}).items()}
        self.total_days = data.get("total_days", 96)
        self.all_words = []
        for d, words in self.days_data.items():
            self.all_words.extend(words)

    def get_day_words(self, day: int):
        return self.days_data.get(day, [])

    def get_available_days(self):
        return sorted(list(self.days_data.keys()))

    def generate_quiz(self, day: int = 1, count: int = 10, q_mode: str = "choice", time_limit: int = 15):
        """
        Generates a round of questions for a battle.
        q_mode: 'choice' (strictly 4-choice tests) or 'written' (strictly written translation)
        time_limit: 10, 15, 20, 25, or 30 seconds per question.
        NO MIXING when user chooses a specific mode!
        """
        day_words = self.get_day_words(day)
        if not day_words:
            # Fallback to random words
            day_words = random.sample(self.all_words, min(count, len(self.all_words)))

        # Shuffle words of this day
        selected_words = random.sample(day_words, min(count, len(day_words)))
        
        # Strictly enforce choice or written based on user selection
        is_all_written = (q_mode == "written")
        
        questions = []
        for i, word in enumerate(selected_words):
            if not is_all_written:
                # 4-choice question:
                correct_uz = word["primary_uz"]
                
                # Pick 3 distractors from the same day first for maximum challenge!
                other_words = [w for w in day_words if w["id"] != word["id"] and w["primary_uz"] != correct_uz]
                if len(other_words) < 3:
                    # Pick from all words
                    extra = [w for w in self.all_words if w["id"] != word["id"] and w["primary_uz"] != correct_uz]
                    other_words.extend(extra)
                
                distractors = random.sample(other_words, 3)
                options = [correct_uz] + [d["primary_uz"] for d in distractors]
                random.shuffle(options)
                correct_index = options.index(correct_uz)

                questions.append({
                    "id": i + 1,
                    "type": "choice",
                    "word_id": word["id"],
                    "en": word["en"],
                    "pron": word.get("pron", ""),
                    "uz": word["uz"],
                    "correct": correct_uz,
                    "options": options,
                    "correct_index": correct_index,
                    "time_limit": time_limit
                })
            else:
                # Written question: user types in the translation
                valid_answers = [w.strip().lower() for w in word["uz"].replace(";", ",").split(",") if w.strip()]
                if word["primary_uz"].lower() not in valid_answers:
                    valid_answers.append(word["primary_uz"].lower())

                questions.append({
                    "id": i + 1,
                    "type": "written",
                    "word_id": word["id"],
                    "en": word["en"],
                    "pron": word.get("pron", ""),
                    "uz": word["uz"],
                    "correct": word["primary_uz"],
                    "valid_answers": valid_answers,
                    "time_limit": time_limit
                })

        return questions

vocab_mgr = VocabManager()
