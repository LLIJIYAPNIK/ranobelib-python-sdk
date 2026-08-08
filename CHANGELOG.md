# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows [Semantic Versioning](https://semver.org/). Entries are generated from
[Conventional Commits](https://www.conventionalcommits.org/) messages by `cliff.toml` +
`.github/workflows/changelog.yml`, which regenerates this whole file and pushes it to
`main` whenever a GitHub Release is published — don't hand-edit released sections, fix the
underlying commit message/PR title instead and let the next release regenerate this file.

## [0.6.0] - 2026-08-08

### Added

- Add ApiClient.list_titles for catalog browsing
- Add Catalog entry point for listing/searching titles

## [0.5.0] - 2026-08-07

### Added

- Add on_chapter progress callback to download_title()

## [0.4.1] - 2026-08-06

### Fixed

- Cancel superseded docs deploy runs instead of queueing them
- Sanitize HTML-string chapter content, not just prosemirror

## [0.4.0] - 2026-08-06

### Added

- Add chapter/volume size estimation and RanobeLib.estimate_title_size()
- Add interactive console output via verbosity parameter

### Fixed

- Stop dropping releases with only ci: commits from CHANGELOG.md

## [0.3.0] - 2026-08-06

### Changed

- Generate CHANGELOG.md from Conventional Commits via git-cliff

## [0.2.0] - 2026-08-06

### Added

- Add RanobeLib.download_title() for whole-title bulk downloads

## [0.1.0] - 2026-08-05

### Added

- Add exception hierarchy
- Add title URL/slug parsing
- Add async API client for title metadata
- Add Title model with prosemirror summary parsing
- Add RanobeLib facade with get_info
- Add Chapter and Volume models
- Add get_chapters to the API client
- Add get_table_of_contents to RanobeLib
- Add ChapterNotFoundError
- Normalize chapter content to HTML on Chapter.content
- Add ApiClient.get_chapter
- Add RanobeLib.get_chapter
- Add VolumeNotFoundError
- Add RanobeLib.get_volume
- Add RanobeLib.get_chapters
- Add RanobeLib.get_volumes
- Add MultipleTranslationsError
- Add branch_id translation selection to RanobeLib
- Add DiskCache
- Cache raw API responses in RanobeLib
- Add concurrency limiting and retry with backoff to ApiClient
- Add Exporter protocol and format registry
- Add TxtExporter
- Add RanobeLib.export
- Add Fb2Exporter
- Add EpubExporter
- Add PdfExporter
- Set up the mkdocs-material documentation site

### Changed

- Add GitHub Actions workflow
- Add docs build check to ci.yml and a deploy workflow
- Upload coverage to Coveralls from the test job
- Add release.yml to publish to PyPI via Trusted Publishing

### Fixed

- Pin setup-uv to an existing tag
- Make Exporter.export async

[0.6.0]: https://github.com/LLIJIYAPNIK/ranobelib-python-sdk/compare/v0.5.0..v0.6.0
[0.5.0]: https://github.com/LLIJIYAPNIK/ranobelib-python-sdk/compare/v0.4.1..v0.5.0
[0.4.1]: https://github.com/LLIJIYAPNIK/ranobelib-python-sdk/compare/v0.4.0..v0.4.1
[0.4.0]: https://github.com/LLIJIYAPNIK/ranobelib-python-sdk/compare/v0.3.0..v0.4.0
[0.3.0]: https://github.com/LLIJIYAPNIK/ranobelib-python-sdk/compare/v0.2.0..v0.3.0
[0.2.0]: https://github.com/LLIJIYAPNIK/ranobelib-python-sdk/compare/v0.1.0..v0.2.0
[0.1.0]: https://github.com/LLIJIYAPNIK/ranobelib-python-sdk/tree/v0.1.0

