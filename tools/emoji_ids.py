"""Prints custom_emoji_id for every emoji in a custom emoji pack.

Usage: python tools/emoji_ids.py <BOT_TOKEN> [set_name]
"""
import json
import sys
import urllib.parse
import urllib.request

SET_NAME = "emerald_by_EmrldWork_bot"


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python tools/emoji_ids.py <BOT_TOKEN> [set_name]")
    token = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else SET_NAME

    url = f"https://api.telegram.org/bot{token}/getStickerSet?" + urllib.parse.urlencode({"name": name})
    with urllib.request.urlopen(url) as r:
        data = json.load(r)
    if not data.get("ok"):
        sys.exit(data.get("description", "request failed"))

    stickers = data["result"]["stickers"]
    print(f"# {data['result']['title']} — {len(stickers)} emoji\n")
    for i, s in enumerate(stickers, 1):
        emoji = s.get("emoji", "⭐")
        eid = s["custom_emoji_id"]
        print(f'E{i} = \'<tg-emoji emoji-id="{eid}">{emoji}</tg-emoji>\'  # {emoji}')


if __name__ == "__main__":
    main()
