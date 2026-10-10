import re, shutil, py_compile, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/root/tg_bot"
INLINE = f"{ROOT}/handlers/inline_handler.py"
MSG = f"{ROOT}/handlers/msg_handler.py"
UTILS = f"{ROOT}/utils.py"


def flex(old):
    # same code, any indentation / line breaks
    return re.compile(r"\s*".join(re.escape(line.strip()) for line in old.strip().splitlines()))


EDITS = [
    # --- ввод ника ---
    (INLINE, '''await edit_text(call.message,
text=f"{E.STAR} Введите новый ник, который будет отображаться в отстуке:",''',
     '''await edit_card(call.message, card("nickname"),
                f"{E.STAR} Введите новый ник, который будет отображаться в отстуке:",'''),
    # --- выбор кошелька ---
    (INLINE, '''await edit_text(call.message,
text=f"{E.CARD} Выберите кошелек TRX",''',
     '''await edit_card(call.message, card("wallet_trx"),
                f"{E.CARD} Выберите кошелек TRX",'''),
    # --- ввод адреса кошелька ---
    (INLINE, '''await edit_text(call.message,
text=f"{E.CARD} Введите новый адрес вашего {wallet_name} кошелька",''',
     '''await edit_card(call.message, card_photo(cards.wallet_address(wallet_name)),
                f"{E.CARD} Введите новый адрес вашего {wallet_name} кошелька",'''),
    # --- на какой кошелек выплата ---
    (INLINE, '''await edit_text(call.message,
text=f"{E.MONEY_WINGS} На какой кошелек вы хотите заказать выплату?",''',
     '''await edit_card(call.message, card("payout_choose"),
                f"{E.MONEY_WINGS} На какой кошелек вы хотите заказать выплату?",'''),
    # --- нет кошелька для выплаты ---
    (INLINE, '''await edit_text(call.message,
text=f"{E.NO} Укажите {str(call.data).split('_')[1]} кошелек для выплаты"
)''',
     '''await edit_card(call.message, card_photo(cards.payout_no_wallet(str(call.data).split('_')[1])),
                    f"{E.NO} Укажите {str(call.data).split('_')[1]} кошелек для выплаты",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                        [types.InlineKeyboardButton(text="< Назад", callback_data="user_profile")]
                    ])
                )'''),
    # --- ввод суммы выплаты (запоминаем новое сообщение, старое удаляется) ---
    (INLINE, '''await edit_text(call.message,
text=text,
reply_markup=payout_btns
)
await state.set_state(States.payout_amount)
await state.update_data(msg2edit=call.message)''',
     '''payout_msg = await edit_card(call.message,
                card_photo(cards.payout_amount(DB.get(user_id=call.from_user.id, data='balance', table=DB.users_table))),
                text,
                reply_markup=payout_btns
            )
            await state.set_state(States.payout_amount)
            await state.update_data(msg2edit=payout_msg if isinstance(payout_msg, types.Message) else call.message)'''),
    # --- ИСПРАВЛЕНИЕ: отклонение выплаты читает сумму и из подписи к картинке ---
    (INLINE, '''msg_text_list = str(call.message.text).splitlines()''',
     '''msg_text_list = str(call.message.text or call.message.caption).splitlines()'''),
    # --- топ депозитов ---
    (INLINE, '''text = utils.create_top_deposits(period)
await edit_text(call.message,
text=text,''',
     '''await utils.show_top_deposits(call.message, period,'''),
    # --- новый ник сохранен ---
    (MSG, '''msg2edit = await msg.answer(f"{E.OK} Новый ник успешно сохранен!")''',
     '''msg2edit = await msg.answer_photo(card_photo(cards.nickname_saved(new_username)), caption=f"{E.OK} Новый ник успешно сохранен!")'''),
]

UTILS_ADD = '''


# =============================================
# 🥇 ТОП ДЕПОЗИТОВ КАРТОЧКОЙ
# =============================================

def top_deposits_rows(period: str, limit: int = 5):
    """[(имя, сумма), ...] для карточки топа, лучшие первыми"""
    now = datetime.now()
    if period == "day":
        where, params = "WHERE date = ?", (now.strftime("%Y-%m-%d"),)
    elif period == "week":
        where, params = "WHERE date >= ?", ((now - timedelta(days=7)).strftime("%Y-%m-%d"),)
    elif period == "month":
        where, params = "WHERE date >= ?", ((now - timedelta(days=30)).strftime("%Y-%m-%d"),)
    else:
        where, params = "", ()
    cursor.execute(
        f"SELECT worker_id, SUM(amountUSD) as total FROM deposits {where} GROUP BY worker_id ORDER BY total DESC LIMIT ?",
        (*params, limit)
    )
    rows = []
    for worker_id, total in cursor.fetchall():
        username = DB.get(user_id=worker_id, data="tg_username", table=DB.users_table)
        firstname = DB.get(user_id=worker_id, data="tg_firstname", table=DB.users_table)
        name = f"@{username}" if username else (firstname or f"id{worker_id}")
        rows.append((name, round(float(total or 0), 2)))
    return rows


async def show_top_deposits(message: types.Message, period: str, reply_markup=None):
    """
    Топ депозитов карточкой: на картинке топ-5, в подписи полный текст.
    Если текст длиннее 1024 символов (лимит подписи) - уйдет просто текстом.
    """
    text = create_top_deposits(period)
    if period not in ("day", "week", "month", "all") or len(text) > 1024:
        return await edit_text(message, text, reply_markup=reply_markup)
    photo = card_photo(cards.top_deposits(period, top_deposits_rows(period)))
    return await edit_card(message, photo, text, reply_markup=reply_markup)
'''

files = {p: open(p, encoding="utf-8").read() for p in (INLINE, MSG, UTILS)}
new = dict(files)
problems = []
for path, old, repl in EDITS:
    pat = flex(old)
    found = len(pat.findall(new[path]))
    if found != 1:
        problems.append(f"{path.split('/')[-1]}: '{[l for l in old.strip().splitlines() if 'edit_text(call.message' not in l][0].strip()[:70]}' найдено {found} раз")
        continue
    new[path] = pat.sub(lambda m: repl, new[path])
if "def show_top_deposits" not in new[UTILS]:
    new[UTILS] = new[UTILS].rstrip() + UTILS_ADD

if problems:
    print("НЕ ПОЛУЧИЛОСЬ, ни один файл не изменен:")
    print("\n".join(problems))
    sys.exit(1)

for p in files:
    shutil.copy(p, p + ".bak2")
    open(p, "w", encoding="utf-8").write(new[p])
try:
    for p in files:
        py_compile.compile(p, doraise=True)
except py_compile.PyCompileError as err:
    for p in files:
        shutil.copy(p + ".bak2", p)
    print("НЕ ПОЛУЧИЛОСЬ (ошибка в коде), все файлы возвращены как были:")
    print(err)
    sys.exit(1)
print(f"ГОТОВО: {len(EDITS)} замен + топ депозитов в utils.py. Копии старых файлов: *.bak2")
