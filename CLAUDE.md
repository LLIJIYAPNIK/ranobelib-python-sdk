# CLAUDE.md

Инструкции для Claude Code при работе над репозиторием **ranobelib-python-sdk**.

## О проекте

Python SDK для сайта ranobelib.me: получение метаданных тайтла, скачивание глав/томов и
экспорт в epub/fb2/txt/pdf. SDK дёргает недокументированный, но открытый JSON API сети
lib.social (`api.cdnlibs.org`), а не парсит HTML.

Пакет публикуется как `ranobelib-python-sdk` (репозиторий и PyPI-имя), импортируется как
`ranobelib`.

Код, докстринги, комментарии, README и публичная документация — **на английском**
(стандарт для OSS-пакета на PyPI). Issue/PR-описания и коммуникация с пользователем внутри
таск-трекера могут быть на русском, если пользователь сам пишет по-русски.

## Ключевые технические решения (зафиксированы, не пересматривать без явного запроса)

| Область | Решение |
|---|---|
| HTTP-клиент | `httpx.AsyncClient`, только async, без sync-обёртки |
| Модели данных | pydantic v2 |
| Менеджер пакетов | `uv` (никаких pip/poetry/pipenv в проекте) |
| Минимальная версия Python | 3.11 |
| Авторизация | не реализуется в MVP (только открытый контент) |
| CLI | не делаем, только библиотека |
| PDF | WeasyPrint (HTML/CSS → PDF, общий HTML-шаблон с epub/fb2) |
| Иллюстрации | обложка тайтла + картинки внутри глав встраиваются в epub и pdf; в fb2/txt — без иллюстраций (fb2 технически поддерживает картинки, но в MVP не подключаем, чтобы не усложнять — если понадобится, отдельный PR) |
| Тесты API | VCR-кассеты: `pytest-recording` + `vcrpy` |
| Покрытие тестами | 95%+, проверяется в CI (`--cov-fail-under=95`) |
| Линт/форматирование | `ruff` (lint + format) |
| Типизация | `mypy --strict` (или разумно близко к strict) |
| Документация | `mkdocs-material` + `mkdocstrings`, деплой на GitHub Pages |
| Лицензия | MIT |
| Git workflow | атомарные коммиты по фиче, один PR на фичу, merge — вручную пользователем |

## Публичный API (контракт SDK)

Главная точка входа — класс `RanobeLib`, инициализируется ссылкой на тайтл:

```python
from ranobelib import RanobeLib

async with RanobeLib("https://ranobelib.me/ru/book/6712--high-school-dxd-novel") as lib:
    info = await lib.get_info()                       # метаданные тайтла
    toc = await lib.get_table_of_contents()            # тома/главы/названия, без контента

    chapter = await lib.get_chapter(volume=6, number=51, number_secondary="6")
    volume = await lib.get_volume(volume=6)

    chapters = await lib.get_chapters([(6, "51", "6"), (6, "52", None)])
    volumes = await lib.get_volumes([1, 2, 3])

    translations = await lib.get_translations(volume=6, number=51, number_secondary="6")
    chapter = await lib.get_chapter(volume=6, number=51, number_secondary="6", team_id=...)

    await lib.export(chapters, fmt="epub", path="output.epub")
```

Требования из ТЗ и как они ложатся на методы:

1. Скачивание отдельной главы (том + номер главы, с учётом `number_secondary`) → `get_chapter`
2. Скачивание тома → `get_volume`
3. Скачивание нескольких глав → `get_chapters`
4. Скачивание нескольких томов → `get_volumes`
5. Вывод данных о тайтле (тома, главы, названия, контент) → `get_info`, `get_table_of_contents`,
   объекты `Chapter`/`Volume` с полем `.content`
6. Экспорт в epub/fb2/txt/pdf → `export()` с реестром экспортёров
7. Выбор перевода при наличии → `get_translations()` + параметр `team_id` во всех методах
   скачивания; если не указан и переводов несколько — либо явная ошибка
   `MultipleTranslationsError` с перечислением вариантов, либо детерминированный дефолт
   (первая команда по `branches`) — решить и задокументировать в первом PR, где это
   появится, не молчать об этом выборе.

