"""«Новый депозит» новой карточкой-чеком (зеленая, от 1000 $ - золотая).

python3 patch_deposit_card.py [/root/tg_bot]

Скачивает из репозитория emerald_cards/deposit.py, фоны и шрифты, проверяет, что
карточка рисуется, и переключает на нее _send_deposit_card в utils.py.
Если новая карточка не нарисуется, бот пошлет старую, а если и она нет - текст.
Копия старого файла: utils.py.bak_dep
"""
import os, re, shutil, py_compile, sys, urllib.request

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/root/tg_bot"
UTILS = f"{ROOT}/utils.py"
RAW = "https://raw.githubusercontent.com/biscuits67/emrld/claude/elegant-johnson-ujpfw7/bot/"
FILES = [
    "emerald_cards/deposit.py",
    "emerald_cards/assets/deposit/emerald.jpg",
    "emerald_cards/assets/deposit/gold.jpg",
    "emerald_cards/assets/deposit/layout.json",
    "emerald_cards/assets/fonts/Inter-ExtraBold.otf",
    "emerald_cards/assets/fonts/Inter-Bold.otf",
    "emerald_cards/assets/fonts/Inter-SemiBold.otf",
]
OLD_CALL = "cards.new_deposit(worker, int(float(amount)))"

HELPER = '''


# =============================================
# 🧾 НОВЫЙ ДЕПОЗИТ: КАРТОЧКА-ЧЕК
# =============================================

_METHOD = re.compile(r"\\b(USDT|USDC|BTC|ETH|LTC|TRX|TON|SOL|BNB|XMR|DOGE)\\b(?:[\\s(-]*(TRC-?20|ERC-?20|BEP-?20|SPL|TON))?", re.I)


def _deposit_card_info(worker, amount, text):
    """Номер, метод, выплата воркеру и итог дня - то, что удалось найти в базе и тексте"""
    info = {}
    try:
        m = _METHOD.search(re.sub(r"<[^>]+>", " ", str(text)))
        if m:
            info["method"] = " ".join(p.upper().replace("-", "") for p in m.groups() if p)
    except Exception:
        pass
    worker_id = None
    try:
        nick = str(worker or "").lstrip("@")
        for col in ("username", "tg_username"):
            cursor.execute(f"SELECT user_id, percentage FROM {DB.users_table} WHERE {col} = ? LIMIT 1", (nick,))
            row = cursor.fetchone()
            if row:
                worker_id, pct = row
                if pct not in (None, ""):
                    info["share"] = float(pct)
                    info["payout"] = round(float(amount) * float(pct) / 100, 2)
                break
    except Exception:
        pass
    try:
        cursor.execute("SELECT rowid, worker_id, amountUSD FROM deposits ORDER BY rowid DESC LIMIT 1")
        last = cursor.fetchone()
        saved = bool(last) and abs(float(last[2] or 0) - float(amount)) < 0.01 and (worker_id is None or str(last[1]) == str(worker_id))
        info["number"] = (last[0] if saved else (last[0] + 1)) if last else 1
        cursor.execute("SELECT COALESCE(SUM(amountUSD), 0) FROM deposits WHERE date = ?", (datetime.now().strftime("%Y-%m-%d"),))
        total = float(cursor.fetchone()[0] or 0)
        info["day_total"] = total if saved else total + float(amount)
    except Exception:
        pass
    return info


def _deposit_photo(worker, amount, text):
    """Новая карточка; если не вышло - старая"""
    try:
        from emerald_cards.deposit import new_deposit_card
        return new_deposit_card(worker, float(amount), **_deposit_card_info(worker, amount, text))
    except Exception as err:
        create_logger("utils").error(f"newDeposit: new card error: {err}")
        return cards.new_deposit(worker, int(float(amount)))
'''

src = open(UTILS, encoding="utf-8").read()
if "def _deposit_photo" in src:
    print("Новая карточка уже подключена, utils.py не трогаю (файлы карточки обновлены)")
if OLD_CALL not in src and "def _deposit_photo" not in src:
    print("НЕ ПОЛУЧИЛОСЬ: в utils.py нет _send_deposit_card с карточкой. Сначала нужен patch_cards_3.py. Ничего не изменено.")
    sys.exit(1)

# 1. файлы карточки
for f in FILES:
    dst = os.path.join(ROOT, f)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        urllib.request.urlretrieve(RAW + f, dst + ".part")
        os.replace(dst + ".part", dst)
    except Exception as err:
        print(f"НЕ ПОЛУЧИЛОСЬ скачать {f}: {err}. utils.py не изменен.")
        sys.exit(1)

# 2. пробная карточка
sys.path.insert(0, ROOT)
try:
    from emerald_cards.deposit import new_deposit_card
    test = os.path.join(ROOT, "deposit_test.jpg")
    open(test, "wb").write(new_deposit_card("test", 647, 1284, "USDT TRC20", 420.55, 65, 5397))
except Exception as err:
    print(f"НЕ ПОЛУЧИЛОСЬ нарисовать карточку: {err!r}. utils.py не изменен.")
    sys.exit(1)

if "def _deposit_photo" in src:
    print(f"Пробная карточка: {test}")
    sys.exit(0)

# 3. utils.py
new = src.replace(OLD_CALL, "_deposit_photo(worker, amount, text)", 1).rstrip() + HELPER
if not re.search(r"^import re\b|^import .*\bre\b", new, re.M):
    new = "import re\n" + new
shutil.copy(UTILS, UTILS + ".bak_dep")
open(UTILS, "w", encoding="utf-8").write(new)
try:
    py_compile.compile(UTILS, doraise=True)
except py_compile.PyCompileError as err:
    shutil.copy(UTILS + ".bak_dep", UTILS)
    print("НЕ ПОЛУЧИЛОСЬ (ошибка в коде), utils.py возвращен как был:")
    print(err)
    sys.exit(1)
print("ГОТОВО: «Новый депозит» теперь новой карточкой.")
print(f"Пробная карточка: {test}")
print("Копия старого файла: utils.py.bak_dep")
