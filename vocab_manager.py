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

    def generate_quiz(self, day: int, count: int = 10, mix_written: bool = True):
        """
        Generates a round of questions for a battle.
        Mix of 4-choice test questions and written questions.
        """
        day_words = self.get_day_words(day)
        if not day_words:
            # Fallback to random words
            day_words = random.sample(self.all_words, min(count, len(self.all_words)))

        # Shuffle words of this day
        selected_words = random.sample(day_words, min(count, len(day_words)))
        
        # Decide how many written questions: e.g. 30% written, 70% multiple choice
        # If count is 10: 7 multiple choice (10s each), 3 written (20s each)
        questions = []
        for i, word in enumerate(selected_words):
            # If mix_written is True, every 3rd question is written
            q_type = "written" if (mix_written and (i % 3 == 2)) else "choice"
            
            # 4-choice question:
            if q_type == "choice":
                # Decide direction: mostly English -> Uzbek
                # Correct answer
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
                    "time_limit": 10  # 10 soniya test uchun
                })
            else:
                # Written question: 20 soniya
                questions.append({
                    "id": i + 1,
                    "type": "written",
                    "word_id": word["id"],
                    "en": word["en"],
                    "pron": word.get("pron", ""),
                    "uz": word["uz"],
                    "correct": word["primary_uz"],
                    "valid_answers": [w.strip().lower() for w in word["uz"].replace(";", ",").split(",") if w.strip()],
                    "time_limit": 20  # 20 soniya yozma uchun
                })

        return questions

vocab_mgr = VocabManager()