Номера глав с дробной частью (`number_secondary`) передаются как отдельный опциональный
параметр, а не склеенная строка вида `"51.6"` — меньше просится на ошибки парсинга.

## Что уже известно про API (проверено вручную)

Базовый URL: `https://api.cdnlibs.org/api`. Запросы идут без авторизации, 200 OK,
CAPTCHA/Cloudflare не мешает базовым GET-запросам к `/api/manga/...`.

Список глав тайтла:

```
GET /api/manga/{slug}/chapters
```

Ответ: `{"data": [...]}`, каждый элемент:

```json
{
  "id": 187667,
  "index": 68,
  "item_number": 68,
  "volume": "5",
  "number": "51",
  "number_secondary": "5",
  "name": "Послесловие",
  "branches_count": 1,
  "branches": [
    {
      "id": 187667,
      "branch_id": null,
      "created_at": "2018-03-20T14:09:28.000000Z",
      "teams": [],
      "user": {"username": "DUB1401", "id": 4790}
    }
  ],
  "bundle_id": null
}
```

`number_secondary` — строка, может быть многозначной (встречалось `"10"`), это и есть
дробная часть номера главы (`c86.10`). Весь список, включая дробные главы, отдаётся одним
запросом — никакого перебора `.1`, `.2` и т.д. быть не должно, это заменяет то, что
обсуждалось в начале.

`branches` — переводы разных команд одной главы; при `branches_count > 1` есть выбор
перевода (пункт 7 из ТЗ), выбирается по `id`/`teams`.

Метаданные тайтла:

```
GET /api/manga/{slug}?fields[]=background&fields[]=eng_name&fields[]=otherNames&fields[]=summary&fields[]=releaseDate&fields[]=genres&fields[]=tags&fields[]=teams&fields[]=authors&fields[]=artists&fields[]=chap_count&fields[]=status_id&...
```

Список доступных `fields[]` не полностью каталогизирован — при реализации `get_info()`
свериться через devtools/network, какие поля реально нужны для наших моделей, и не тащить
лишнее.

### Что НЕ проверено и требует исследования перед реализацией (не гадать, не хардкодить наугад)

- Эндпоинт и формат содержимого главы (текст). Скорее всего `GET /api/manga/{slug}/chapter?number=...&volume=...&branch_id=...`
  или похожий, отдаёт какую-то структурированную разметку (судя по использованию prosemirror
  в соседнем проекте `ranobelib-loader` для *загрузки*, для *чтения* формат может быть
  HTML или prosemirror-doc JSON) — перед PR на скачивание контента главы нужно открыть
  реальную страницу главы в браузере, посмотреть Network-запросы и зафиксировать реальную
  структуру ответа в этом файле или в `docs/api-notes.md`.
- Что означает `number_secondary` для "обычных" глав без дробной части — `"0"` или `"1"`
  по умолчанию, и как это влияет на URL чтения (`/read/v{volume}/c{number}` без точки vs
  всегда с точкой). Проверить на паре примеров перед тем, как писать логику построения URL.
- Домен и структура CDN для картинок (встречался `cover.cdnlibs.org`, но для иллюстраций
  внутри глав нужно свериться отдельно).
- Поведение при 403/404/пейволле (платные/ранние главы, 18+ без токена) — коды ответа,
  тело ошибки. Нужно для нормальных кастомных исключений, а не голых `httpx.HTTPStatusError`.
- Есть ли пагинация у `/chapters` для очень больших тайтлов (у проверенного тайтла 308 глав
  пришли одним ответом, но не факт, что так всегда).

Каждый такой пункт закрывается коротким ручным исследованием (аналогично тому, как
уже сделано для списка глав) **до** написания продакшен-кода соответствующей фичи, и
результат фиксируется в PR (описание + при необходимости обновление этого файла).

## Структура репозитория

