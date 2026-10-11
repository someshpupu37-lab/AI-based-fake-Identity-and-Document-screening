import json
from pathlib import Path

from paddleocr import PaddleOCR


class OCRService:
    """
    OCR service for SIH26188.
    Uses PaddleOCR to extract text and confidence scores.
    """

    def __init__(self):
        print("Loading PaddleOCR...")

        self.ocr = PaddleOCR(
            lang="en",
            device="cpu",
            enable_mkldnn=False
        )

        print("PaddleOCR loaded successfully.")

    def _get_result_data(self, result):
        """
        Convert a PaddleOCR result into a Python dictionary.
        Handles the result formats used by current PaddleOCR versions.
        """

        # Try the .json property/method
        data = getattr(result, "json", None)

        if callable(data):
            data = data()

        # JSON string -> dictionary
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = None

        # Dictionary returned directly
        if isinstance(data, dict):
            return data

        # Some result objects expose a dictionary-like value
        if isinstance(result, dict):
            return result

        return None

    def extract_text(self, image_path: str) -> dict:
        """
        Extract text from an image.

        Returns:
            {
                "text": [...],
                "scores": [...],
                "text_count": int,
                "average_confidence": float
            }
        """

        image_path = str(
            Path(image_path).resolve()
        )

        if not Path(image_path).exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        # Run OCR
        results = self.ocr.predict(
            input=image_path
        )

        all_text = []
        all_scores = []

        for result in results:

            data = self._get_result_data(
                result
            )

            if not isinstance(data, dict):
                continue

            # Current PaddleOCR usually stores
            # recognition fields inside "res".
            ocr_data = data.get(
                "res",
                data
            )

            if not isinstance(ocr_data, dict):
                continue

            texts = ocr_data.get(
                "rec_texts",
                []
            )

            scores = ocr_data.get(
                "rec_scores",
                []
            )

            if not isinstance(texts, list):
                texts = []

            if not isinstance(scores, list):
                scores = []

            for index, text in enumerate(
                texts
            ):

                text = str(
                    text
                ).strip()

                if not text:
                    continue

                all_text.append(
                    text
                )

                if index < len(scores):

                    try:
                        score = float(
                            scores[index]
                        )

                    except (
                        TypeError,
                        ValueError
                    ):

                        score = 0.0

                else:

                    score = 0.0

                all_scores.append(
                    round(
                        score,
                        4
                    )
                )

        # Calculate average confidence
        if all_scores:

            average_confidence = round(
                sum(all_scores)
                / len(all_scores),
                4
            )

        else:

            average_confidence = 0.0

        return {
            "text": all_text,
            "scores": all_scores,
            "text_count": len(all_text),
            "average_confidence": average_confidence
        }


# ------------------------------------------------------------
# Simple standalone test
# ------------------------------------------------------------

if __name__ == "__main__":

    print(
        "OCRService module loaded successfully."
    )