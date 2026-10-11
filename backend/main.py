from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
from PIL import Image, ExifTags
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from paddleocr import PaddleOCR


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_FILE = BASE_DIR / "sih26188.db"


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="SIH26188 Backend",
    description="AI-Based Fake Identity & Document Screening System",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE
# ============================================================

def init_database():
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verification_id TEXT UNIQUE,
            document_type TEXT,
            name TEXT,
            document_number TEXT,
            risk_score REAL,
            risk_level TEXT,
            status TEXT,
            result_json TEXT,
            created_at TEXT
        )
        """
    )

    connection.commit()
    connection.close()


init_database()


# ============================================================
# PADDLEOCR
# ============================================================

print("Loading PaddleOCR...")

ocr_engine = PaddleOCR(
    lang="en",
    device="cpu",
    enable_mkldnn=False,
)

print("PaddleOCR loaded successfully.")


# ============================================================
# DOCUMENT TYPES
# ============================================================

DOCUMENT_TYPES = {
    "pan_card": [
        "pan_number",
        "name",
        "father_name",
        "date_of_birth",
    ],
    "passport": [
        "name",
        "passport_number",
        "nationality",
        "date_of_birth",
        "expiry_date",
        "gender",
    ],
    "national_id": [
        "name",
        "id_number",
        "date_of_birth",
        "gender",
    ],
    "driving_license": [
        "name",
        "license_number",
        "date_of_birth",
        "expiry_date",
    ],
    "visa": [
        "visa_number",
        "visa_type",
        "entry_valid_from",
        "entry_valid_until",
        "stay_duration",
    ],
    "permit": [
        "name",
        "permit_number",
        "issue_date",
        "expiry_date",
    ],
}


NUMBER_FIELDS = {
    "pan_card": "pan_number",
    "passport": "passport_number",
    "national_id": "id_number",
    "driving_license": "license_number",
    "visa": "visa_number",
    "permit": "permit_number",
}


# ============================================================
# PROTOTYPE BLACKLIST
# ============================================================

BLACKLIST = {
    "DEMO-BLACK-001",
    "DEMO-BLACK-002",
    "DEMO-ID-BLACK-001",
    "DEMO-VISA-BLACK-001",
    "DEMO-LIC-BLACK-001",
    "DEMO-PERMIT-BLACK-001",
}


# ============================================================
# FILE SAVE
# ============================================================

async def save_file(file: UploadFile) -> dict:

    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are allowed.",
        )

    contents = await file.read()

    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Maximum file size is 10 MB.",
        )

    extension = allowed_types[file.content_type]

    filename = f"{uuid.uuid4().hex}{extension}"

    file_path = UPLOAD_DIR / filename

    file_path.write_bytes(contents)

    return {
        "original_filename": file.filename or "unknown",
        "saved_filename": filename,
        "path": str(file_path),
        "content_type": file.content_type,
        "size_bytes": len(contents),
    }


# ============================================================
# OCR
# ============================================================

def run_ocr(image_path: str) -> dict:

    results = ocr_engine.predict(
        input=str(image_path)
    )

    all_text = []
    all_scores = []

    for result in results:

        data = getattr(
            result,
            "json",
            None,
        )

        if callable(data):
            data = data()

        if isinstance(data, str):

            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = None

        if not isinstance(data, dict):
            continue

        ocr_data = data.get(
            "res",
            data,
        )

        if not isinstance(ocr_data, dict):
            continue

        texts = ocr_data.get(
            "rec_texts",
            [],
        )

        scores = ocr_data.get(
            "rec_scores",
            [],
        )

        if not isinstance(texts, list):
            continue

        for index, text in enumerate(texts):

            text = str(text).strip()

            if not text:
                continue

            all_text.append(text)

            if index < len(scores):

                try:
                    score = float(
                        scores[index]
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    score = 0.0

            else:
                score = 0.0

            all_scores.append(
                round(score, 4)
            )

    average_confidence = 0.0

    if all_scores:

        average_confidence = round(
            sum(all_scores) / len(all_scores),
            4,
        )

    return {
        "text": all_text,
        "scores": all_scores,
        "text_count": len(all_text),
        "average_confidence": average_confidence,
    }


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_lines(
    lines: list[str],
) -> list[str]:

    cleaned = []

    for line in lines:

        value = re.sub(
            r"\s+",
            " ",
            str(line).strip(),
        )

        if value:
            cleaned.append(value)

    return cleaned


def find_value(
    lines: list[str],
    labels: list[str],
) -> Optional[str]:

    for index, line in enumerate(lines):

        normalized = (
            line.lower().strip()
        )

        for label in labels:

            label_lower = label.lower()

            if normalized.startswith(
                label_lower
            ):

                remaining = (
                    line[len(label):]
                    .strip()
                )

                remaining = (
                    remaining
                    .lstrip(":|-")
                    .strip()
                )

                if remaining:
                    return remaining

                if index + 1 < len(lines):

                    next_line = (
                        lines[index + 1]
                        .strip()
                    )

                    if next_line:
                        return next_line

    return None


# ============================================================
# PAN NUMBER EXTRACTION
# ============================================================

def find_pan_number(
    lines: list[str],
) -> Optional[str]:

    pattern = re.compile(
        r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
    )

    for line in lines:

        cleaned = (
            line
            .upper()
            .replace(" ", "")
            .replace("-", "")
        )

        match = pattern.search(
            cleaned
        )

        if match:
            return match.group(0)

    for index, line in enumerate(lines):

        lower = line.lower()

        if (
            "pan" in lower
            or "account number" in lower
            or "permanent account" in lower
        ):

            start = max(
                0,
                index - 1,
            )

            end = min(
                len(lines),
                index + 3,
            )

            for candidate in lines[start:end]:

                cleaned = (
                    candidate
                    .upper()
                    .replace(" ", "")
                    .replace("-", "")
                )

                match = pattern.search(
                    cleaned
                )

                if match:
                    return match.group(0)

    return None


# ============================================================
# DATE EXTRACTION
# ============================================================

def find_date(
    lines: list[str],
) -> Optional[str]:

    patterns = [
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{2}-\d{2}-\d{4}\b",
        r"\b\d{2}\.\d{2}\.\d{4}\b",
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        r"\b\d{1,2}-\d{1,2}-\d{4}\b",
    ]

    for line in lines:

        for pattern in patterns:

            match = re.search(
                pattern,
                line,
            )

            if match:
                return match.group(0)

    return None


def find_date_near_label(
    lines: list[str],
    labels: list[str],
) -> Optional[str]:

    patterns = [
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{2}-\d{2}-\d{4}\b",
        r"\b\d{2}\.\d{2}\.\d{4}\b",
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        r"\b\d{1,2}-\d{1,2}-\d{4}\b",
    ]

    for index, line in enumerate(lines):

        lower = line.lower()

        label_found = False

        for label in labels:

            if label.lower() in lower:
                label_found = True
                break

        if not label_found:
            continue

        end = min(
            len(lines),
            index + 4,
        )

        for candidate in lines[index:end]:

            for pattern in patterns:

                match = re.search(
                    pattern,
                    candidate,
                )

                if match:
                    return match.group(0)

    return None


# ============================================================
# NAME EXTRACTION
# ============================================================

def extract_person_name(
    lines: list[str],
) -> Optional[str]:

    value = find_value(
        lines,
        [
            "name",
            "full name",
            "/name",
        ],
    )

    if value:
        return value

    for index, line in enumerate(lines):

        normalized = (
            line.lower()
            .replace("/", " ")
            .replace(":", " ")
            .replace("-", " ")
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        ).strip()

        if (
            normalized == "name"
            or normalized.endswith(" name")
        ):

            if index + 1 < len(lines):

                candidate = (
                    lines[index + 1]
                    .strip()
                )

                if candidate:
                    return candidate

    return None


# ============================================================
# FATHER NAME EXTRACTION
# ============================================================

def extract_father_name(
    lines: list[str],
) -> Optional[str]:

    value = find_value(
        lines,
        [
            "father's name",
            "father name",
            "father",
            "fa/father's name",
            "fa/father name",
        ],
    )

    if value:
        return value

    for index, line in enumerate(lines):

        normalized = (
            line.lower()
            .replace("/", " ")
            .replace(":", " ")
            .replace("-", " ")
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        ).strip()

        if (
            "father" in normalized
            and "name" in normalized
        ):

            if index + 1 < len(lines):

                candidate = (
                    lines[index + 1]
                    .strip()
                )

                if candidate:
                    return candidate

    return None


# ============================================================
# FIELD EXTRACTION
# ============================================================

def extract_fields(
    document_type: str,
    lines: list[str],
) -> dict:

    lines = clean_lines(lines)

    # --------------------------------------------------------
    # PAN CARD
    # --------------------------------------------------------

    if document_type == "pan_card":

        return {
            "pan_number": find_pan_number(
                lines
            ),
            "name": extract_person_name(
                lines
            ),
            "father_name": extract_father_name(
                lines
            ),
            "date_of_birth": (
                find_date_near_label(
                    lines,
                    [
                        "date of birth",
                        "dob",
                    ],
                )
                or find_date(lines)
            ),
        }

    # --------------------------------------------------------
    # PASSPORT
    # --------------------------------------------------------

    if document_type == "passport":

        return {
            "name": extract_person_name(
                lines
            ),
            "passport_number": find_value(
                lines,
                [
                    "passport number",
                    "passport no",
                    "passport",
                    "document number",
                    "document no",
                ],
            ),
            "nationality": find_value(
                lines,
                [
                    "nationality",
                ],
            ),
            "date_of_birth": (
                find_date_near_label(
                    lines,
                    [
                        "date of birth",
                        "dob",
                    ],
                )
            ),
            "expiry_date": (
                find_date_near_label(
                    lines,
                    [
                        "expiry date",
                        "date of expiry",
                        "expiry",
                    ],
                )
            ),
            "gender": find_value(
                lines,
                [
                    "gender",
                    "sex",
                ],
            ),
        }

    # --------------------------------------------------------
    # NATIONAL ID
    # --------------------------------------------------------

    if document_type == "national_id":

        return {
            "name": extract_person_name(
                lines
            ),
            "id_number": find_value(
                lines,
                [
                    "id number",
                    "id no",
                    "identity number",
                    "document number",
                    "document no",
                ],
            ),
            "date_of_birth": (
                find_date_near_label(
                    lines,
                    [
                        "date of birth",
                        "dob",
                    ],
                )
            ),
            "gender": find_value(
                lines,
                [
                    "gender",
                    "sex",
                ],
            ),
        }

    # --------------------------------------------------------
    # DRIVING LICENSE
    # --------------------------------------------------------

    if document_type == "driving_license":

        return {
            "name": extract_person_name(
                lines
            ),
            "license_number": find_value(
                lines,
                [
                    "license number",
                    "licence number",
                    "license no",
                    "licence no",
                    "document number",
                ],
            ),
            "date_of_birth": (
                find_date_near_label(
                    lines,
                    [
                        "date of birth",
                        "dob",
                    ],
                )
            ),
            "expiry_date": (
                find_date_near_label(
                    lines,
                    [
                        "expiry date",
                        "expiry",
                    ],
                )
            ),
        }

    # --------------------------------------------------------
    # VISA
    # --------------------------------------------------------

    if document_type == "visa":

        return {
            "visa_number": find_value(
                lines,
                [
                    "visa number",
                    "visa no",
                ],
            ),
            "visa_type": find_value(
                lines,
                [
                    "visa type",
                ],
            ),
            "entry_valid_from": find_value(
                lines,
                [
                    "valid from",
                    "entry valid from",
                ],
            ),
            "entry_valid_until": find_value(
                lines,
                [
                    "valid until",
                    "entry valid until",
                ],
            ),
            "stay_duration": find_value(
                lines,
                [
                    "stay duration",
                    "duration of stay",
                ],
            ),
        }

    # --------------------------------------------------------
    # PERMIT
    # --------------------------------------------------------

    if document_type == "permit":

        return {
            "name": extract_person_name(
                lines
            ),
            "permit_number": find_value(
                lines,
                [
                    "permit number",
                    "permit no",
                    "document number",
                ],
            ),
            "issue_date": (
                find_date_near_label(
                    lines,
                    [
                        "issue date",
                    ],
                )
            ),
            "expiry_date": (
                find_date_near_label(
                    lines,
                    [
                        "expiry date",
                        "expiry",
                    ],
                )
            ),
        }

    raise ValueError(
        f"Unsupported document type: {document_type}"
    )


# ============================================================
# DATE PARSING
# ============================================================

def parse_date(
    value: Optional[str],
):

    if not value:
        return None

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
    ]

    for date_format in formats:

        try:
            return datetime.strptime(
                value.strip(),
                date_format,
            )
        except ValueError:
            pass

    return None


# ============================================================
# VALIDATION
# ============================================================

def validate_document(
    document_type: str,
    fields: dict,
) -> dict:

    required_fields = DOCUMENT_TYPES[
        document_type
    ]

    missing_fields = [
        field
        for field in required_fields
        if not fields.get(field)
    ]

    total_fields = len(
        required_fields
    )

    available_fields = (
        total_fields -
        len(missing_fields)
    )

    completeness_score = round(
        (
            available_fields /
            total_fields
        ) * 100,
        2,
    )

    expiry_result = {
        "checked": False,
        "expired": None,
        "valid_format": True,
        "message": (
            "Expiry check not required."
        ),
    }

    if "expiry_date" in fields:

        expiry_result["checked"] = True

        expiry_value = fields.get(
            "expiry_date"
        )

        if not expiry_value:

            expiry_result[
                "message"
            ] = (
                "Expiry date not detected."
            )

        else:

            parsed = parse_date(
                expiry_value
            )

            if parsed is None:

                expiry_result[
                    "valid_format"
                ] = False

                expiry_result[
                    "message"
                ] = (
                    "Expiry date format is invalid."
                )

            else:

                is_expired = (
                    parsed.date()
                    < datetime.now().date()
                )

                expiry_result[
                    "expired"
                ] = is_expired

                expiry_result[
                    "message"
                ] = (
                    "Document is expired."
                    if is_expired
                    else
                    "Document is not expired."
                )

    document_number_field = (
        NUMBER_FIELDS[
            document_type
        ]
    )

    document_number = fields.get(
        document_number_field
    )

    number_valid = False

    if document_number:

        if document_type == "pan_card":

            number_valid = bool(
                re.fullmatch(
                    r"[A-Za-z]{5}[0-9]{4}[A-Za-z]",
                    document_number.strip(),
                )
            )

        else:

            number_valid = bool(
                re.fullmatch(
                    r"[A-Za-z0-9]"
                    r"[A-Za-z0-9\-/ ]*",
                    document_number.strip(),
                )
            )

    validation_score = (
        completeness_score
    )

    if not number_valid:
        validation_score -= 10

    if expiry_result[
        "expired"
    ] is True:

        validation_score -= 25

    validation_score = max(
        0,
        min(
            100,
            round(
                validation_score,
                2,
            ),
        ),
    )

    valid = (
        len(missing_fields) == 0
        and number_valid
        and expiry_result[
            "valid_format"
        ]
        and expiry_result[
            "expired"
        ] is not True
    )

    return {
        "valid": valid,
        "score": validation_score,
        "required_fields": required_fields,
        "missing_fields": missing_fields,
        "number_valid": number_valid,
        "expiry": expiry_result,
    }


# ============================================================
# BLACKLIST
# ============================================================

def check_blacklist(
    document_type: str,
    fields: dict,
) -> dict:

    field = NUMBER_FIELDS[
        document_type
    ]

    value = fields.get(
        field
    )

    if not value:

        return {
            "checked": True,
            "blacklisted": False,
            "message": (
                "No document number detected."
            ),
        }

    normalized_value = (
        value.upper().strip()
    )

    matched = (
        normalized_value in BLACKLIST
    )

    return {
        "checked": True,
        "blacklisted": matched,
        "document_number": value,
        "message": (
            "Prototype blacklist match detected."
            if matched
            else
            "No prototype blacklist match."
        ),
    }


# ============================================================
# IMAGE ANALYSIS
# ============================================================

def analyze_image(
    image_path: str,
) -> dict:

    image = cv2.imread(
        str(image_path)
    )

    if image is None:

        return {
            "integrity_score": 0,
            "tampering_suspicion": 100,
            "indicators": [
                "Image could not be read."
            ],
        }

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    sharpness = cv2.Laplacian(
        gray,
        cv2.CV_64F,
    ).var()

    indicators = []

    suspicion = 0

    if sharpness < 50:

        indicators.append(
            "Image appears blurry or low-sharpness."
        )

        suspicion += 15

    elif sharpness < 120:

        indicators.append(
            "Image has moderate sharpness."
        )

        suspicion += 5

    else:

        indicators.append(
            "Image sharpness is acceptable."
        )

    metadata = {}

    try:

        image_pil = Image.open(
            image_path
        )

        exif = image_pil.getexif()

        for key, value in exif.items():

            tag = ExifTags.TAGS.get(
                key,
                str(key),
            )

            metadata[tag] = str(value)

    except Exception:

        metadata = {}

    if metadata:

        indicators.append(
            "Image metadata is present."
        )

    else:

        indicators.append(
            "No EXIF metadata detected."
        )

    suspicion = max(
        0,
        min(
            100,
            suspicion,
        ),
    )

    return {
        "integrity_score": (
            100 - suspicion
        ),
        "tampering_suspicion": suspicion,
        "sharpness": round(
            float(sharpness),
            2,
        ),
        "metadata": metadata,
        "indicators": indicators,
    }


# ============================================================
# RISK ENGINE
# ============================================================

def calculate_risk(
    ocr_confidence: float,
    validation_score: float,
    tampering_suspicion: float,
    blacklisted: bool,
) -> dict:

    risk = 0.0

    risk += (
        (
            100 -
            (
                ocr_confidence *
                100
            )
        )
        * 0.20
    )

    risk += (
        (
            100 -
            validation_score
        )
        * 0.35
    )

    risk += (
        tampering_suspicion
        * 0.45
    )

    if blacklisted:
        risk += 50

    risk = max(
        0,
        min(
            100,
            round(
                risk,
                2,
            ),
        ),
    )

    if risk <= 30:

        risk_level = "LOW"
        status = "VERIFIED"

    elif risk <= 60:

        risk_level = "MEDIUM"
        status = "REVIEW_REQUIRED"

    else:

        risk_level = "HIGH"
        status = "HIGH_RISK"

    if blacklisted:

        risk_level = "HIGH"
        status = "BLOCKED_REVIEW"

    return {
        "risk_score": risk,
        "risk_level": risk_level,
        "status": status,
    }


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "project": "SIH26188",
        "message": "Backend is running successfully",
        "status": "online",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
    }


# ============================================================
# UPLOAD
# ============================================================

@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
):

    result = await save_file(
        file
    )

    return {
        "success": True,
        "message": (
            "Document uploaded successfully."
        ),
        "file": result,
    }


# ============================================================
# OCR
# ============================================================

@app.post("/api/ocr")
async def perform_ocr(
    file: UploadFile = File(...),
):

    result = await save_file(
        file
    )

    file_path = result["path"]

    try:

        ocr_result = run_ocr(
            file_path
        )

        return {
            "success": True,
            "message": (
                "OCR completed successfully."
            ),
            "filename": (
                result[
                    "original_filename"
                ]
            ),
            "text": (
                ocr_result[
                    "text"
                ]
            ),
            "scores": (
                ocr_result[
                    "scores"
                ]
            ),
            "text_count": (
                ocr_result[
                    "text_count"
                ]
            ),
            "average_confidence": (
                ocr_result[
                    "average_confidence"
                ]
            ),
        }

    finally:

        Path(
            file_path
        ).unlink(
            missing_ok=True
        )


# ============================================================
# COMPLETE VERIFICATION
# ============================================================

@app.post("/api/verify")
async def verify_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
):

    document_type = (
        document_type
        .lower()
        .strip()
    )

    if document_type not in DOCUMENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Unsupported document type."
                ),
                "allowed_types": list(
                    DOCUMENT_TYPES.keys()
                ),
            },
        )

    result = await save_file(
        file
    )

    file_path = result["path"]

    try:

        ocr_result = run_ocr(
            file_path
        )

        fields = extract_fields(
            document_type,
            ocr_result["text"],
        )

        validation = validate_document(
            document_type,
            fields,
        )

        blacklist = check_blacklist(
            document_type,
            fields,
        )

        image_analysis = analyze_image(
            file_path
        )

        risk = calculate_risk(
            ocr_confidence=(
                ocr_result[
                    "average_confidence"
                ]
            ),
            validation_score=(
                validation[
                    "score"
                ]
            ),
            tampering_suspicion=(
                image_analysis[
                    "tampering_suspicion"
                ]
            ),
            blacklisted=(
                blacklist[
                    "blacklisted"
                ]
            ),
        )

        verification_id = (
            "SIH-"
            +
            datetime.now().strftime(
                "%Y%m%d-%H%M%S"
            )
            +
            "-"
            +
            uuid.uuid4().hex[
                :6
            ].upper()
        )

        name = fields.get(
            "name"
        )

        number_field = (
            NUMBER_FIELDS[
                document_type
            ]
        )

        document_number = (
            fields.get(
                number_field
            )
        )

        result_payload = {
            "fields": fields,
            "validation": validation,
            "blacklist": blacklist,
            "image_analysis": image_analysis,
        }

        connection = sqlite3.connect(
            DATABASE_FILE
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO verifications
            (
                verification_id,
                document_type,
                name,
                document_number,
                risk_score,
                risk_level,
                status,
                result_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                verification_id,
                document_type,
                name,
                document_number,
                risk["risk_score"],
                risk["risk_level"],
                risk["status"],
                json.dumps(
                    result_payload
                ),
                datetime.now().isoformat(),
            ),
        )

        connection.commit()
        connection.close()

        return {
            "success": True,
            "message": (
                "Complete document verification completed."
            ),
            "verification_id": (
                verification_id
            ),
            "document_type": (
                document_type
            ),
            "original_filename": (
                result[
                    "original_filename"
                ]
            ),
            "ocr": {
                "text": (
                    ocr_result[
                        "text"
                    ]
                ),
                "scores": (
                    ocr_result[
                        "scores"
                    ]
                ),
                "text_count": (
                    ocr_result[
                        "text_count"
                    ]
                ),
                "average_confidence": (
                    ocr_result[
                        "average_confidence"
                    ]
                ),
            },
            "extracted_fields": fields,
            "validation": validation,
            "blacklist": blacklist,
            "image_analysis": image_analysis,
            "risk": risk,
        }

    except Exception as exc:

        print(
            "VERIFICATION ERROR:",
            repr(exc)
        )

        return {
            "success": False,
            "message": "Verification failed.",
            "error": str(exc),
        }

    finally:

        Path(
            file_path
        ).unlink(
            missing_ok=True
        )


# ============================================================
# HISTORY
# ============================================================

@app.get("/api/history")
async def get_history():

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = (
        sqlite3.Row
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            verification_id,
            document_type,
            name,
            document_number,
            risk_score,
            risk_level,
            status,
            created_at
        FROM verifications
        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# SINGLE HISTORY RECORD
# ============================================================

@app.get(
    "/api/history/{verification_id}"
)
async def get_history_record(
    verification_id: str,
):

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = (
        sqlite3.Row
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM verifications
        WHERE verification_id = ?
        """,
        (
            verification_id,
        ),
    )

    row = cursor.fetchone()

    connection.close()

    if row is None:

        raise HTTPException(
            status_code=404,
            detail="Verification not found.",
        )

    result = dict(row)

    if result.get(
        "result_json"
    ):

        result["result"] = json.loads(
            result[
                "result_json"
            ]
        )

    result.pop(
        "result_json",
        None,
    )

    return result