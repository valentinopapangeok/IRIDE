from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class LocalAsset:
    path: str
    title: str
    media_type: str | None = None
    roles: list[str] | None = None


@dataclass
class LocalMetadataAsset:
    path: str
    title: str


@dataclass
class LocalThumbnailAsset:
    path: str
    title: str
    description: str


@dataclass
class LocalProjectionExt:
    code: str
    wkt2: str


@dataclass
class LocalSvcItem:
    item_id: str
    collection_id: str
    geometry: dict[str, Any]
    bbox: tuple[float, float, float, float]
    datetime_range: tuple[datetime, datetime, datetime]
    assets: dict[str, LocalAsset]
    metadata: LocalMetadataAsset
    thumbnail: LocalThumbnailAsset
    projection_ext: LocalProjectionExt
    marketplace_description: str
    exploitation_tool_link: str
    marketplace_link_id: str
    issa_activation_identifier: str
    issa_update_frequency: str
    issa_spatial_resolution: dict[str, Any]
    issa_thematic_accuracy: dict[str, Any]

    def output_dir(self, root: Path) -> Path:
        return root / self.item_id
