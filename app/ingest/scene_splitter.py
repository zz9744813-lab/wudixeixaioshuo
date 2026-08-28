"""Scene splitting (spec §7).

Within a Chapter we start a new Scene whenever a *structural break signal* appears
on its own line (spec §7.1). Without an LLM we use the reliable, falsifiable
signals:

* a section heading (Markdown ``##`` / EPUB ``<h2>`` / DOCX ``Heading2``),
* an ornament / scene-break line (``* * *``, ``---``, ``§``, ``#`` centered, ...),
* an explicit time-jump phrase (``第二天``, ``三年后``, ``与此同时`` ...),
* a POV marker (``张三视角``, ``[张三]``).

A chapter with no break signal is a single Scene; if that lone Scene is
unusually long we fall back to a size-based split at paragraph boundaries so the
research layer still gets addressable units (flagged ``heuristic=True``).
"""
from __future__ import annotations

import re
from typing import List, Optional

from app.ingest.lines import build_line_index
from app.ingest.types import ChapterBlock, Heading, Paragraph, SceneBlock

# A single over-long Scene is split into chunks no larger than this (heuristic).
MAX_SCENE_CHARS = 5000
TARGET_CHUNK_CHARS = 3500

_ORNAMENT = re.compile(r"^\s*([*•·\-_=★☆§#.]\s*){2,}\s*$")
_BRACKET_POV = re.compile(r"^\s*\[[^\]]{1,40}\]\s*$")
_POV = re.compile(r"^\s*[一-龥A-Za-z]{1,10}\s*(的视角|视角|POV)\s*$", re.IGNORECASE)
_TIMEJUMP = re.compile(
    r"^(第二天|次日|第二天一早|第二天清晨|第二天早晨|第二天晚上|第三天|数日后|几天后|"
    r"一周后|半月后|一个月后|一年后|三年后|数年后|多年以后|多年后|十年后|二十年後|"
    r"此时|与此同时|就在此时|傍晚|清晨|深夜|午夜|正午|天亮后|天黑后|夜深了|半年后|"
    r"那一年|后来|天刚亮|太阳落山后|黄昏|黎明|破晓|子夜)\b",
    re.IGNORECASE,
)
# A time-jump only breaks a scene when it is a near-standalone temporal marker,
# not a full sentence like "清晨，张三离开了家乡。" (which is ordinary narration).
_TIMEJUMP_TAIL = "，。、；：！？,.!?;: "
_BLANKLINE = re.compile(r"\n\s*\n")


def _is_scene_break(line: str, level: Optional[int]) -> bool:
    s = line.strip()
    if not s:
        return False
    if level is not None and level == 2:
        return True
    if _ORNAMENT.match(s):
        return True
    m = _TIMEJUMP.match(s)
    if m:
        tail = s[m.end():].strip()
        # Break only if the rest is punctuation/whitespace (marker stands alone).
        return tail == "" or all(ch in _TIMEJUMP_TAIL for ch in tail)
    if _POV.match(s):
        return True
    if _BRACKET_POV.match(s):
        return True
    return False


def _paragraphs(seg_text: str, seg_start: int) -> List[Paragraph]:
    paras: List[Paragraph] = []
    pos = 0
    for raw in _BLANKLINE.split(seg_text):
        stripped = raw.strip()
        if not stripped:
            pos += len(raw)
            continue
        start = seg_text.find(stripped, pos)
        if start == -1:
            start = pos
        paras.append(
            Paragraph(
                char_start=seg_start + start,
                char_end=seg_start + start + len(stripped),
                text=stripped,
            )
        )
        pos = start + len(raw)
    return paras


def _make_scene(index: int, seg: str, start: int, end: int, heuristic: bool = False) -> SceneBlock:
    return SceneBlock(
        index=index,
        raw_text=seg.strip(),
        char_start=start,
        char_end=end,
        paragraphs=_paragraphs(seg, start),
        heuristic=heuristic,
    )


def _split_giant(scene: SceneBlock) -> List[SceneBlock]:
    """Fallback: break one over-long Scene into paragraph-aligned chunks."""
    paras = scene.paragraphs or [Paragraph(scene.char_start, scene.char_end, scene.raw_text)]
    out: List[SceneBlock] = []
    cur_start = paras[0].char_start
    cur_end = cur_start
    cur_len = 0
    for p in paras:
        if cur_len > 0 and (cur_len + len(p.text)) > TARGET_CHUNK_CHARS:
            out.append(_make_scene(len(out), "", cur_start, cur_end, heuristic=True))
            cur_start = p.char_start
            cur_len = 0
        cur_end = p.char_end
        cur_len += len(p.text) + 1
    if cur_start < cur_end:
        out.append(_make_scene(len(out), "", cur_start, cur_end, heuristic=True))
    return out


def split_chapter(chapter: ChapterBlock, headings: List[Heading]) -> List[SceneBlock]:
    """Split a Chapter's text into Scenes (offsets are relative to the chapter)."""
    text = chapter.raw_text
    # Only headings that fall inside this chapter matter.
    heading_levels = {h.char_offset: h.level for h in headings if chapter.char_start <= h.char_offset < chapter.char_end}
    lines = build_line_index(text, [Heading(level, "", off) for off, level in heading_levels.items()])

    scenes: List[SceneBlock] = []
    scene_start = 0
    for line in lines:
        if _is_scene_break(line.text, line.heading_level):
            seg = text[scene_start : line.char_start]
            if seg.strip():
                scenes.append(_make_scene(len(scenes), seg, scene_start, line.char_start))
            scene_start = line.char_start

    tail = text[scene_start:]
    if tail.strip():
        scenes.append(_make_scene(len(scenes), tail, scene_start, len(text)))

    if not scenes:
        scenes.append(_make_scene(0, text, 0, len(text)))

    # Fallback for an over-long, unbroken chapter.
    if len(scenes) == 1 and len(scenes[0].raw_text) > MAX_SCENE_CHARS:
        scenes = _split_giant(scenes[0])

    for new_idx, s in enumerate(scenes):
        s.index = new_idx
    return scenes
