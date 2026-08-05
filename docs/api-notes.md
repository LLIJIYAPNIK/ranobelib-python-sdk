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
- `summary` is prosemirror-doc JSON (`{"type": "doc", "content": [...]}`), confirming the
  suspicion from the original notes — chapter content (still unresearched, see below)
  presumably uses the same document format. The SDK flattens it to plain text by
  concatenating `text` leaves paragraph by paragraph; this is a minimal parser and will need
  to be revisited (bold/italic/headings/lists) when chapter content is implemented.
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

## Open questions

See the "Что НЕ проверено" section of `CLAUDE.md` for the current list: chapter content
endpoint/format, how a fractional `number` affects the reading URL, illustration CDN
structure, paywall/403 behavior, and `/chapters` pagination for very large titles.
