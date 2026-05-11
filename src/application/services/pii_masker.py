import re

# Regex for basic email matching
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

# Regex for US phone numbers (including 7-digit and 10-digit formats)
PHONE_PATTERN = re.compile(
    r'(\+?\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}|\b\d{3}[\s.-]?\d{4}\b'
)

def mask_pii(text: str) -> str:
    """Redact emails and phone numbers from the given text."""
    if not text:
        return text
    
    # Mask emails
    text = EMAIL_PATTERN.sub('[REDACTED EMAIL]', text)
    
    # Mask phone numbers
    text = PHONE_PATTERN.sub('[REDACTED PHONE]', text)
    
    return text
