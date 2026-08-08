"""List/search the ranobelib.me catalog with Catalog.list_titles().

Catalog is a separate entry point from RanobeLib: browsing/searching the whole site isn't
scoped to any one title, so it doesn't belong on the class that's built around a title's URL.
It reuses the same Title model as RanobeLib.get_info() for each list item, just with some
fields (genres, summary, chapter_count, ...) left at their defaults, since the catalog
listing endpoint doesn't send them.
"""

import asyncio

from ranobelib import Catalog


async def main() -> None:
    # Catalog is also an async context manager, same reasoning as RanobeLib: it owns an
    # httpx.AsyncClient and closes it on exit. No title URL is needed to construct it.
    async with Catalog() as catalog:
        # Free-text search matches against name/rus_name/eng_name. Results come back as a
        # CatalogPage: `.items` (list[Title]) plus `.has_next_page` to know whether to ask
        # for more without needing a separate "how many total results" call.
        page = await catalog.list_titles(query="dxd")
        print(f"page {page.page}, has_next_page={page.has_next_page}")
        for title in page.items[:5]:
            print(f"  {title.id}: {title.name} ({title.status.label})")

        # `genres`/`status` filter narrows results; `genres` is a list of ids because a
        # title can be filtered by more than one at once (it must have *all* of them, not
        # just any one — see docs/api-notes.md). There's no public way to look up which id
        # means which genre from this SDK, so ids have to come from elsewhere (e.g. the
        # site's own filter UI) — the SDK just passes them through.
        completed_page = await catalog.list_titles(status=2, per_page=10)
        print(f"\n{len(completed_page.items)} completed titles on page 1:")
        for title in completed_page.items[:5]:
            print(f"  {title.id}: {title.name}")

        # `sort` picks the ordering — despite the keyword name, this is sent to the API as
        # `sort_by`; a real `sort` parameter exists on the wire but the API silently ignores
        # it (see docs/api-notes.md). Default is "last_chapter_at" (most recently updated).
        newest_page = await catalog.list_titles(sort="created_at", per_page=10)
        print(f"\n5 newest titles: {[title.name for title in newest_page.items[:5]]}")


asyncio.run(main())

# Expected output (real run against the live site; new titles are added constantly, so the
# exact ids/names here will drift over time — that's the site changing, not a bug):
#
# page 1, has_next_page=True
#   261856: DxD : A Nameless Star (Онгоинг)
#   65799: DXD: Isekai Driver's Multiverse Retirement (Novel) (Завершён)
#   256087: DxD: Gambling With Fate (Онгоинг)
#   257880: DxD : Draconic Rebellion (Онгоинг)
#   248229: DxD: The Replication System! (Онгоинг)
#
# 10 completed titles on page 1:
#   270852: Heonteo Yeogo-ui Namseonsaeng
#   237172: dakeu pantajisog seong-gisa
#   199982: beulraekppaejo
#   91050: soseol sog magnaehwangjaga doeeossda (Novel)
#   37072: mungwalado an joesonghan isegyelo gam
#
# 5 newest titles: ['Проклятая песнь', 'Бремя Некро-Меча', 'The Enhanced Doctor', 'Я простой
# смертный, который встретил в обыкновенном кафе раненого величайшего святого', 'Wings of
# Reverie']
