# Notes on the undocumented ranobelib API

Living document of findings about the `api.cdnlibs.org` API, gathered by manual inspection
(browser devtools / network tab) before implementing the corresponding SDK feature. Update
this file as new endpoints or edge cases are investigated — see `CLAUDE.md` for the current
list of open questions.

## Confirmed

- Base URL: `https://api.cdnlibs.org/api`, no authorization required for public content.
- `GET /api/manga/{slug}/chapters` returns the full chapter list (including fractional
  chapters) in a single response, keyed under `"data"`. No pagination observed so far on a
  308-chapter title.
- `GET /api/manga/{slug}?fields[]=...` returns title metadata; the full set of useful
  `fields[]` values has not been catalogued yet.

### Site scoping: `Site-Id` header

`api.cdnlibs.org` is shared across the whole lib.social network (mangalib, ranobelib,
hentailib, ...). Title-detail and chapter-list endpoints (`GET /api/manga/{slug_url}`,
`GET /api/manga/{slug_url}/chapters`) need a `Site-Id: 3` request header to scope the lookup
to ranobelib.me — `3` is the value found in `<html data-id="3">` on ranobelib.me pages.
Without this header (or with the wrong site id), a request for a real, existing title
returns **404** with the same generic body as an actually-missing title:

```json
{"data": {"toast": {"type": "silent", "message": "Not Found"}}}
```

i.e. a bare 404 from this API does not distinguish "wrong site" from "title doesn't exist" —
the SDK always sends the correct header, so in practice this collapses to `TitleNotFoundError`.

The `GET /api/manga` search/list endpoint uses a *different* mechanism: a `site_id[]=3` query
parameter instead of the header (e.g. `GET /api/manga?q=foo&site_id[]=3`).

### `Accept: application/json` is required for JSON error bodies

On error status codes (404 confirmed), the API serves an HTML SPA shell (the site's own
404 page) unless the request sends `Accept: application/json` — with that header it serves
the JSON error body shown above instead. Successful (2xx) responses are JSON either way. The
SDK client sends `Accept: application/json` on every request to avoid parsing HTML by
accident.

### `get_info()` — verified `fields[]` list

Confirmed against a real title (`91443--new-hero-in-dxd`) with
`Site-Id: 3` + `Accept: application/json`:

```
GET /api/manga/{slug_url}?fields[]=background&fields[]=eng_name&fields[]=otherNames
    &fields[]=summary&fields[]=releaseDate&fields[]=genres&fields[]=tags&fields[]=teams
    &fields[]=authors&fields[]=artists&fields[]=chap_count
```

Notes on individual fields, since the mapping from requested `fields[]` name to response key
is not always 1:1:

- `chap_count` does **not** add a `chap_count` key — it surfaces `items_count: {"uploaded":
  int, "total": int}` instead. `uploaded` is the actual number of published chapters; this is
  what the SDK's `Title.chapter_count` is populated from.
- `status_id` (not currently requested by the SDK) surfaces `scanlateStatus: {"id", "label"}`
  — the *translation* status (e.g. "Заброшен" / abandoned by the team), distinct from the
  title's own `status` field (e.g. "Онгоинг" / ongoing), which is present by default without
  requesting any extra fields.
- `summary` is prosemirror-doc JSON (`{"type": "doc", "content": [...]}`). The SDK flattens
  it to plain text by concatenating `text` leaves paragraph by paragraph — deliberately
  simpler than the chapter-content renderer below, since a title summary doesn't need
  bold/italic/images preserved the way chapter content does.
- Fields present without being requested: `id`, `name`, `rus_name`, `eng_name`, `model`,
  `slug`, `slug_url`, `cover`, `ageRestriction`, `site`, `type`, `is_licensed`,
  `content_marking`, `status`, `releaseDateString`.

### Title URL / slug format

A title URL like `https://ranobelib.me/ru/book/91443--new-hero-in-dxd` (locale prefix is
optional — `/book/91443--new-hero-in-dxd` also resolves) has the API's `slug_url`
(`{numeric_id}--{slug}`) as its last path segment. The SDK extracts this segment and uses it
directly as the path parameter for `/api/manga/{slug_url}` — no separate slug/id lookup step
needed.

### `number_secondary` is not a chapter-number fraction — it mirrors `volume`

CLAUDE.md's original notes guessed `number_secondary` was the fractional part of a chapter
number (e.g. `number_secondary: "5"` on a `number: "51"` chapter, read as chapter `"51.5"`).
Verified against three different titles totaling 667 chapters (`6712--high-school-dxd-novel`,
308 chapters, 25 volumes; `147836--o-moem-pererozdenii-v-bessmertnogo`, 84 chapters, 8
volumes, including fractional chapter numbers `"6.5"`/`"81.5"`; `11407--solo-leveling`, 275
chapters including 20 multi-team-branch chapters): **`number_secondary` equals `volume` in
every single case, zero exceptions.** The exact example the original guess was based on
(`volume: "5", number: "51", number_secondary: "5"`) fits this pattern too — it wasn't a
coincidental fraction, `number_secondary` was just echoing the volume.

