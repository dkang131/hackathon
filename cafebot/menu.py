"""Drink menu (loaded from JSON) and mood detection data."""

from .models import Drink
from .menu_manager import load_menu, save_menu

# Load menu from data/menu.json at import time
DRINK_MENU: list[Drink] = load_menu()

MOOD_KEYWORDS: dict[str, list[str]] = {
    # English
    "tired": [
        "tired", "exhausted", "sleepy", "drained", "wiped out", "no energy", "burnt out", "dead",
        # Indonesian / Malay
        "lelah", "capek", "ngantuk", "lesu", "habis tenaga",
        # Chinese (simplified)
        "累", "疲倦", "困", "没精神",
        # Japanese
        "疲れた", "眠い", "だるい", "眠たい",
        # Korean
        "피곤해", "졸려", "지쳤어",
    ],
    "stressed": [
        "stressed", "anxious", "overwhelmed", "nervous", "worried", "panic", "pressure",
        "stres", "cemas", "khawatir", "panik",
        "压力", "焦虑", "紧张",
        "stress", "不安", "緊張",
        "스트레스", "불안해",
    ],
    "sad": [
        "sad", "down", "depressed", "blue", "melancholy", "miserable", "heartbroken", "crying", "tear",
        "sedih", "murung", "kecewa", "nangis",
        "难过", "伤心", "想哭", "沮丧",
        "悲しい", "落ち込んでる", "泣きたい",
        "슬퍼", "우울해", "눈물",
    ],
    "frustrated": [
        "frustrated", "angry", "mad", "annoyed", "irritated", "pissed", "furious", "rage",
        "frustasi", "marah", "kesal", "sebal",
        "生气", "烦", "恼火",
        "イライラ", "怒ってる", "むかつく",
        "화났어", "짜증나",
    ],
    "bored": [
        "bored", "unmotivated", "lazy", "nothing to do", "blah", "meh", "dull",
        "bosan", "malas", "ga ada kerjaan",
        "无聊", "没劲", "懒得",
        "退屈", "やる気ない", "暇",
        "심심해", "지루해",
    ],
    "nostalgic": [
        "nostalgic", "homesick", "missing", "remember", "used to", "old days", "memory",
        "kangen", "rindu", "masa lalu",
        "怀旧", "想家", "回忆",
        "懐かしい", "故郷",
        "그리워", "추억",
    ],
    "confident": [
        "confident", "focused", "determined", "productive", "sharp", "ready", "crushing it",
        "percaya diri", "fokus", "semangat",
        "自信", "专注", "状态好",
        "自信ある", "集中してる", "調子いい",
        "자신감", "집중",
    ],
    "happy": [
        "happy", "celebrating", "excited", "joyful", "cheerful", "grateful", "love", "amazing day",
        "senang", "bahagia", "gembira", "hebat",
        "开心", "高兴", "兴奋", "快乐",
        "嬉しい", "楽しい", "幸せ",
        "행복해", "기분좋아",
    ],
    "sick": [
        "sick", "under the weather", "cold", "flu", "sore throat", "not feeling well", "achy",
        "sakit", "demam", "pilek", "tidak enak badan",
        "生病", "感冒", "不舒服", "嗓子疼",
        "具合悪い", "風邪", "喉痛い",
        "아파", "감기", "몸이 안좋아",
    ],
    "playful": [
        "playful", "fun", "youthful", "bouncy", "hyper", "wanna have fun",
        "seru", "lucu", "fun",
        "好玩", "想玩",
        "楽しみたい", "遊びたい",
        "놀고싶어", "신나",
    ],
}
