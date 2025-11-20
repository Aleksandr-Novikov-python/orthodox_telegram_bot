def load_bad_words(filename="bad_words.txt") -> set[str]:
    with open(filename, "r", encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}
    
BAD_WORDS = load_bad_words()
MAX_VIOLATIONS = 3
BAN_DURATION = 86400 
ADMIN_LOG_CHAT_ID = -1003450027830