#!/usr/bin/env python3
"""
visual_diff.py - Adversarial Visual Difference & Quality Gate Engine for Kage Bunshin UI/UX

Computes Structural Similarity Index (SSIM) and Mean Absolute Error (MAE) between
original design screenshot and rendered preview, generating a colored difference heatmap.

Dependencies: opencv-python, scikit-image, numpy, Pillow
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

import cv2
import numpy as np
try:
    from skimage.metrics import structural_similarity as ssim_func  # type: ignore[import-untyped,import-not-found]
except ImportError:
    ssim_func = None


def load_and_preprocess_images(orig_path: str, rend_path: str) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int]]:
    """Load both images, align their dimensions, and return as BGR numpy arrays."""
    p_orig = Path(orig_path)
    p_rend = Path(rend_path)

    if not p_orig.exists():
        raise FileNotFoundError(f"Original image not found: {orig_path}")
    if not p_rend.exists():
        raise FileNotFoundError(f"Rendered image not found: {rend_path}")

    img_orig = cv2.imread(str(p_orig), cv2.IMREAD_COLOR)
    img_rend = cv2.imread(str(p_rend), cv2.IMREAD_COLOR)

    if img_orig is None:
        raise ValueError(f"Failed to decode original image: {orig_path}")
    if img_rend is None:
        raise ValueError(f"Failed to decode rendered image: {rend_path}")

    h_orig, w_orig = img_orig.shape[:2]
    h_rend, w_rend = img_rend.shape[:2]

    target_w = max(w_orig, w_rend)
    target_h = max(h_orig, h_rend)

    # Pad or resize rendered image to match target dimensions
    if (w_orig, h_orig) != (target_w, target_h):
        img_orig = cv2.resize(img_orig, (target_w, target_h), interpolation=cv2.INTER_AREA)
    if (w_rend, h_rend) != (target_w, target_h):
        img_rend = cv2.resize(img_rend, (target_w, target_h), interpolation=cv2.INTER_AREA)

    return img_orig, img_rend, (target_w, target_h)


def calculate_metrics(img_orig: np.ndarray, img_rend: np.ndarray) -> Tuple[float, float, np.ndarray]:
    """Calculate SSIM, MAE, and per-pixel difference matrix."""
    # Convert to grayscale for SSIM calculation
    gray_orig = cv2.cvtColor(img_orig, cv2.COLOR_BGR2GRAY)
    gray_rend = cv2.cvtColor(img_rend, cv2.COLOR_BGR2GRAY)

    # Compute SSIM and difference map
    if ssim_func is None:
        raise ImportError("scikit-image is not installed. Install via `pip install scikit-image`.")
    score_ssim, diff_map = ssim_func(gray_orig, gray_rend, full=True)
    score_ssim = float(score_ssim)

    # Compute MAE in 8-bit color space [0, 255]
    abs_diff = cv2.absdiff(img_orig, img_rend)
    mae_score = float(np.mean(abs_diff))

    return score_ssim, mae_score, abs_diff


def generate_diff_heatmap(abs_diff: np.ndarray, output_path: str) -> None:
    """Generate and save an amplified JET colormap heatmap showing spatial pixel error locations."""
    # Convert 3-channel absolute difference to single channel max intensity
    gray_diff = cv2.cvtColor(abs_diff, cv2.COLOR_BGR2GRAY)

    # Amplify differences for clear visualization (scale non-zero diffs)
    amplified = cv2.normalize(gray_diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)  # type: ignore[call-overload]
    
    # Apply colormap (Blue = Match, Green/Yellow = Slight Shift, Red = Severe Error)
    heatmap = cv2.applyColorMap(amplified, cv2.COLORMAP_JET)

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_p), heatmap)


def evaluate_quality_gate(
    orig_path: str,
    rend_path: str,
    heatmap_path: str = "diff_heatmap.png",
    min_ssim: float = 0.95,
    max_mae: float = 5.0,
) -> Dict[str, Any]:
    """Run full adversarial visual diff evaluation."""
    img_orig, img_rend, dims = load_and_preprocess_images(orig_path, rend_path)
    ssim_val, mae_val, abs_diff = calculate_metrics(img_orig, img_rend)

    generate_diff_heatmap(abs_diff, heatmap_path)

    passed = (ssim_val >= min_ssim) and (mae_val <= max_mae)

    result = {
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "metrics": {
            "ssim": round(ssim_val, 4),
            "mae": round(mae_val, 2),
            "ssim_threshold": min_ssim,
            "mae_threshold": max_mae,
        },
        "dimensions": {
            "width": dims[0],
            "height": dims[1],
        },
        "artifacts": {
            "heatmap": heatmap_path,
            "original": orig_path,
            "rendered": rend_path,
        },
        "recommendation": (
            "Quality gate satisfied."
            if passed
            else "Inspect heatmap. Check typography line-heights, container gaps, and fill colors."
        ),
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Adversarial visual diff engine (SSIM & MAE).")
    parser.add_argument("--original", required=True, help="Path to original reference screenshot")
    parser.add_argument("--rendered", required=True, help="Path to rendered target preview image")
    parser.add_argument("-o", "--heatmap", default="diff_heatmap.png", help="Path to save diff heatmap image")
    parser.add_argument("--min-ssim", type=float, default=0.95, help="Minimum SSIM threshold (default: 0.95)")
    parser.add_argument("--max-mae", type=float, default=5.0, help="Maximum MAE threshold (default: 5.0)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    try:
        report = evaluate_quality_gate(
            orig_path=args.original,
            rend_path=args.rendered,
            heatmap_path=args.heatmap,
            min_ssim=args.min_ssim,
            max_mae=args.max_mae,
        )

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"=== Visual Diff Verification Report ===")
            print(f"Status:   {report['status']}")
            print(f"SSIM:     {report['metrics']['ssim']:.4f} (target >= {args.min_ssim})")
            print(f"MAE:      {report['metrics']['mae']:.2f} (target <= {args.max_mae})")
            print(f"Heatmap:  {report['artifacts']['heatmap']}")
            print(f"Action:   {report['recommendation']}")

        if not report["passed"]:
            sys.exit(2)

    except Exception as err:
        print(f"Error executing visual diff: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
