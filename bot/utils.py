from io import StringIO
import html
import json
import re
import logging
import sys
import time
import requests
from aiogram import types
from config import *
from db import DB, cursor, conn
import api
from datetime import datetime, timedelta
import asyncio
from pydantic import BaseModel
from log import create_logger
from aiogram.exceptions import TelegramBadRequest
import pycountry
from emojis import E, ID
from emerald_cards import cards
from card_utils import card_photo, edit_card, edit_text


def safe_int(value, default=0):
    """
    Безопасное преобразование в int
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


_LAST_TP = {}


async def send_request_to_admin(msg: types.Message, forum_url: str, exp: str):
    """
    Отправка заявок о регистрации по ADMIN_ID (указываеться в config.ini)
    """
    btns = [
        [types.InlineKeyboardButton(text="Отклонить", callback_data=f"user_request_decline?{msg.from_user.id}",
                                    icon_custom_emoji_id=ID.NO),
         types.InlineKeyboardButton(text="Принять", callback_data=f"user_request_accept?{msg.from_user.id}",
                                    icon_custom_emoji_id=ID.OK)]
    ]
    u = msg.from_user
    name = f"{u.first_name} {u.last_name or ''}".strip()
    user_line = f"{name} @{u.username}" if u.username else name
    text = (
        f"{E.BELL} <b>Новая заявка!</b>\n"
        f"{E.CHAT} Опыт: {html.escape(exp)}\n"
        f"{E.LINK} Форум: {html.escape(forum_url)}\n"
        f"{E.USERS} {html.escape(name)} / <code>{u.id}</code> / @{u.username}"
    )

    await bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=card_photo(cards.new_application(user_line, u.id, exp, forum_url)),
        caption=text,
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns)
    )


async def show_user_profile(call: types.CallbackQuery = None, msg: types.Message = None, msg2edit: types.Message = None):
    """
    Формирование профиля пользователя. 
    Тут правда костыль с user_id для того чтобы запускался как функция.
    Но зато все работает :)
    """

    if call is not None:
        user_id = call.from_user.id
    elif msg is not None:
        user_id = msg.from_user.id
    # ===== ФИЛИАЛ =====
    branch_id = DB.get(user_id=user_id, data="branch_id", table=DB.users_table)
    branch_name = None

    if branch_id:
        cursor.execute("SELECT name FROM branches WHERE id = ?", (branch_id,))
        row = cursor.fetchone()
        if row:
            branch_name = str(row[0])
            branch_line = f"{E.GEM_2} <b>Филиал:</b> {html.escape(branch_name)}"
        else:
            branch_line = f"{E.NO} <b>Филиал:</b> не найден"
    else:
        branch_line = f"{E.NO} <b>Филиал:</b> не состоит"

    sol_wallet = DB.get(user_id=user_id, data="sol_wallet", table=DB.users_table) or "Не привязан"
    balance = DB.get(user_id=user_id, data="balance", table=DB.users_table)
    percentage = DB.get(user_id=user_id, data="percentage", table=DB.users_table)
    username = DB.get(user_id=user_id, data="username", table=DB.users_table)

    text = (
        f"{E.CROWN} <b>Профиль</b>\n"
        f"\n"
        f"{E.INFO} <b>Ваш ID:</b> <code>{user_id}</code>\n"
        f"{E.MONEY_WINGS} <b>Ваш баланс:</b> <code>{balance}$</code>\n"
        f"{E.CHART} <b>Процент:</b> <code>{percentage}%</code>\n"
        f"{branch_line}\n"
        f"\n"
        f"{E.PURSE} <b>Привязанные кошельки:</b>\n"
        f"└ SOL: <code>{html.escape(str(sol_wallet))}</code>\n"
        f"\n"
        f"{E.STAR} <b>Ник в отстуке:</b> <code>{html.escape(str(username))}</code>"
    )

    profile_btns = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Изменить ник", callback_data="change_username", icon_custom_emoji_id=ID.STAR),
         types.InlineKeyboardButton(text="Привязать кошелек", callback_data="link_wallet", icon_custom_emoji_id=ID.PURSE)],
        [types.InlineKeyboardButton(text="Заказать выплату", callback_data="payout", icon_custom_emoji_id=ID.MONEY_WINGS)],
        [types.InlineKeyboardButton(text="< Назад", callback_data="back_main")]
    ])
    target = msg2edit if msg2edit is not None else call.message
    photo = card_photo(cards.profile(balance, percentage, username, branch_name))
    await edit_card(target, photo, text, reply_markup=profile_btns, parse_mode="HTML")


async def send_payout_to_admin(user_id: int, amount_of_payout: float, wallet_name: str):
    """
    Отправка заявок на вывод админу по CHANNEL_ID (указываеться в config.ini)
    """

    user_firstname = DB.get(user_id=user_id, data="tg_firstname", table=DB.users_table)
    user_name = DB.get(user_id=user_id, data="tg_username", table=DB.users_table)
    wallet = DB.get(user_id=user_id, data=f"{wallet_name.lower()}_wallet", table=DB.users_table)
    text = (
        f"{E.MONEY_BAG} <b>Заявка на выплату</b>\n"
        f"{E.USERS} {html.escape(str(user_firstname))} / <code>{user_id}</code> / @{user_name}\n"
        f"{E.BOLT} Сумма: <code>{amount_of_payout} $</code>\n"
        f"{E.PURSE} Кошелек:\n"
        f"└ {wallet_name}: <code>{html.escape(str(wallet))}</code>"
    )

    send_payout_btns = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Отклонено", callback_data=f"payout_request_decline?{user_id}",
                                    icon_custom_emoji_id=ID.NO),
         types.InlineKeyboardButton(text="Выплачено", callback_data=f"payout_request_accept?{user_id}",
                                    icon_custom_emoji_id=ID.OK)]
    ])

    user_line = f"{user_firstname} @{user_name}" if user_name else str(user_firstname)
    await bot.send_photo(
        chat_id=USERS_PAYOUTS,
        photo=card_photo(cards.payout_request(user_line, user_id, amount_of_payout, f"{wallet_name}: {wallet}")),
        caption=text,
        reply_markup=send_payout_btns,
        parse_mode="HTML"
    )


async def update_user_balance(user_id: int, amount_of_payout: float, msg2edit: types.Message, wallet_name: str):
    """
    Хз, зачем я вывел в отдельную функцию, но она просто делает проверку на балик и списывания денег с балика
    """

    balance = float(DB.get(user_id=user_id, data="balance", table=DB.users_table))
    if amount_of_payout <= 0:
        await edit_text(msg2edit, f"{E.NO} Сумма вывода должна быть больше нуля", parse_mode="HTML")
        return
    elif balance == 0:
        await edit_text(msg2edit, f"{E.NO} Доступный баланс равен нулю", parse_mode="HTML")
        return
    elif amount_of_payout > balance:
        await edit_text(msg2edit, f"{E.NO} Сумма вывода больше, чем доступный баланс", parse_mode="HTML")
        return

    else:
        new_balance = balance - amount_of_payout
        DB.update(user_id=user_id, column="balance", new_data=new_balance, table=DB.users_table)
        await edit_text(msg2edit, f"{E.OK} Заявка на выплату успешно создана! Ожидайте зачисления", parse_mode="HTML")
        await send_payout_to_admin(user_id=user_id, amount_of_payout=amount_of_payout, wallet_name=wallet_name)


async def create_btns(
    btns_type: str,
    data_list: list,
    callback_data_main_btns: str,
    callback_data_nav_btns: str,
    back_callback: str,
    page: int = 0,
    main_btns_prefix: str = None,
    ids: list = None,
    main_btns_icon: str = None,
):
    """
    Алгоритм создания списка кнопок с промиками.

    btns_type = "stats", "delete", "edit" используется для информации промокодов
    main_btns_icon = ID премиум-эмодзи для кнопок (ставится иконкой слева от текста)
    """
    buttons_per_page = 4
    inline_keyboard = []
    start_idx = page * buttons_per_page
    end_idx = start_idx + buttons_per_page
    promo_page = data_list[start_idx:end_idx]
    total_pages = (len(data_list) + buttons_per_page - 1) // buttons_per_page

    if -1 < page < total_pages:

        for i in range(0, len(promo_page), 2):
            row_buttons = []
            for j, code in enumerate(promo_page[i:i + 2]):

                idx_in_data_list = start_idx + i + j

                current_btns_type = ids[idx_in_data_list] if ids and idx_in_data_list < len(ids) else btns_type
                row_buttons.append(types.InlineKeyboardButton(
                    text=(main_btns_prefix or "") + str(code),
                    callback_data=f"{callback_data_main_btns}{code}?{current_btns_type}",
                    icon_custom_emoji_id=main_btns_icon
                ))
            inline_keyboard.append(row_buttons)


        navigation_buttons = [
            types.InlineKeyboardButton(text="<", callback_data=f"{callback_data_nav_btns}{page - 1}?{btns_type}"),
            types.InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="pass"),
            types.InlineKeyboardButton(text=">", callback_data=f"{callback_data_nav_btns}{page + 1}?{btns_type}")
        ]
        inline_keyboard.append(navigation_buttons)
        inline_keyboard.append([types.InlineKeyboardButton(text="< Назад", callback_data=back_callback)])
        # Создаем InlineKeyboardMarkup с параметром inline_keyboard
        return types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    else:
        return False


async def create_promo_btns(user_id: int, btns_type: str, page: int = 0):

    promo_codes = DB.get_all_user_id(
        user_id=user_id,
        data="name",
        table=DB.promocodes
    )
    return await create_btns(btns_type=btns_type, 
                             page=page, 
                             data_list=promo_codes, 
                             callback_data_main_btns="promocode_", 
                             callback_data_nav_btns="promo_page_",
                             main_btns_prefix="",
                             back_callback="materials"
                             )


async def create_workers_btns(data_list: list, page: int = 0):
    return await create_btns(btns_type=None, 
                             page=page, 
                             data_list=data_list, 
                             callback_data_main_btns="worker_", 
                             callback_data_nav_btns="workers_page_", 
                             main_btns_prefix="",
                             main_btns_icon=ID.USERS,
                             back_callback="back_admin"
                             )

async def create_deposits_btns(data_list: list, ids: list, page: int = 0):
    return await create_btns(btns_type=None, 
                             page=page, 
                             data_list=data_list, 
                             callback_data_main_btns="deposit_", 
                             callback_data_nav_btns="deposits_page_", 
                             main_btns_prefix="",
                             main_btns_icon=ID.MONEY_BAG,
                             ids=ids,
                             back_callback="back_admin"
                             )    

async def create_branches_btns(data_list: list):
    """
    data_list = [(id, name), (id, name)]
    """
    buttons = []

    for branch_id, branch_name in data_list:
        buttons.append([
            types.InlineKeyboardButton(
                text=str(branch_name),
                callback_data=f"branch_select_{branch_id}",
                icon_custom_emoji_id=ID.GEM_2
            )
        ])

    buttons.append([
        types.InlineKeyboardButton(text="< Назад", callback_data="back_admin")
    ])

    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


# =============================================
# 📊 ФУНКЦИИ ДЛЯ СТАТИСТИКИ (С РАЗДЕЛЕНИЕМ ПРАВ)
# =============================================

async def promo_view_stats(promo_name: str, user_id: int = None, is_admin: bool = False):
    """
    ПОЛУЧЕНИЕ СТАТИСТИКИ - С РАЗДЕЛЕНИЕМ ПРАВ
    
    🔐 АДМИН (is_admin=True): данные из API
    👨‍💻 ВОРКЕР (user_id=ID): данные из БД (только свои)
    """
    try:
        # =============================================
        # 🔐 РЕЖИМ АДМИНА - данные из API
        # =============================================
        if is_admin:
            logger.info(f"Админ запрашивает статистику API для {promo_name}")
            
            # 1️⃣ Основные данные промокода
            api_result = await api.get_promo(promo_name)
            if not api_result or "data" not in api_result:
                return None
            
            promo_data = api_result["data"]
            
            # 2️⃣ Статистика по странам
            api_stats = await api.get_promo_stats(promo_name)
            
            # Формируем словарь стран для админа
            countries_dict = {}
            if api_stats and "data" in api_stats:
                countries = api_stats["data"].get("countries", [])
                for country in countries:
                    code = country["name"]
                    countries_dict[code] = {
                        "activations": int(country["activations"]),
                        "amount": float(country["amount"])
                    }
            
            return {
                "name": promo_data["name"],
                "amount": promo_data["amount"],
                "activations": int(promo_data["activations"]),
                "deposits": float(promo_data["deposits"]),
                "shouldWager": promo_data["shouldWager"],
                "countries": countries_dict,
                "is_admin": True
            }
        
        # =============================================
        # 👨‍💻 РЕЖИМ ВОРКЕРА - активации из API, страны из API stats
        # =============================================
        elif user_id:
            logger.info(f"Воркер {user_id} запрашивает свою статистику для {promo_name}")
            
            # 1️⃣ Основные данные из API
            api_result = await api.get_promo(promo_name)
            
            if not api_result or not api_result.get("success"):
                logger.error(f"Ошибка получения данных из API для {promo_name}")
                api_activations = 0
                promo_amount = 0
                should_wager = False
                countries_data = []
            else:
                api_activations = api_result["data"].get("activations", 0)
                promo_amount = api_result["data"].get("amount", 0)
                should_wager = api_result["data"].get("shouldWager", False)
                
                # 2️⃣ Статистика по странам из API
                stats_result = await api.get_promo_stats(promo_name)
                if stats_result and stats_result.get("success"):
                    countries_data = stats_result["data"].get("countries", [])
                else:
                    countries_data = []
            
            # 3️⃣ Получаем свои депозиты из БД (для сумм)
            cursor.execute("""
                SELECT 
                    d.country,
                    COALESCE(SUM(d.amountUSD), 0) as deposits
                FROM deposits d
                JOIN mammoth_deposits md ON md.mammoth_id = d.mammoth_id
                WHERE md.promo = ?
                AND d.worker_id = ?
                GROUP BY d.country
            """, (promo_name, user_id))
            
            deposit_rows = cursor.fetchall()
            
            # Создаем словарь депозитов по странам
            deposit_dict = {}
            total_deposits = 0
            for row in deposit_rows:
                country = row[0] if row[0] else "UNKNOWN"
                amount = row[1]
                deposit_dict[country] = amount
                total_deposits += amount
            
            # 4️⃣ Формируем итоговый словарь стран
            countries_dict = {}
            
            # Сначала добавляем данные из API stats (активации)
            for country_data in countries_data:
                code = country_data.get("name")
                activations = country_data.get("activations", 0)
                if code:
                    countries_dict[code] = {
                        "activations": activations,
                        "amount": round(deposit_dict.get(code, 0), 2)
                    }
            
            return {
                "name": promo_name,
                "amount": promo_amount,
                "activations": api_activations,
                "deposits": round(total_deposits, 2),
                "shouldWager": should_wager,
                "countries": countries_dict,
                "is_admin": False
            }
        
        else:
            logger.error("Не указан режим вызова (нужен is_admin или user_id)")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка в promo_view_stats для {promo_name}: {e}")
        return None

def build_promo_stats_with_diff(promo_data: dict, snapshot: dict | None = None):
    """
    ФОРМАТИРОВАНИЕ СТАТИСТИКИ - С ДЕЛЬТОЙ
    """
    # ===== ЗАГОЛОВОК =====
    text = (
        f"{E.CHART} <b>Статистика по промокоду</b> <code>{promo_data['name']}</code>\n"
        f"<blockquote>"
        f"{E.MONEY_WINGS} <b>Сумма промокода:</b> <code>{promo_data['amount']}$</code>\n"
    )
    
    # ===== АКТИВАЦИИ С ДЕЛЬТОЙ =====
    acts = promo_data['activations']
    act_line = f"{E.USERS} <b>Активаций:</b> <code>{acts}</code>"
    
    if snapshot:
        old_acts = snapshot.get("activations", acts)
        diff = acts - old_acts
        if diff > 0:
            act_line = f"{E.USERS} <b>Активаций:</b> <code>{acts} (+{diff})</code>"
        elif diff < 0:
            act_line = f"{E.USERS} <b>Активаций:</b> <code>{acts} ({diff})</code>"
        # Если diff == 0, оставляем без дельты
    
    text += act_line + "\n"
    
    # ===== ДЕПОЗИТЫ С ДЕЛЬТОЙ =====
    deps = promo_data['deposits']
    dep_line = f"{E.GEM} <b>Депозитов:</b> <code>{deps}$</code>"
    
    if snapshot:
        old_deps = snapshot.get("deposits", deps)
        diff = round(deps - old_deps, 2)
        if diff > 0:
            dep_line = f"{E.GEM} <b>Депозитов:</b> <code>{deps}$ (+{diff}$)</code>"
        elif diff < 0:
            dep_line = f"{E.GEM} <b>Депозитов:</b> <code>{deps}$ ({diff}$)</code>"
        # Если diff == 0, оставляем без дельты
    
    text += dep_line + "\n"
    
    # ===== ОТЫГРЫШ =====
    text += (
        f"{E.BOLT} <b>Отыгрыш:</b> <code>{'включен' if promo_data['shouldWager'] else 'отключен'}</code>"
        f"</blockquote>\n\n"
    )
    
    # ===== СТРАНЫ =====
    text += f"<b>Страна / Активаций / Депозитов</b>\n"
    
    if promo_data.get("countries") and len(promo_data["countries"]) > 0:
        for code, data in promo_data["countries"].items():
            activations = data.get("activations", 0)
            amount = data.get("amount", 0)
            
            # Форматируем сумму
            if isinstance(amount, float) and amount.is_integer():
                amount_str = str(int(amount))
            else:
                amount_str = f"{amount:.2f}".rstrip('0').rstrip('.')
            
            flag = country_code_to_flag(code)
            
            # Формируем строку страны
            line = f"{flag} {code} / {activations}"
            
            if snapshot and snapshot.get("countries"):
                old_country = snapshot["countries"].get(code)
                if old_country:
                    diff = activations - old_country.get("activations", activations)
                    if diff > 0:
                        line += f" (+{diff})"
                    elif diff < 0:
                        line += f" ({diff})"
                    # Если diff == 0, без дельты
            
            line += f" / {amount_str}$"
            text += line + "\n"
    
    return text


async def show_promo_stats(message: types.Message, promo_data: dict, snapshot: dict | None = None, reply_markup=None):
    """
    Показывает статистику промокода карточкой: картинка рисуется по тем же данным, что и текст.
    Подпись к фото ограничена 1024 символами, если стран очень много - уйдет просто текстом.
    """
    text = build_promo_stats_with_diff(promo_data, snapshot)
    if len(re.sub(r"<[^>]+>", "", text)) > 1024:
        return await edit_text(message, text, reply_markup=reply_markup, parse_mode="HTML")
    photo = card_photo(cards.promo_stats(promo_data, snapshot))
    return await edit_card(message, photo, text, reply_markup=reply_markup, parse_mode="HTML")


def country_code_to_flag(country_code):
    """
    Преобразование кода страны в эмодзи флага
    """
    code_points = [ord(char) - 0x41 + 0x1F1E6 for char in country_code.upper()]
    return chr(code_points[0]) + chr(code_points[1])


# =============================================
# 💾 ФУНКЦИИ ДЛЯ СНАПШОТОВ (СРАВНЕНИЕ СТАТИСТИКИ)
# =============================================


def get_promo_snapshot(promo_name: str, user_id: int):
    cursor.execute(
        "SELECT data FROM promo_snapshots WHERE promo_name = ? AND user_id = ?",
        (promo_name, user_id)
    )
    row = cursor.fetchone()
    return json.loads(row[0]) if row else None

def save_promo_snapshot(promo_name: str, user_id: int, data: dict):
    cursor.execute("""
        INSERT INTO promo_snapshots (promo_name, user_id, data, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(promo_name, user_id)
        DO UPDATE SET
            data = excluded.data,
            updated_at = excluded.updated_at
    """, (
        promo_name,
        user_id,
        json.dumps(data),
        int(time.time())
    ))
    conn.commit()
