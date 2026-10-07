import logging
import os
import re

logger = logging.getLogger(__name__)


def _safe_name(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_")
    return clean or "retinascan_report"


def _build_report_text(
    predicted_class: str,
    confidence: float,
    language: str
) -> str:

    confidence_pct = float(confidence) * 100

    stage_map = {
        "Mild": {
            "en": "Mild diabetic retinopathy",
            "ta": "லேசான டயபடிக் ரெட்டிநோபதி"
        },
        "Moderate": {
            "en": "Moderate diabetic retinopathy",
            "ta": "மிதமான டயபடிக் ரெட்டிநோபதி"
        },
        "No_DR": {
            "en": "No diabetic retinopathy detected",
            "ta": "டயபடிக் ரெட்டிநோபதி கண்டறியப்படவில்லை"
        },
        "Proliferate_DR": {
            "en": "Proliferative diabetic retinopathy",
            "ta": "ப்ரோலிஃபரேட்டிவ் டயபடிக் ரெட்டிநோபதி"
        },
        "Severe": {
            "en": "Severe diabetic retinopathy",
            "ta": "கடுமையான டயபடிக் ரெட்டிநோபதி"
        }
    }

    if predicted_class not in stage_map:
        predicted_class = "No_DR"

    stage_label = stage_map[predicted_class][language]

    if language == "ta":
        return (
            f"ரெட்டினாஸ்கேன் திரையிடல் முடிவு. "
            f"{stage_label}. "
            f"நம்பிக்கை அளவு {confidence_pct:.1f} சதவீதம். "
            f"இது செயற்கை நுண்ணறிவு மூலம் வழங்கப்படும் "
            f"திரையிடல் முடிவு மட்டுமே. "
            f"இது இறுதி மருத்துவ நோயறிதல் அல்ல. "
            f"மேலும் பரிசோதனை மற்றும் உறுதிப்படுத்தலுக்காக "
            f"கண் மருத்துவரை அணுகவும்."
        )

    return (
        f"RetinaScan screening result. "
        f"{stage_label}. "
        f"Confidence is {confidence_pct:.1f} percent. "
        f"This is an AI-generated screening result "
        f"and not a final medical diagnosis. "
        f"Please consult an eye-care professional "
        f"for confirmation and follow-up care."
    )


def generate_voice_report(
    predicted_class: str,
    confidence: float,
    language: str = "en",
    output_dir: str = "static/audio",
    filename_prefix: str = "retinascan_report"
) -> str:

    language = (language or "en").strip().lower()

    if language not in ("en", "ta"):
        raise ValueError(
            f"Unsupported language: {language}. Use 'en' or 'ta'."
        )

    os.makedirs(output_dir, exist_ok=True)

    safe_prefix = _safe_name(filename_prefix)

    audio_filename = f"{safe_prefix}_{language}.mp3"
    audio_path = os.path.join(output_dir, audio_filename)

    text = _build_report_text(
        predicted_class,
        confidence,
        language
    )

    try:
        from gtts import gTTS
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency: gTTS. Install it with 'python -m pip install gTTS'."
        ) from exc

    # IMPORTANT:
    # gTTS language code:
    # en = English
    # ta = Tamil
    try:
        tts = gTTS(
            text=text,
            lang=language,
            slow=False
        )
        tts.save(audio_path)
    except Exception as exc:
        logger.exception("gTTS failed while generating voice report for %s/%s", language, safe_prefix)
        raise RuntimeError(
            "Voice generation failed. Check that gTTS is installed and that the environment can reach Google Translate."
        ) from exc

    return audio_path


__all__ = ["generate_voice_report"]