import re, shutil, py_compile, sys

UTILS = (sys.argv[1] if len(sys.argv) > 1 else "/root/tg_bot") + "/utils.py"


def flex(old):
    return re.compile(r"\s*".join(re.escape(line.strip()) for line in old.strip().splitlines()))


EDITS = [
    ("в группу", '''if route == "worker":
group_resp = requests.post(
f"https://api.telegram.org/bot{bot_token}/sendMessage",
params={
"chat_id": GROUP_ID,
"text": group_text,
"parse_mode": "HTML"
},
timeout=5
)''', '''if route == "worker":
        group_resp = _send_deposit_card(bot_token, GROUP_ID, group_text, worker_username, amountUsd)'''),
    ("воркеру", '''if worker_id != CONTROL_WORKER_ID:
worker_resp = requests.post(
f"https://api.telegram.org/bot{bot_token}/sendMessage",
params={
"chat_id": worker_id,
"text": worker_text,
"parse_mode": "HTML"
},
timeout=5
)''', '''if worker_id != CONTROL_WORKER_ID:

        worker_resp = _send_deposit_card(bot_token, worker_id, worker_text, worker_username, amountUsd)'''),
]

HELPER = '''


# =============================================
# 🚀 НОВЫЙ ДЕПОЗИТ КАРТОЧКОЙ
# =============================================

def _send_deposit_card(bot_token, chat_id, text, worker, amount):
    """Новый депозит карточкой; если фото не ушло - обычным текстом, как раньше"""
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
            data={"chat_id": chat_id, "caption": text, "parse_mode": "HTML"},
            files={"photo": ("deposit.jpg", cards.new_deposit(worker, int(float(amount))), "image/jpeg")},
            timeout=10
        )
        if resp.status_code == 200:
            return resp
        create_logger("utils").error(f"newDeposit: card send error {resp.status_code}: {resp.text}")
    except Exception as err:
        create_logger("utils").error(f"newDeposit: card send error: {err}")
    return requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        params={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=5
    )
'''

src = open(UTILS, encoding="utf-8").read()
new = src
problems = []
for name, old, repl in EDITS:
    pat = flex(old)
    found = len(pat.findall(new))
    if found != 1:
        problems.append(f"отправка {name}: найдено {found} раз")
        continue
    new = pat.sub(lambda m: repl, new)
if problems:
    print("НЕ ПОЛУЧИЛОСЬ, файл не изменен:")
    print("\n".join(problems))
    sys.exit(1)
if "def _send_deposit_card" not in new:
    new = new.rstrip() + HELPER

shutil.copy(UTILS, UTILS + ".bak3")
open(UTILS, "w", encoding="utf-8").write(new)
try:
    py_compile.compile(UTILS, doraise=True)
except py_compile.PyCompileError as err:
    shutil.copy(UTILS + ".bak3", UTILS)
    print("НЕ ПОЛУЧИЛОСЬ (ошибка в коде), файл возвращен как был:")
    print(err)
    sys.exit(1)
print("ГОТОВО: «Новый депозит» теперь уходит карточкой. Копия старого файла: utils.py.bak3")
