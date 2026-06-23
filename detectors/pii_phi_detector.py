"""
Stage 2: PII/PHI Detection (Fast Triage)
Uses Microsoft Presidio with custom pattern recognizers for efficient detection.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# Presidio imports
try:
    from presidio_analyzer import AnalyzerEngine, PatternRecognizer, EntityRecognizer
    from presidio_analyzer.nlp_engine import NlpEngine
    from presidio_analyzer.recognizer_registry import RecognizerRegistry
except ImportError:
    AnalyzerEngine = None
    PatternRecognizer = None
    EntityRecognizer = None
    NlpEngine = None
    RecognizerRegistry = None

try:
    import spacy
except ImportError:
    spacy = None


logger = logging.getLogger(__name__)


class EntityCategory(Enum):
    """PII/PHI classification."""
    PII = "PII"
    PHI = "PHI"


@dataclass
class PiiPhiEntity:
    """Detected PII/PHI entity."""
    entity_type: str
    label: str
    category: str  # "PII" or "PHI"
    value: str
    start: int
    end: int
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TriageResult:
    """Triage result for a document."""
    pii_phi_matches: List[Dict[str, Any]] = field(default_factory=list)
    match_count: int = 0
    contains_pii: bool = False
    contains_phi: bool = False
    flagged_for_review: bool = False


class PiiPhiDetector:
    """
    Detects PII and PHI using Microsoft Presidio with custom patterns.
    Optimized for offline, cost-effective detection on millions of documents.
    """

    # Entity type to human label mapping
    ENTITY_LABELS = {
        "US_SSN": "Social Security Number",
        "EMAIL_ADDRESS": "Email Address",
        "PHONE_NUMBER": "Phone Number",
        "CREDIT_CARD": "Credit Card Number",
        "PASSPORT_NUMBER": "Passport Number",
        "MEDICAL_RECORD_NUMBER": "Medical Record Number",
        "HEALTH_INSURANCE_ID": "Health Insurance ID",
        "ICD10_CODE": "ICD-10 Diagnosis Code",
        "DATE_OF_BIRTH": "Date of Birth",
        "US_BANK_NUMBER": "Bank Account Number",
        "IP_ADDRESS": "IP Address",
        "NAME": "Person Name",
        "LOCATION": "Location",
        "ORGANIZATION": "Organization"
    }

    # PII vs PHI classification
    PII_ENTITIES = {
        "US_SSN", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
        "PASSPORT_NUMBER", "US_BANK_NUMBER", "IP_ADDRESS", "NAME"
    }

    PHI_ENTITIES = {
        "MEDICAL_RECORD_NUMBER", "HEALTH_INSURANCE_ID", "ICD10_CODE", "DATE_OF_BIRTH"
    }

    # Score threshold for matching
    CONFIDENCE_THRESHOLD = 0.55

    def __init__(self, use_spacy_ner: bool = False):
        """
        Initialize the PII/PHI detector.
        
        Args:
            use_spacy_ner: If True, use spaCy's built-in NER (requires en_core_web_lg).
                          If False, use regex-based detection only (offline, no model download).
        """
        self.use_spacy_ner = use_spacy_ner
        self.analyzer = self._init_analyzer()

    def _init_analyzer(self) -> Optional[AnalyzerEngine]:
        """
        Initialize Presidio AnalyzerEngine with custom patterns.
        Uses a blank spaCy pipeline to avoid auto-downloading models.
        """
        if AnalyzerEngine is None:
            logger.warning("Presidio not installed; detection will be unavailable")
            return None

        try:
            # Create custom NLP engine with blank spaCy model (no model download)
            if spacy is None:
                logger.warning("spaCy not installed; using regex-only detection")
                nlp_engine = None
            else:
                try:
                    # Use blank English pipeline (no network access, no auto-download)
                    nlp = spacy.blank("en")
                    nlp_engine = NlpEngine(
                        nlp_type="spacy",
                        spacy_model_path=None,
                        # Pass the blank model directly to avoid auto-download
                        spacy_nlp=nlp
                    )
                except Exception as e:
                    logger.warning(f"Could not initialize spaCy NLP engine: {e}. Falling back to regex.")
                    nlp_engine = None

            # Create registry and remove recognizers that require network or full models
            registry = RecognizerRegistry()
            registry.load_predefined_recognizers(nlp_engine=nlp_engine)

            # Remove UrlRecognizer and SpacyRecognizer (network/model dependent)
            recognizers_to_remove = [
                "UrlRecognizer",
                "SpacyRecognizer"  # Requires en_core_web_lg
            ]
            for recognizer_name in recognizers_to_remove:
                try:
                    registry.remove_recognizer(recognizer_name)
                    logger.info(f"Removed {recognizer_name}")
                except:
                    pass

            # Initialize analyzer
            analyzer = AnalyzerEngine(
                registry=registry,
                nlp_engine=nlp_engine
            )

            # Add custom pattern recognizers for high-confidence PII/PHI
            self._add_custom_recognizers(analyzer)

            logger.info("PiiPhiDetector initialized successfully")
            return analyzer

        except Exception as e:
            logger.error(f"Failed to initialize AnalyzerEngine: {e}")
            return None

    def _add_custom_recognizers(self, analyzer: AnalyzerEngine):
        """Add custom pattern-based recognizers to Presidio."""
        if PatternRecognizer is None:
            return

        custom_patterns = [
            # US Social Security Number (XXX-XX-XXXX or XXXXXXXXX)
            PatternRecognizer(
                supported_entity="US_SSN",
                patterns=[
                    re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),  # XXX-XX-XXXX
                    re.compile(r'\b\d{9}\b')  # XXXXXXXXX (without dashes)
                ],
                score=0.85
            ),

            # Phone Number (various US formats)
            PatternRecognizer(
                supported_entity="PHONE_NUMBER",
                patterns=[
                    re.compile(r'\b\d{3}[-.]\d{3}[-.]\d{4}\b'),  # XXX-XXX-XXXX or XXX.XXX.XXXX
                    re.compile(r'\b\(\d{3}\)\s*\d{3}[-.]\d{4}\b'),  # (XXX) XXX-XXXX
                    re.compile(r'\+1\s*\d{3}[-.]\d{3}[-.]\d{4}\b')  # +1 XXX-XXX-XXXX
                ],
                score=0.70
            ),

            # Credit Card (generic 4-4-4-4 or similar)
            PatternRecognizer(
                supported_entity="CREDIT_CARD",
                patterns=[
                    re.compile(r'\b(?:\d{4}[- ]){3}\d{4}\b'),  # XXXX-XXXX-XXXX-XXXX or XXXX XXXX XXXX XXXX
                    re.compile(r'\b\d{4}\d{4}\d{4}\d{4}\b')  # 16 digit card number
                ],
                score=0.75
            ),

            # Passport Number (various formats)
            PatternRecognizer(
                supported_entity="PASSPORT_NUMBER",
                patterns=[
                    re.compile(r'(?:Passport\s*(?:No|Number|#)?[\s:]*)([A-Z0-9]{6,9})\b', re.IGNORECASE),
                    re.compile(r'(?:Passport)[\s:-]*([A-Z][0-9]{7,8})\b', re.IGNORECASE)
                ],
                score=0.85
            ),

            # Medical Record Number
            PatternRecognizer(
                supported_entity="MEDICAL_RECORD_NUMBER",
                patterns=[
                    re.compile(r'(?:MRN|Medical\s*Record\s*(?:No|Number|#)?[\s:]*)([0-9]{6,12})\b', re.IGNORECASE),
                    re.compile(r'(?:Record\s*Number)[\s:]([0-9]{6,12})\b', re.IGNORECASE)
                ],
                score=0.85
            ),

            # Health Insurance ID / Member ID
            PatternRecognizer(
                supported_entity="HEALTH_INSURANCE_ID",
                patterns=[
                    re.compile(r'(?:Member\s*(?:ID|Number|#)?|Policy\s*(?:#|Number)?|Insurance\s*(?:ID|Number))[\s:]([A-Z0-9]{6,15})\b', re.IGNORECASE),
                    re.compile(r'(?:Group\s*Number)[\s:]([0-9A-Z]{4,12})\b', re.IGNORECASE)
                ],
                score=0.80
            ),

            # ICD-10 Diagnosis Code (e.g., A01.00, Z12.89)
            PatternRecognizer(
                supported_entity="ICD10_CODE",
                patterns=[
                    re.compile(r'\b[A-TV-Z][0-9][0-9AB]\.(?:[0-9]{1}|[A-Z]{1})[A-Z0-9]?\b')  # ICD-10-CM pattern
                ],
                score=0.60
            ),

            # Date of Birth (various formats)
            PatternRecognizer(
                supported_entity="DATE_OF_BIRTH",
                patterns=[
                    re.compile(r'(?:DOB|Date\s*of\s*Birth|Birth\s*Date)[\s:]?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', re.IGNORECASE),
                    re.compile(r'(?:Born|Birthday)[\s:]?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', re.IGNORECASE)
                ],
                score=0.90
            ),

            # US Bank Account Number
            PatternRecognizer(
                supported_entity="US_BANK_NUMBER",
                patterns=[
                    re.compile(r'(?:Account\s*(?:Number|#))[\s:]?([0-9]{8,17})\b', re.IGNORECASE),
                    re.compile(r'(?:Bank\s*Account)[\s:]?([0-9]{8,17})\b', re.IGNORECASE)
                ],
                score=0.80
            ),

            # IP Address
            PatternRecognizer(
                supported_entity="IP_ADDRESS",
                patterns=[
                    re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')
                ],
                score=0.70
            )
        ]

        for recognizer in custom_patterns:
            try:
                analyzer.registry.add_recognizer(recognizer)
                logger.debug(f"Added recognizer for {recognizer.supported_entity}")
            except Exception as e:
                logger.warning(f"Could not add recognizer for {recognizer.supported_entity}: {e}")

    def triage(self, document_text: str) -> TriageResult:
        """
        Fast triage pass: detect all PII/PHI in the document.
        
        Args:
            document_text: The full text of the document to analyze
            
        Returns:
            TriageResult with detected entities and summary counts
        """
        if not self.analyzer or not document_text:
            return TriageResult()

        try:
            # Run Presidio analysis
            presidio_results = self.analyzer.analyze(
                text=document_text,
                language="en",
                score_threshold=self.CONFIDENCE_THRESHOLD
            )

            matches = []
            pii_found = False
            phi_found = False

            for result in presidio_results:
                entity_type = result.entity_type
                label = self.ENTITY_LABELS.get(entity_type, entity_type)

                # Classify as PII or PHI
                if entity_type in self.PII_ENTITIES:
                    category = "PII"
                    pii_found = True
                elif entity_type in self.PHI_ENTITIES:
                    category = "PHI"
                    phi_found = True
                else:
                    # Default to PII if not explicitly PHI
                    category = "PII"
                    pii_found = True

                # Extract the matched text
                matched_text = document_text[result.start:result.end]

                match_dict = {
                    "entity_type": entity_type,
                    "label": label,
                    "category": category,
                    "value": matched_text,
                    "start": result.start,
                    "end": result.end,
                    "confidence": result.score
                }
                matches.append(match_dict)

            return TriageResult(
                pii_phi_matches=matches,
                match_count=len(matches),
                contains_pii=pii_found,
                contains_phi=phi_found,
                flagged_for_review=len(matches) > 0
            )

        except Exception as e:
            logger.error(f"Error during triage: {e}")
            return TriageResult()

    def extract_structured(self, document_text: str) -> Dict[str, Any]:
        """
        Structured extraction for a flagged document.
        Currently returns the same as triage; in production would call an LLM.
        
        Args:
            document_text: The full text of the document
            
        Returns:
            Dictionary with structured PII/PHI grouped by type
        """
        triage_result = self.triage(document_text)

        # Group by entity type
        grouped = {}
        for match in triage_result.pii_phi_matches:
            entity_type = match["entity_type"]
            if entity_type not in grouped:
                grouped[entity_type] = []
            grouped[entity_type].append(match)

        return {
            "entities_by_type": grouped,
            "summary": {
                "total_matches": triage_result.match_count,
                "pii_found": triage_result.contains_pii,
                "phi_found": triage_result.contains_phi
            }
        }
