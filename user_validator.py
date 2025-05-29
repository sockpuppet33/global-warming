import re

def validate_username(username):
    return bool(re.fullmatch(r'[A-Za-z0-9_-]+', username)) and len(username) <= 25

def validate_password(pw):
    if len(pw) < 8:
        return False
    if not re.search(r'[A-Z]', pw):
        return False
    if not re.search(r'[a-z]', pw):
        return False
    if not re.search(r'\d', pw):
        return False
    if not re.search(r'[^\w\s]', pw):
        return False
    return True
