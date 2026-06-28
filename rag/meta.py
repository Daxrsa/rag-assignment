import re

# Short, history-dependent inputs that ask the assistant to confirm or repeat its previous statement.
# These must NOT be rewritten into a claim-verification question.
META_QUESTION_PATTERNS = [
    r"^(are |you )?(really |absolutely |totally |actually )?sure\??$",
    r"^are you (really |absolutely |totally |actually )?sure(\?| .*)?$",
    r"^really\??$",
    r"^seriously\??$",
    r"^honestly\??$",
    r"^is that (right|true|correct|so)\??$",
    r"^that('?s| is) (right|true|correct)\??$",
    r"^can you confirm(\?| .*)?$",
    r"^please confirm(\?| .*)?$",
    r"^(say|repeat) that again\??$",
    r"^are you certain(\?| .*)?$",
    r"^(but )?are you (really |absolutely |totally )?sure(\?| .*)?$",
]


def is_meta_question(text: str) -> bool:
    t = text.strip().lower()
    return any(re.match(p, t) for p in META_QUESTION_PATTERNS)
