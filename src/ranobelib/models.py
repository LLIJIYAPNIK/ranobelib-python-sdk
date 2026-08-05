"""Pydantic models: Title, Chapter, Volume, Team, Branch, and related types."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SITE_BASE_URL = "https://ranobelib.me"
"""Base URL used to resolve relative asset paths (e.g. in-chapter image attachments)."""


def _prosemirror_to_text(doc: dict[str, Any]) -> str:
    """Flatten a prosemirror-doc JSON structure into plain text paragraphs.

    This is a minimal parser (text leaves only, joined paragraph by paragraph) sufficient
    for a title's summary. Chapter content will need a richer version that preserves
    formatting (bold/italic/headings/lists) once that feature is implemented.
    """

    def extract(node: dict[str, Any]) -> str:
        if node.get("type") == "text":
            return str(node.get("text", ""))
        return "".join(extract(child) for child in node.get("content", []))

    paragraphs = [extract(block) for block in doc.get("content", [])]
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def _child_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = node.get("content") or []
    return content


def _resolve_attachment_url(image_id: str, attachments: list[dict[str, Any]]) -> str | None:
    for attachment in attachments:
        if attachment.get("name") == image_id:
            url = attachment.get("url")
            return f"{SITE_BASE_URL}{url}" if url else None
    return None


def _render_prosemirror_marks(text: str, marks: list[dict[str, Any]]) -> str:
    for mark in marks:
        if mark.get("type") == "bold":
            text = f"<strong>{text}</strong>"
        elif mark.get("type") == "italic":
            text = f"<em>{text}</em>"
    return text


def _render_prosemirror_inline(node: dict[str, Any], attachments: list[dict[str, Any]]) -> str:
    node_type = node.get("type")
    if node_type == "text":
        text = html.escape(str(node.get("text", "")))
        return _render_prosemirror_marks(text, node.get("marks") or [])
    if node_type == "hardBreak":
        return "<br />"
    if node_type == "image":
        images = node.get("attrs", {}).get("images") or []
        urls = (_resolve_attachment_url(image.get("image", ""), attachments) for image in images)
        return "".join(f'<img loading="lazy" src="{url}" />' for url in urls if url)
    return "".join(_render_prosemirror_inline(child, attachments) for child in _child_nodes(node))


def _render_prosemirror_block(node: dict[str, Any], attachments: list[dict[str, Any]]) -> str:
    node_type = node.get("type")
    if node_type == "paragraph":
        inner = "".join(
            _render_prosemirror_inline(child, attachments) for child in _child_nodes(node)
        )
        return f"<p>{inner}</p>"
    if node_type == "image":
        return _render_prosemirror_inline(node, attachments)
    if node_type == "horizontalRule":
        return "<hr />"
    return "".join(_render_prosemirror_block(child, attachments) for child in _child_nodes(node))


def _prosemirror_to_html(doc: dict[str, Any], attachments: list[dict[str, Any]]) -> str:
    """Render a prosemirror-doc JSON structure as an HTML fragment.

    Chapter content comes from the API in one of two formats — an HTML string, or
    prosemirror-doc JSON (see docs/api-notes.md) — this makes the latter match the tag
    vocabulary (``p``/``img``/``strong``/``em``) the former already uses natively, so
    downstream consumers (exporters) only ever handle one shape. Image nodes reference
    attachments by an opaque id, resolved against the chapter response's ``attachments``
    array.
    """
    return "".join(_render_prosemirror_block(block, attachments) for block in _child_nodes(doc))


class Cover(BaseModel):
    """A set of cover image URLs at different sizes."""

    filename: str | None = None
    thumbnail: str | None = None
    default: str | None = None
    md: str | None = None


class Label(BaseModel):
    """A small ``{id, label}`` enum value used throughout the API (status, age rating, ...)."""

    id: int
    label: str


class Genre(BaseModel):
    """A genre tag (e.g. Fantasy, Romance)."""

    id: int
    name: str
    adult: bool = False


class Tag(BaseModel):
    """A free-form content tag."""

    id: int
    name: str
    adult: bool = False


class Person(BaseModel):
    """An author or artist credited on a title."""

    id: int
    slug: str
    slug_url: str
    name: str
    rus_name: str | None = None


class Team(BaseModel):
    """A translation team."""

    id: int
    slug: str
    slug_url: str
    name: str


class Title(BaseModel):
    """Metadata for a single title (novel)."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    rus_name: str | None = None
    eng_name: str | None = None
    other_names: list[str] = Field(default_factory=list, alias="otherNames")
    slug: str
    slug_url: str
    cover: Cover
    age_restriction: Label = Field(alias="ageRestriction")
    status: Label
    summary: str | None = None
    release_date: str | None = Field(default=None, alias="releaseDate")
    is_licensed: bool = False
    genres: list[Genre] = Field(default_factory=list)
    tags: list[Tag] = Field(default_factory=list)
    authors: list[Person] = Field(default_factory=list)
    artists: list[Person] = Field(default_factory=list)
    teams: list[Team] = Field(default_factory=list)
    chapter_count: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _flatten_chapter_count(cls, data: Any) -> Any:
        if isinstance(data, dict) and "chapter_count" not in data:
            items_count = data.get("items_count")
            if isinstance(items_count, dict):
                data = {**data, "chapter_count": items_count.get("uploaded")}
        return data

    @field_validator("summary", mode="before")
    @classmethod
    def _parse_summary(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return _prosemirror_to_text(value)
        return str(value)


class ChapterUser(BaseModel):
    """The uploader of a chapter branch."""

    id: int
    username: str


class ChapterBranch(BaseModel):
    """A single team's (or solo uploader's) translation of a chapter.

    A chapter has more than one branch when several teams have translated it
    independently; see ``Chapter.branches_count``.
    """

    id: int
    branch_id: int | None = None
    created_at: datetime
    teams: list[Team] = Field(default_factory=list)
    user: ChapterUser


class Chapter(BaseModel):
    """A chapter: volume, number, name, available translations, and optionally its content.

    ``index``/``item_number``/``branches_count``/``branches`` come from the chapter-list
    endpoint (see ``RanobeLib.get_table_of_contents()``) and are ``None``/empty when a
    ``Chapter`` instead comes from fetching a single chapter's content, which has a
    different response shape (see docs/api-notes.md). ``content`` is the reverse: only
    populated by the single-chapter endpoint.
    """

    id: int
    volume: str
    number: str
    name: str | None = None
    index: int | None = None
    item_number: int | None = None
    branches_count: int = 1
    branches: list[ChapterBranch] = Field(default_factory=list)
    bundle_id: int | None = None
    content: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_content(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("content"), dict):
            attachments = data.get("attachments") or []
            data = {**data, "content": _prosemirror_to_html(data["content"], attachments)}
        return data


class Volume(BaseModel):
    """A volume: its number and the chapters it contains, in title order."""

    number: str
    chapters: list[Chapter] = Field(default_factory=list)
