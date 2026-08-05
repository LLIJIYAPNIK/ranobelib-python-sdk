# API reference

## Entry point

::: ranobelib.RanobeLib

## Models

::: ranobelib.Title

::: ranobelib.Chapter

::: ranobelib.Volume

::: ranobelib.ChapterBranch

## Exceptions

::: ranobelib.RanobeLibError

::: ranobelib.TitleNotFoundError

::: ranobelib.ChapterNotFoundError

::: ranobelib.VolumeNotFoundError

::: ranobelib.MultipleTranslationsError

::: ranobelib.AuthRequiredError

::: ranobelib.RateLimitError

## Exporters

Not re-exported from the top-level `ranobelib` package — import from `ranobelib.exporters`.
Adding a new export format is a new module in `ranobelib/exporters/` implementing
`Exporter` and decorated with `@register`; no changes needed elsewhere.

::: ranobelib.exporters.Exporter

::: ranobelib.exporters.register

::: ranobelib.exporters.EXPORTERS
    options:
      show_root_heading: false
      show_root_toc_entry: false