```
ranobelib-python-sdk/
├── src/
│   └── ranobelib/
│       ├── __init__.py          # публичный экспорт (RanobeLib, модели, исключения)
│       ├── client.py            # низкоуровневый HTTP-клиент к api.cdnlibs.org
│       ├── sdk.py                # класс RanobeLib — публичный фасад
│       ├── models.py             # pydantic-модели (Title, Chapter, Volume, Team, Branch, ...)
│       ├── exceptions.py
│       ├── cache.py              # дисковый кэш сырых ответов API
│       ├── numbering.py          # логика номеров глав / number_secondary / парсинг URL тайтла
│       └── exporters/
│           ├── __init__.py       # Protocol Exporter + реестр форматов
│           ├── txt.py
│           ├── fb2.py
│           ├── epub.py
│           └── pdf.py            # WeasyPrint, переиспользует HTML-шаблон из epub
├── tests/
│   ├── cassettes/                 # VCR-кассеты (записанные реальные ответы API)
│   ├── unit/
│   └── integration/                # тесты поверх кассет (используют реальные записанные данные)
├── docs/
│   ├── index.md
│   └── api-notes.md               # сюда складывать находки про недокументированный API
├── .github/workflows/
│   ├── ci.yml                     # появляется вместе с первым функциональным PR
│   └── docs.yml
├── pyproject.toml
├── README.md
├── LICENSE
└── CLAUDE.md
```

## Кэширование

Сырые JSON-ответы (метаданные тайтла, список глав, контент конкретной главы) кэшируются на
диск (`.ranobelib_cache/` в текущей директории по умолчанию, путь настраивается параметром
конструктора `RanobeLib(..., cache_dir=...)`). Цель — повторный экспорт в другой формат или
докачка новых глав не должны заново дёргать API за уже полученными данными. TTL и
принудительный `refresh=True` — предусмотреть, но не переусложнять в первой версии кэша.

## Rate limiting и ошибки

- Ограничение конкурентности: семафор на конфигурируемое число одновременных запросов
  (дефолт — разумное консервативное значение, например 5), плюс небольшая задержка между
  запросами по умолчанию.
- Retry с exponential backoff на 429 и 5xx (например через `tenacity` или ручную реализацию
  — на усмотрение реализующего PR, задокументировать выбор).
- Кастомные исключения в `exceptions.py`: `RanobeLibError` (база), `TitleNotFoundError`,
  `ChapterNotFoundError`, `VolumeNotFoundError`, `MultipleTranslationsError`,
  `AuthRequiredError` (для 403/платного контента — понятная ошибка вместо падения), `RateLimitError`.

## Экспорт

Общий интерфейс в `exporters/__init__.py`:

```python
class Exporter(Protocol):
    format: ClassVar[str]

    def export(self, title: Title, chapters: list[Chapter], output_path: Path) -> Path: ...

EXPORTERS: dict[str, type[Exporter]] = {}

def register(exporter: type[Exporter]) -> type[Exporter]: ...
```

Новый формат — новый файл в `exporters/`, декоратор `@register`, без правок ядра.
`txt` — самый простой формат, имеет смысл делать первым: так интерфейс `Exporter`
проверяется на практике до того, как в epub/pdf добавится сложность с картинками/вёрсткой.

## Документация

- Докстринги в Google-стиле для всех публичных классов/методов.
- `mkdocs.yml` + `mkdocstrings[python]` для автогенерации API-референса из докстрингов.
- `docs/api-notes.md` — живой документ с находками о недокументированном API ranobelib
  (эндпоинты, форматы полей, edge-кейсы) — обновлять по ходу реализации, не только в момент
  первого исследования.
- README.md: назначение проекта, установка (`uv add ranobelib-python-sdk` / `pip install`),
  quickstart-пример (аналогичный блоку из раздела "Публичный API" выше), ссылка на полную
  документацию.

## Git workflow

- Одна фича — одна ветка — один PR. Не смешивать несколько фич в одном PR.
- Именование веток: `feature/<короткое-описание>` (например `feature/chapters-listing`,
  `feature/epub-exporter`).
