import logging
from typing import Any

from PIL import Image

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.multiAssetPostprocessor import (
    MultiAssetPostprocessor,
)

logger = logging.getLogger(__name__)


class PiqImageQualityAssessment(MultiAssetPostprocessor):
    @property
    def info(self) -> str:
        return "Assessing image quality using PIQ."

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        import torch
        import torchvision.transforms as transforms

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.preprocess = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
            ]
        )

    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        import piq
        import torch

        img_assets = [asset for asset in assets if asset.type == "image"]
        imgs = []
        for asset in img_assets:
            img = Image.open(asset.path).convert("RGB")
            img_tensor = self.preprocess(img)
            imgs.append(img_tensor)

        batch = torch.stack(imgs).to(self.device)  # [B, 3, 224, 224]
        clipiqa = piq.CLIPIQA().to(self.device)

        with torch.no_grad():
            scores = clipiqa(batch)  # [B]

        threshold = 0.1

        for asset, score in zip(img_assets, scores, strict=False):
            asset.quality = score.item()

            if asset.quality is not None and asset.quality < threshold:
                asset.is_bad = True