The actual fractional part of a chapter number, when present, is already embedded directly
in the `number` field as a string (`"6.5"`, `"81.5"`, `"0.1"`) — there is no separate field
for it. This means the SDK's `get_chapter`/`get_chapters`/`get_translations` take `number:
str` as-is from the API instead of a separate `number_secondary` parameter; see CLAUDE.md's
"Публичный API" section for the corrected signatures (this was originally documented
differently, based on the wrong guess above, before `get_table_of_contents` was
implemented).

### Chapter content: endpoint, and two different content formats

```
GET /api/manga/{slug_url}/chapter?number={number}&volume={volume}&branch_id={branch_id}
```

`number`/`volume` match `CLAUDE.md`'s guessed pattern exactly (first try). `branch_id` is
optional; confirmed working against a title with two translation teams (`11407--solo-leveling`,
chapter `volume=1, number=0`, `branch_id=2251` vs `branch_id=635` returned that branch's own
`teams`). **Without `branch_id`, the API did not pick `branches[0]` from the chapter-list
response** — it returned the *older* of the two branches (created 2019 vs 2020). Default
branch selection is not simply "first in the list"; needs its own investigation before
implementing team selection / `MultipleTranslationsError` (roadmap step 9). 404 on an
unknown `number`/`volume` combination returns the same generic body as title-not-found.

The single-chapter response shape differs from a chapter's entry in the `/chapters` list:
no `index`/`item_number`/`branches_count`/`branches` — instead a singular `branch_id` and a
flat `teams` array (the teams for *that* branch specifically, can be empty even when the
chapter has a team in the list endpoint's `branches[].teams`). Extra fields not modeled:
`moderated`, `likes_count`, `is_liked`, `is_viewed`, `expired_type`, `expired_at`,
`publish_at`, `translation_quality_rating`, `bundle`, `manga_id`, `created_at`.

**Content is not always prosemirror-doc JSON**, despite CLAUDE.md's original suspicion
(reasonable at the time, based on `ranobelib-loader`'s upload format and `Title.summary`
being prosemirror). Sampled all 308 chapters of `6712--high-school-dxd-novel`'s `content`
field (some requests hit 429 partway through — sample is 273 successfully fetched chapters,
still large enough to be conclusive):

- **235 chapters (~86%): `content` is an HTML string**, e.g.
  `<p data-paragraph-index="1">text</p><p data-paragraph-index="2">text</p>`. Tags observed
  across samples from two titles: `p`, `img`, `em`, `strong`, `b`, `i` (inconsistent between
  `<em>/<strong>` and `<b>/<i>` for the same semantic meaning — presumably different editor
  versions over the site's history; both pairs occur, never mixed within one chapter in the
  samples checked). `data-paragraph-index` looks like a pure editor artifact, safe to ignore.
  Image `<img>` tags carry an already-absolute `src`, e.g.
  `<img loading="lazy" src="https://ranobelib.me/uploads/ranobe/{slug}/chapters/{chapter_id}/{filename}" />`.
- **38 chapters (~14%): `content` is prosemirror-doc JSON** (`{"type": "doc", "content":
  [...]}`), matching `Title.summary`'s format. Node types observed: `paragraph` (can have no
  `content` key at all for a blank line; can carry `attrs: {"textAlign": "center"}` — not
  currently reproduced in the SDK's HTML output, a known gap), `image` (block-level, sibling
  to paragraphs, not nested inside one), `hardBreak`, `horizontalRule`. Mark types on `text`
  nodes: `bold`, `italic`. No headings/lists/blockquotes observed in the sample.
- The `content` format is a **per-chapter** property, not per-title or per-team — seen both
  formats within the same title.

**Image resolution for the prosemirror format**: an `image` node doesn't carry a URL
directly, only an opaque id: `{"type": "image", "attrs": {"images": [{"image":
"9bb930b8-...-f717bf"}]}}`. The response's top-level `attachments` array resolves it — find
the entry whose `name` equals that id, then prepend `https://ranobelib.me` to its `url`
(relative, e.g. `/uploads/ranobe/{slug}/chapters/{chapter_id}/{filename}.{extension}`) to
get the same absolute URL shape the HTML-string format embeds directly. `attachments` is
empty (`[]`) for chapters with no images, present alongside either content format.

The SDK normalizes both formats into a single HTML fragment on `Chapter.content` (string
format: passed through as-is; prosemirror format: rendered with the same tag vocabulary —
`<p>`, `<img loading="lazy" src="...">`, `<strong>`, `<em>`, `<br />`, `<hr />` — so
exporters only ever handle one shape), see `models.py`.

### No bulk "volume content" endpoint

Checked for a shortcut before implementing `get_volume()` (fetch a whole volume's chapters
in fewer requests than one-per-chapter): `GET /api/manga/{slug}/volume?volume=1`,
`GET /api/manga/{slug}/volumes` both 404. `GET /api/manga/{slug}/chapter?volume=1` (omitting
`number`) returns **422** with `{"data": {"number": ["Поле number обязательно для
заполнения."]}}` — `number` is a required parameter, confirming there's no way to fetch a
volume's chapters in one call. `get_volume()` fetches the chapter list once (to find which
numbers belong to the requested volume), then fetches each of those chapters individually,
same as calling `get_chapter()` in a loop. Sequential, not concurrent — no rate-limit/retry
handling exists yet (roadmap step 11), so no concurrency control to bound it either.

## Open questions

See the "Что НЕ проверено" section of `CLAUDE.md` for the current list: how a fractional
`number` affects the reading URL, illustration CDN structure for the `p`/`img`-only cases
(confirmed to be `ranobelib.me` itself, not a separate CDN — see above, so this is largely
resolved, but worth re-confirming CDN domain doesn't vary by title/region), paywall/403
behavior, `/chapters` pagination for very large titles, default branch/team selection logic
(see chapter-content section above), and reproducing `textAlign`/heading/list formatting
from the prosemirror format if it turns out to matter for exports.
