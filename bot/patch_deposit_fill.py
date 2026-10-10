"""Карточка «Новый депозит»: заполняет Метод, Выплату воркеру, Номер и Итог дня.

python3 patch_deposit_fill.py [/root/tg_bot]

1) utils.py: если метода нет в тексте - берет его из последней записи в deposits
   (колонки currency/coin/method/network...); процент воркера - еще и по worker_id.
2) fake_activity/engine.py: фейковые депозиты получают метод, выплату (по проценту
   воркера или 60-70%), сквозной номер и итог дня (храним в fake_activity/card_state.json).
Копии старых файлов: *.bak_fill
"""
import re, shutil, py_compile, sys, os

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/root/tg_bot"
UTILS = f"{ROOT}/utils.py"
ENGINE = f"{ROOT}/fake_activity/engine.py"

UTILS_ANCHOR = "    return info\n\n\ndef _deposit_photo"
UTILS_EXTRA = '''    # метод и процент из записи о депозите, если в тексте/по нику не нашлись
    try:
        if saved and ("method" not in info or "share" not in info):
            cursor.execute("PRAGMA table_info(deposits)")
            cols = [r[1] for r in cursor.fetchall()]
            mcols = [c for c in cols if c.lower() in ("method", "payment_method", "currency", "coin", "crypto",
                                                      "asset", "token", "network", "chain")]
            if "method" not in info and mcols:
                cursor.execute(f"SELECT {', '.join(mcols)} FROM deposits WHERE rowid = ?", (last[0],))
                row = cursor.fetchone() or ()
                parts = [str(v).strip().upper() for v in row if v not in (None, "") and str(v).strip()]
                if parts:
                    info["method"] = " ".join(dict.fromkeys(parts))
            if "share" not in info and last[1]:
                cursor.execute(f"SELECT percentage FROM {DB.users_table} WHERE user_id = ?", (last[1],))
                row = cursor.fetchone()
                if row and row[0] not in (None, ""):
                    info["share"] = float(row[0])
                    info["payout"] = round(float(amount) * float(row[0]) / 100, 2)
    except Exception:
        pass
'''

ENGINE_HELPER = '''


_FAKE_METHODS = [("USDT TRC20", 40), ("USDT ERC20", 10), ("BTC", 15), ("ETH", 10),
                 ("SOL", 12), ("LTC", 6), ("TON", 7)]


def _fake_card_info(worker, amount):
    """Метод, выплата, номер и итог дня для фейкового депозита"""
    import json, os, random
    from datetime import datetime
    info = {}
    try:
        import utils
        info = utils._deposit_card_info(worker, amount, "")
    except Exception:
        pass
    info["method"] = random.choices([m for m, _ in _FAKE_METHODS], [w for _, w in _FAKE_METHODS])[0]
    if "share" not in info:
        info["share"] = random.choice([60, 65, 70])
        info["payout"] = round(float(amount) * info["share"] / 100, 2)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "card_state.json")
    try:
        state = json.load(open(path, encoding="utf-8"))
    except Exception:
        state = {}
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("date") != today:
        state["date"], state["fake_total"] = today, 0
    number = max(int(state.get("number") or random.randint(140, 320)) + 1, int(info.get("number") or 0))
    real_total = float(info.get("day_total") or float(amount))
    info["number"] = number
    info["day_total"] = round(real_total + float(state["fake_total"]), 2)
    state["number"] = number
    state["fake_total"] = round(float(state["fake_total"]) + float(amount), 2)
    try:
        json.dump(state, open(path, "w", encoding="utf-8"))
    except Exception:
        pass
    return info


def _fake_deposit_photo(worker, amount):
    """Новая карточка депозита (как у настоящих), с методом и выплатой; если не вышло - старая"""
    try:
        from emerald_cards.deposit import new_deposit_card
        return new_deposit_card(worker, float(amount), **_fake_card_info(worker, amount))
    except Exception:
        try:
            import utils
            return utils._deposit_photo(worker, amount, "")
        except Exception:
            return cards.new_deposit(worker, amount)
'''

new, done, problems = {}, [], []

# --- 1. utils.py ---
src = open(UTILS, encoding="utf-8").read()
if "def _deposit_card_info" not in src:
    problems.append("utils.py: нет _deposit_card_info (сначала нужен patch_deposit_card.py)")
elif "PRAGMA table_info(deposits)" in src:
    done.append("utils.py: уже исправлен")
elif src.count(UTILS_ANCHOR) != 1:
    problems.append(f"utils.py: место для вставки найдено {src.count(UTILS_ANCHOR)} раз")
else:
    new[UTILS] = src.replace(UTILS_ANCHOR, UTILS_EXTRA + UTILS_ANCHOR, 1)
    done.append("utils.py: метод и процент берутся еще и из записи о депозите")

# --- 2. fake_activity/engine.py ---
try:
    src = open(ENGINE, encoding="utf-8").read()
except FileNotFoundError:
    src = None
if src is None:
    done.append("fake_activity/engine.py: нет файла, пропускаю")
elif "_fake_card_info" in src:
    done.append("fake_activity/engine.py: уже исправлен")
else:
    s = re.sub(r"\n*def _fake_deposit_photo\(worker, amount\):.*?return cards\.new_deposit\(worker, amount\)\n?",
               "\n", src, count=1, flags=re.S)
    n = s.count("cards.new_deposit(worker, amount)")
    if n:
        s = s.replace("cards.new_deposit(worker, amount)", "_fake_deposit_photo(worker, amount)")
    if "_fake_deposit_photo(worker, amount)" not in s:
        problems.append("fake_activity/engine.py: не нашел, где рисуется карточка депозита")
    else:
        new[ENGINE] = s.rstrip() + ENGINE_HELPER
        done.append("fake_activity/engine.py: метод, выплата, номер и итог дня у фейков")

if problems:
    print("НЕ ПОЛУЧИЛОСЬ, ни один файл не изменен:")
    print("\n".join(problems))
    sys.exit(1)

for p, text in new.items():
    shutil.copy(p, p + ".bak_fill")
    open(p, "w", encoding="utf-8").write(text)
try:
    for p in new:
        py_compile.compile(p, doraise=True)
except py_compile.PyCompileError as err:
    for p in new:
        shutil.copy(p + ".bak_fill", p)
    print("НЕ ПОЛУЧИЛОСЬ (ошибка в коде), все файлы возвращены как были:")
    print(err)
    sys.exit(1)

print("ГОТОВО:")
print("\n".join(done))

# диагностика: откуда настоящий депозит может взять метод
try:
    import sqlite3
    sys.path.insert(0, ROOT)
    from db import cursor
    cursor.execute("PRAGMA table_info(deposits)")
    print("Колонки deposits:", ", ".join(r[1] for r in cursor.fetchall()) or "таблицы нет")
    cursor.execute("SELECT COUNT(*) FROM deposits")
    print("Записей в deposits:", cursor.fetchone()[0])
except Exception as err:
    print("Диагностика базы не вышла:", err)
if new:
    print("Копии старых файлов: *.bak_fill")
