"""Premium emoji from the emerald_by_EmrldWork_bot pack.

Use in messages with parse_mode="HTML":
    await bot.send_message(user_id, f"{E.CARD} Выплата совершена", parse_mode="HTML")
Use on buttons via the raw id:
    InlineKeyboardButton(text="Кошелек", callback_data="w", icon_custom_emoji_id=ID.PURSE)
"""


class ID:
    MONEY_WINGS = "5355136950330239138"  # 💸
    GEM = "5352852809412814624"          # 💎
    OK = "5352800187473505485"           # ✅
    NO = "5352818342300266748"           # ❌
    STOP = "5355313696824406496"         # ⛔
    CARD = "5352930977817605054"         # 💳
    STAR = "5354839412175839090"         # ⭐
    BOLT = "5353027949589213920"         # ⚡
    USERS = "5355110922828426195"        # 👥
    MONEY_BAG = "5352903391242661158"    # 💰
    CHART = "5354825041215268668"        # 📊
    LIKE = "5354956952545830850"         # 👍
    PLANE = "5352937235584952216"        # ✈
    CHAT = "5355122484880388192"         # 💬
    LINK = "5353075915783974323"         # 🔗
    BOOK = "5352822933620305141"         # 📕
    INFO = "5352603185913574333"         # ℹ
    MEDAL = "5352917349886373161"        # 🥇
    CROWN = "5352914459373382499"        # 👑
    CALENDAR = "5352613068633320647"     # 📅
    HOURGLASS = "5352780988969693792"    # ⏳
    BELL = "5352848974007021193"         # 🔔
    CROWN_2 = "5352533551608805264"      # 👑
    GEM_2 = "5353006470457769622"        # 💎
    PURSE = "5354817993173936715"        # 👛


def _e(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


class E:
    MONEY_WINGS = _e(ID.MONEY_WINGS, "💸")
    GEM = _e(ID.GEM, "💎")
    OK = _e(ID.OK, "✅")
    NO = _e(ID.NO, "❌")
    STOP = _e(ID.STOP, "⛔")
    CARD = _e(ID.CARD, "💳")
    STAR = _e(ID.STAR, "⭐")
    BOLT = _e(ID.BOLT, "⚡")
    USERS = _e(ID.USERS, "👥")
    MONEY_BAG = _e(ID.MONEY_BAG, "💰")
    CHART = _e(ID.CHART, "📊")
    LIKE = _e(ID.LIKE, "👍")
    PLANE = _e(ID.PLANE, "✈")
    CHAT = _e(ID.CHAT, "💬")
    LINK = _e(ID.LINK, "🔗")
    BOOK = _e(ID.BOOK, "📕")
    INFO = _e(ID.INFO, "ℹ")
    MEDAL = _e(ID.MEDAL, "🥇")
    CROWN = _e(ID.CROWN, "👑")
    CALENDAR = _e(ID.CALENDAR, "📅")
    HOURGLASS = _e(ID.HOURGLASS, "⏳")
    BELL = _e(ID.BELL, "🔔")
    CROWN_2 = _e(ID.CROWN_2, "👑")
    GEM_2 = _e(ID.GEM_2, "💎")
    PURSE = _e(ID.PURSE, "👛")
