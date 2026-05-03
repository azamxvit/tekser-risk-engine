SCAM_DICT = {
    "fake_police": ["кнб", "мвд", "полици", "следовател", "допрос", "майор", "капитан"],
    "bank_fraud": ["каспи", "kaspi", "халык", "halyk", "кредит", "перевод", "счет", "безопасност"],
    "spam": ["стоматолог", "опрос", "робот", "курсы", "бесплатн"],
    "investment": ["инвестици", "крипт", "брокер", "доход", "биржа"]
}

def get_scam_type(text: str) -> str:
    """Определяет тип мошенничества по ключевым словам."""
    text_lower = text.lower()
    for scam_type, keywords in SCAM_DICT.items():
        if any(kw in text_lower for kw in keywords):
            return scam_type
    return "other"