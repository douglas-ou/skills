#!/usr/bin/env python3
"""Validate an AB-prototype review bundle using only the stdlib."""

from __future__ import annotations

import argparse
import itertools
import json
import re
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse


SCHEMA_VERSION = "1.0.0"
REQUIRED_FILES = ("before.html", "after.html", "comparison.html", "prototype-manifest.json")
REQUIRED_DIRS = ("assets", "screenshots")
PROTOTYPE_PAGES = ("before", "after")
CLASSIFICATIONS = {"exact", "derived", "approximate"}
APPROVED_REMOTE_RESOURCES = {
    "https://unpkg.com/react@18.3.1/umd/react.development.js",
    "https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js",
    "https://unpkg.com/@babel/standalone@7.29.0/babel.min.js",
}
PLACEHOLDER_RE = re.compile(r"__[A-Z][A-Z0-9_]*__")
TODO_RE = re.compile(r"\bTODO\b", re.IGNORECASE)
APPROXIMATION_MARKER_RE = re.compile(r"approximate:([A-Za-z0-9._-]+)")
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)", re.IGNORECASE)
DIRECT_JSX_RESOURCE_RE = re.compile(
    r"(?:src|href|poster)\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE
)
DIRECT_CLASS_RE = re.compile(r"className\s*=\s*['\"]([^'\"]+)['\"]")
CSS_CLASS_RE = re.compile(r"\.((?:\\.|[A-Za-z0-9_-])+)")


