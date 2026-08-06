"""Fetch title metadata with RanobeLib.get_info().

get_info() is the cheapest call in the SDK: one request to the title metadata endpoint,
returning a Title model (name, status, genres, authors, etc.) without touching the chapter
list or any chapter content at all.
"""

import asyncio

from ranobelib import RanobeLib


async def main() -> None:
    # RanobeLib is an async context manager: it owns the underlying httpx.AsyncClient and
    # closes it on exit, so always use `async with` rather than instantiating it bare.
    # The only required argument is the title's URL (any ranobelib.me title page works).
    async with RanobeLib("https://ranobelib.me/ru/book/6712--high-school-dxd-novel") as lib:
        info = await lib.get_info()

        # `name` is the original (usually Japanese/romanized) title, `rus_name` is the
        # Russian translation of the title itself — both come straight from the API,
        # neither is derived from the other.
        print(info.name)
        print(info.rus_name)

        # `status` is an enum-like model; `.label` is its human-readable Russian text as
        # ranobelib.me shows it ("Завершён", "Онгоинг", ...).
        print(info.status.label)

        # Total chapter count as reported by the site itself, not computed by the SDK.
        print(info.chapter_count)

        # `genres` is a list of Genre models; slicing keeps the printed output short.
        print([genre.name for genre in info.genres[:5]])


asyncio.run(main())

# Expected output (real run against the live site):
#
# Haisukuru Di Di (Novel)
# Старшая школа D×D (Новелла)
# Завершён
# 308
# ['Боевик', 'Боевые искусства', 'Вампиры', 'Гарем', 'Драма']
