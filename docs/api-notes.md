# Notes on the undocumented ranobelib API

Living document of findings about the `api.cdnlibs.org` API, gathered by manual inspection
(browser devtools / network tab) before implementing the corresponding SDK feature. Update
this file as new endpoints or edge cases are investigated — see `CLAUDE.md` for the current
list of open questions.

## Confirmed

- Base URL: `https://api.cdnlibs.org/api`, no authorization required for public content.
- `GET /api/manga/{slug}/chapters` returns the full chapter list (including fractional
  `number_secondary` chapters) in a single response, keyed under `"data"`. No pagination
  observed so far on a 308-chapter title.
- `GET /api/manga/{slug}?fields[]=...` returns title metadata; the full set of useful
  `fields[]` values has not been catalogued yet.

## Open questions

See the "Что НЕ проверено" section of `CLAUDE.md` for the current list: chapter content
endpoint/format, `number_secondary` default for non-fractional chapters, illustration CDN
structure, paywall/403 behavior, and `/chapters` pagination for very large titles.