- Коммиты атомарные и осмысленные, конвенция — Conventional Commits
  (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`). Один коммит = одно логическое
  изменение, не "накопил и залил одним махом".
- **Никогда не мержить и не пушить в `main` напрямую.** PR открывается и оставляется на
  ревью — пользователь мержит вручную.
- Если следующая фича логически зависит от ещё не смерженного PR — либо явно спросить
  пользователя, с какой ветки продолжать, либо ответвиться от ветки предыдущей фичи и
  явно указать это в описании нового PR (потребуется ребейз после мержа зависимости).
- Перед открытием PR: локально прогнать `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy src`, `uv run pytest --cov`. Не открывать PR с падающими проверками.
- Каждый PR с новой фичей включает: код, тесты (держащие общее покрытие ≥95%), обновление
  докстрингов/документации, при необходимости — обновление `docs/api-notes.md`.

## CI (GitHub Actions)

CI появляется вместе с **первым PR, содержащим реальную функциональность** (первый клиент +
`get_info`), не раньше — на голом скелете проекта (структура папок, `pyproject.toml`, линт-конфиги)
CI не нужен.

`.github/workflows/ci.yml`, триггеры — `pull_request` и `push` в `main`:

- job `lint`: `uv run ruff check .`, `uv run ruff format --check .`
- job `typecheck`: `uv run mypy src`
- job `test`: матрица по Python 3.11 / 3.12 / 3.13, `uv run pytest --cov=ranobelib --cov-report=xml --cov-fail-under=95`
- job `build`: `uv build`, проверка, что пакет собирается

`.github/workflows/docs.yml`: сборка и деплой `mkdocs` на GitHub Pages при пуше в `main`
(отдельно от `ci.yml`, не блокирует PR).

Кэшировать `uv` (`astral-sh/setup-uv` с `enable-cache: true`) для скорости.

## Тестирование

- `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"` в конфиге).
- `pytest-recording` + `vcrpy` для тестов, которые бьют по `RanobeLib`/клиенту: кассеты в
  `tests/cassettes/<test_name>.yaml`, `record_mode="once"` (перезаписываются только вручную,
  через `--record-mode=rewrite`, если API поменялось).
- Модульные тесты без сети — для `numbering.py` (разбор `number`/`number_secondary`,
  парсинг URL тайтла из разных форматов ссылок), моделей (валидация pydantic на кривом
  JSON), исключений (маппинг статус-кодов → нужный exception), экспортёров (генерируемый
  epub/fb2 — проверять структуру через `ebooklib`/`lxml`, а не только "файл создался").
- Обязательно покрыть error-paths: 404 на несуществующую главу/том, 403 без авторизации,
  429 с ретраями, `MultipleTranslationsError` при нескольких командах без выбора.
- Порог покрытия — 95%, настроен в `pyproject.toml` (`[tool.coverage.report] fail_under = 95`)
  и продублирован флагом в CI. Закрывать метрику честными тестами поведения, а не
  `# pragma: no cover` на всём подряд.

## Порядок реализации фич (предлагаемая последовательность PR)

Ориентир для Claude Code — не жёсткий протокол, но не перескакивать вперёд через
незакрытые зависимости без необходимости:

1. **Scaffolding** — `uv init`, `pyproject.toml`, `ruff`/`mypy` конфиги, структура папок,
   `LICENSE` (MIT), заготовка README. Без функционала, без CI.
2. **HTTP-клиент + метаданные тайтла** (`get_info`) + базовые исключения + модели `Title`.
   Первый функциональный PR → добавляется `ci.yml`.
3. **Список глав и нумерация** (`get_table_of_contents`, `numbering.py`, обработка
   `number_secondary`, разбор URL тайтла).
4. **Исследование + реализация контента главы** (сначала ручное исследование эндпоинта,
   фиксация в `docs/api-notes.md`, потом код + модель `Chapter.content`).
5. **`get_chapter`** — скачивание одной главы.
6. **`get_volume`** — скачивание тома.
7. **`get_chapters`** — несколько глав.
8. **`get_volumes`** — несколько томов.
9. **Выбор перевода** — `get_translations`, параметр `team_id`, `MultipleTranslationsError`.
10. **Дисковый кэш** (`cache.py`) поверх уже готового клиента.
11. **Rate limiting + retry** в клиенте.
12. **Exporter-интерфейс + `txt`-экспортёр** (проверка интерфейса на простом формате).
13. **`fb2`-экспортёр**.
14. **`epub`-экспортёр** (+ обложка и иллюстрации).
15. **`pdf`-экспортёр** (WeasyPrint, переиспользование HTML-шаблона).
16. **Документация** — `mkdocs`, `docs.yml`, дописать README до полноценного quickstart.

Каждый пункт — отдельная ветка/PR по правилам из раздела Git workflow.
