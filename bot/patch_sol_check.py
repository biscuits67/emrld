"""Проверка SOL-адреса при привязке кошелька.

python3 patch_sol_check.py [/root/tg_bot]

В обработчик ввода адреса (handlers/msg_handler.py) добавляется проверка:
адрес Solana - base58, 32-44 символа, ровно 32 байта. Неверный адрес не
сохраняется, бот просит ввести еще раз (состояние не сбрасывается).
Копия старого файла: msg_handler.py.bak_solcheck
"""
import re, shutil, py_compile, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/root/tg_bot"
MSG = f"{ROOT}/handlers/msg_handler.py"

HELPER = '''


# =============================================
# ПРОВЕРКА SOL-АДРЕСА
# =============================================

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _is_sol_address(address) -> bool:
    """Адрес Solana: base58, 32-44 символа, раскодируется ровно в 32 байта"""
    address = str(address or "").strip()
    if not 32 <= len(address) <= 44 or any(c not in _B58 for c in address):
        return False
    num = 0
    for c in address:
        num = num * 58 + _B58.index(c)
    raw = num.to_bytes((num.bit_length() + 7) // 8, "big")
    zeros = len(address) - len(address.lstrip("1"))
    return len(raw) + zeros == 32
'''

src = open(MSG, encoding="utf-8").read()
if "_is_sol_address" in src:
    print("Проверка уже стоит, ничего не изменено")
    sys.exit(0)

lines = src.splitlines(keepends=True)
decos = [i for i, l in enumerate(lines)
         if re.match(r"\s*@", l) and re.search(r"wallet", l, re.I) and not re.search(r"payout", l, re.I)]
if len(decos) != 1:
    print(f"НЕ ПОЛУЧИЛОСЬ: обработчиков ввода кошелька найдено {len(decos)}, файл не изменен.")
    print("Пришли вывод этой команды:")
    print(f"grep -n -i -A30 'wallet' {MSG}")
    sys.exit(1)

i = decos[0]
while i < len(lines) and not re.match(r"\s*async def ", lines[i]):
    i += 1
m = re.match(r"\s*async def \w+\(\s*(\w+)", lines[i]) if i < len(lines) else None
if not m:
    print("НЕ ПОЛУЧИЛОСЬ: не нашел функцию после обработчика, файл не изменен.")
    print(f"Пришли вывод: grep -n -i -A30 'wallet' {MSG}")
    sys.exit(1)
param = m.group(1)

# первая строка тела функции (сигнатура может занимать несколько строк)
j = i
while not lines[j].rstrip().endswith(":"):
    j += 1
j += 1
while not lines[j].strip():
    j += 1
indent = re.match(r"\s*", lines[j]).group(0)

check = (
    f"{indent}if not _is_sol_address({param}.text):\n"
    f"{indent}    await {param}.answer(f\"{{E.NO}} Это не похоже на SOL-адрес. Проверь и отправь адрес Solana еще раз.\")\n"
    f"{indent}    return\n"
)
if not re.search(r"import[^\n]*\bE\b", src):
    check = check.replace("{E.NO} ", "❌ ").replace('f"❌', '"❌')

new = "".join(lines[:j]) + check + "".join(lines[j:])
new = new.rstrip() + HELPER

shutil.copy(MSG, MSG + ".bak_solcheck")
open(MSG, "w", encoding="utf-8").write(new)
try:
    py_compile.compile(MSG, doraise=True)
except py_compile.PyCompileError as err:
    shutil.copy(MSG + ".bak_solcheck", MSG)
    print("НЕ ПОЛУЧИЛОСЬ (ошибка в коде), файл возвращен как был:")
    print(err)
    sys.exit(1)

print(f"ГОТОВО: проверка SOL-адреса добавлена в {lines[i].strip()}")
print("Копия старого файла: msg_handler.py.bak_solcheck")
