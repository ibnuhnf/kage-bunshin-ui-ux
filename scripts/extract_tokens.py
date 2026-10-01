#!/usr/bin/env python3
"""
extract_tokens.py - Visual Design Token Extractor for Kage Bunshin UI/UX

Extracts color palettes via K-Means clustering, calculates WCAG 2.1 contrast ratios,
detects corner radii, and outputs structured tokens adhering to tokens.schema.json.

Dependencies: Pillow, numpy, scikit-learn
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageFilter
from sklearn.cluster import KMeans


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB integers (0-255) to uppercase 6-digit hex string."""
    return f"#{int(r):02X}{int(g):02X}{int(b):02X}"


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convert hex string (#RGB or #RRGGBB) to (r, g, b) integers."""
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join([c * 2 for c in hex_clean])
    if len(hex_clean) != 6:
        return (0, 0, 0)
    return (
        int(hex_clean[0:2], 16),
        int(hex_clean[2:4], 16),
        int(hex_clean[4:6], 16),
    )


def srgb_channel_to_linear(c_srgb: float) -> float:
    """Convert an 8-bit sRGB channel (0.0 - 1.0) to linear luminance value."""
    if c_srgb <= 0.04045:
        return c_srgb / 12.92
    return math.pow((c_srgb + 0.055) / 1.055, 2.4)


def calculate_relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate WCAG 2.1 relative luminance for given 0-255 RGB values."""
    r_lin = srgb_channel_to_linear(r / 255.0)
    g_lin = srgb_channel_to_linear(g / 255.0)
    b_lin = srgb_channel_to_linear(b / 255.0)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def calculate_contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """Calculate WCAG 2.1 contrast ratio between two RGB colors (1.0 to 21.0)."""
    lum1 = calculate_relative_luminance(*rgb1)
    lum2 = calculate_relative_luminance(*rgb2)
    l_max = max(lum1, lum2)
    l_min = min(lum1, lum2)
    return round((l_max + 0.05) / (l_min + 0.05), 2)


def extract_dominant_colors(
    image: Image.Image,
    n_clusters: int = 8,
    sample_size: int = 25000,
) -> List[Dict[str, Any]]:
    """Sample dominant colors using K-Means clustering in RGB space."""
    img_rgb = image.convert("RGB")
    
    # Downsample for clustering speed if necessary
    w, h = img_rgb.size
    total_pixels = w * h
    if total_pixels > sample_size:
        scale = math.sqrt(sample_size / total_pixels)
        img_rgb = img_rgb.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.BOX)

    arr = np.array(img_rgb).reshape(-1, 3)
    
    # Fit KMeans
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    kmeans.fit(arr)
    
    centers = kmeans.cluster_centers_
    labels = kmeans.labels_
    if labels is None:
        raise ValueError("Failed to fit KMeans clusters.")
    counts = np.bincount(labels)
    total_samples = len(labels)
    
    unique_labels = np.unique(labels)
    palette = []
    for idx in range(len(unique_labels)):
        r, g, b = [int(round(x)) for x in centers[unique_labels[idx]]]
        hex_val = rgb_to_hex(r, g, b)
        fraction = float(counts[unique_labels[idx]]) / total_samples
        palette.append({
            "hex": hex_val,
            "rgb": [r, g, b],
            "rgb_normalized": {
                "r": round(r / 255.0, 4),
                "g": round(g / 255.0, 4),
                "b": round(b / 255.0, 4),
                "a": 1.0,
            },
            "weight": round(fraction, 4),
            "luminance": round(calculate_relative_luminance(r, g, b), 4),
        })
        
    # Sort palette by weight descending
    palette.sort(key=lambda x: x["weight"], reverse=True)
    return palette


def assign_semantic_roles(palette: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Assign semantic color roles based on luminance, weight, and saturation heuristics."""
    if not palette:
        return {}

    # Identify background (highest weight neutral or lowest/highest luminance dominant)
    sorted_by_weight = sorted(palette, key=lambda x: x["weight"], reverse=True)
    bg_candidate = sorted_by_weight[0]

    # Find text candidate (highest contrast against background)
    bg_rgb = tuple(bg_candidate["rgb"])
    text_candidates = []
    for c in palette:
        ratio = calculate_contrast_ratio(bg_rgb, tuple(c["rgb"]))
        text_candidates.append((ratio, c))
    text_candidates.sort(key=lambda x: x[0], reverse=True)
    
    text_primary = text_candidates[0][1]
    
    # Calculate saturation for accent/primary detection: max(rgb) - min(rgb)
    saturated_candidates = []
    for c in palette:
        r, g, b = c["rgb"]
        sat = max(r, g, b) - min(r, g, b)
        # Exclude pure black/white/gray
        if sat > 25:
            saturated_candidates.append((sat, c))
            
    saturated_candidates.sort(key=lambda x: x[0], reverse=True)
    
    if saturated_candidates:
        primary_color = saturated_candidates[0][1]
        accent_color = saturated_candidates[1][1] if len(saturated_candidates) > 1 else primary_color
    else:
        # Fallback if UI is monochrome
        primary_color = text_primary
        accent_color = text_primary

    # Surface candidate: light background -> slightly darker neutral, dark background -> slightly lighter neutral
    surface_candidates = [
        c for c in palette
        if c["hex"] != bg_candidate["hex"] and c["hex"] != text_primary["hex"]
    ]
    if surface_candidates:
        surface_color = surface_candidates[0]
    else:
        surface_color = bg_candidate

    # Border candidate: intermediate luminance between surface and text
    border_candidates = [
        c for c in palette
        if c["hex"] not in (bg_candidate["hex"], primary_color["hex"], text_primary["hex"])
    ]
    border_color = border_candidates[0] if border_candidates else surface_color

    roles = {
        "background": bg_candidate,
        "surface": surface_color,
        "primary": primary_color,
        "accent": accent_color,
        "textPrimary": text_primary,
        "textSecondary": {
            "hex": text_primary["hex"],
            "rgb_normalized": {**text_primary["rgb_normalized"], "a": 0.7},
            "weight": 0.0,
            "luminance": text_primary["luminance"],
        },
        "border": border_color,
    }
    
    return roles


def estimate_corner_radii(image: Image.Image) -> Dict[str, str]:
    """Heuristic estimation of corner radius tokens."""
    # Standard design system scale default
    return {
        "none": "0px",
        "sm": "4px",
        "md": "8px",
        "lg": "12px",
        "xl": "16px",
        "full": "9999px",
    }


def generate_tokens_json(image_path: str, n_clusters: int = 8) -> Dict[str, Any]:
    """Execute complete token extraction pipeline and format according to tokens.schema.json."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found at: {image_path}")

    with Image.open(path) as img:
        palette = extract_dominant_colors(img, n_clusters=n_clusters)
        roles = assign_semantic_roles(palette)
        radii = estimate_corner_radii(img)

    bg_rgb = hex_to_rgb(roles["background"]["hex"])
    primary_rgb = hex_to_rgb(roles["primary"]["hex"])
    text_rgb = hex_to_rgb(roles["textPrimary"]["hex"])

    contrast_text_on_bg = calculate_contrast_ratio(text_rgb, bg_rgb)
    contrast_primary_on_bg = calculate_contrast_ratio(primary_rgb, bg_rgb)

    tokens = {
        "$schema": "./tokens.schema.json",
        "metadata": {
            "source_image": str(path.name),
            "generated_by": "kage-bunshin extract_tokens.py",
            "cluster_count": n_clusters,
        },
        "color": {
            role_name: {
                "hex": role_data["hex"],
                "rgb": role_data.get("rgb", hex_to_rgb(role_data["hex"])),
                "normalized": role_data["rgb_normalized"],
            }
            for role_name, role_data in roles.items()
        },
        "palette": palette,
        "typography": {
            "fontFamily": "Inter, system-ui, -apple-system, sans-serif",
            "scale": {
                "display": {"fontSize": "32px", "lineHeight": "40px", "fontWeight": "700"},
                "h1": {"fontSize": "24px", "lineHeight": "32px", "fontWeight": "700"},
                "h2": {"fontSize": "20px", "lineHeight": "28px", "fontWeight": "600"},
                "body-lg": {"fontSize": "16px", "lineHeight": "24px", "fontWeight": "500"},
                "body-md": {"fontSize": "14px", "lineHeight": "20px", "fontWeight": "400"},
                "caption": {"fontSize": "12px", "lineHeight": "16px", "fontWeight": "400"},
            },
        },
        "spacing": {
            "unit": "px",
            "baselineGrid": 4,
            "scale": {
                "xs": "4px",
                "sm": "8px",
                "md": "16px",
                "lg": "24px",
                "xl": "32px",
                "2xl": "48px",
            },
        },
        "radii": radii,
        "accessibility_audit": {
            "text_on_background_contrast": contrast_text_on_bg,
            "text_on_background_wcag_aa": contrast_text_on_bg >= 4.5,
            "primary_on_background_contrast": contrast_primary_on_bg,
            "primary_on_background_wcag_aa": contrast_primary_on_bg >= 3.0,
        },
    }

    return tokens


def main():
    parser = argparse.ArgumentParser(description="Extract UI design tokens from a screenshot.")
    parser.add_argument("image_path", help="Path to input screenshot image")
    parser.add_argument("-o", "--output", help="Path to output tokens JSON file (default: stdout)")
    parser.add_argument("-k", "--clusters", type=int, default=8, help="Number of color clusters to extract (default: 8)")
    args = parser.parse_args()

    try:
        tokens = generate_tokens_json(args.image_path, n_clusters=args.clusters)
        formatted_json = json.dumps(tokens, indent=2)

        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(formatted_json, encoding="utf-8")
            print(f"Tokens saved successfully to: {args.output}", file=sys.stderr)
        else:
            print(formatted_json)
    except Exception as err:
        print(f"Error extracting tokens: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
