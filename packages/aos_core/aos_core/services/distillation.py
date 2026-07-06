"""Repository content extraction / distillation (RFC-0008 MVP).

The scanner (``repository_scanner.py``) reads a repository's structural
**fingerprint** — extensions, manifests, the directory tree — but never its
**content**. A curated-catalog repo whose entire value is its README therefore
yields a fingerprint abstention (the ``free-llm-api-resources`` reality test).

This module builds the content-extraction MVP: it reads a scanned repo's actual
README, runs a **deterministic, provenance-tagged extractor** (pure Python over
real content — no LLM, hermetic, CI-runnable), renders an Obsidian-friendly page
to ``knowledge/wiki/repositories/<slug>.md`` (the repo vault = source of truth,
RFC-0002/0004), and projects a re-syncable :class:`~aos_core.models.KnowledgePage`
(``page_type="repository"``). ``sync_knowledge`` re-derives the page from the
vault, so a DB reset loses nothing. The distilled summary also stamps the
otherwise-unused ``RepositoryDNA.purpose``.

Local-first write discipline mirrors the ADR-export seam (:mod:`aos_core.services.adr`):
a non-writable (``:ro``-mounted / read-only) vault yields a graceful **409**,
never a 500, and never mutates state. Stdlib-only; no new dependencies; no LLM.
"""

from __future__ import annotations

import ast
import hashlib
import os
import re
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..llm import get_provider
from ..models import KnowledgePage, Repository, RepositoryDNA
from ..repository_scanner import EXTENSIONS, LANGUAGE_CLASS, safe_repo_path
from .council import _loads_tolerant

_PAGE_TYPE = "repository"
_README_CAP_BYTES = 40_000
_FALLBACK_TITLE = "Untitled repository"

# Phase-2 (RFC-0008) source selection: bound + ignore.
_IGNORED_SOURCE_DIRS = {"node_modules", "__pycache__"}
# Primary manifests, in the order we prefer them (declare purpose/deps/scripts).
_MANIFEST_PRIORITY = ("pyproject.toml", "package.json", "go.mod")
# Entry points by exact filename and by stem (with any extension).
_ENTRY_POINT_NAMES = {"__init__.py", "lib.rs", "mod.rs"}
_ENTRY_POINT_STEMS = {"main", "cli", "app", "index"}
# Cap on top-level symbols surfaced per component (keeps the page readable).
_SYMBOL_CAP = 12

