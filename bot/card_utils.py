"""Helpers for sending Emerald cards (photos) and editing messages that may be cards."""
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, FSInputFile, InputMediaPhoto

from emerald_cards import cards

_ANSWER_KWARGS = ("reply_markup", "parse_mode", "entities", "link_preview_options", "disable_web_page_preview")


def card(name):
    return FSInputFile(cards.static(name))


def card_photo(data):
    return BufferedInputFile(data, filename="emerald.jpg")


def _has_buttons(markup):
    return markup is not None and any(getattr(markup, "inline_keyboard", None) or [])


async def _delete(message):
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def answer_card(msg, photo, caption, **kwargs):
    # caption is limited to 1024 chars; longer text goes as a separate message
    if len(caption) <= 1024:
        return await msg.answer_photo(photo, caption=caption, **kwargs)
    await msg.answer_photo(photo)
    return await msg.answer(caption, **kwargs)


async def edit_text(message, text=None, *args, **kwargs):
    """message.edit_text that also works when the message is a card:
    a photo can't become a text message, so it is replaced with a new one."""
    if not message.photo:
        return await message.edit_text(text, *args, **kwargs)
    send = {k: v for k, v in kwargs.items() if k in _ANSWER_KWARGS}
    if "reply_markup" in send and not _has_buttons(send["reply_markup"]):
        send.pop("reply_markup")
    await _delete(message)
    return await message.answer(text, **send)


async def edit_card(message, photo, caption, reply_markup=None, **kwargs):
    """Show a card in place of the message (edits a photo, replaces a text message)."""
    if message.photo:
        return await message.edit_media(
            InputMediaPhoto(media=photo, caption=caption, **kwargs), reply_markup=reply_markup
        )
    await _delete(message)
    return await message.answer_photo(photo, caption=caption, reply_markup=reply_markup, **kwargs)
