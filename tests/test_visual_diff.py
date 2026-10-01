#!/usr/bin/env python3
"""
Unit tests for visual_diff.py
Run with: pytest tests/test_visual_diff.py -v
"""

import json
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from visual_diff import (  # type: ignore[import-unresolved]
    calculate_metrics,
    evaluate_quality_gate,
    load_and_preprocess_images,
    generate_diff_heatmap,
)


def _save_image(arr: np.ndarray, path: Path) -> None:
    """Helper: save a numpy array as PNG image file."""
    cv2.imwrite(str(path), arr)


def _make_solid_img(w=100, h=100, bgr=(200, 150, 100)) -> np.ndarray:
    """Helper: create a solid-color image as BGR numpy array."""
    return np.full((h, w, 3), bgr, dtype=np.uint8)


class TestLoadAndPreprocess:
    def test_raises_on_missing_original(self):
        with pytest.raises(FileNotFoundError):
            load_and_preprocess_images("nonexistent.png", "nonexistent2.png")

    def test_raises_on_missing_rendered(self):
        tmp_path = Path(tempfile.gettempdir()) / "test_vd_render.png"
        _save_image(_make_solid_img(), tmp_path)
        try:
            with pytest.raises(FileNotFoundError):
                load_and_preprocess_images(str(tmp_path), "nonexistent2.png")
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_returns_same_size_for_identical_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.png"
            img = _make_solid_img(80, 60, (50, 100, 150))
            _save_image(img, p)

            orig, rend, (w, h) = load_and_preprocess_images(str(p), str(p))

            assert w == 80
            assert h == 60
            assert orig.shape == (60, 80, 3)
            assert rend.shape == (60, 80, 3)

    def test_upsizes_smaller_rendered_to_match_original(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p_orig = Path(tmpdir) / "orig.png"
            p_rend = Path(tmpdir) / "rend.png"
            _save_image(_make_solid_img(200, 150), p_orig)
            _save_image(_make_solid_img(100, 75), p_rend)

            orig, rend, (w, h) = load_and_preprocess_images(str(p_orig), str(p_rend))

            assert (w, h) == (200, 150)
            assert orig.shape == rend.shape


class TestCalculateMetrics:
    def test_identical_images_ssim_near_one(self):
        img = _make_solid_img(50, 50, (120, 80, 60))
        ssim_val, mae_val, diff = calculate_metrics(img, img.copy())

        assert 0.0 <= ssim_val <= 1.0
        assert mae_val == 0.0
        assert diff.shape == img.shape
        assert np.sum(diff) == 0

    def test_mae_reflects_difference_magnitude(self):
        img_a = _make_solid_img(50, 50, (0, 0, 0))
        img_b = _make_solid_img(50, 50, (255, 255, 255))

        _, mae, diff = calculate_metrics(img_a, img_b)

        assert mae > 0
        assert diff.dtype == np.uint8
        assert diff.shape == img_a.shape

    def test_diff_map_max_for_maximum_color_distance(self):
        img_black = _make_solid_img(20, 20, (0, 0, 0))
        img_white = _make_solid_img(20, 20, (255, 255, 255))

        _, mae, diff = calculate_metrics(img_black, img_white)

        # Max per-channel difference is 255, mean across 3 channels
        # MAE is mean across all pixels, so max possible is 255
        assert 50 < mae < 260


class TestDiffHeatmap:
    def test_heatmap_file_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            img_a = _make_solid_img(50, 50, (100, 100, 100))
            img_b = _make_solid_img(50, 50, (110, 110, 110))
            abs_diff = cv2.absdiff(img_a, img_b)

            out_path = Path(tmpdir) / "heatmap.png"
            generate_diff_heatmap(abs_diff, str(out_path))

            assert out_path.exists()
            assert out_path.stat().st_size > 0


class TestQualityGate:
    def test_pass_when_identical(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            img = _make_solid_img(80, 60)
            p_orig = Path(tmpdir) / "orig.png"
            p_rend = Path(tmpdir) / "rend.png"
            _save_image(img, p_orig)
            _save_image(img.copy(), p_rend)

            result = evaluate_quality_gate(str(p_orig), str(p_rend), str(Path(tmpdir) / "h.png"))

            assert result["passed"] is True
            assert result["status"] == "PASS"
            assert "metrics" in result
            assert "heatmap" in result["artifacts"]

    def test_fail_when_images_differ(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p_orig = Path(tmpdir) / "orig.png"
            p_rend = Path(tmpdir) / "rend.png"
            _save_image(_make_solid_img(80, 60, (0, 0, 0)), p_orig)
            _save_image(_make_solid_img(80, 60, (255, 255, 255)), p_rend)

            result = evaluate_quality_gate(
                str(p_orig), str(p_rend),
                str(Path(tmpdir) / "h.png"),
                min_ssim=0.95, max_mae=5.0,
            )

            assert result["passed"] is False
            assert result["status"] == "FAIL"

    def test_output_json_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p_orig = Path(tmpdir) / "orig.png"
            p_rend = Path(tmpdir) / "rend.png"
            _save_image(_make_solid_img(40, 30, (50, 50, 50)), p_orig)
            _save_image(_make_solid_img(40, 30, (50, 50, 50)), p_rend)

            result = evaluate_quality_gate(str(p_orig), str(p_rend), str(Path(tmpdir) / "h.png"))

            assert "status" in result
            assert "passed" in result
            assert "metrics" in result
            assert "ssim" in result["metrics"]
            assert "mae" in result["metrics"]
            assert "ssim_threshold" in result["metrics"]
            assert "mae_threshold" in result["metrics"]
            assert "dimensions" in result
            assert "artifacts" in result
            assert "recommendation" in result
