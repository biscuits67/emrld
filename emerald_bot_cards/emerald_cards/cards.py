"""One function per bot message. Each returns ready-to-send image bytes
(dynamic cards) or a path to a PNG (static cards)."""
from pathlib import Path

from .render import ASSETS, render

STATIC = (
    "application_accepted",  # ✅ Заявка была принята
    "wallet_trx",            # 💳 Выберите кошелек TRX
    "wallet_sol",            # 💳 Выберите кошелек SOL
    "nickname",              # ⭐️ Введите новый ник
    "payout_choose",         # 💸 На какой кошелек вы хотите заказать выплату?
    "payout_done",           # ✅ Выплата совершена
    "payout_rejected",       # ❌ Выплата отклонена
    "forum_link",            # 👍 Отлично, теперь отправьте ссылку на свой профиль форума
    "application_sent",      # ✈️ Ваша заявка успешно отправлена!
    "application_failed",    # ⛔️ Ваша заявка не была отправлена!
    "enter_number",          # ❌ Введите число
    "promo_name",            # 💬 Введите название промокода
    "promo_exists",          # ❌ Данный промокод уже существует
    "domain_bad_format",     # ❌ Неверный формат домена. Пример: example.com
    "domains_not_found",     # ❌ Активные домены не найдены
    "menu_materials",        # 📕 Материалы
    "menu_info",             # ℹ️ Информация
    "top_deposits",          # 🥇 Выберите период для топа депозитов
    "add_domain",            # 💬 Введите домен (example.com)
    "cancelled",             # Операция отменена.
    "confirmed",             # Операция подтверждена.
    "unknown_command",       # Неизвестная команда
    "banned",                # ⛔️ Вы были заблокированы администрацией
    "profile_error",         # ⛔️ Ошибка профиля. Обратитесь к администратору.
)


def static(name: str) -> Path:
    if name not in STATIC:
        raise ValueError(f"unknown static card {name!r}, choose from {STATIC}")
    return ASSETS / "static" / f"{name}.jpg"


def money(value) -> str:
    """1234.5 -> '1 234.50 $' (thin, non-breaking thousands separator)."""
    try:
        return f"{float(value):,.2f}".replace(",", " ") + " $"
    except (TypeError, ValueError):
        return f"{value} $"


def _at(username) -> str:
    username = str(username or "").strip()
    return username if not username or username.startswith("@") else "@" + username


def application_rejected(admin_username) -> bytes:
    """❌ Заявка была отклонена ... свяжитесь с администрацией - {admin_username}"""
    return render("application_rejected", admin=_at(admin_username))


def wallet_address(wallet_name) -> bytes:
    """💳 Введите новый адрес вашего {wallet_name} кошелька"""
    return render("wallet_address", wallet=wallet_name)


def payout_no_wallet(wallet_name) -> bytes:
    """❌ Укажите {wallet} кошелек для выплаты"""
    return render("payout_no_wallet", wallet=wallet_name)


def payout_amount(balance) -> bytes:
    """💸 Введите сумму выплаты ⚡️ Доступно: {balance} $"""
    return render("payout_amount", balance=money(balance))


def branch_info(members, turnover, percent) -> bytes:
    """👥 Участников / 💰 Оборот филиала / 📊 Процент филиала"""
    return render(
        "branch_info",
        members=members,
        turnover=money(round(float(turnover), 2)),
        percent=f"{percent}%",
    )


def nickname_saved(nick) -> bytes:
    """✅ Новый ник успешно сохранен!"""
    return render("nickname_saved", nick=nick)


def domain_added(domain) -> bytes:
    """✅ Домен {domain} добавлен!"""
    return render("domain_added", domain=domain)


def domain_exists(domain) -> bytes:
    """❌ Домен {domain} уже существует!"""
    return render("domain_exists", domain=domain)


