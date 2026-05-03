import re

def extract_kz_phones(text: str) -> set:
    """Извлекает и нормализует казахстанские номера из текста."""
    if not text:
        return set()
    
    raw_pattern = r'(?:\+?7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}'
    raw_matches = re.findall(raw_pattern, text)
    
    clean_phones = set()
    for match in raw_matches:
        digits_only = re.sub(r'\D', '', match)
        if digits_only.startswith('8'):
            digits_only = '7' + digits_only[1:]
        
        if len(digits_only) == 11 and digits_only.startswith('7'):
            clean_phones.add(f"+{digits_only}")
            
    return clean_phones