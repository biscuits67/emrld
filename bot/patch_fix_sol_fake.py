"""1) Проверка SOL-адреса: старая проверка TRX (T + 34 символа) -> настоящая проверка Solana.
2) Фейковая активность (fake_activity/engine.py) рисует депозиты новой карточкой.

.venv/bin/python patch_fix_sol_fake.py [/root/tg_bot]
Копии старых файлов: *.bak_fix
"""
import re, shutil, py_compile, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/root/tg_bot"
MSG = f"{ROOT}/handlers/msg_handler.py"
ENGINE = f"{ROOT}/fake_activity/engine.py"

ENGINE_HELPER = '''


def _fake_deposit_photo(worker, amount):
    """Новая карточка депозита (как у настоящих); если не вышло - старая"""
    try:
        import utils
        return utils._deposit_photo(worker, amount, "")
    except Exception:
        return cards.new_deposit(worker, amount)
'''

new, done, problems = {}, [], []

# --- 1. проверка SOL ---
src = open(MSG, encoding="utf-8").read()
s = src
if "_is_sol_address" not in s:
    problems.append("msg_handler.py: нет _is_sol_address (сначала нужен patch_sol_check.py)")
else:
    old_ret = re.compile(r"return\s+len\(address\)\s*==\s*34\s+and\s+address\.startswith\(['\"]T['\"]\)\s+and\s+bool\(SOL_REGEX\.match\(address\)\)")
    s, n = old_ret.subn("return _is_sol_address(address)", s)
    if n != 1 and "return _is_sol_address(address)" not in s:
        problems.append(f"msg_handler.py: старая проверка адреса найдена {n} раз")
    s = re.sub(r"Адрес должен начинаться с T и содержать 34 символа\.?",
               "Адрес Solana: 32–44 символа, латиница и цифры.", s)
    if s != src:
        new[MSG] = s
        done.append("msg_handler.py: проверка адреса теперь под Solana")

# --- 2. фейковая активность ---
try:
    src = open(ENGINE, encoding="utf-8").read()
except FileNotFoundError:
    src = None
if src is not None and "_fake_deposit_photo" not in src:
    n = src.count("cards.new_deposit(worker, amount)")
    if n == 0:
        problems.append("fake_activity/engine.py: не нашел cards.new_deposit(worker, amount)")
    else:
        new[ENGINE] = src.replace("cards.new_deposit(worker, amount)", "_fake_deposit_photo(worker, amount)").rstrip() + ENGINE_HELPER
        done.append(f"fake_activity/engine.py: новая карточка ({n} место)")

if problems:
    print("НЕ ПОЛУЧИЛОСЬ, ни один файл не изменен:")
    print("\n".join(problems))
    sys.exit(1)
if not new:
    print("Все уже исправлено, ничего не изменено")
    sys.exit(0)

for p, text in new.items():
    shutil.copy(p, p + ".bak_fix")
    open(p, "w", encoding="utf-8").write(text)
try:
    for p in new:
        py_compile.compile(p, doraise=True)
except py_compile.PyCompileError as err:
    for p in new:
        shutil.copy(p + ".bak_fix", p)
    print("НЕ ПОЛУЧИЛОСЬ (ошибка в коде), все файлы возвращены как были:")
    print(err)
    sys.exit(1)

# самопроверка SOL
sys.path.insert(0, ROOT)
ns = {}
code = open(MSG, encoding="utf-8").read()
exec(code[code.index("_B58 ="):], ns)
ok = ns["_is_sol_address"]("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM") and not ns["_is_sol_address"]("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
print("ГОТОВО:")
print("\n".join(done))
print("Проверка SOL: " + ("работает" if ok else "!!! что-то не так, пришли этот вывод"))
print("Копии старых файлов: *.bak_fix")