class BundleHTMLParser(HTMLParser):
    """Collect validation-relevant structure without third-party parsers."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.doctype = False
        self.tags: dict[str, int] = {}
        self.ids: list[str] = []
        self.classes: set[str] = set()
        self.resources: list[tuple[str, str]] = []
        self.style_fragments: list[str] = []
        self.inline_scripts: list[dict[str, Any]] = []
        self._capture: dict[str, Any] | None = None

    def handle_decl(self, decl: str) -> None:
        if decl.strip().lower() == "doctype html":
            self.doctype = True

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags[tag] = self.tags.get(tag, 0) + 1
        attributes = {name: value or "" for name, value in attrs}

        if attributes.get("id"):
            self.ids.append(attributes["id"])
        if attributes.get("class"):
            self.classes.update(attributes["class"].split())
        if attributes.get("style"):
            self.style_fragments.append(attributes["style"])

        if attributes.get("src"):
            self.resources.append((f"<{tag}> src", attributes["src"]))
        if attributes.get("poster"):
            self.resources.append((f"<{tag}> poster", attributes["poster"]))
        if tag == "link" and attributes.get("href"):
            self.resources.append(("<link> href", attributes["href"]))
        if tag in {"use", "image"}:
            value = attributes.get("href") or attributes.get("xlink:href")
            if value:
                self.resources.append((f"<{tag}> href", value))

        if tag in {"style", "script"}:
            self._capture = {"tag": tag, "attrs": attributes, "text": []}

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._capture["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capture is None or self._capture["tag"] != tag:
            return
        text = "".join(self._capture["text"])
        if tag == "style":
            self.style_fragments.append(text)
        else:
            self._capture["text"] = text
            self.inline_scripts.append(self._capture)
        self._capture = None

    @property
    def has_unclosed_capture(self) -> bool:
        return self._capture is not None


class BundleValidator:
    def __init__(self, bundle: Path) -> None:
        self.bundle = bundle.resolve()
        self.errors: list[str] = []
        self.manifest: dict[str, Any] = {}
        self.pages: dict[str, tuple[str, BundleHTMLParser]] = {}

    def error(self, message: str) -> None:
        self.errors.append(message)

    def validate(self) -> list[str]:
        self._validate_layout()
        if self.errors:
            return self.errors
        self._load_manifest()
        if not self.manifest:
            return self.errors
        self._validate_manifest()
        self._parse_pages()
        self._validate_page_protocol()
        self._validate_page_resources_and_classes()
        self._validate_approximation_markers()
        self._validate_comparison()
        self._validate_asset_tree()
        self._validate_screenshots()
        return self.errors

    def _validate_layout(self) -> None:
        if not self.bundle.is_dir():
            self.error(f"bundle directory does not exist: {self.bundle}")
            return
        for name in REQUIRED_FILES:
            path = self.bundle / name
            if not path.is_file():
                self.error(f"missing required file: {name}")
        for name in REQUIRED_DIRS:
            path = self.bundle / name
            if not path.is_dir():
                self.error(f"missing required directory: {name}/")

    def _load_manifest(self) -> None:
        path = self.bundle / "prototype-manifest.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.error(f"prototype-manifest.json is not valid UTF-8 JSON: {exc}")
            return
        if not isinstance(value, dict):
            self.error("prototype-manifest.json root must be an object")
            return
        self.manifest = value

    def _require_object(self, parent: dict[str, Any], key: str, where: str) -> dict[str, Any]:
        value = parent.get(key)
        if not isinstance(value, dict):
            self.error(f"{where}.{key} must be an object")
            return {}
        return value

    def _string_list(self, value: Any, where: str, *, nonempty: bool) -> list[str]:
        if not isinstance(value, list) or (nonempty and not value):
            suffix = "a non-empty array" if nonempty else "an array"
            self.error(f"{where} must be {suffix} of strings")
            return []
        if any(not isinstance(item, str) or not item for item in value):
            self.error(f"{where} must contain only non-empty strings")
            return []
        if len(set(value)) != len(value):
            self.error(f"{where} contains duplicate values")
        return value

    def _validate_manifest(self) -> None:
        manifest = self.manifest
        if manifest.get("schemaVersion") != SCHEMA_VERSION:
            self.error(f"schemaVersion must be {SCHEMA_VERSION!r}")

        flow = self._require_object(manifest, "flow", "manifest")
        for key in ("id", "name", "intent"):
            if not isinstance(flow.get(key), str) or not flow[key].strip():
                self.error(f"manifest.flow.{key} must be a non-empty string")

        source = self._require_object(manifest, "source", "manifest")
        source_root = source.get("root")
        if not isinstance(source_root, str) or not Path(source_root).is_absolute():
            self.error("manifest.source.root must be an absolute path")
        revision = source.get("gitRevision")
        if not isinstance(revision, str) or not (
            revision == "unavailable" or re.fullmatch(r"[0-9a-fA-F]{7,64}", revision)
        ):
            self.error("manifest.source.gitRevision must be a git revision or 'unavailable'")

        files = self._require_object(manifest, "files", "manifest")
        expected_files = {
            "before": "before.html",
            "after": "after.html",
            "comparison": "comparison.html",
            "assets": "assets",
            "screenshots": "screenshots",
        }
        for key, expected in expected_files.items():
            if files.get(key) != expected:
                self.error(f"manifest.files.{key} must be {expected!r}")

        protocol = self._require_object(manifest, "protocol", "manifest")
        scenes = self._string_list(protocol.get("scenes"), "manifest.protocol.scenes", nonempty=True)
        themes = self._optional_protocol_values(protocol, "themes")
        langs = self._optional_protocol_values(protocol, "langs")

        viewports = protocol.get("viewports")
        viewport_ids: list[str] = []
        if not isinstance(viewports, list) or len(viewports) < 2:
            self.error("manifest.protocol.viewports must contain at least desktop and mobile entries")
            viewports = []
        for index, viewport in enumerate(viewports):
            where = f"manifest.protocol.viewports[{index}]"
            if not isinstance(viewport, dict):
                self.error(f"{where} must be an object")
                continue
            viewport_id = viewport.get("id")
            if not isinstance(viewport_id, str) or not viewport_id:
                self.error(f"{where}.id must be a non-empty string")
            else:
                viewport_ids.append(viewport_id)
            for dimension in ("width", "height"):
                value = viewport.get(dimension)
                if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                    self.error(f"{where}.{dimension} must be a positive integer")
        if len(set(viewport_ids)) != len(viewport_ids):
            self.error("manifest.protocol.viewports contains duplicate ids")
        if viewports and not any(v.get("width", 0) >= 768 for v in viewports if isinstance(v, dict)):
            self.error("manifest.protocol.viewports must include a desktop-width viewport")
        if viewports and not any(v.get("width", 10**9) < 768 for v in viewports if isinstance(v, dict)):
            self.error("manifest.protocol.viewports must include a mobile-width viewport")

        self._validate_states(scenes, themes, langs)
        self._validate_regions()
        self._validate_approximations()

    def _optional_protocol_values(self, protocol: dict[str, Any], key: str) -> list[str]:
        if key not in protocol:
            return []
        values = self._string_list(protocol[key], f"manifest.protocol.{key}", nonempty=True)
        if len(values) < 2:
            self.error(f"manifest.protocol.{key} should be omitted unless multiple values are supported")
        return values

    def _validate_states(self, scenes: list[str], themes: list[str], langs: list[str]) -> None:
        states = self.manifest.get("states")
        if not isinstance(states, list):
            self.error("manifest.states must be an array")
            return
        expected = set(itertools.product(scenes, themes or [None], langs or [None]))
        actual: set[tuple[str | None, str | None, str | None]] = set()
        for index, state in enumerate(states):
            where = f"manifest.states[{index}]"
            if not isinstance(state, dict):
                self.error(f"{where} must be an object")
                continue
            scene = state.get("scene")
            theme = state.get("theme")
            lang = state.get("lang")
            if scene not in scenes:
                self.error(f"{where}.scene is not declared in protocol.scenes")
            if themes and theme not in themes:
                self.error(f"{where}.theme is not declared in protocol.themes")
            if not themes and "theme" in state:
                self.error(f"{where} must omit theme because the project has no theme protocol")
            if langs and lang not in langs:
                self.error(f"{where}.lang is not declared in protocol.langs")
            if not langs and "lang" in state:
                self.error(f"{where} must omit lang because the project has no language protocol")
            key = (scene, theme if themes else None, lang if langs else None)
            if key in actual:
                self.error(f"{where} duplicates another state")
            actual.add(key)
        missing = expected - actual
        extra = actual - expected
        if missing:
            self.error(f"manifest.states is missing protocol combinations: {self._format_states(missing)}")
        if extra:
            self.error(f"manifest.states has invalid protocol combinations: {self._format_states(extra)}")

    @staticmethod
    def _format_states(states: Iterable[tuple[Any, Any, Any]]) -> str:
        return ", ".join(
            f"scene={scene!r},theme={theme!r},lang={lang!r}"
            for scene, theme, lang in sorted(states, key=lambda item: tuple(str(v) for v in item))
        )

    def _validate_regions(self) -> None:
        regions = self.manifest.get("regions")
        if not isinstance(regions, list) or not regions:
            self.error("manifest.regions must be a non-empty array")
            return
        seen: set[str] = set()
        for index, region in enumerate(regions):
            where = f"manifest.regions[{index}]"
            if not isinstance(region, dict):
                self.error(f"{where} must be an object")
                continue
            region_id = region.get("id")
            if not isinstance(region_id, str) or not region_id:
                self.error(f"{where}.id must be a non-empty string")
            elif region_id in seen:
                self.error(f"{where}.id duplicates {region_id!r}")
            else:
                seen.add(region_id)
            for key in ("componentSources", "styleSources", "tokenSources", "resourceSources"):
                values = region.get(key)
                if not isinstance(values, list):
                    self.error(f"{where}.{key} must be an array")
                elif key != "styleSources" and any(
                    not isinstance(value, str) or not value for value in values
                ):
                    self.error(f"{where}.{key} must contain only non-empty strings")
            if isinstance(region.get("componentSources"), list) and not region["componentSources"]:
                self.error(f"{where}.componentSources must identify at least one source component")
            if isinstance(region.get("styleSources"), list) and not region["styleSources"]:
                self.error(f"{where}.styleSources must identify at least one style source")
            for style_index, source in enumerate(region.get("styleSources", [])):
                style_where = f"{where}.styleSources[{style_index}]"
                if not isinstance(source, dict):
                    self.error(f"{style_where} must be an object")
                    continue
                for key in ("path", "context"):
                    if not isinstance(source.get(key), str) or not source[key]:
                        self.error(f"{style_where}.{key} must be a non-empty string")
                classification = source.get("classification")
                if classification not in CLASSIFICATIONS:
                    self.error(f"{style_where}.classification must be exact, derived, or approximate")
                if classification == "derived" and not source.get("derivation"):
                    self.error(f"{style_where}.derivation is required for derived styles")
                if classification == "approximate" and not source.get("approximationId"):
                    self.error(f"{style_where}.approximationId is required for approximate styles")

    def _validate_approximations(self) -> None:
        approximations = self.manifest.get("approximations")
        if not isinstance(approximations, list):
            self.error("manifest.approximations must be an array")
            return
        seen: set[str] = set()
        for index, approximation in enumerate(approximations):
            where = f"manifest.approximations[{index}]"
            if not isinstance(approximation, dict):
                self.error(f"{where} must be an object")
                continue
            approximation_id = approximation.get("id")
            if not isinstance(approximation_id, str) or not approximation_id:
                self.error(f"{where}.id must be a non-empty string")
            elif approximation_id in seen:
                self.error(f"{where}.id duplicates {approximation_id!r}")
            else:
                seen.add(approximation_id)
            if not isinstance(approximation.get("reason"), str) or not approximation["reason"]:
                self.error(f"{where}.reason must be a non-empty string")
            context = approximation.get("originalContext")
            if not isinstance(context, dict) or not isinstance(context.get("detail"), str) or not context["detail"]:
                self.error(f"{where}.originalContext.detail must be a non-empty string")

    def _parse_pages(self) -> None:
        for filename in ("before.html", "after.html", "comparison.html"):
            path = self.bundle / filename
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                self.error(f"{filename} is not readable UTF-8: {exc}")
                continue
            parser = BundleHTMLParser()
            try:
                parser.feed(source)
                parser.close()
            except Exception as exc:  # HTMLParser may raise on malformed declarations.
                self.error(f"{filename} cannot be parsed as HTML: {exc}")
            self.pages[filename] = (source, parser)
            if not parser.doctype:
                self.error(f"{filename} must start with <!doctype html>")
            for tag in ("html", "head", "body"):
                if parser.tags.get(tag, 0) != 1:
                    self.error(f"{filename} must contain exactly one <{tag}> element")
            duplicate_ids = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
            if duplicate_ids:
                self.error(f"{filename} contains duplicate ids: {', '.join(duplicate_ids)}")
            if parser.has_unclosed_capture:
                self.error(f"{filename} has an unclosed <style> or <script> block")
            if TODO_RE.search(source):
                self.error(f"{filename} contains a residual TODO")
            placeholders = sorted(set(PLACEHOLDER_RE.findall(source)))
            if placeholders:
                self.error(f"{filename} contains unresolved template placeholders: {', '.join(placeholders)}")
            for script in parser.inline_scripts:
                if script["attrs"].get("src"):
                    continue
                text = script["text"].strip()
                if not text:
                    self.error(f"{filename} contains an empty inline script")
                if script["attrs"].get("type") == "application/json":
                    try:
                        json.loads(text)
                    except json.JSONDecodeError as exc:
                        script_id = script["attrs"].get("id", "<anonymous>")
                        self.error(f"{filename} inline JSON script {script_id!r} is invalid: {exc}")

    def _config_from_page(self, filename: str) -> dict[str, Any] | None:
        page = self.pages.get(filename)
        if not page:
            return None
        scripts = [
            script
            for script in page[1].inline_scripts
            if script["attrs"].get("id") == "prototype-config"
        ]
        if len(scripts) != 1:
            self.error(f"{filename} must contain exactly one #prototype-config script")
            return None
        if scripts[0]["attrs"].get("type") != "application/json":
            self.error(f"{filename} #prototype-config must use type=application/json")
            return None
        try:
            value = json.loads(scripts[0]["text"])
        except json.JSONDecodeError:
            return None
        if not isinstance(value, dict):
            self.error(f"{filename} #prototype-config must contain a JSON object")
            return None
        return value

    def _validate_page_protocol(self) -> None:
        protocol = self.manifest.get("protocol", {})
        expected = {"scenes": protocol.get("scenes", [])}
        if "themes" in protocol:
            expected["themes"] = protocol["themes"]
        if "langs" in protocol:
            expected["langs"] = protocol["langs"]
        configs: dict[str, dict[str, Any]] = {}
        for page in PROTOTYPE_PAGES:
            filename = f"{page}.html"
            config = self._config_from_page(filename)
            if config is None:
                continue
            configs[page] = config
            if config != expected:
                self.error(f"{filename} #prototype-config does not exactly match manifest protocol")
            source = self.pages[filename][0]
            if "URLSearchParams" not in source:
                self.error(f"{filename} does not read URLSearchParams")
            for parameter in ("scene", "theme", "lang"):
                protocol_key = {"scene": "scenes", "theme": "themes", "lang": "langs"}[parameter]
                if protocol_key in expected and not re.search(rf"['\"]{parameter}['\"]", source):
                    self.error(f"{filename} does not implement the {parameter!r} query parameter")
        if len(configs) == 2 and configs["before"] != configs["after"]:
            self.error("before.html and after.html declare different scene protocols")

    def _validate_page_resources_and_classes(self) -> None:
        for filename, (source, parser) in self.pages.items():
            resources = list(parser.resources)
            inline_css = "\n".join(parser.style_fragments)
            resources.extend(
                ("inline CSS url()", match.group(2)) for match in CSS_URL_RE.finditer(inline_css)
            )
            resources.extend(("JSX resource", match.group(1)) for match in DIRECT_JSX_RESOURCE_RE.finditer(source))
            seen_resources: set[tuple[str, str]] = set()
            for context, reference in resources:
                key = (context, reference)
                if key in seen_resources:
                    continue
                seen_resources.add(key)
                self._validate_resource_reference(filename, context, reference, self.bundle)

            declared_classes = set(parser.classes)
            for match in DIRECT_CLASS_RE.finditer(source):
                declared_classes.update(match.group(1).split())
            css_source = "\n".join(parser.style_fragments)
            defined_classes = {
                self._unescape_css_identifier(match.group(1)) for match in CSS_CLASS_RE.finditer(css_source)
            }
            unresolved = sorted(
                class_name
                for class_name in declared_classes
                if class_name and class_name not in defined_classes
            )
            if unresolved:
                self.error(f"{filename} contains unresolved classes: {', '.join(unresolved)}")

        for page in PROTOTYPE_PAGES:
            filename = f"{page}.html"
            entry = self.pages.get(filename)
            if not entry:
                continue
            babel_scripts = [
                script
                for script in entry[1].inline_scripts
                if script["attrs"].get("type") == "text/babel"
            ]
            if len(babel_scripts) != 1 or "ReactDOM.createRoot" not in babel_scripts[0]["text"]:
                self.error(f"{filename} must contain one React text/babel application script")
            remote = {
                reference
                for _context, reference in entry[1].resources
                if urlparse(reference).scheme in {"http", "https"}
            }
            missing = APPROVED_REMOTE_RESOURCES - remote
            if missing:
                self.error(f"{filename} is missing fixed runtime scripts: {', '.join(sorted(missing))}")

    @staticmethod
    def _unescape_css_identifier(value: str) -> str:
        return re.sub(r"\\(.)", r"\1", value)

    def _validate_resource_reference(
        self, filename: str, context: str, reference: str, base_directory: Path
    ) -> None:
        reference = reference.strip()
        if not reference or reference.startswith(("#", "data:", "blob:", "mailto:", "tel:", "javascript:")):
            return
        parsed = urlparse(reference)
        if parsed.scheme in {"http", "https"} or parsed.netloc:
            if reference not in APPROVED_REMOTE_RESOURCES:
                self.error(f"{filename} uses unapproved remote resource in {context}: {reference}")
            return
        if parsed.scheme:
            self.error(f"{filename} uses unsupported resource scheme in {context}: {reference}")
            return
        relative = unquote(parsed.path)
        if not relative:
            return
        if relative.startswith("/"):
            self.error(f"{filename} uses a root-absolute resource in {context}: {reference}")
            return
        candidate = (base_directory / relative).resolve()
        try:
            candidate.relative_to(self.bundle)
        except ValueError:
            self.error(f"{filename} resource escapes the bundle in {context}: {reference}")
            return
        if not candidate.is_file():
            self.error(f"{filename} references a missing resource in {context}: {reference}")

    def _validate_approximation_markers(self) -> None:
        declared = {
            item.get("id")
            for item in self.manifest.get("approximations", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        used_by_regions = {
            source.get("approximationId")
            for region in self.manifest.get("regions", [])
            if isinstance(region, dict)
            for source in region.get("styleSources", [])
            if isinstance(source, dict) and source.get("classification") == "approximate"
        }
        markers: set[str] = set()
        for page in PROTOTYPE_PAGES:
            entry = self.pages.get(f"{page}.html")
            if entry:
                markers.update(APPROXIMATION_MARKER_RE.findall(entry[0]))
        for approximation_id in sorted(markers - declared):
            self.error(f"approximation marker {approximation_id!r} is missing from manifest.approximations")
        for approximation_id in sorted(used_by_regions - declared, key=str):
            self.error(f"region approximation {approximation_id!r} is missing from manifest.approximations")
        for approximation_id in sorted(declared - markers):
            self.error(f"manifest approximation {approximation_id!r} has no marker in before.html or after.html")
        for approximation_id in sorted(declared - used_by_regions):
            self.error(f"manifest approximation {approximation_id!r} is not connected to a region style source")

    def _validate_comparison(self) -> None:
        entry = self.pages.get("comparison.html")
        if not entry:
            return
        source, parser = entry
        embedded = [
            script
            for script in parser.inline_scripts
            if script["attrs"].get("id") == "embedded-prototype-manifest"
        ]
        if len(embedded) != 1:
            self.error("comparison.html must contain exactly one #embedded-prototype-manifest script")
        else:
            try:
                embedded_manifest = json.loads(embedded[0]["text"])
            except json.JSONDecodeError:
                embedded_manifest = None
            if embedded_manifest is not None and embedded_manifest != self.manifest:
                self.error("comparison.html embedded manifest is stale or differs from prototype-manifest.json")
        required_fragments = (
            "data-prototype-comparison",
            "URLSearchParams",
            "manifest.files[page]",
            "iframe.style.width",
            "iframe.style.height",
            "scale(",
            "data-page-tab",
        )
        for fragment in required_fragments:
            if fragment not in source:
                self.error(f"comparison.html is missing review behavior marker: {fragment}")
        for parameter, key in (("scene", "scenes"), ("theme", "themes"), ("lang", "langs")):
            if key in self.manifest.get("protocol", {}) and f'"{parameter}"' not in source:
                self.error(f"comparison.html does not synchronize {parameter!r}")

    def _validate_asset_tree(self) -> None:
        assets = self.bundle / "assets"
        if not assets.is_dir():
            return
        for path in assets.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            suffix = path.suffix.lower()
            if suffix not in {".css", ".svg"}:
                continue
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                self.error(f"asset is not readable UTF-8: {path.relative_to(self.bundle)}: {exc}")
                continue
            relative_name = str(path.relative_to(self.bundle))
            if TODO_RE.search(source) or PLACEHOLDER_RE.search(source):
                self.error(f"asset contains a residual TODO or template placeholder: {relative_name}")
            for match in CSS_URL_RE.finditer(source):
                self._validate_resource_reference(relative_name, "asset url()", match.group(2), path.parent)
            if suffix == ".svg":
                parser = BundleHTMLParser()
                try:
                    parser.feed(source)
                    parser.close()
                except Exception as exc:
                    self.error(f"SVG cannot be parsed: {relative_name}: {exc}")
                    continue
                for context, reference in parser.resources:
                    self._validate_resource_reference(relative_name, context, reference, path.parent)

    def _validate_screenshots(self) -> None:
        screenshots = self.manifest.get("screenshots")
        if not isinstance(screenshots, list) or not screenshots:
            self.error("manifest.screenshots must be a non-empty array")
            return
        protocol = self.manifest.get("protocol", {})
        scenes = set(protocol.get("scenes", []))
        themes = set(protocol.get("themes", []))
        langs = set(protocol.get("langs", []))
        viewports = {
            viewport.get("id"): viewport
            for viewport in protocol.get("viewports", [])
            if isinstance(viewport, dict) and isinstance(viewport.get("id"), str)
        }
        coverage: set[tuple[str, str]] = set()
        scene_coverage: set[str] = set()
        seen_files: set[str] = set()
        for index, capture in enumerate(screenshots):
            where = f"manifest.screenshots[{index}]"
            if not isinstance(capture, dict):
                self.error(f"{where} must be an object")
                continue
            filename = capture.get("file")
            page = capture.get("page")
            scene = capture.get("scene")
            viewport_id = capture.get("viewport")
            if page not in PROTOTYPE_PAGES:
                self.error(f"{where}.page must be before or after")
            if scene not in scenes:
                self.error(f"{where}.scene is not declared in protocol.scenes")
            else:
                scene_coverage.add(scene)
            if viewport_id not in viewports:
                self.error(f"{where}.viewport is not declared in protocol.viewports")
            if themes and capture.get("theme") not in themes:
                self.error(f"{where}.theme is not declared in protocol.themes")
            if not themes and "theme" in capture:
                self.error(f"{where} must omit theme because themes are unsupported")
            if langs and capture.get("lang") not in langs:
                self.error(f"{where}.lang is not declared in protocol.langs")
            if not langs and "lang" in capture:
                self.error(f"{where} must omit lang because languages are unsupported")
            if isinstance(page, str) and isinstance(viewport_id, str):
                coverage.add((page, viewport_id))
            if not isinstance(filename, str) or not filename.startswith("screenshots/"):
                self.error(f"{where}.file must be a relative path under screenshots/")
                continue
            if filename in seen_files:
                self.error(f"{where}.file duplicates {filename!r}")
            seen_files.add(filename)
            path = (self.bundle / filename).resolve()
            try:
                path.relative_to((self.bundle / "screenshots").resolve())
            except ValueError:
                self.error(f"{where}.file escapes screenshots/: {filename}")
                continue
            if not path.is_file():
                self.error(f"{where}.file does not exist: {filename}")
                continue
            dimensions = self._png_dimensions(path)
            if dimensions is None:
                self.error(f"{where}.file is not a valid PNG: {filename}")
            elif viewport_id in viewports:
                viewport = viewports[viewport_id]
                expected = (viewport.get("width"), viewport.get("height"))
                if dimensions != expected:
                    self.error(
                        f"{where}.file has dimensions {dimensions[0]}x{dimensions[1]}, "
                        f"expected {expected[0]}x{expected[1]} for viewport {viewport_id!r}"
                    )

        expected_coverage = set(itertools.product(PROTOTYPE_PAGES, viewports))
        missing_coverage = expected_coverage - coverage
        if missing_coverage:
            formatted = ", ".join(f"{page}/{viewport}" for page, viewport in sorted(missing_coverage))
            self.error(f"screenshots do not cover both pages at every viewport: {formatted}")
        missing_scenes = scenes - scene_coverage
        if missing_scenes:
            self.error(f"screenshots do not cover scenes: {', '.join(sorted(missing_scenes))}")

    @staticmethod
    def _png_dimensions(path: Path) -> tuple[int, int] | None:
        try:
            header = path.read_bytes()[:24]
        except OSError:
            return None
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
            return None
        return struct.unpack(">II", header[16:24])


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Path to the generated review bundle")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable result")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    validator = BundleValidator(args.bundle)
    errors = validator.validate()
    if args.json:
        print(
            json.dumps(
                {"ok": not errors, "bundle": str(validator.bundle), "errors": errors},
                ensure_ascii=False,
                indent=2,
            )
        )
    elif errors:
        print(f"FAIL: {len(errors)} validation error(s)")
        for error in errors:
            print(f"- {error}")
    else:
        print(f"PASS: valid AB-prototype bundle at {validator.bundle}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
