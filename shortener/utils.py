import hashlib

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def base62_encode(num: int) -> str:
    if num < 0:
        raise ValueError("num must be non-negative")
    if num == 0:
        return ALPHABET[0]
    out = []
    while num:
        num, rem = divmod(num, 62)
        out.append(ALPHABET[rem])
    return "".join(reversed(out))


def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()


def parse_user_agent(ua: str):
    ua = (ua or "").lower()
    device = "mobile" if ("mobile" in ua or "android" in ua or "iphone" in ua) else "desktop"
    browser = "other"
    for name, key in [("edge", "edg"), ("chrome", "chrome"), ("firefox", "firefox"), ("safari", "safari")]:
        if key in ua:
            browser = name
            break
    return device, browser