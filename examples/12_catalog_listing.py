"""List/search the ranobelib.me catalog with Catalog.list_titles()/list_genres()/list_countries().

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

        # `list_genres()` is the id -> name lookup for the `genres` filter below: it fetches
        # every genre ranobelib.me actually uses (the underlying API endpoint covers the
        # whole lib.social network at once, tagged by site — Catalog filters that down to
        # ranobelib for you, see docs/api-notes.md), cached on disk like list_titles().
        genres = await catalog.list_genres()
        print(f"{len(genres)} genres available, e.g.: {[genre.name for genre in genres[:5]]}")
        action_genre = next(genre for genre in genres if genre.name == "Боевик")

        # `genres`/`status` filter narrows results; `genres` is a list of ids because a
        # title can be filtered by more than one at once (it must have *all* of them, not
        # just any one — see docs/api-notes.md). Ids come from list_genres() above, or from
        # the site's own filter UI.
        action_page = await catalog.list_titles(genres=[action_genre.id], per_page=10)
        print(f"\n5 '{action_genre.name}' titles:")
        for title in action_page.items[:5]:
            print(f"  {title.id}: {title.name}")

        completed_page = await catalog.list_titles(status=2, per_page=10)
        print(f"\n{len(completed_page.items)} completed titles on page 1:")
        for title in completed_page.items[:5]:
            print(f"  {title.id}: {title.name}")

        # `list_countries()` is the id -> name lookup for the `country` filter below, same
        # pattern as `list_genres()` above (network-wide constants endpoint, filtered down to
        # ranobelib.me by Catalog). Despite the name, this covers more than literal countries
        # for ranobelib.me specifically — three real countries (Japan/Korea/China) plus three
        # non-national origin categories the site classifies the same way (original English,
        # original/non-translated, fanfiction) — see docs/api-notes.md.
        countries = await catalog.list_countries()
        print(f"\n{len(countries)} countries available: {[country.name for country in countries]}")
        korea = next(country for country in countries if country.name == "Корея")

        # `country` takes a single id, unlike `genres` — a title only has one country of
        # origin. Every returned Title's `.country` reflects it (also populated on
        # RanobeLib.get_info() results, since it's the same model field).
        korean_page = await catalog.list_titles(country=korea.id, per_page=10)
        print(f"\n5 titles from {korea.name}:")
        for title in korean_page.items[:5]:
            print(f"  {title.id}: {title.name}")

        # `tags` filters the same way `genres` does (AND semantics — a title must have
        # *all* given tag ids, confirmed against the live API even though tags are more
        # numerous/specific than genres, see docs/api-notes.md), but there's no
        # `list_countries()`/`list_genres()`-style `list_tags()` lookup: unlike genres/
        # countries, this SDK's own tag ids/names only ever come from a Title already
        # fetched elsewhere (e.g. `title.tags` from `RanobeLib.get_info()`, or from a
        # previous catalog result's `.tags` — though catalog listing items don't send
        # `tags`, same as `genres`). 218 = "Боги" (Gods), found that way in a real title.
        tag_page = await catalog.list_titles(tags=[218], per_page=10)
        print(f"\n{len(tag_page.items)} 'Боги' titles on page 1:")
        for title in tag_page.items[:5]:
            print(f"  {title.id}: {title.name}")

        # `sort` picks the ordering — despite the keyword name, this is sent to the API as
        # `sort_by`; a real `sort` parameter exists on the wire but the API silently ignores
        # it (see docs/api-notes.md). Default is "last_chapter_at" (most recently updated).
        newest_page = await catalog.list_titles(sort="created_at", per_page=10)
        print(f"\n5 newest titles: {[title.name for title in newest_page.items[:5]]}")


asyncio.run(main())

# Expected output (real run against the live site; new titles are added constantly and the
# genre list can change too, so the exact ids/names here will drift over time — that's the
# site changing, not a bug):
#
# page 1, has_next_page=True
#   261856: DxD : A Nameless Star (Онгоинг)
#   65799: DXD: Isekai Driver's Multiverse Retirement (Novel) (Завершён)
#   256087: DxD: Gambling With Fate (Онгоинг)
#   257880: DxD : Draconic Rebellion (Онгоинг)
#   248229: DxD: The Replication System! (Онгоинг)
# 54 genres available, e.g.: ['Арт', 'Безумие', 'Боевик', 'Боевые искусства', 'Вампиры']
#
# 5 'Боевик' titles:
#   135591: Reaper of the Drifting Moon (Novel)
#   227705: Shepherd Wizard
#   43981: Metcha shōkan sa reta kudan (Novel)
#   166389: Già Thiên
#   243244: Yǐ yī lóng zhī lì dǎdǎo zhěnggè shìjiè!
#
# 10 completed titles on page 1:
#   270852: Heonteo Yeogo-ui Namseonsaeng
#   135591: Reaper of the Drifting Moon (Novel)
#   227705: Shepherd Wizard
#   18802: Xiu Zhen Liao Tian Qun
#   166389: Già Thiên
#
# 6 countries available: ['Япония', 'Корея', 'Китай', 'Английский', 'Авторский', 'Фанфик']
#
# 5 titles from Корея:
#   227705: Shepherd Wizard
#   135591: Reaper of the Drifting Moon (Novel)
#   214246: gwedame tteoreojyeodo chulgeuneul haeya haneunguna
#   40022: agdang daegongnim-ui gwihadigwihan yeodongsaeng
#   268050: I'll Become the Academy Gacha Villain
#
# 10 'Боги' titles on page 1:
#   6720: Tondemo Skill de Isekai Hourou Meshi (WN)
#   243244: Yǐ yī lóng zhī lì dǎdǎo zhěnggè shìjiè!
#   271058: Kuàichuān gōnglüè: Yāoniè sùzhǔ, kāiguà le
#   227705: Shepherd Wizard
#   265281: Harem System In A fantasy World
#
# 5 newest titles: ['Chwimi Bangsongimnida', 'Ropan Sok Choijongboseuneun Deo Isang Chamji
# Anneunda', 'domangchin agonganeuro EX-ga Jjotawatta', 'Kimi wa Boku no Regret', 'Ani,
# jeoneun hwangnyeonimman kkosyeotdanikkayo?']
