import os
from PIL import Image
import numpy as np
import tensorflow as tf


# Fixed class order used during model training
CLASS_NAMES = [
    "Mild",
    "Moderate",
    "No_DR",
    "Proliferate_DR",
    "Severe"
]


def load_model(model_path: str):
    """Load the trained RetinaScan model."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = tf.keras.models.load_model(
        model_path,
        compile=False
    )

    return model


def preprocess_image(
    image_path: str,
    target_size=(224, 224)
) -> np.ndarray:
    """
    Prepare an image for the trained EfficientNetV2B0 model.

    Important:
    Do NOT divide by 255 here.
    EfficientNetV2 includes its own preprocessing and expects
    float pixel values in the 0-255 range.
    """

    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img = img.resize(target_size, Image.BILINEAR)

        # Keep pixel values in the 0-255 range.
        arr = np.asarray(img, dtype=np.float32)

    # Add batch dimension:
    # (224, 224, 3) -> (1, 224, 224, 3)
    arr = np.expand_dims(arr, axis=0)

    return arr


def predict_from_path(model, image_path: str):
    """
    Predict diabetic retinopathy stage.

    Returns:
        predicted_class
        confidence
        probabilities
    """

    img = preprocess_image(image_path)

    # Run model prediction
    preds = model.predict(img, verbose=0)

    # Remove batch dimension
    probs = np.asarray(preds).squeeze()

    # Expected output: 5 probabilities
    if probs.ndim != 1 or probs.shape[0] != len(CLASS_NAMES):
        raise ValueError(
            f"Unexpected model output shape: {probs.shape}. "
            f"Expected 5 class probabilities."
        )

    # The trained model uses softmax.
    # Only apply softmax if the output does not already look
    # like probabilities.
    if (
        np.any(probs < 0)
        or np.any(probs > 1)
        or not np.isclose(np.sum(probs), 1.0, atol=1e-3)
    ):
        probs = tf.nn.softmax(probs).numpy()

    predicted_index = int(np.argmax(probs))

    predicted_class = CLASS_NAMES[predicted_index]

    confidence = float(probs[predicted_index])

    return {
        "predicted_class": predicted_class,
        "confidence": confidence,
        "probabilities": [
            float(x) for x in probs
        ]
    }


__all__ = [
    "load_model",
    "preprocess_image",
    "predict_from_path",
    "CLASS_NAMES"
]