def domains_list(domains, active_domain=None, all_active=False) -> bytes:
    """🔗 Актуальные домены.
    Admin list: domains_list(domains, active_domain) — the active one is highlighted.
    User menu:  domains_list(active_domains, all_active=True) — every domain gets a check."""
    return render("domains_list", domains=(list(domains or []), active_domain, all_active))


TOP_PERIODS = {"day": "top_day", "week": "top_week", "month": "top_month", "all": "top_all"}


def top_deposits(period, rows) -> bytes:
    """📅 Топ депозитов за день / неделю / месяц / всё время.
    period -- "day" | "week" | "month" | "all" (or callback_data like "top_deposits_week")
    rows   -- [(name, amount), ...] best first; up to 5 are shown, amounts as numbers or text."""
    period = str(period).rsplit("_", 1)[-1]
    if period not in TOP_PERIODS:
        raise ValueError(f"period must be one of {list(TOP_PERIODS)}")
    prepared = [(name, money(amount) if isinstance(amount, (int, float)) else amount) for name, amount in rows]
    return render(TOP_PERIODS[period], rows=prepared)


def new_deposit(worker, amount) -> bytes:
    """🚀 Новый депозит 🧑‍💻 Воркер: {worker} 💵 Сумма USD: ${amount}"""
    try:
        amount = "$" + f"{round(float(amount), 2):,.2f}".replace(",", " ")
    except (TypeError, ValueError):
        amount = f"${amount}"
    return render("new_deposit", worker=worker, amount=amount)


def profile(balance, percent, nick, branch=None) -> bytes:
    """👨‍💻 Профиль: 💸 баланс, 🫰 процент, ⭐ ник в отстуке, 🏢 филиал"""
    return render(
        "profile",
        balance=money(balance),
        percent=f"{percent}%",
        nick=nick or "—",
        branch=branch or "Не состоит",
    )


def new_application(user, user_id, exp, forum) -> bytes:
    """🚀 Новая заявка: 🆔 пользователь / ID, 📨 опыт, 🔗 форум"""
    return render("new_application", user=user or "—", user_id=user_id, exp=exp or "—", forum=forum or "—")


def payout_request(user, user_id, amount, wallet) -> bytes:
    """💰 Заявка на выплату (админам): 🆔 пользователь / ID, ⚡ сумма, 👛 кошелек"""
    return render("payout_request", user=user or "—", user_id=user_id, amount=money(amount), wallet=wallet or "—")


def _num(value) -> str:
    """3213123.0 -> '3 213 123', 450.5 -> '450.5'."""
    try:
        value = round(float(value or 0), 2)
    except (TypeError, ValueError):
        return str(value)
    text = f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}".rstrip("0").rstrip(".")
    return text.replace(",", " ")


def _delta(new, old, suffix="") -> str:
    if old is None:
        return ""
    diff = round(float(new or 0) - float(old or 0), 2)
    if diff > 0:
        return f" (+{_num(diff)}{suffix})"
    if diff < 0:
        return f" (-{_num(-diff)}{suffix})"
    return ""


def promo_stats(promo_data: dict, snapshot: dict | None = None) -> bytes:
    """👀 Статистика по промокоду: 💵 сумма, 🎰 отыгрыш, 🧟 активации, 💎 депозиты.
    promo_data -- dict from promo_view_stats(); snapshot -- previous data, adds (+N) to activations and deposits."""
    snapshot = snapshot or {}
    acts = promo_data.get("activations", 0)
    deps = promo_data.get("deposits", 0)
    return render(
        "promo_stats",
        name=promo_data.get("name", ""),
        amount=f"{_num(promo_data.get('amount'))} $",
        wager="включен" if promo_data.get("shouldWager") else "отключен",
        activations=f"{_num(acts)}{_delta(acts, snapshot.get('activations'))}",
        deposits=f"{_num(deps)} ${_delta(deps, snapshot.get('deposits'), ' $')}",
    )
