import re
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# --- Initialize ---
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# --- Custom Recognizers ---

# CVV only when formatted as value (cvv: 123)
cvv_recognizer = PatternRecognizer(
    supported_entity="CVV",
    patterns=[
        Pattern(
            name="cvv_value",
            regex=r"\b(?:cvv|cvc)\s*[:=]\s*\d{3,4}\b",
            score=0.8,
        )
    ],
)

# PIN only when formatted as value (pin=1234)
pin_recognizer = PatternRecognizer(
    supported_entity="PIN",
    patterns=[
        Pattern(
            name="pin_value",
            regex=r"\bpin\s*[:=]\s*\d{3,6}\b",
            score=0.8,
        )
    ],
)

analyzer.registry.add_recognizer(cvv_recognizer)
analyzer.registry.add_recognizer(pin_recognizer)


def mask_sensitive(text: str) -> str:
    if not text:
        return text

    results = analyzer.analyze(
        text=text,
        language="en",
        entities=["CREDIT_CARD", "CVV", "PIN"],
    )

    if not results:
        return text

    operators = {
        "CREDIT_CARD": OperatorConfig("replace", {"new_value": "<PAN_REDACTED>"}),
        "CVV": OperatorConfig("replace", {"new_value": "<CVV_REDACTED>"}),
        "PIN": OperatorConfig("replace", {"new_value": "<PIN_REDACTED>"}),
    }

    return anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators,
    ).text


# --- Manual Test Cases ---
if __name__ == "__main__":

    samples = [
        "Card number: 4111 1111 1111 1111",
        "cvv: 123",
        "cvc=9876",
        "pin: 1234",
        "The CVV result was N (should NOT redact)",
        "masked_pan: ************5506 (should NOT redact)",
        "token: tok_123456 (should NOT redact)",
    ]

    for s in samples:
        print("Original :", s)
        print("Redacted :", mask_sensitive(s))
        print("-" * 60)