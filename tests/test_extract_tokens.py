#!/usr/bin/env python3
"""
Unit tests for extract_tokens.py
Run with: pytest tests/test_extract_tokens.py -v
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from extract_tokens import (  # type: ignore[import-unresolved]
    assign_semantic_roles,
    calculate_contrast_ratio,
    calculate_relative_luminance,
    extract_dominant_colors,
    generate_tokens_json,
    hex_to_rgb,
    rgb_to_hex,
    srgb_channel_to_linear,
)


class TestRgbHexConversions:
    def test_rgb_to_hex_black(self):
        assert rgb_to_hex(0, 0, 0) == "#000000"

    def test_rgb_to_hex_white(self):
        assert rgb_to_hex(255, 255, 255) == "#FFFFFF"

    def test_rgb_to_hex_arbitrary(self):
        assert rgb_to_hex(13, 37, 255) == "#0D25FF"

    def test_rgb_to_hex_uppercase(self):
        assert rgb_to_hex(100, 100, 100) == "#646464"

    def test_hex_to_rgb_black(self):
        assert hex_to_rgb("#000000") == (0, 0, 0)

    def test_hex_to_rgb_white(self):
        assert hex_to_rgb("#FFFFFF") == (255, 255, 255)

    def test_hex_to_rgb_arbitrary(self):
        assert hex_to_rgb("#0D25FF") == (13, 37, 255)

    def test_hex_to_rgb_short_form(self):
        assert hex_to_rgb("#FFF") == (255, 255, 255)

    def test_roundtrip(self):
        orig = (42, 128, 200)
        assert hex_to_rgb(rgb_to_hex(*orig)) == orig


class TestSrgbConversion:
    def test_srgb_black(self):
        assert math.isclose(srgb_channel_to_linear(0.0), 0.0, abs_tol=1e-9)

    def test_srgb_white(self):
        assert math.isclose(srgb_channel_to_linear(1.0), 1.0, abs_tol=1e-9)

    def test_srgb_midpoint(self):
        val = srgb_channel_to_linear(0.5)
        assert 0.0 < val < 1.0


class TestContrastRatio:
    def test_black_white_max_contrast(self):
        cr = calculate_contrast_ratio((0, 0, 0), (255, 255, 255))
        assert cr == 21.0

    def test_contrast_ratio_symmetric(self):
        cr1 = calculate_contrast_ratio((10, 10, 10), (200, 200, 200))
        cr2 = calculate_contrast_ratio((200, 200, 200), (10, 10, 10))
        assert cr1 == cr2

    def test_same_color_contrast_is_one(self):
        cr = calculate_contrast_ratio((128, 128, 128), (128, 128, 128))
        assert cr == 1.0

    def test_contrast_ratio_in_range(self):
        cr = calculate_contrast_ratio((50, 50, 50), (200, 200, 200))
        assert 1.0 <= cr <= 21.0

    def test_wcag_aa_normal_text_requires_4_5(self):
        black = (0, 0, 0)
        white = (255, 255, 255)
        cr = calculate_contrast_ratio(black, white)
        assert cr >= 4.5, "Black on white must meet WCAG AA for normal text"


class TestDominantColors:
    def _make_gradient_image(self, colors):
        """Helper: create a tiny image with a few solid-color horizontal strips."""
        w, h = 10, len(colors)
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        for i, (r, g, b) in enumerate(colors):
            arr[i, :] = [r, g, b]
        from PIL import Image
        return Image.fromarray(arr)

    def test_extracts_requested_cluster_count(self):
        img = self._make_gradient_image([(255, 0, 0)] * 10 + [(0, 0, 255)] * 10)
        palette = extract_dominant_colors(img, n_clusters=2)
        assert len(palette) <= 2

    def test_palette_sorted_by_weight(self):
        img = self._make_gradient_image([(255, 0, 0)] * 5 + [(0, 0, 255)] * 20)
        palette = extract_dominant_colors(img, n_clusters=2)
        weights = [c["weight"] for c in palette]
        assert weights == sorted(weights, reverse=True), "Palette must be sorted by weight descending"

    def test_palette_entry_has_required_fields(self):
        img = self._make_gradient_image([(128, 64, 192)] * 5)
        palette = extract_dominant_colors(img, n_clusters=1)
        assert len(palette) == 1
        entry = palette[0]
        assert "hex" in entry and entry["hex"].startswith("#")
        assert "rgb" in entry and len(entry["rgb"]) == 3
        assert "rgb_normalized" in entry and "r" in entry["rgb_normalized"]
        assert "weight" in entry
        assert "luminance" in entry

    def test_raises_on_zero_clusters(self):
        from PIL import Image
        img = Image.new("RGB", (5, 5))
        with pytest.raises(Exception):
            extract_dominant_colors(img, n_clusters=0)


class TestSemanticRoles:
    def test_assigns_background_role(self):
        palette = [
            {"hex": "#FFFFFF", "rgb": [255, 255, 255], "rgb_normalized": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}, "weight": 0.7, "luminance": 1.0},
            {"hex": "#000000", "rgb": [0, 0, 0], "rgb_normalized": {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0}, "weight": 0.3, "luminance": 0.0},
        ]
        roles = assign_semantic_roles(palette)
        assert "background" in roles
        assert "textPrimary" in roles
        assert "primary" in roles
        assert "accent" in roles

    def test_empty_palette_returns_empty_dict(self):
        roles = assign_semantic_roles([])
        assert roles == {}

    def test_all_6_roles_present(self):
        palette = [
            {"hex": "#F5F5F5", "rgb": [245, 245, 245], "rgb_normalized": {"r": 0.96, "g": 0.96, "b": 0.96, "a": 1.0}, "weight": 0.5, "luminance": 0.93},
            {"hex": "#1A1A1A", "rgb": [26, 26, 26], "rgb_normalized": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1.0}, "weight": 0.15, "luminance": 0.01},
            {"hex": "#3B82F6", "rgb": [59, 130, 246], "rgb_normalized": {"r": 0.23, "g": 0.51, "b": 0.96, "a": 1.0}, "weight": 0.2, "luminance": 0.19},
            {"hex": "#10B981", "rgb": [16, 185, 129], "rgb_normalized": {"r": 0.06, "g": 0.73, "b": 0.51, "a": 1.0}, "weight": 0.1, "luminance": 0.19},
            {"hex": "#6B7280", "rgb": [107, 114, 128], "rgb_normalized": {"r": 0.42, "g": 0.45, "b": 0.5, "a": 1.0}, "weight": 0.05, "luminance": 0.19},
        ]
        roles = assign_semantic_roles(palette)
        expected_roles = {"background", "surface", "primary", "accent", "textPrimary", "textSecondary", "border"}
        assert set(roles.keys()) == expected_roles


class TestTokensJson:
    def test_generate_tokens_json_missing_file(self):
        with pytest.raises(FileNotFoundError):
            generate_tokens_json("nonexistent_image.png")

    def test_generate_tokens_json_output_structure(self):
        from PIL import Image
        img = Image.new("RGB", (20, 20), color=(100, 150, 200))
        tmp_path = Path(tempfile.gettempdir()) / "test_tokens_structure.png"
        img.save(tmp_path)
        try:
            tokens = generate_tokens_json(str(tmp_path), n_clusters=4)
        finally:
            tmp_path.unlink(missing_ok=True)

        assert "$schema" in tokens
        assert "metadata" in tokens
        assert "color" in tokens
        assert "palette" in tokens
        assert "typography" in tokens
        assert "spacing" in tokens
        assert "radii" in tokens
        assert "accessibility_audit" in tokens

    def test_accessibility_audit_fields(self):
        from PIL import Image
        img = Image.new("RGB", (20, 20), color=(255, 255, 255))
        tmp_path = Path(tempfile.gettempdir()) / "test_tokens_audit.png"
        img.save(tmp_path)
        try:
            tokens = generate_tokens_json(str(tmp_path), n_clusters=2)
        finally:
            tmp_path.unlink(missing_ok=True)

        audit = tokens["accessibility_audit"]
        assert "text_on_background_contrast" in audit
        assert "text_on_background_wcag_aa" in audit
        assert "primary_on_background_contrast" in audit
        assert "primary_on_background_wcag_aa" in audit


class TestRadiusScale:
    def test_estimate_corner_radii_returns_all_keys(self):
        from PIL import Image
        from extract_tokens import estimate_corner_radii  # type: ignore[import-unresolved]
        img = Image.new("RGB", (10, 10))
        radii = estimate_corner_radii(img)
        expected = {"none", "sm", "md", "lg", "xl", "full"}
        assert set(radii.keys()) == expected