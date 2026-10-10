"""Выплата только на SOL: убирает кнопки BTC и USDT из клавиатур, где есть кнопка SOL.

python3 patch_sol_only.py [/root/tg_bot]
Копии старых файлов: *.bak_solonly
"""
import ast, os, re, shutil, py_compile, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/root/tg_bot"
SKIP_DIRS = {"venv", ".venv", "env", "__pycache__", "emerald_cards", "watchers", ".git"}
DROP = {"BTC", "USDT"}


def handler_files():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if f.endswith(".py") and not f.startswith("patch_"):
                yield os.path.join(d, f)


def button_text(node):
    """Текст кнопки InlineKeyboardButton/KeyboardButton без эмодзи, если он задан строкой"""
    if not (isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")).endswith("KeyboardButton")):
        return None
    for kw in node.keywords:
        if kw.arg == "text" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return re.sub(r"[^A-Za-z]", "", kw.value.value).upper()
    return None


def offsets(src):
    starts, pos = [0], 0
    for line in src.splitlines(keepends=True):
        pos += len(line)
        starts.append(pos)
    return lambda ln, col: starts[ln - 1] + len(src.splitlines(keepends=True)[ln - 1].encode()[:col].decode())


def cut_spans(src):
    tree = ast.parse(src)
    off = offsets(src)
    spans = []
    for kb in ast.walk(tree):
        # клавиатура = список рядов-списков
        if not (isinstance(kb, ast.List) and kb.elts and all(isinstance(r, ast.List) for r in kb.elts)):
            continue
        texts = [button_text(b) for r in kb.elts for b in r.elts]
        if "SOL" not in texts or not DROP & set(texts):
            continue
        for row in kb.elts:
            drop = [b for b in row.elts if button_text(b) in DROP]
            if not drop:
                continue
            items = [row] if len(drop) == len(row.elts) else drop
            parent = kb.elts if items == [row] else row.elts
            for it in items:
                i = parent.index(it)
                a, b = off(it.lineno, it.col_offset), off(it.end_lineno, it.end_col_offset)
                if i + 1 < len(parent):           # до следующего элемента
                    b = off(parent[i + 1].lineno, parent[i + 1].col_offset)
                elif i > 0:                       # последний: съедаем запятую перед ним
                    prev = parent[i - 1]
                    a = off(prev.end_lineno, prev.end_col_offset)
                    m = re.match(r"\s*,?[ \t]*", src[b:])
                    b += len(m.group(0).rstrip("\n ")) if m and "," in m.group(0) else 0
                spans.append((a, b))
    return sorted(set(spans), reverse=True)


new, done = {}, []
for path in handler_files():
    src = open(path, encoding="utf-8").read()
    if "SOL" not in src or not any(t in src for t in DROP):
        continue
    try:
        spans = cut_spans(src)
    except SyntaxError:
        continue
    if not spans:
        continue
    s = src
    for a, b in spans:
        s = s[:a] + s[b:]
    new[path] = s
    done.append(f"{os.path.relpath(path, ROOT)}: убрано кнопок/рядов: {len(spans)}")

if not new:
    print("Кнопок BTC/USDT рядом с SOL не нашел, ничего не изменено (возможно, уже убраны).")
    print("Если они все еще есть, пришли вывод:  grep -rn '\"BTC\"\\|\"USDT\"' --include=*.py /root/tg_bot/handlers")
    sys.exit(1)

for p, text in new.items():
    shutil.copy(p, p + ".bak_solonly")
    open(p, "w", encoding="utf-8").write(text)
try:
    for p in new:
        py_compile.compile(p, doraise=True)
except py_compile.PyCompileError as err:
    for p in new:
        shutil.copy(p + ".bak_solonly", p)
    print("НЕ ПОЛУЧИЛОСЬ (ошибка в коде), все файлы возвращены как были:")
    print(err)
    sys.exit(1)
print("ГОТОВО:")
print("\n".join(done))
print("Копии старых файлов: *.bak_solonly")
