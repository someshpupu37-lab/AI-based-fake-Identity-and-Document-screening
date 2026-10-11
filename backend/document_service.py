from datetime import datetime


class DocumentService:

    REQUIRED_FIELDS = {
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

    def __init__(self):
        pass

    def _find_value(self, lines, labels):
        for i, line in enumerate(lines):
            line = line.strip()
            lower = line.lower()

            for label in labels:
                label_lower = label.lower()

                if lower.startswith(label_lower):
                    value = line[len(label):].strip()
                    value = value.lstrip(":|-").strip()

                    if value:
                        return value

                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line:
                            return next_line

        return None

    def extract_fields(self, document_type, text_lines):
        lines = [
            str(line).strip()
            for line in text_lines
            if str(line).strip()
        ]

        document_type = document_type.lower().strip()

        if document_type == "passport":
            return {
                "name": self._find_value(
                    lines,
                    ["name", "full name"]
                ),
                "passport_number": self._find_value(
                    lines,
                    ["passport number", "passport no", "passport"]
                ),
                "nationality": self._find_value(
                    lines,
                    ["nationality"]
                ),
                "date_of_birth": self._find_value(
                    lines,
                    ["date of birth", "dob"]
                ),
                "expiry_date": self._find_value(
                    lines,
                    ["expiry date", "expiry", "date of expiry"]
                ),
                "gender": self._find_value(
                    lines,
                    ["gender", "sex"]
                ),
            }

        if document_type == "national_id":
            return {
                "name": self._find_value(
                    lines,
                    ["name", "full name"]
                ),
                "id_number": self._find_value(
                    lines,
                    ["id number", "id no", "identity number"]
                ),
                "date_of_birth": self._find_value(
                    lines,
                    ["date of birth", "dob"]
                ),
                "gender": self._find_value(
                    lines,
                    ["gender", "sex"]
                ),
            }

        if document_type == "driving_license":
            return {
                "name": self._find_value(
                    lines,
                    ["name", "full name"]
                ),
                "license_number": self._find_value(
                    lines,
                    ["license number", "licence number", "license no", "licence no"]
                ),
                "date_of_birth": self._find_value(
                    lines,
                    ["date of birth", "dob"]
                ),
                "expiry_date": self._find_value(
                    lines,
                    ["expiry date", "expiry"]
                ),
            }

        if document_type == "visa":
            return {
                "visa_number": self._find_value(
                    lines,
                    ["visa number", "visa no", "visa"]
                ),
                "visa_type": self._find_value(
                    lines,
                    ["visa type"]
                ),
                "entry_valid_from": self._find_value(
                    lines,
                    ["valid from", "entry valid from"]
                ),
                "entry_valid_until": self._find_value(
                    lines,
                    ["valid until", "entry valid until"]
                ),
                "stay_duration": self._find_value(
                    lines,
                    ["stay duration", "duration of stay"]
                ),
            }

        if document_type == "permit":
            return {
                "name": self._find_value(
                    lines,
                    ["name", "full name"]
                ),
                "permit_number": self._find_value(
                    lines,
                    ["permit number", "permit no"]
                ),
                "issue_date": self._find_value(
                    lines,
                    ["issue date"]
                ),
                "expiry_date": self._find_value(
                    lines,
                    ["expiry date", "expiry"]
                ),
            }

        raise ValueError(
            f"Unsupported document type: {document_type}"
        )

    def validate(self, document_type, fields):
        document_type = document_type.lower().strip()

        if document_type not in self.REQUIRED_FIELDS:
            raise ValueError(
                f"Unsupported document type: {document_type}"
            )

        required = self.REQUIRED_FIELDS[document_type]

        missing_fields = [
            field
            for field in required
            if not fields.get(field)
        ]

        completeness_score = round(
            (
                (len(required) - len(missing_fields))
                / len(required)
            ) * 100,
            2,
        )

        expiry = {
            "checked": False,
            "expired": None,
            "valid_format": True,
        }

        if "expiry_date" in fields:
            expiry["checked"] = True

            value = fields.get("expiry_date")

            if value:
                parsed = self._parse_date(value)

                if parsed is None:
                    expiry["valid_format"] = False
                else:
                    expiry["expired"] = (
                        parsed.date() < datetime.now().date()
                    )

        score = completeness_score

        if expiry["expired"] is True:
            score -= 25

        score = max(
            0,
            min(100, round(score, 2))
        )

        valid = (
            len(missing_fields) == 0
            and expiry["valid_format"]
            and expiry["expired"] is not True
        )

        return {
            "valid": valid,
            "score": score,
            "missing_fields": missing_fields,
            "expiry": expiry,
        }

    def _parse_date(self, value):
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%d.%m.%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(
                    value.strip(),
                    fmt
                )
            except ValueError:
                pass

        return None