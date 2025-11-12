from collections.abc import Callable
from typing import Any

import numpy as np
from PIL import Image

from mkmapdiary.lib.asset import AssetRecord
from mkmapdiary.postprocessors.base.multiAssetPostprocessor import (
    MultiAssetPostprocessor,
)


class AutoRotator(MultiAssetPostprocessor):
    """Automatically rotate images based on their content."""

    @property
    def info(self) -> str:
        return "Auto-rotating images based on content"

    def __init__(self, ai: Callable[..., Any], config: dict) -> None:
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download

        super().__init__(ai, config)
        model_path = hf_hub_download(
            repo_id="DuarteBarbosa/deep-image-orientation-detection",
            filename="orientation_model_v2_0.9882.onnx",
        )
        self.sess = ort.InferenceSession(model_path)

    def processAllAssets(self, assets: list[AssetRecord]) -> None:
        import torchvision.transforms as T

        # Pre-processing transforms
        transform = T.Compose(
            [
                T.Resize((384, 384)),  # Model input size – check model card
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

        # Get input & output names for session
        input_name = self.sess.get_inputs()[0].name
        output_name = self.sess.get_outputs()[0].name

        for asset in assets:
            if asset.type != "image":
                continue

            if "autorotate" not in asset.effects:
                continue

            img_path = str(asset.path)
            img = Image.open(img_path).convert("RGB")
            x = transform(img).unsqueeze(0).numpy()  # shape (1,3,224,224)
            # ONNX expects NHWC or NCHW depending, but here assume NCHW
            # If needed, check sess input shape/dtype
            preds = self.sess.run([output_name], {input_name: x})[0]
            # preds assumed shape (1,4) for classes [0°,90°,180°,270°]
            class_idx = np.argmax(preds, axis=1)[0]
            angle_map = {0: 0, 1: 90, 2: 180, 3: 270}
            rotation = angle_map.get(class_idx, 0)

            # Rotate image if needed
            if rotation != 0:
                img = img.rotate(-rotation, expand=True)
                options = self.config["site"]["image_options"]
                img.save(img_path, **options)
