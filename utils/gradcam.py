import os
from typing import Optional

import cv2
import numpy as np
import tensorflow as tf
from PIL import Image


def find_target_conv_layer(model: tf.keras.Model) -> Optional[tf.keras.layers.Layer]:
    """
    Find the final convolutional layer inside the existing
    EfficientNetV2B0 backbone used by the RetinaScan V5 model.
    """
    try:
        backbone = model.layers[2]

        if hasattr(backbone, "get_layer"):
            return backbone.get_layer("top_conv")

    except Exception:
        pass

    return None


def make_gradcam_heatmap(
    img_array: np.ndarray,
    model: tf.keras.Model,
    last_conv_layer_name: str,
    pred_index: int
) -> np.ndarray:
    """
    Generate Grad-CAM from the existing RetinaScan V5 model.

    The important part is that the EfficientNetV2B0 backbone
    produces both:
        1. top_conv activation
        2. backbone output

    during the same forward pass.

    No model retraining or model rebuilding is performed.
    """

    # ---------------------------------------------------------
    # 1. Get the existing model structure
    # ---------------------------------------------------------

    if len(model.layers) < 9:
        raise RuntimeError(
            "The RetinaScan V5 model does not have the expected architecture."
        )

    backbone = model.layers[2]

    if not hasattr(backbone, "get_layer"):
        raise RuntimeError(
            "The EfficientNetV2B0 backbone could not be accessed."
        )

    # Exact Grad-CAM target layer
    last_conv = backbone.get_layer(last_conv_layer_name)

    if last_conv is None:
        raise RuntimeError(
            f"Could not find convolutional layer: {last_conv_layer_name}"
        )

    # ---------------------------------------------------------
    # 2. Create a VIEW of the existing backbone
    #
    # This does NOT create a new input layer.
    # It simply exposes top_conv and backbone output together.
    # ---------------------------------------------------------

    feature_model = tf.keras.Model(
        inputs=backbone.input,
        outputs=[
            last_conv.output,
            backbone.output
        ],
        name="retinascan_gradcam_features"
    )

    # ---------------------------------------------------------
    # 3. Convert image to Tensor
    # ---------------------------------------------------------

    x = tf.convert_to_tensor(img_array, dtype=tf.float32)

    # ---------------------------------------------------------
    # 4. ONE connected forward pass
    # ---------------------------------------------------------

    with tf.GradientTape() as tape:

        # The original V5 augmentation layer
        augmentation = model.layers[1]

        # Apply the same augmentation layer used by the model.
        # training=False means no random augmentation is applied.
        x_augmented = augmentation(x, training=False)

        # Get top_conv activation AND backbone output
        # from the SAME backbone forward pass.
        conv_outputs, backbone_output = feature_model(
            x_augmented,
            training=False
        )

        # -----------------------------------------------------
        # 5. Recreate ONLY the existing classification head
        #
        # We are using the actual existing layers from the model.
        # Nothing is retrained or changed.
        # -----------------------------------------------------

        gap = model.layers[3]
        batch_norm = model.layers[4]
        dropout_1 = model.layers[5]
        dense_1 = model.layers[6]
        dropout_2 = model.layers[7]
        output_layer = model.layers[8]

        y = gap(backbone_output)
        y = batch_norm(y, training=False)
        y = dropout_1(y, training=False)
        y = dense_1(y)
        y = dropout_2(y, training=False)
        predictions = output_layer(y)

        # -----------------------------------------------------
        # 6. Select predicted class
        # -----------------------------------------------------

        if pred_index is None:
            pred_index = tf.argmax(
                predictions[0]
            )

        pred_index = tf.cast(pred_index, tf.int32)

        class_score = predictions[:, pred_index]

    # ---------------------------------------------------------
    # 7. Calculate Grad-CAM gradients
    # ---------------------------------------------------------

    grads = tape.gradient(
        class_score,
        conv_outputs
    )

    if grads is None:
        raise RuntimeError(
            "Grad-CAM gradient is None. "
            "The selected class score is not connected to top_conv."
        )

    # ---------------------------------------------------------
    # 8. Global average pooling of gradients
    # ---------------------------------------------------------

    pooled_grads = tf.reduce_mean(
        grads,
        axis=(1, 2),
        keepdims=True
    )

    # ---------------------------------------------------------
    # 9. Weighted combination of feature maps
    # ---------------------------------------------------------

    heatmap = tf.reduce_sum(
        conv_outputs * pooled_grads,
        axis=-1
    )

    # ReLU: keep only positive influence
    heatmap = tf.nn.relu(heatmap)

    # Remove batch dimension
    heatmap = tf.squeeze(
        heatmap,
        axis=0
    )

    heatmap = heatmap.numpy()

    if heatmap.size == 0:
        raise ValueError(
            "Grad-CAM heatmap is empty."
        )

    # ---------------------------------------------------------
    # 10. Normalize heatmap to 0..1
    # ---------------------------------------------------------

    heatmap = heatmap - np.min(heatmap)

    max_val = np.max(heatmap)

    if not np.isfinite(max_val) or max_val <= 1e-8:
        return np.zeros_like(
            heatmap,
            dtype=np.float32
        )

    heatmap = heatmap / max_val

    return np.clip(
        heatmap,
        0.0,
        1.0
    ).astype(np.float32)


