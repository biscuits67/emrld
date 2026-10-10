"""TRX -> SOL: кошелек для выплат теперь Solana.

python3 patch_sol.py [/root/tg_bot]

- кнопки, подписи, callback_data и колонка кошелька в обработчиках: TRX -> SOL
- профиль в utils.py: └ SOL
- карточка «Выберите кошелёк SOL» (скачивается из репозитория)
- в таблицу пользователей добавляется колонка sol_wallet (TRX-адреса остаются в trx_wallet)
Перед изменением делаются копии *.bak_sol, при ошибке все возвращается как было.
"""
import os, re, shutil, py_compile, sys, sqlite3, urllib.request

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/root/tg_bot"
UTILS = f"{ROOT}/utils.py"
CARDS = f"{ROOT}/emerald_cards/cards.py"
IMG = f"{ROOT}/emerald_cards/assets/static/wallet_sol.jpg"
IMG_URL = ("https://raw.githubusercontent.com/biscuits67/emrld/claude/elegant-johnson-ujpfw7/"
           "bot/emerald_cards/assets/static/wallet_sol.jpg")
SKIP_DIRS = {"venv", ".venv", "env", "__pycache__", "emerald_cards", "watchers", ".git"}
SKIP_FILES = {"utils.py", "api.py", "config.py", "db.py", "patch_sol.py"}

TICKER = re.compile(r"(?<![A-Za-z])TRX(?![A-Za-z])")
TICKER_LOW = re.compile(r"(?<![A-Za-z])trx(?![A-Za-z])")
WALLETISH = re.compile(r"кошел|wallet|callback_data|F\.data|call\.data|TRON", re.I)


def handler_files():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if f.endswith(".py") and f not in SKIP_FILES:
                yield os.path.join(d, f)


def to_sol(line):
    line = line.replace("TRON", "Solana")
    line = TICKER.sub("SOL", line)
    return TICKER_LOW.sub("sol", line)


new, changed = {}, []
for path in handler_files():
    src = open(path, encoding="utf-8").read()
    if not WALLETISH.search(src) or not (TICKER.search(src) or TICKER_LOW.search(src)):
        continue
    out = []
    for n, line in enumerate(src.splitlines(keepends=True), 1):
        fixed = to_sol(line)
        if fixed != line:
            changed.append(f"{os.path.relpath(path, ROOT)}:{n}: {fixed.strip()}")
        out.append(fixed)
    new[path] = "".join(out)

# utils.py: только профиль (депозиты с TRX не трогаем)
src = open(UTILS, encoding="utf-8").read()
fixed = src.replace("trx_wallet", "sol_wallet").replace("└ TRX:", "└ SOL:")
if fixed != src:
    new[UTILS] = fixed
    changed.append("utils.py: профиль -> └ SOL, колонка sol_wallet")

# карточка в списке
src = open(CARDS, encoding="utf-8").read()
if '"wallet_sol"' not in src:
    new[CARDS] = re.sub(r'^(\s*"wallet_trx",.*)$', r'\1\n    "wallet_sol",            # Выберите кошелек SOL',
                        src, count=1, flags=re.M)

if not changed:
    print("TRX в обработчиках не найден, ничего не изменено (возможно, скрипт уже запускался)")
    sys.exit(1)

# картинка
try:
    if not os.path.exists(IMG):
        urllib.request.urlretrieve(IMG_URL, IMG)
except Exception as err:
    print(f"НЕ ПОЛУЧИЛОСЬ скачать карточку ({err}), ничего не изменено.")
    print(f"Скачай вручную: {IMG_URL}\nи положи в {IMG}, потом запусти скрипт снова")
    sys.exit(1)

for p, text in new.items():
    shutil.copy(p, p + ".bak_sol")
    open(p, "w", encoding="utf-8").write(text)
try:
    for p in new:
        py_compile.compile(p, doraise=True)
except py_compile.PyCompileError as err:
    for p in new:
        shutil.copy(p + ".bak_sol", p)
    print("НЕ ПОЛУЧИЛОСЬ (ошибка в коде), все файлы возвращены как были:")
    print(err)
    sys.exit(1)

# колонка sol_wallet
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    from db import DB, cursor, conn
    table = DB.users_table
    cursor.execute(f"PRAGMA table_info({table})")
    if "sol_wallet" not in [r[1] for r in cursor.fetchall()]:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN sol_wallet TEXT")
        conn.commit()
    db_note = f"колонка sol_wallet в таблице {table} есть"
except Exception as err:
    db_note = f"!!! колонку sol_wallet добавить не удалось: {err}"

print("ГОТОВО. Изменено:")
print("\n".join(changed))
print(db_note)

# проверки адреса под TRON (начинается с T, длина 34) для SOL не подойдут
suspect = []
for p in new:
    for n, line in enumerate(open(p, encoding="utf-8"), 1):
        if re.search(r"startswith\(\s*['\"]T['\"]|[=!]=\s*34\b|\b34\s*[=!]=|\[0\]\s*==\s*['\"]T['\"]|base58", line):
            suspect.append(f"{os.path.relpath(p, ROOT)}:{n}: {line.strip()}")
if suspect:
    print("\nВНИМАНИЕ, похоже на проверку TRX-адреса (пришли эти строки):")
    print("\n".join(suspect))
print("\nКопии старых файлов: *.bak_sol")