# Top-level symbol names in non-Python source (JS/TS/Go/Rust/…). Anchored to the
# line start (re.M) so only top-level (unindented) declarations are captured.
_GENERIC_SYMBOL_RE = re.compile(
    r"^(?:pub\s+)?(?:export\s+)?(?:default\s+)?(?:async\s+)?"
    r"(?:func|fn|class|def|function)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
# Python fallback when ``ast.parse`` fails on a syntactically-broken file.
_PY_FALLBACK_RE = re.compile(r"^(?:async\s+)?(def|class)\s+(\w+)", re.MULTILINE)

# A fenced code block opens with ``` (or ~~~) optionally followed by a language.
_FENCE_RE = re.compile(r"^(?:```+|~~~+)\s*([A-Za-z0-9_+#.-]+)?\s*$")
# A numbered-list item (``1.`` / ``2)``) is not prose.
_NUMBERED_RE = re.compile(r"^\d+[.)]\s")

# --- Deterministic summary floor (AOS-DISTILL-003) ---------------------------
# The summary floor drops noise-only lines (badges/image-links, bare links, HTML
# comments, headings) and then prefers the first *declarative description
# sentence* — "<Name> ... is/are/provides/... a ..." where <Name> matches the
# distilled title or repo name — else the first clean prose paragraph. It never
# emits badge/link-only markup: with no clean prose it yields the honest
# fallback. Pure and LLM-free (operates on the passed README lines).
_SUMMARY_FALLBACK = "README present but no prose summary could be extracted."
# Once a declarative sentence anchors the summary we append following prose
# blocks until the running length reaches this budget (so a description whose
# defining tokens live a paragraph below the lead sentence is still captured);
# the whole summary is then capped at _SUMMARY_MAX.
_SUMMARY_BUDGET = 500
_SUMMARY_MAX = 1200
# Copulas/verbs that mark "<Name> <copula> ..." as a declarative description.
_COPULAS = frozenset(
    {
        "is", "are", "provides", "provide", "lets", "let", "helps", "help",
        "aims", "aim", "makes", "make", "enables", "enable", "offers", "offer",
        "allows", "allow", "supports", "support", "powers", "power",
    }
)
_ATX_HEADING_RE = re.compile(r"^#{1,6}\s")
_HTML_HEADING_RE = re.compile(r"^<h[1-6][\s>]", re.IGNORECASE)
_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _normalize_name(text: str | None) -> str:
    """Collapse a title/repo name to its bare alphanumeric identity (lowercased)."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _strip_markup(line: str) -> str:
    """Reduce one markdown/HTML line to plain text (images/badges/tags/markers removed)."""
    text = re.sub(r"<!--.*?-->", " ", line)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)          # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)       # inline links -> text
    text = re.sub(r"</?[a-zA-Z][^>]*>", " ", text)             # html tags
    text = re.sub(r"[`*#~>|]", " ", text)                      # emphasis / markers
    text = re.sub(r"[\[\]]", " ", text)                        # stray brackets (ref links)
    return re.sub(r"\s+", " ", text).strip()


def _line_kind(stripped: str) -> str:
    """Classify a non-empty, non-fence, non-comment line: heading / skip / prose."""
    if _ATX_HEADING_RE.match(stripped) or _HTML_HEADING_RE.match(stripped):
        return "heading"
    if stripped[0] in "-*+>|=":
        return "skip"
    if _NUMBERED_RE.match(stripped):
        return "skip"
    return "prose"


def _classify_readme(lines: list[str]) -> list[tuple[str, str]]:
    """Ordered ``(kind, text)`` entries — ``heading`` lines and joined ``prose`` blocks.

    Fenced code, HTML comments, badge/link-only lines, bullets, blockquotes,
    tables and numbered lists are dropped. Consecutive prose lines are joined into
    one block (so a wrapped sentence is not split); a blank line, heading, or
    noise-only line ends the current block.
    """
    entries: list[tuple[str, str]] = []
    prose_buf: list[str] = []
    in_comment = False
    in_fence = False

    def flush() -> None:
        if prose_buf:
            text = _strip_markup(" ".join(prose_buf)).strip()
            if text:
                entries.append(("prose", text))
            prose_buf.clear()

    for raw in lines:
        s = raw.strip()
        if in_comment:
            if "-->" in s:
                in_comment = False
            continue
        if _FENCE_RE.match(s):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if s.startswith("<!--"):
            flush()
            if "-->" not in s:
                in_comment = True
            continue
        if not s:
            flush()
            continue
        kind = _line_kind(s)
        if kind == "heading":
            flush()
            text = _strip_markup(s).strip()
            if text:
                entries.append(("heading", text))
            continue
        if kind == "skip":
            flush()
            continue
        # Prose candidate: a line that is only badges/links strips to empty and is
        # treated as noise (block separator), never emitted as a summary.
        if not _strip_markup(s).strip():
            flush()
            continue
        prose_buf.append(s)
    flush()
    return entries


def _split_sentences(text: str) -> list[str]:
    return [part for part in _SENTENCE_SPLIT_RE.split(text.strip()) if part]


def _declares(sentence: str, names_norm: set[str]) -> bool:
    """Whether ``sentence`` reads as ``<Name> ... <copula> ...`` for a known name.

    The subject (words before the first copula/verb) must begin with a known name
    at a word boundary — so "Gin is …", "Kubernetes, also known as K8s, is …", and
    "Pydantic AI is …" match, but "Gindalf is …" (for repo "gin") does not.
    """
    words = [w.lower() for w in _WORD_RE.findall(sentence)]
    for index, word in enumerate(words):
        if word not in _COPULAS:
            continue
        if index == 0:
            return False
        acc = ""
        for pre in words[:index]:
            acc += re.sub(r"[^a-z0-9]", "", pre)
            if acc in names_norm:
                return True
            if all(len(acc) > len(name) for name in names_norm):
                break
        return False
    return False


def _cap_summary(text: str) -> str:
    text = text.strip()
    if len(text) <= _SUMMARY_MAX:
        return text
    clipped = text[:_SUMMARY_MAX].rsplit(" ", 1)[0].rstrip()
    return f"{clipped}…"


def _clean_summary(lines: list[str], *, names) -> str | None:
    """The deterministic summary for a README, or ``None`` when no clean prose exists.

    Prefers the first declarative description sentence (subject = title/repo name +
    copula); a heading-sourced declarative sentence contributes only itself, while a
    prose-sourced one is extended with following prose blocks up to ``_SUMMARY_BUDGET``
    (so tokens a paragraph below the lead sentence are still captured). Falls back to
    the first clean prose paragraph. Never returns badge/link-only markup.
    """
    names_norm = {n for n in (_normalize_name(x) for x in names) if n}
    entries = _classify_readme(lines)
    if not entries:
        return None

    if names_norm:
        # Prose declaratives beat heading declaratives: a section heading like
        # "Gin 1.12.0 is now available!" structurally matches "<Name> ... is ..."
        # but a real description sentence ("Gin is a high-performance … framework")
        # lives in prose. Only when no prose sentence declares (e.g. PydanticAI,
        # whose description sits in an ``<h3>``) do we accept a heading.
        for want_kind in ("prose", "heading"):
            for entry_index, (kind, text) in enumerate(entries):
                if kind != want_kind:
                    continue
                sentences = _split_sentences(text)
                for sentence_index, sentence in enumerate(sentences):
                    if not _declares(sentence, names_norm):
                        continue
                    lead = " ".join(sentences[sentence_index:])
                    if kind == "heading":
                        return _cap_summary(lead)
                    parts = [lead]
                    total = len(lead)
                    following = entry_index + 1
                    while following < len(entries) and total < _SUMMARY_BUDGET:
                        next_kind, next_text = entries[following]
                        if next_kind == "heading":
                            break
                        parts.append(next_text)
                        total += len(next_text) + 1
                        following += 1
                    return _cap_summary(" ".join(parts))

    for kind, text in entries:
        if kind == "prose":
            return _cap_summary(text)
    return None

# useful_for heuristics: an ordered (keyword-set → phrase) mapping so a
# content-rich repo advertises what it is for. Order fixes determinism; each hit
# cites the keyword that triggered it as provenance.
_USEFUL_FOR_SIGNALS: list[tuple[tuple[str, ...], str]] = [
    (("catalog", "curated", "awesome", "resources", " list ", "lists ", "directory of"),
     "Reference catalog / curated list to consult for options"),
    (("library", "package"), "Reusable library to depend on"),
    (("framework",), "Application framework to build on"),
    (("sdk",), "SDK for integrating a service"),
    (("cli", "command-line", "command line"), "Command-line tool"),
    (("template", "boilerplate", "starter", "scaffold"),
     "Project template / starter to scaffold from"),
    (("example", "sample", "demo", "tutorial"), "Example / reference implementation to learn from"),
]


def _first_heading(lines: list[str]) -> str | None:
    """The text of the first level-1 (``# ``) ATX heading, or ``None``."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def _section_headings(lines: list[str]) -> list[tuple[str, str | None]]:
    """Level-2/3 (``##``/``###``) headings, each with its first content line.

    Fenced code is skipped so a ``## comment`` inside a code block is not
    mistaken for a section. Returns ``[(heading, first_content_line_or_None)]``.
    """
    out: list[tuple[str, str | None]] = []
    in_fence = False
    n = len(lines)
    for i, line in enumerate(lines):
        s = line.strip()
        if _FENCE_RE.match(s):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{2,3})\s+(.*)$", s)
        if not m:
            continue
        heading = m.group(2).strip().rstrip("#").strip()
        if not heading:
            continue
        detail: str | None = None
        for follow in lines[i + 1 : min(i + 6, n)]:
            fs = follow.strip()
            if not fs:
                continue
            if fs.startswith("#") or _FENCE_RE.match(fs):
                break
            detail = fs.lstrip("-*+>| ").strip() or None
            break
        out.append((heading, detail))
    return out


def _fence_languages(lines: list[str]) -> list[str]:
    """Languages tagged on fenced code blocks, in first-seen order."""
    langs: list[str] = []
    in_fence = False
    for line in lines:
        m = _FENCE_RE.match(line.strip())
        if not m:
            continue
        if not in_fence:
            lang = m.group(1)
            if lang and lang.lower() not in (existing.lower() for existing in langs):
                langs.append(lang)
        in_fence = not in_fence
    return langs


def _dna_technologies(dna: RepositoryDNA | None) -> list[tuple[str, str]]:
    """(technology, source) pairs grounded in the DNA scan, in a stable order."""
    if dna is None:
        return []
    pairs: list[tuple[str, str]] = []
    for manager in dna.package_managers or []:
        pairs.append((str(manager), "RepositoryDNA.package_managers"))
    summary = (dna.scan_summary or {}).get("summary") if isinstance(dna.scan_summary, dict) else None
    language_classes = summary.get("language_classes") if isinstance(summary, dict) else None
    if isinstance(language_classes, dict):
        for language, klass in language_classes.items():
            if klass == "source":
                pairs.append((str(language), "RepositoryDNA.scan_summary.language_classes"))
    return pairs


def _dedupe_preserving(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for value, source in items:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append((value.strip(), source))
    return out


def extract_repo_knowledge(
    readme_text: str, *, dna: RepositoryDNA | None = None, sources=None, name: str | None = None
) -> dict:
    """Distil provenance-tagged knowledge from a repo's README (pure, no I/O).

    Deterministic and LLM-free: derives ``title`` (first ``# `` heading, else a
    fallback), ``summary`` (the deterministic summary floor — the first declarative
    description sentence for the distilled title / ``name``, else the first clean
    prose paragraph, never badge/link-only markup), ``key_points`` (``##``/``###``
    section headings with their first content line), ``technologies`` (DNA package
    managers + source languages ∪ README fenced-code languages), ``useful_for``
    (keyword heuristics), and ``provenance`` (every item cites its source). Each
    ``provenance`` entry is ``{"item": str, "source": str}``.

    Tolerant: an empty / whitespace README yields a minimal dict (fallback title,
    a summary noting the absence, DNA-only technologies) and never raises.
    """
    text = readme_text or ""
    lines = text.splitlines()
    has_content = bool(text.strip())

    provenance: list[dict] = []

    title = _first_heading(lines) or _FALLBACK_TITLE
    if title != _FALLBACK_TITLE:
        provenance.append({"item": f"title: {title}", "source": "README.md (# heading)"})

    if has_content:
        summary_names = [title if title != _FALLBACK_TITLE else None, name]
        summary = _clean_summary(lines, names=summary_names) or _SUMMARY_FALLBACK
        summary_source = "README.md (cleaned summary)"
    else:
        summary = "No README content was available to distill for this repository."
        summary_source = "(no README found)"
    provenance.append({"item": "summary", "source": summary_source})

    key_points: list[str] = []
    for heading, detail in _section_headings(lines):
        point = f"{heading}: {detail}" if detail else heading
        key_points.append(point)
        provenance.append({"item": f"key point: {heading}", "source": f"README.md (## {heading})"})

    tech_pairs = _dedupe_preserving(_dna_technologies(dna) + [(lang, "README.md (fenced code block)") for lang in _fence_languages(lines)])
    technologies = [value for value, _ in tech_pairs]
    for value, source in tech_pairs:
        provenance.append({"item": f"technology: {value}", "source": source})

    useful_for: list[str] = []
    haystack = f" {text.lower()} "
    for keywords, phrase in _USEFUL_FOR_SIGNALS:
        matched = next((kw for kw in keywords if kw.strip() and kw in haystack), None)
        if matched and phrase not in useful_for:
            useful_for.append(phrase)
            provenance.append({"item": f"useful for: {phrase}", "source": f"README.md (keyword '{matched.strip()}')"})

    return {
        "title": title,
        "summary": summary,
        "key_points": key_points,
        "technologies": technologies,
        "useful_for": useful_for,
        "provenance": provenance,
    }


# --- Phase 2 (RFC-0008): code-aware distillation -----------------------------


def _language_class_of(name: str) -> str | None:
    """The coarse language class (``source``/``config``/…) of a filename, or None."""
    language = EXTENSIONS.get(Path(name).suffix.lower())
    return LANGUAGE_CLASS.get(language) if language else None


def _is_entry_point(name: str) -> bool:
    """Whether a source filename reads as an entry point (per-language heuristic)."""
    if name in _ENTRY_POINT_NAMES:
        return True
    dot = name.rfind(".")
    if dot <= 0:
        return False
    return name[:dot] in _ENTRY_POINT_STEMS


def select_source_files(
    repository: Repository, *, dna: RepositoryDNA | None = None, cap_files: int = 10, cap_bytes: int = 40_000
) -> list[dict]:
    """Pick a bounded, meaningful set of source files from a scanned repo (I/O, tolerant).

    Selects entry-point files (``main.*``/``__init__.py``/``cli.*``/``app.*``/
    ``index.*``/``lib.rs``/``mod.rs``/``main.go``), the largest **source-classified**
    files (via the scanner's ``LANGUAGE_CLASS``), and the primary manifest
    (``pyproject.toml``/``package.json``/``go.mod``). Reads content via
    ``safe_repo_path``; honours ``cap_files`` and a running ``cap_bytes`` total;
    skips unreadable / binary (decode error) / oversized files and ignores
    ``.git``/``node_modules``/``__pycache__``/dot-directories. Each item is
    ``{"path": rel, "text": content, "is_entry_point": bool, "role": ...}`` where
    ``role`` is ``"entry_point"``/``"module"``/``"manifest"``. Tolerant: a repo we
    cannot read yields ``[]`` and never raises out of distillation.
    """
    try:
        repo_dir = safe_repo_path(get_settings().repository_root, repository.local_path)
    except Exception:
        return []

    source_candidates: list[tuple[str, int, str]] = []  # (rel, size, name)
    manifest_candidates: dict[str, tuple[str, int]] = {}  # name -> (rel, depth)
    try:
        for dirpath, dirnames, filenames in os.walk(repo_dir):
            dirnames[:] = sorted(
                d for d in dirnames if not d.startswith(".") and d not in _IGNORED_SOURCE_DIRS
            )
            for name in sorted(filenames):
                full = Path(dirpath) / name
                try:
                    rel = full.relative_to(repo_dir).as_posix()
                except ValueError:
                    continue
                if name in _MANIFEST_PRIORITY:
                    depth = rel.count("/")
                    prev = manifest_candidates.get(name)
                    if prev is None or depth < prev[1]:
                        manifest_candidates[name] = (rel, depth)
                    continue
                if _language_class_of(name) == "source":
                    try:
                        size = full.stat().st_size
                    except OSError:
                        continue
                    source_candidates.append((rel, size, name))
    except Exception:
        return []

    entry = sorted((c for c in source_candidates if _is_entry_point(c[2])), key=lambda c: c[0])
    entry_paths = {c[0] for c in entry}
    modules = sorted(
        (c for c in source_candidates if c[0] not in entry_paths), key=lambda c: (-c[1], c[0])
    )

    ordered: list[tuple[str, str, bool]] = [(rel, "entry_point", True) for rel, _, _ in entry]
    for mname in _MANIFEST_PRIORITY:
        if mname in manifest_candidates:
            ordered.append((manifest_candidates[mname][0], "manifest", False))
            break
    ordered += [(rel, "module", False) for rel, _, _ in modules]

    selected: list[dict] = []
    seen: set[str] = set()
    running = 0
    for rel, role, is_ep in ordered:
        if len(selected) >= cap_files:
            break
        if rel in seen:
            continue
        try:
            content = (repo_dir / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        encoded = len(content.encode("utf-8"))
        if running + encoded > cap_bytes:
            continue
        running += encoded
        seen.add(rel)
        selected.append({"path": rel, "text": content, "is_entry_point": is_ep, "role": role})
    return selected


def _first_docstring_line(docstring: str | None) -> str | None:
    if not docstring or not docstring.strip():
        return None
    return docstring.strip().splitlines()[0].strip() or None


def _summarize_python(text: str) -> tuple[str | None, list[str]]:
    """Module docstring first line + top-level def/class names (``ast``; regex fallback)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        symbols: list[str] = []
        for _, name in _PY_FALLBACK_RE.findall(text):
            if name not in symbols:
                symbols.append(name)
        return None, symbols

    doc = _first_docstring_line(ast.get_docstring(tree))
    symbols = []
    all_names: list[str] | None = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name not in symbols:
                symbols.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    try:
                        value = ast.literal_eval(node.value)
                    except Exception:
                        value = None
                    if isinstance(value, (list, tuple)):
                        all_names = [str(v) for v in value if isinstance(v, str)]
    for name in all_names or []:
        if name not in symbols:
            symbols.append(name)
    return doc, symbols


def _leading_comment(text: str) -> str | None:
    """A leading ``//``/``#``/``/*`` comment line, if the file opens with one."""
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("//"):
            return s.lstrip("/").strip() or None
        if s.startswith("#"):
            return s.lstrip("#").strip() or None
        if s.startswith("/*"):
            return s[2:].strip().rstrip("*/").strip() or None
        return None
    return None


def _summarize_generic(text: str) -> tuple[str | None, list[str]]:
    """Top-level export/func/fn/class/def names + a leading comment as the docstring."""
    symbols: list[str] = []
    for name in _GENERIC_SYMBOL_RE.findall(text):
        if name not in symbols:
            symbols.append(name)
    return _leading_comment(text), symbols


def summarize_sources(files: list[dict]) -> dict:
    """Deterministic, stdlib-only structural summary of selected source files (pure).

    Per file, builds a **component** — ``{"path", "role", "docstring"(first line or
    None), "symbols"(top-level names, capped), "provenance": path}``. Python is parsed
    with ``ast`` (tolerant of ``SyntaxError`` → regex fallback); other source languages
    use a top-level-symbol regex + a leading comment. Never raises — a file that cannot
    be summarized yields an empty component. Returns
    ``{"components": [...], "entry_points": [paths]}``.
    """
    components: list[dict] = []
    entry_points: list[str] = []
    for f in files or []:
        path = str(f.get("path") or "")
        text = f.get("text") or ""
        role = f.get("role") or "module"
        if f.get("is_entry_point"):
            entry_points.append(path)
        try:
            if path.endswith(".py"):
                docstring, symbols = _summarize_python(text)
            else:
                docstring, symbols = _summarize_generic(text)
        except Exception:
            docstring, symbols = None, []
        components.append(
            {
                "path": path,
                "role": role,
                "docstring": docstring,
                "symbols": symbols[:_SYMBOL_CAP],
                "provenance": path,
            }
        )
    return {"components": components, "entry_points": entry_points}


_REASON_SYSTEM_PROMPT = (
    "You are a code-distillation agent. You are given the SOURCE of a repository, each file "
    "labelled with its path. Reason ONLY from the supplied files — do not invent APIs, files, "
    "or behaviour that is not present. Determine what the repository was built for, how its "
    "components work together, and what is reusable. CITE the file paths your conclusions rest "
    "on. Respond ONLY with a JSON object with keys: built_for (string), how_it_works (string), "
    "reusable (array of strings), provenance (array of file paths you used)."
)


def _coerce_str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value)]


def reason_over_source(files: list[dict], provider) -> dict:
    """Reason over selected source with a real provider (LES-021 isolated), citing files.

    Builds ONE bounded, path-labelled prompt (each file as ``### <path>\\n<text>`` — the
    files are already capped by :func:`select_source_files`), runs ``provider.generate``,
    and parses the output with the council's tolerant ``_loads_tolerant`` into
    ``{"built_for", "how_it_works", "reusable", "provenance"}``. Only produces a narrative
    for a **real** provider: a ``deterministic`` provider (or an empty parse) yields ``{}``
    — no fabrication. Never raises out of distillation: any provider error → ``{}``.
    """
    if not files:
        return {}
    if getattr(provider, "name", "") == "deterministic":
        return {}
    try:
        blocks = "\n\n".join(f"### {f.get('path')}\n{f.get('text') or ''}" for f in files)
        prompt = (
            "Distil the following repository source into structured knowledge.\n\n"
            f"{blocks}"
        )
        result = provider.generate(system=_REASON_SYSTEM_PROMPT, prompt=prompt)
        obj = _loads_tolerant(result.text or "")
    except Exception:
        return {}
    if not obj:
        return {}
    narrative = {
        "built_for": str(obj.get("built_for") or "").strip(),
        "how_it_works": str(obj.get("how_it_works") or "").strip(),
        "reusable": _coerce_str_list(obj.get("reusable")),
        "provenance": _coerce_str_list(obj.get("provenance")),
    }
    if not (narrative["built_for"] or narrative["how_it_works"] or narrative["reusable"]):
        return {}
    return narrative


def render_repository_markdown(distillation: dict) -> str:
    """Render a distillation dict into an Obsidian-friendly markdown page (pure)."""
    title = (distillation.get("title") or _FALLBACK_TITLE).strip()
    summary = (distillation.get("summary") or "").strip() or "No summary available."

    lines: list[str] = [
        f"# {title}",
        "",
        "## Summary",
        "",
        summary,
        "",
        "## What it is / useful for",
        "",
    ]
    useful_for = distillation.get("useful_for") or []
    lines.extend([f"- {item}" for item in useful_for] or ["- Not determined from available content."])

    lines += ["", "## Key points", ""]
    key_points = distillation.get("key_points") or []
    lines.extend([f"- {point}" for point in key_points] or ["- None extracted."])

    lines += ["", "## Technologies", ""]
    technologies = distillation.get("technologies") or []
    lines.extend([f"- {tech}" for tech in technologies] or ["- None detected."])

    # Components (from source): always present, one bullet per summarized file,
    # each citing its own path (deterministic structural layer — RFC-0008 Phase 2).
    lines += ["", "## Components (from source)", ""]
    components = distillation.get("components") or []
    component_lines: list[str] = []
    for component in components:
        path = component.get("path", "")
        role = component.get("role", "module")
        docstring = component.get("docstring")
        symbols = component.get("symbols") or []
        if docstring:
            detail = docstring
        elif symbols:
            detail = "symbols: " + ", ".join(str(sym) for sym in symbols)
        else:
            detail = "no docstring or top-level symbols"
        component_lines.append(f"- `{path}` — {role} — {detail}")
    lines.extend(component_lines or ["- None extracted from source."])

    # How it works / Built for: only when a real provider produced a narrative
    # (the deterministic provider fabricates nothing).
    narrative = distillation.get("narrative") or {}
    if narrative and (narrative.get("built_for") or narrative.get("how_it_works") or narrative.get("reusable")):
        lines += ["", "## How it works / Built for", ""]
        if narrative.get("built_for"):
            lines += ["**Built for:** " + str(narrative["built_for"]).strip(), ""]
        if narrative.get("how_it_works"):
            lines += ["**How it works:** " + str(narrative["how_it_works"]).strip(), ""]
        reusable = narrative.get("reusable") or []
        if reusable:
            lines.append("**Reusable:**")
            lines.extend([f"- {item}" for item in reusable])

    lines += ["", "## Provenance", ""]
    provenance = distillation.get("provenance") or []
    prov_lines = [f"- {entry.get('item', '')} — source: {entry.get('source', '')}" for entry in provenance]
    for source_file in distillation.get("source_files") or []:
        prov_lines.append(f"- source file read — source: {source_file}")
    lines.extend(prov_lines or ["- None recorded."])
    lines.append("")
    return "\n".join(lines)


def _repo_slug(name: str) -> str:
    """Lowercased, non-alphanumeric-collapsed slug; stable per repo → idempotent."""
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "repository").lower()).strip("-")
    return slug or "repository"


