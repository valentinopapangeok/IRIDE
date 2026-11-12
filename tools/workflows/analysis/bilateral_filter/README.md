# Satellite Data Smoothing & Texture Blending

## Overview
This tool is designed to post-process fused satellite imagery, specifically addressing the "blocky" artifacts that occur when merging data of widely different spatial resolutions (e.g., fusing low-res aerosol data with high-res optical feeds).

Unlike standard smoothing filters which often preserve artificial block edges, this script uses a **multi-stage "Melting & Blending" approach**. It removes pixelation artifacts while preserving the scientific dynamic range (min/max values) and retaining the high-frequency granularity of the original sensor data.

## Features
* **Artifact Removal:** aggressively smooths out square "staircase" artifacts from low-resolution data sources.
* **Range Recovery:** Automatically rescales the smoothed output to match the original scientific min/max values (preventing data dilution).
* **Texture Blending:** Re-introduces a configurable percentage of the original "grain" to ensure the output looks like satellite imagery, not plastic.
* **Geo-Preservation:** Uses `rasterio` to strictly preserve all georeferencing, projections, and coordinate systems.
* **NaN Handling:** robustly handles NoData/Cloud masks without creating edge artifacts.

## Requirements
* Python 3.8+
* `numpy`
* `opencv-python` (headless version recommended for servers: `opencv-python-headless`)
* `rasterio`

## Installation
```bash
pip install numpy opencv-python rasterio