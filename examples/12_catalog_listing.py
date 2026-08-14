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

        # `list_countries()` is the id -> name lookup for the `countries` filter below, same
        # pattern as `list_genres()` above (network-wide constants endpoint, filtered down to
        # ranobelib.me by Catalog). Despite the name, this covers more than literal countries
        # for ranobelib.me specifically — three real countries (Japan/Korea/China) plus three
        # non-national origin categories the site classifies the same way (original English,
        # original/non-translated, fanfiction) — see docs/api-notes.md.
        countries = await catalog.list_countries()
        print(f"\n{len(countries)} countries available: {[country.name for country in countries]}")
        korea = next(country for country in countries if country.name == "Корея")
        japan = next(country for country in countries if country.name == "Япония")

        # `countries` takes a list of ids, same shape as `genres`/`tags`, but with OR (not
        # AND) semantics — a title only ever has one country of origin, so it matches if that
        # country is *any* of the given ids, not all of them (requiring all would never match
        # past the first id). Every returned Title's `.country` reflects it (also populated on
        # RanobeLib.get_info() results, since it's the same model field). A single id still
        # works as a one-element list, e.g. `countries=[korea.id]`.
        korean_page = await catalog.list_titles(countries=[korea.id], per_page=10)
        print(f"\n5 titles from {korea.name}:")
        for title in korean_page.items[:5]:
            print(f"  {title.id}: {title.name}")

        jp_or_kr_page = await catalog.list_titles(
            countries=[japan.id, korea.id], per_page=10, sort="name"
        )
        print(f"\n5 titles from {japan.name} or {korea.name} (mixed):")
        for title in jp_or_kr_page.items[:5]:
            origin = title.country.name if title.country else "?"
            print(f"  {title.id}: {title.name} ({origin})")

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
#   271317: Isegye Geomeun Meori Oegugin
#   268176: baedeu ending meikeo
#   25089: Jaeang-geub yeong-ungnim-i gwihwanhasyeossda
#   251723: I found a dragon egg
#   237642: Mòshì tiānzāi: Cóng dǎzào bìnàn suǒ kāishǐ
#
# 10 completed titles on page 1:
#   244924: guwon, geu janhogham-e daehayeo
#   271058: Kuàichuān gōnglüè: Yāoniè sùzhǔ, kāiguà le
#   57693: don-eulo yaghonjaleul
#   271317: Isegye Geomeun Meori Oegugin
#   268176: baedeu ending meikeo
#
# 6 countries available: ['Япония', 'Корея', 'Китай', 'Английский', 'Авторский', 'Фанфик']
#
# 5 titles from Корея:
#   244924: guwon, geu janhogham-e daehayeo
#   57693: don-eulo yaghonjaleul
#   49961: Geumbal-ui jeonglyeongs
#   267643: lopan sog haegunjedog-i doeeossda
#   271317: Isegye Geomeun Meori Oegugin
#
# 5 titles from Япония or Корея (mixed):
#   16498: 잔여 포인트 999999999999P (Novel) (Корея)
#   214726: ■■ eul wihan segyeneun eobsda (Корея)
#   227524: √4: Uchi no Juunin wa Minna Ijou desu (Япония)
#   55978: Я получил читерные способности в другом мире и стал экстраординарным в реальном~
#   повышение уровня изменило мою жизнь~ (Novel) (Япония)
#   231169: Я не ищу связей на одну ночь (Новелла) (Корея)
#
# 10 'Боги' titles on page 1:
#   271058: Kuàichuān gōnglüè: Yāoniè sùzhǔ, kāiguà le
#   267643: lopan sog haegunjedog-i doeeossda
#   25089: Jaeang-geub yeong-ungnim-i gwihwanhasyeossda
#   232975: Jiuri zhi lu
#   270776: Yongsapati Beorimbadeun Saje
#
# 5 newest titles: ['Salajin sindelella', 'Warden of the Mysteries', 'In all his overwhelming
# tenacity', 'Ekseuteoui 2hoechaneun Goemul Baeuda', 'Avatar: The Rise of Kyoshi']