def _read_primary_readme(repository: Repository) -> str:
    """Read the primary README of a scanned repo, tolerantly.

    Resolves the repo dir via ``safe_repo_path`` and picks ``README.md`` /
    ``README`` / the first ``readme*`` (case-insensitive), capped at ~40 KB. Any
    unreadable dir / README (missing path, ``:ro`` mount, permission error) is
    treated as an empty README — reading never raises out of distillation.
    """
    try:
        repo_dir = safe_repo_path(get_settings().repository_root, repository.local_path)
    except Exception:
        return ""
    try:
        entries = sorted(p for p in repo_dir.iterdir() if p.is_file())
    except OSError:
        return ""
    readme_path: Path | None = None
    lower = {p.name.lower(): p for p in entries}
    if "readme.md" in lower:
        readme_path = lower["readme.md"]
    elif "readme" in lower:
        readme_path = lower["readme"]
    else:
        for p in entries:
            if p.name.lower().startswith("readme"):
                readme_path = p
                break
    if readme_path is None:
        return ""
    try:
        return readme_path.read_text(encoding="utf-8", errors="replace")[:_README_CAP_BYTES]
    except OSError:
        return ""


def distill_repository(
    db: Session, *, repository_id: str, knowledge_root: Path | str, provider=None
) -> KnowledgePage:
    """Distil a scanned repo's content into a vault page + ``KnowledgePage``.

    404s a missing repository. Reads the primary README (tolerantly — an
    unreadable repo/README is treated as empty), runs the deterministic extractor,
    renders an Obsidian-friendly page, and writes it under
    ``<knowledge_root>/wiki/repositories/<slug>.md`` (creating dirs). A
    non-writable vault raises **409** (naming the writable-checkout requirement)
    and leaves state untouched. Upserts one ``KnowledgePage`` keyed on
    ``vault_path`` (``page_type="repository"``, ``validation_state="derived"``,
    sha256 checksum) and, when a ``RepositoryDNA`` row exists, stamps its
    ``purpose`` with the distilled summary. Idempotent.
    """
    repository = db.get(Repository, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    if provider is None:
        provider = get_provider(get_settings())

    readme_text = _read_primary_readme(repository)
    dna = repository.dna
    distillation = extract_repo_knowledge(readme_text, dna=dna, name=repository.name)
    if not readme_text.strip():
        # No README to name the repo — fall back to the registered repo name.
        distillation["title"] = repository.name

    # Phase 2 (RFC-0008): a bounded, provenance-tagged read of the actual source.
    # The deterministic structural summary is always produced (hermetic, CI-tested);
    # the reasoned narrative is produced only for a real provider (no fabrication).
    files = select_source_files(repository, dna=dna)
    code = summarize_sources(files)
    narrative = reason_over_source(files, provider) if getattr(provider, "name", "") != "deterministic" else {}
    distillation["components"] = code["components"]
    distillation["entry_points"] = code["entry_points"]
    distillation["source_files"] = [f["path"] for f in files]
    distillation["narrative"] = narrative

    markdown = render_repository_markdown(distillation)
    slug = _repo_slug(repository.name)
    filename = f"{slug}.md"
    vault_path = f"wiki/repositories/{filename}"
    target = Path(knowledge_root) / "wiki" / "repositories" / filename
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        # Read-only / :ro-mounted vault: fail gracefully (409, not 500) and do
        # NOT mutate state.
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot write the repository distillation to the knowledge vault at "
                f"'{knowledge_root}': {exc}. Distillation requires a writable, local-first "
                "checkout of the vault (the compose stack mounts it read-only); run it from "
                "a writable local vault."
            ),
        ) from exc

    checksum = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    source_refs: list[dict] = [
        {"type": "repository", "id": repository.id},
        {"type": "vault_file", "ref": vault_path},
    ]

    page = db.query(KnowledgePage).filter(KnowledgePage.vault_path == vault_path).first()
    if page is None:
        page = KnowledgePage(
            project_id=repository.project_id,
            title=distillation["title"],
            vault_path=vault_path,
            page_type=_PAGE_TYPE,
            validation_state="derived",
            source_refs=source_refs,
            checksum=checksum,
        )
        db.add(page)
    else:
        page.project_id = repository.project_id
        page.title = distillation["title"]
        page.page_type = _PAGE_TYPE
        page.validation_state = "derived"
        page.source_refs = source_refs
        page.checksum = checksum

    if dna is not None:
        dna.purpose = distillation["summary"]

    db.commit()
    db.refresh(page)
    return page


__all__ = [
    "extract_repo_knowledge",
    "select_source_files",
    "summarize_sources",
    "reason_over_source",
    "render_repository_markdown",
    "distill_repository",
]
