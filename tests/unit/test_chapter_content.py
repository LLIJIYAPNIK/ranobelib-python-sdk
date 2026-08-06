"""Unit tests for chapter content normalization (ranobelib.models.Chapter.content)."""

from typing import Any

from ranobelib.models import Chapter

BASE_CHAPTER: dict[str, Any] = {
    "id": 1,
    "volume": "1",
    "number": "1",
    "name": "Chapter 1",
}


def test_chapter_content_string_strips_editor_attributes() -> None:
    # data-paragraph-index is a pure editor artifact (see docs/api-notes.md) and isn't in
    # the restricted tag/attribute vocabulary the sanitizer allows through.
    raw = {**BASE_CHAPTER, "content": '<p data-paragraph-index="1">Hello.</p>'}

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p>Hello.</p>"


def test_chapter_content_string_keeps_allowed_tags() -> None:
    raw = {
        **BASE_CHAPTER,
        "content": (
            "<p>a<strong>b</strong><em>c</em>d</p><hr /><p>e<br />f"
            '<img loading="lazy" src="https://ranobelib.me/uploads/x.jpg" /></p>'
        ),
    }

    chapter = Chapter.model_validate(raw)

    assert chapter.content == (
        "<p>a<strong>b</strong><em>c</em>d</p><hr /><p>e<br />f"
        '<img loading="lazy" src="https://ranobelib.me/uploads/x.jpg" /></p>'
    )


def test_chapter_content_string_maps_b_and_i_to_strong_and_em() -> None:
    # Observed as interchangeable with strong/em across samples, see docs/api-notes.md.
    raw = {**BASE_CHAPTER, "content": "<p><b>bold</b> <i>italic</i></p>"}

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p><strong>bold</strong> <em>italic</em></p>"


def test_chapter_content_string_drops_disallowed_tags_keeps_text() -> None:
    raw = {**BASE_CHAPTER, "content": '<p>before <a href="https://evil.example">link</a> after</p>'}

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p>before link after</p>"


def test_chapter_content_string_drops_script_tag_and_its_text() -> None:
    raw = {**BASE_CHAPTER, "content": "<p>safe</p><script>alert(document.cookie)</script>"}

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p>safe</p>"


def test_chapter_content_string_strips_event_handler_attributes() -> None:
    raw = {**BASE_CHAPTER, "content": '<p onclick="alert(1)">text</p>'}

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p>text</p>"


def test_chapter_content_string_drops_img_with_unsafe_scheme() -> None:
    raw = {**BASE_CHAPTER, "content": '<p><img src="javascript:alert(1)" /></p>'}

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p></p>"


def test_chapter_content_string_escapes_text() -> None:
    raw = {**BASE_CHAPTER, "content": "<p>&lt;not a real tag&gt; &amp; &quot;quoted&quot;</p>"}

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p>&lt;not a real tag&gt; &amp; &quot;quoted&quot;</p>"


def test_chapter_content_defaults_to_none() -> None:
    chapter = Chapter.model_validate(BASE_CHAPTER)

    assert chapter.content is None


def test_chapter_content_prosemirror_paragraphs() -> None:
    raw = {
        **BASE_CHAPTER,
        "content": {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "First."}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "Second."}]},
            ],
        },
    }

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p>First.</p><p>Second.</p>"


def test_chapter_content_prosemirror_empty_paragraph() -> None:
    raw = {
        **BASE_CHAPTER,
        "content": {"type": "doc", "content": [{"type": "paragraph"}]},
    }

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p></p>"


def test_chapter_content_prosemirror_bold_and_italic_marks() -> None:
    raw = {
        **BASE_CHAPTER,
        "content": {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "bold", "marks": [{"type": "bold"}]},
                        {"type": "text", "text": " and "},
                        {"type": "text", "text": "italic", "marks": [{"type": "italic"}]},
                    ],
                }
            ],
        },
    }

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p><strong>bold</strong> and <em>italic</em></p>"


def test_chapter_content_prosemirror_escapes_text() -> None:
    raw = {
        **BASE_CHAPTER,
        "content": {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "<script>&"}]}],
        },
    }

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p>&lt;script&gt;&amp;</p>"


def test_chapter_content_prosemirror_hard_break_and_horizontal_rule() -> None:
    raw = {
        **BASE_CHAPTER,
        "content": {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "hardBreak"}]},
                {"type": "horizontalRule"},
            ],
        },
    }

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p><br /></p><hr />"


def test_chapter_content_prosemirror_image_resolved_via_attachments() -> None:
    raw = {
        **BASE_CHAPTER,
        "content": {
            "type": "doc",
            "content": [
                {"type": "image", "attrs": {"images": [{"image": "abc-123"}]}},
            ],
        },
        "attachments": [
            {
                "name": "abc-123",
                "filename": "abc-123.jpg",
                "url": "/uploads/ranobe/example/chapters/1/abc-123.jpg",
            }
        ],
    }

    chapter = Chapter.model_validate(raw)

    assert chapter.content == (
        '<img loading="lazy" '
        'src="https://ranobelib.me/uploads/ranobe/example/chapters/1/abc-123.jpg" />'
    )


def test_chapter_content_prosemirror_image_unresolvable_omitted() -> None:
    raw = {
        **BASE_CHAPTER,
        "content": {
            "type": "doc",
            "content": [{"type": "image", "attrs": {"images": [{"image": "missing"}]}}],
        },
        "attachments": [],
    }

    chapter = Chapter.model_validate(raw)

    assert chapter.content == ""


def test_chapter_content_prosemirror_unknown_block_node_recurses_into_children() -> None:
    # Forward-compat: an unrecognized block wrapper (e.g. a node type not yet seen in the
    # wild, see docs/api-notes.md) should still surface its text rather than dropping it.
    raw = {
        **BASE_CHAPTER,
        "content": {
            "type": "doc",
            "content": [
                {
                    "type": "blockquote",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Quoted."}]}
                    ],
                }
            ],
        },
    }

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p>Quoted.</p>"


def test_chapter_content_prosemirror_unknown_inline_node_recurses_into_children() -> None:
    raw = {
        **BASE_CHAPTER,
        "content": {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "link", "content": [{"type": "text", "text": "link"}]}],
                }
            ],
        },
    }

    chapter = Chapter.model_validate(raw)

    assert chapter.content == "<p>link</p>"


def test_chapter_content_prosemirror_no_attachments_key() -> None:
    raw = {
        **BASE_CHAPTER,
        "content": {"type": "doc", "content": [{"type": "image", "attrs": {"images": []}}]},
    }

    chapter = Chapter.model_validate(raw)

    assert chapter.content == ""