def overlay_heatmap_on_image(
    original_img_path: str,
    heatmap: np.ndarray,
    output_path: str,
    alpha: float = 0.4
):
    """
    Overlay the Grad-CAM heatmap on the original retinal image.
    """

    img = cv2.imread(original_img_path)

    if img is None:
        raise FileNotFoundError(
            f"Original image not found: {original_img_path}"
        )

    # Convert 0..1 heatmap to 0..255
    heatmap_uint8 = np.uint8(
        255 * np.clip(
            heatmap,
            0.0,
            1.0
        )
    )

    # Resize heatmap to original image size
    heatmap_resized = cv2.resize(
        heatmap_uint8,
        (img.shape[1], img.shape[0])
    )

    # Apply OpenCV color map
    heatmap_color = cv2.applyColorMap(
        heatmap_resized,
        cv2.COLORMAP_JET
    )

    # Blend heatmap and original image
    overlay = cv2.addWeighted(
        heatmap_color,
        alpha,
        img,
        1 - alpha,
        0
    )

    # Make sure destination folder exists
    output_dir = os.path.dirname(output_path)

    if output_dir:
        os.makedirs(
            output_dir,
            exist_ok=True
        )

    # Save result
    success = cv2.imwrite(
        output_path,
        overlay
    )

    if not success:
        raise IOError(
            f"Could not save Grad-CAM image: {output_path}"
        )

    return output_path


def generate_gradcam(
    model: tf.keras.Model,
    image_path: str,
    class_index: int,
    dest_path: str,
    image_tensor: Optional[np.ndarray] = None
) -> str:
    """
    Generate and save a Grad-CAM overlay for the supplied retinal image.
    """

    # ---------------------------------------------------------
    # 1. Prepare image tensor
    # ---------------------------------------------------------

    img_arr = image_tensor

    if img_arr is None:

        with Image.open(image_path) as pil_img:

            pil_img = pil_img.convert("RGB")

            pil_resized = pil_img.resize(
                (224, 224),
                Image.BILINEAR
            )

            img_arr = np.asarray(
                pil_resized,
                dtype=np.float32
            )

            # Match the preprocessing used by the Flask
            # prediction pipeline.

            img_arr = np.expand_dims(
                img_arr,
                axis=0
            )

    # ---------------------------------------------------------
    # 2. Find target convolutional layer
    # ---------------------------------------------------------

    target_layer = find_target_conv_layer(model)

    if target_layer is None:
        raise RuntimeError(
            "Could not find the required EfficientNetV2B0 top_conv layer."
        )

    # ---------------------------------------------------------
    # 3. Generate heatmap
    # ---------------------------------------------------------

    heatmap = make_gradcam_heatmap(
        img_arr,
        model,
        target_layer.name,
        class_index
    )

    # ---------------------------------------------------------
    # 4. Save overlay
    # ---------------------------------------------------------

    output_dir = os.path.dirname(dest_path)

    if output_dir:
        os.makedirs(
            output_dir,
            exist_ok=True
        )

    overlay_heatmap_on_image(
        image_path,
        heatmap,
        dest_path
    )

    return dest_path


__all__ = [
    "generate_gradcam",
    "find_target_conv_layer",
    "make_gradcam_heatmap",
    "overlay_heatmap_on_image"
]