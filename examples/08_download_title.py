"""Download an entire title in one call with RanobeLib.download_title().

download_title() fetches every chapter of a title without the caller having to enumerate
volumes/chapters by hand (compare to manually looping get_volumes() over every volume
number). Two things make it different from the other bulk methods:

1. `chapter_delay` — an extra pause *after each downloaded chapter*, on top of the
   ApiClient's own request pacing/backoff (see "Rate limiting" in CLAUDE.md). This is a
   bulk-download-specific courtesy delay, not a proxy for the client's internal settings,
   which stay client-only and aren't exposed through RanobeLib.
2. Translation ambiguity is resolved for the *whole title at once*: instead of raising on
   the first ambiguous chapter it finds (like get_chapter() does), it first checks every
   chapter, then raises a single MultipleTitleTranslationsError listing *all* ambiguous
   chapters together — so you're not stuck fixing one chapter, rerunning, hitting the next
   ambiguous one, rerunning again, and so on.
"""

import asyncio

from ranobelib import MultipleTitleTranslationsError, RanobeLib


async def main() -> None:
    # This title has no translation ambiguity, so download_title() just works with only the
    # bulk-download courtesy delay set.
    async with RanobeLib("https://ranobelib.me/ru/book/40195--enbizaka-no-shitateya") as lib:
        # Returns list[Volume], the same shape get_table_of_contents() returns, but with
        # every Chapter.content already downloaded.
        volumes = await lib.download_title(chapter_delay=0.5)
        for volume in volumes:
            print(volume.number, [chapter.number for chapter in volume.chapters])

    # This title, by contrast, has several chapters with more than one translation branch.
    slug = "113306--bungou-stray-dogs-gaiden-ayatsuji-yukito-vs-kyogoku-natsuhiko"
    async with RanobeLib(f"https://ranobelib.me/ru/book/{slug}") as lib:
        try:
            # No branch_id/translation_index passed -> default behavior: raise once all
            # ambiguous chapters have been collected.
            await lib.download_title()
        except MultipleTitleTranslationsError as exc:
            print(f"{len(exc.chapters)} ambiguous chapter(s):")
            for chapter in exc.chapters:
                print(" ", chapter.volume, chapter.number, [b.branch_id for b in chapter.branches])

        # translation_index=0 resolves every ambiguous chapter by picking the first branch
        # *in that chapter's own branch list* — not a shared branch_id across chapters (see
        # the note below about why chapter "1" ends up with a different team than "0"/"2").
        volumes = await lib.download_title(translation_index=0)
        print([chapter.number for chapter in volumes[0].chapters])


asyncio.run(main())

# Expected output (real run against the live site):
#
# 1 ['0', '1']
# 3 ambiguous chapter(s):
#   1 0 [12954, 12955]
#   1 1 [12955, 12954]
#   1 2 [12954, 12955]
# ['0', '1', '2', '3', '4', '5']
#
# Note chapter "1"'s branches are listed in the opposite order from chapters "0"/"2" above —
# translation_index=0 resolves by each chapter's own branch order, not a shared branch_id,
# which is why it ends up picking a different team for chapter "1" than for "0"/"2" here.
# Use branch_id instead of translation_index when you know the specific translation you
# want and it's shared across chapters (same idea as 07_translation_selection.py, applied
# title-wide).
