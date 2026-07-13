"""Rule-based recall enrichment prototype.

This script reads a small batch of FDA recall records from PostgreSQL,
classifies recall reasons using transparent rules, and inserts the
results into ai_recall_enrichment.

no-cost prototype before integrating a real LLM.
"""
from __future__ import annotations
import json
import os
import re
from datetime import datetime
from typing import Any
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

PROMPT_VERSION = "rule_based_v1"
MODEL_NAME = "rule_based_classifier_v1"
BATCH_SIZE = 1000

# When True, the script only previews classifications.
# It will NOT insert or update rows in ai_recall_enrichment.
DRY_RUN = True

def get_database_connection() -> psycopg2.extensions.connection:
    """PostgreSQL connection using environment variables."""

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "fda_recall_ai"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )

def normalize_text(value: str | None) -> str:
    """Return lowercase searchable text."""

    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip().lower()

def classify_recall(
    product_description: str | None,
    reason_for_recall: str | None,
    classification: str | None,
) -> dict[str, Any]:
    """Classify one recall using transparent keyword rules."""

    product_text = normalize_text(product_description)
    reason_text = normalize_text(reason_for_recall)
    combined_text = f"{product_text} {reason_text}"

    # Major allergens commonly seen in food recalls.
    allergen_keywords = {
        "milk": "Milk",
        "peanut": "Peanut",
        "peanuts": "Peanut",
        "tree nut": "Tree nut",
        "walnut": "Walnut",
        "almond": "Almond",
        "cashew": "Cashew",
        "sulfite": "Sulfites",
        "sulfites": "Sulfites",
        "gluten": "Gluten",
        "pistachio": "Pistachio",
        "wheat": "Wheat",
        "soy": "Soy",
        "coconut": "Tree nut",
        "almond flour": "Tree nut",
        "walnuts": "Tree nut",
        "green walnuts": "Tree nut",
        "pistachio": "Tree nut",
        "peanut protein": "Peanut",
        "milk-containing": "Milk",
        "milk ingredient": "Milk",
        "tree nuts": "Tree nut",
        "egg": "Egg",
        "salmon": "Salmon",
        "soy flour": "Soy",
        "pecan": "Tree nut",
        "flaxseed": "Flaxseed",
        "fish": "Fish",
        "anchovy": "Fish",
        "anchovies": "Fish",
        "soy lecithin": "Soy",
        "shellfish": "Shellfish",
        "sesame": "Sesame",
        "butter": "Milk",
        "cream": "Milk",
        "pistachio": "Tree nut",
        "whey": "Milk",
        "whey protein": "Milk",
    }

    pathogen_keywords = {
        "salmonella": "Salmonella",
        "listeria": "Listeria",
        "l. monocytogenes": "Listeria",
        "monocytogenes": "Listeria",
        "hepatitis a": "Hepatitis A",
        "e. coli": "E. coli",
        "ecoli": "E. coli",
        "burkholderia cepacia": "Burkholderia cepacia",
        "microbial contamination": "Microbial contamination",
        "botulinum": "Clostridium botulinum",
        "pseudomonas aeruginosa": "Pseudomonas aeruginosa",
        "cronobacter": "Cronobacter",
        "e.coli": "E. coli",
        "l. mono": "Listeria",
        "stenotrophomonas maltophilia": "Stenotrophomonas maltophilia",
        "norovirus": "Norovirus",
        "cyclospora": "Cyclospora",
        "e-coli": "E. coli",
        "giardia": "Giardia",
        "staphylococcus enterotoxin": "Staphylococcus enterotoxin",
        "coliform": "Coliform",
    }

    foreign_material_keywords = {
        "metal": "Metal pieces",
        "glass": "Glass",
        "plastic": "Plastic",
        "wood": "Wood",
        "rubber": "Rubber",
        "foreign object": "Foreign object",
        "foreign objects": "Foreign objects",
        "foreign material": "Foreign material",
    }

    chemical_keywords = {
        "yellow #5": "Yellow #5",
        "yellow 5": "Yellow #5",
        "yellow #6": "Yellow #6",
        "yellow 6": "Yellow #6",
        "red #40": "Red #40",
        "red 40": "Red #40",
        "ochratoxin a": "Ochratoxin A",
        "tadalafil": "Tadalafil",
        "hydrocyanic acid": "Hydrocyanic acid",
        "aflatoxin": "Aflatoxin",
        "monosodium glutamate": "Monosodium glutamate",
        "msg": "Monosodium glutamate",
        "cesium-137": "Cesium-137",
        "cs-137": "Cesium-137",
        "lead": "Lead",
        "arsenic": "Arsenic",
        "pesticide": "Pesticide",
        "chemical": "Chemical contaminant",
        "cleaning solution": "Cleaning solution",
        "fd&c red no. 40": "FD&C Red No. 40",
        "red no. 40": "FD&C Red No. 40",
        "cyclamates": "Cyclamates",
        "cyclamate": "Cyclamates",
        "sanitizer": "Sanitizer",
        "yellow oleander": "Yellow oleander",
        "muscimol": "Muscimol",
        "haloxyfop": "Haloxyfop",
        "herbicide": "Herbicide",
        "chloramphenicol": "Chloramphenicol",
        "beta lactam": "Beta-lactam antibiotics",
        "beta-lactam": "Beta-lactam antibiotics",
        "picamilon": "Picamilon",
        "dmba": "DMBA",
        "aegeline": "Aegeline",
        "kratom": "Kratom",
        "not approved for food use": "Non-food-approved ink",
        "colorants": "Unapproved colorants",
    }

    category = "Other"
    hazard_type = "Unknown"
    hazard_name: str | None = None
    severity = "Medium"
    confidence = 0.70
    chemical_hazards_found: list[str] = []
    
    if (
        "undeclared" in combined_text
        or "does not declare" in combined_text
        or "do not declare" in combined_text
        or "failure to declare" in combined_text
        or "failed to declare" in combined_text
        or "does not include" in combined_text
        or "not declared" in combined_text
        or "labels do not declare" in combined_text
        or "finished products labels do not declare" in combined_text
        or "missing from the \"contains\" statement" in combined_text
        or "missing from the contains statement" in combined_text
        or "fails to declare" in combined_text
        or "failed to list" in combined_text
        or "does not list" in combined_text
        or "not included on the labels" in combined_text
        or "not listed in the ingredient list" in combined_text
        or "not properly declared" in combined_text
        or "not labeled to contain" in combined_text
        or "may contain undeclared" in combined_text
        or "potential allergen cross contact" in combined_text
        or "allergen cross contact" in combined_text
        or "cross packaged" in combined_text
        or "omitted" in combined_text
        or "may contain" in combined_text
        or "potential presence of" in combined_text
        or "possible presence of" in combined_text
        or "potential allergen cross contact" in combined_text
        or "allergen cross contact" in combined_text
        or "same equipment" in combined_text
        or "shared equipment" in combined_text
        or "protein contamination" in combined_text
        or "not included in the ingredient labeling" in combined_text
        or "missing from the label" in combined_text
        or "may contain undeclared" in combined_text
        or "may contain" in combined_text
        or "contaminated with peanut" in combined_text
        or "contaminated with gluten" in combined_text
        or "contamination with gluten" in combined_text
        or "contaminated with peanuts" in combined_text
        or "contaminated with tree nuts" in combined_text
        or "contains almond flour" in combined_text
        or "contains 28.1 ppm sulfites" in combined_text
        or "contains undeclared allergens" in combined_text
        or "contain undeclared allergens" in combined_text
    ):
        allergens_found = [
            display_name
            for keyword, display_name in allergen_keywords.items()
            if keyword in combined_text
        ]

        if allergens_found:
            category = "Undeclared allergen"
            hazard_type = "Allergen"
            hazard_name = " / ".join(sorted(set(allergens_found)))
            severity = "High"
            confidence = 0.95

    if category == "Other" and "choking hazard" in reason_text:
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Choking hazard"
        severity = "High" if classification == "Class I" else "Medium"
        confidence = 0.90

    if category == "Other":
        for keyword, display_name in pathogen_keywords.items():
            if keyword in combined_text:
                category = "Pathogen contamination"
                hazard_type = "Pathogen"
                hazard_name = display_name
                severity = "Critical" if classification == "Class I" else "High"
                confidence = 0.95
                break

    if category == "Other" and (
        "nutrition facts" in reason_text
        or "nutritional data" in reason_text
        or "understated sodium" in reason_text
        or "undeclared ingredients" in reason_text
    ):
        category = "Mislabeling or packaging error"
        hazard_type = "Labeling"

        labeling_hazards = []

        if "monosodium glutamate" in reason_text or "msg" in reason_text:
            labeling_hazards.append("Monosodium glutamate")

        if "sodium" in reason_text:
            labeling_hazards.append("Sodium content")

        hazard_name = " / ".join(labeling_hazards) if labeling_hazards else None
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "lack of proper pasteurization" in reason_text
        or "improper pasteurization" in reason_text
        or "not properly pasteurized" in reason_text
    ):
        category = "Pathogen contamination"
        hazard_type = "Pathogen"
        hazard_name = "Potential pathogen growth"
        severity = "High"
        confidence = 0.85
    if category == "Other" and (
        "may contain individually wrapped and labeled" in reason_text
        or "may contain regular" in reason_text
        or "wrong product" in reason_text
    ):
        category = "Product mix-up"
        hazard_type = "Product Mix-up"
        hazard_name = "Wrong product in package"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "storage instructions" in reason_text
        or "keep refrigerated" in reason_text
    ):
        category = "Mislabeling or packaging error"
        hazard_type = "Labeling"

        labeling_hazards = []

        if "storage instructions" in reason_text:
            labeling_hazards.append("Missing storage instructions")

        if "keep refrigerated" in reason_text:
            labeling_hazards.append("Keep refrigerated")

        hazard_name = " / ".join(labeling_hazards) if labeling_hazards else None
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "unapproved drug claims" in reason_text
        or "misbranded" in reason_text
    ):
        category = "Mislabeling or packaging error"
        hazard_type = "Labeling"

        labeling_hazards = []

        if "unapproved drug claims" in reason_text:
            labeling_hazards.append("Unapproved drug claims")

        if "misbranded" in reason_text:
            labeling_hazards.append("Misbranded")

        hazard_name = " / ".join(labeling_hazards) if labeling_hazards else None
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "good manufacturing practice" in reason_text
        or "current good manufacturing practice" in reason_text
        or "cgmp" in reason_text
        or "cgmps" in reason_text
        or "not manufactured under gmp" in reason_text
        or "products not manufactured under gmp" in reason_text
        or "significant violations of the cgmp regulations" in reason_text
        or "lack of good manufacturing practices" in reason_text
):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "GMP / cGMP manufacturing violation"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "undeclared allergens" in reason_text
        or "contain undeclared allergens" in reason_text
        or "contains undeclared allergens" in reason_text
    ):
        category = "Undeclared allergen"
        hazard_type = "Allergen"
        hazard_name = "Unknown allergen"
        severity = "High"
        confidence = 0.80

    if category == "Other" and (
        "synthetic equivalents of spermine" in reason_text
        or "synthetic equivalents of spermidine" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Unapproved supplement ingredient"
        severity = "Medium"
        confidence = 0.80

    if category == "Other" and (
        "allergen cross contact" in reason_text
        or "milk-containing ingredient" in reason_text
        or "unidentified allergen" in reason_text
        or "allergy alert" in reason_text
    ):
        category = "Undeclared allergen"
        hazard_type = "Allergen"

        if "milk" in reason_text:
            hazard_name = "Milk"
        elif "walnut" in reason_text:
            hazard_name = "Tree nut"
        else:
            hazard_name = "Unknown allergen"

        severity = "High"
        confidence = 0.80
    
    if category == "Other" and (
        "supplier did not store an ingredient" in reason_text
        or "did not store an ingredient" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Ingredient storage issue"
        severity = "Medium"
        confidence = 0.80

    if category == "Other" and (
        "cottage cheese" in combined_text
        and "recalling" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Product quality issue"
        severity = "Medium"
        confidence = 0.75

    if category == "Other" and (
        "flushing reaction" in reason_text
        or "possible production issue" in reason_text
        or "caplets were not coated" in reason_text
        or "difficult to swallow" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Product quality complaint"
        severity = "Medium"
        confidence = 0.80

    if category == "Other" and (
        "not held at proper temperature" in reason_text
        or "not held at an appropriate temperature" in reason_text
        or "shipping container" in reason_text and "proper temperature" in reason_text
    ):
        category = "Temperature or storage issue"
        hazard_type = "Temperature"
        hazard_name = "Improper shipping temperature"
        severity = "Medium"
        confidence = 0.90

    if category == "Other" and (
        "gluten free claim" in reason_text
        or "gluten-free claim" in reason_text
        or "gluten levels above" in reason_text
        or "labeled gluten-free" in reason_text
        or "tested positive for gluten" in reason_text
        or "gluten levels that exceed" in reason_text
    ):
        category = "Mislabeling or packaging error"
        hazard_type = "Labeling"
        hazard_name = "Gluten-free claim / Gluten above threshold"
        severity = "Medium"
        confidence = 0.85

    if category == "Other":
        chemical_hazards_found = [
            display_name
            for keyword, display_name in chemical_keywords.items()
            if keyword in reason_text
        ]

        if chemical_hazards_found:
            category = "Chemical contamination"
            hazard_type = "Chemical"
            hazard_name = " / ".join(sorted(set(chemical_hazards_found)))

            high_severity_chemicals = {
                "Hydrocyanic acid",
                "Lead",
                "Arsenic",
                "Cesium-137",
                "Aflatoxin",
                "Yellow oleander",
                "Muscimol",
                "Ochratoxin A",
                "Tadalafil",
                "Chloramphenicol",
                "Beta-lactam antibiotics",
            }

            severity = (
                "High"
                if any(
                    chemical in chemical_hazards_found
                    for chemical in high_severity_chemicals
                )
                else "Medium"
            )

            confidence = 0.90
    
    if category == "Other" and (
        "under-processing" in reason_text
        or "under processing" in reason_text
        or "no filed scheduled process" in reason_text
        or "unlicensed and uninspected facility" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"

        quality_hazards = []

        if "under-processing" in reason_text or "under processing" in reason_text:
            quality_hazards.append("Potential under-processing")

        if "no filed scheduled process" in reason_text:
            quality_hazards.append("No filed scheduled process")

        if "unlicensed and uninspected facility" in reason_text:
            quality_hazards.append("Unlicensed/uninspected facility")

        hazard_name = " / ".join(quality_hazards) if quality_hazards else None
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "mold growth" in reason_text
        or "mould growth" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Mold growth"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "label is incorrect" in reason_text
        or "on label is incorrect" in reason_text
        or "incorrectly labeled" in reason_text
        or "front labeling" in reason_text
        or "labeling of product stated" in reason_text
    ):
        category = "Mislabeling or packaging error"
        hazard_type = "Labeling"

        labeling_hazards = []

        if "potassium" in reason_text:
            labeling_hazards.append("Incorrect potassium label")

        if "iron" in reason_text:
            labeling_hazards.append("Incorrect iron label")

        if "dried peaches" in reason_text or "dried plums" in reason_text:
            labeling_hazards.append("Product identity mismatch")

        hazard_name = " / ".join(labeling_hazards) if labeling_hazards else None
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and "allergic reaction" in reason_text:
        category = "Undeclared allergen"
        hazard_type = "Allergen"
        hazard_name = "Unknown allergen"
        severity = "High" if classification == "Class I" else "Medium"
        confidence = 0.80

    if category == "Other" and (
        "consumer complaints" in reason_text
        and "peanut" in reason_text
    ):
        category = "Undeclared allergen"
        hazard_type = "Allergen"
        hazard_name = "Peanut"
        severity = "High"
        confidence = 0.85

    if category == "Other" and (
        "deficient in multiple nutrients" in reason_text
        or "infant formula" in reason_text and "does not test for cronobacter" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Infant formula nutrient/process deficiency"
        severity = "High"
        confidence = 0.85    

    if category == "Other" and (
        "chloramphenicol" in reason_text
        or "beta lactam" in reason_text
        or "beta-lactam" in reason_text
        or "antibiotic" in reason_text
    ):
        category = "Chemical contamination"
        hazard_type = "Chemical"

        chemical_hazards = []

        if "chloramphenicol" in reason_text:
            chemical_hazards.append("Chloramphenicol")

        if "beta lactam" in reason_text or "beta-lactam" in reason_text:
            chemical_hazards.append("Beta-lactam antibiotics")

        if "antibiotic" in reason_text and not chemical_hazards:
            chemical_hazards.append("Antibiotic residues")

        hazard_name = " / ".join(chemical_hazards)
        severity = "High"
        confidence = 0.90

    if category == "Other" and (
        "underprocessed" in reason_text
        or "under processed" in reason_text
        or "process deviation" in reason_text
        or "scheduled process" in reason_text
        or "acidified food" in reason_text
        or "acidified foods" in reason_text
        or "without a license" in reason_text
        or "seal defect" in reason_text
        or "seal quality issue" in reason_text
        or "package swelling" in reason_text
        or "bloating" in reason_text
        or "failed to meet air space specifications" in reason_text
        or "quality standards" in reason_text
        or "not met" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"

        quality_hazards = []

        if "underprocessed" in reason_text or "under processed" in reason_text:
            quality_hazards.append("Under-processing")

        if "scheduled process" in reason_text:
            quality_hazards.append("Scheduled process issue")

        if "acidified food" in reason_text or "acidified foods" in reason_text:
            quality_hazards.append("Acidified food process issue")

        if "seal defect" in reason_text or "seal quality issue" in reason_text:
            quality_hazards.append("Seal quality issue")

        if "package swelling" in reason_text or "bloating" in reason_text:
            quality_hazards.append("Package swelling / bloating")

        if "air space specifications" in reason_text:
            quality_hazards.append("Air space specification issue")

        if "quality standards" in reason_text:
            quality_hazards.append("Quality standards not met")

        hazard_name = " / ".join(quality_hazards) if quality_hazards else "Process / quality issue"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "off-odor" in reason_text
        or "off odor" in reason_text
        or "off smell" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Off-odor"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "wrong product" in reason_text
        or "mispackaged" in reason_text
        or "packaging error" in reason_text
        or "incorrect ingredient label" in reason_text
        or "box labeled" in reason_text
        or "do not include ingredients on the labeling" in reason_text
        or "ingredients on the labeling" in reason_text
        or "labels were found" in reason_text
    ):
        category = "Mislabeling or packaging error"
        hazard_type = "Labeling"
        hazard_name = "Packaging / labeling mismatch"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "mold growth" in reason_text
        or "mould growth" in reason_text
        or "tested high for mold" in reason_text
        or "may be moldy" in reason_text
        or "moldy" in reason_text
        or "complaint of mold" in reason_text
        or "mold found" in reason_text
        or "premature spoilage" in reason_text
        or "spoiled before" in reason_text
        or "spoilage before" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Mold / spoilage"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "insanitary conditions" in reason_text
        or "insanitary condition" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Insanitary conditions"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "undeclared flaxseed" in reason_text
        or "flaxseed" in reason_text and "not listed" in reason_text
    ):
        category = "Mislabeling or packaging error"
        hazard_type = "Labeling"
        hazard_name = "Undeclared flaxseed"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
            "reach truck" in reason_text
            or "equipment fluid" in reason_text
            or "fluid from" in reason_text
        ):
            category = "Quality or manufacturing issue"
            hazard_type = "Quality"
            hazard_name = "Equipment fluid"
            severity = "Medium"
            confidence = 0.85

    if category == "Other" and (
        "no approved process" in reason_text
        or "without approved process" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "No approved process"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "leaking" in reason_text
        or "black liquid" in reason_text
        or "black particulates" in reason_text
        or "particulates" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"

        quality_hazards = []

        if "leaking" in reason_text:
            quality_hazards.append("Leaking")

        if "black liquid" in reason_text:
            quality_hazards.append("Black liquid")

        if "black particulates" in reason_text or "particulates" in reason_text:
            quality_hazards.append("Black particulates")

        hazard_name = " / ".join(quality_hazards) if quality_hazards else None
        severity = "Medium"
        confidence = 0.85

        if category == "Other" and (
            "not listed in the contains statement" in reason_text
            or "not listed in contains statement" in reason_text
        ):
            category = "Mislabeling or packaging error"
            hazard_type = "Labeling"

            if "pecan" in reason_text:
                hazard_name = "Missing pecan in Contains statement"
            else:
                hazard_name = "Missing ingredient in Contains statement"

            severity = "Medium"
            confidence = 0.85

    if category == "Other" and (
        "not documenting the mixing time" in reason_text
        or "ph monitoring" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Missing process documentation / pH monitoring"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "recalled whey powder" in reason_text
        or "recalled ingredient" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Recalled ingredient used in production"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
            "lack production record" in reason_text
            or "lack of production record" in reason_text
            or "missing production record" in reason_text
        ):
            category = "Quality or manufacturing issue"
            hazard_type = "Quality"
            hazard_name = "Missing production record"
            severity = "Medium"
            confidence = 0.85

    if category == "Other" and (
        "gluten free claim" in reason_text
        or "gluten-free claim" in reason_text
        or "gluten levels above" in reason_text
        or "labeled gluten-free" in reason_text
        or "tested positive for gluten" in reason_text
    ):
        category = "Mislabeling or packaging error"
        hazard_type = "Labeling"
        hazard_name = "Gluten-free claim / Gluten above threshold"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "lack of proper pasteurization" in reason_text
        or "improper pasteurization" in reason_text
        or "improperly pasteurized" in reason_text
        or "not properly pasteurized" in reason_text
        or "not pasteurized after blending" in reason_text
        or "inadequate pasteurization" in reason_text
        or "did not meet pasteurization specifications" in reason_text
    ):
        category = "Pathogen contamination"
        hazard_type = "Pathogen"
        hazard_name = "Potential pathogen growth"
        severity = "High"
        confidence = 0.85

    if category == "Other" and (
        "mold growth" in reason_text
        or "mould growth" in reason_text
        or "tested high for mold" in reason_text
        or "may be moldy" in reason_text
        or "moldy" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Mold growth"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "recalled milk ingredient" in reason_text
        or "milk ingredient that was recalled" in reason_text
        or "recalled whey powder" in reason_text
        or "recalled ingredient" in reason_text
        or "ingredient supplier did not store" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Recalled or mishandled ingredient used in production"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "sodium claims" in reason_text
        or "sodium claim" in reason_text
        or "incorrect" in reason_text and "serving" in reason_text
    ):
        category = "Mislabeling or packaging error"
        hazard_type = "Labeling"
        hazard_name = "Incorrect nutrition claim"
        severity = "Medium"
        confidence = 0.85

    if category == "Other" and (
        "bottles may burst" in reason_text
        or "may burst" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Bottle burst / packaging pressure issue"
        severity = "Medium"
        confidence = 0.85


    if category == "Other" and (
        "infestation of mice" in reason_text
        or "mice in the facility" in reason_text
        or "rodent" in reason_text
        or "infestation" in reason_text
    ):
        category = "Quality or manufacturing issue"
        hazard_type = "Quality"
        hazard_name = "Facility infestation"
        severity = "Medium"
        confidence = 0.85
        
    if category == "Other":
        foreign_material_phrases = {
            "metal pieces": "Metal pieces",
            "metal fragments": "Metal fragments",
            "pieces of metal": "Metal pieces",
            "piece of metal": "Metal piece",
            "metal contamination": "Metal contamination",
            "potential metal contamination": "Metal contamination",
            "glass pieces": "Glass pieces",
            "small pieces of plastic": "Plastic pieces",
            "piece of plastic": "Plastic pieces",
            "glass fragments": "Glass fragments",
            "plastic pieces": "Plastic pieces",
            "plastic fragments": "Plastic fragments",
            "wood particles": "Wood particles",
            "wood particle": "Wood particle",
            "glass fragment": "Glass fragment",
            "glass fragments": "Glass fragments",
            "glass fragment found": "Glass fragment",
            "metal fragment(s)": "Metal fragments",
            "faulty manufacturing part": "Metal fragments",
            "foreign object": "Foreign object",
            "foreign objects": "Foreign objects",
            "foreign material": "Foreign material",
            "extraneous material": "Foreign material",
            "may contain metal": "Metal pieces",
            "glass and metal": "Glass / Metal",
            "rubber pieces": "Rubber pieces",
            "food-grade rubber pieces": "Rubber pieces",
            "may contain plastic": "Plastic pieces",
            "may contain glass": "Glass fragments",
            "contamination with metal": "Metal pieces",
            "contamination with plastic": "Plastic pieces",
            "contamination with glass": "Glass fragments",
            "sharp edges": "Sharp edges",
            "small particles of glass": "Glass particles",
            "potential glass inclusion": "Glass inclusion",
            "glass inclusion": "Glass inclusion",
            "small pieces of glass": "Glass pieces",
            "presence of small metal shavings": "Metal shavings",
            "small metal shavings": "Metal shavings",
            "metal shavings": "Metal shavings",
            "wire mesh fragments": "Metal wire fragments",
            "metal wire mesh fragments": "Metal wire fragments",
            "tiny metal particles": "Metal particles",
            "glass particles": "Glass particles",
            "cloth material": "Cloth material",
            "plastic contaminated": "Plastic pieces",
            "presence of plastic": "Plastic pieces",
            "high density polyethylene resin": "Plastic resin",
        }

        for phrase, display_name in foreign_material_phrases.items():
            if phrase in reason_text:
                category = "Foreign material contamination"
                hazard_type = "Foreign Material"
                hazard_name = display_name
                severity = "High"
                confidence = 0.90
                break

    if category == "Other" and (
        "labeled as" in combined_text
        or "wrong label" in combined_text
        or "mislabel" in combined_text
        or "incorrect label" in combined_text
    ):
        category = "Mislabeling or packaging error"
        hazard_type = "Labeling"
        hazard_name = None
        severity = "Medium"
        confidence = 0.80

# pH / scheduled process issue
    if category == "Other" and (
            "ph levels" in reason_text
            and "scheduled process" in reason_text
        ):
            category = "Quality or manufacturing issue"
            hazard_type = "Quality"
            hazard_name = "pH above scheduled process"
            severity = "Medium"
            confidence = 0.85


    # Missing ingredient in Contains statement
    if category == "Other" and (
            "contains statement" in reason_text
            and "not listed" in reason_text
        ):
            category = "Mislabeling or packaging error"
            hazard_type = "Labeling"

            if "pecan" in reason_text:
                hazard_name = "Missing pecan in Contains statement"
            else:
                hazard_name = "Missing ingredient in Contains statement"

            severity = "Medium"
            confidence = 0.85

    summary = build_summary(
        category=category,
        hazard_name=hazard_name,
        reason_for_recall=reason_for_recall,
    )

    return {
        "ai_category": category,
        "hazard_type": hazard_type,
        "hazard_name": hazard_name,
        "ai_severity": severity,
        "ai_summary": summary,
        "ai_confidence": confidence,
    }

def build_summary(
    category: str,
    hazard_name: str | None,
    reason_for_recall: str | None,
) -> str:
    """Create a short standardized summary."""

    reason = reason_for_recall or "No recall reason was provided."

    if category == "Undeclared allergen" and hazard_name:
        return (
            f"The product was recalled because {hazard_name} "
            f"was not declared on the label."
        )

    if category == "Pathogen contamination" and hazard_name:
        return (
            f"The product was recalled due to potential "
            f"{hazard_name} contamination."
        )

    if category == "Foreign material contamination" and hazard_name:
        return (
            f"The product was recalled due to possible contamination "
            f"with {hazard_name.lower()}."
        )

    if category == "Chemical contamination" and hazard_name:
        return (
            f"The product was recalled due to an undeclared or "
            f"potential chemical concern involving {hazard_name}."
        )

    if category == "Mislabeling or packaging error":
        return (
            "The product was recalled because of a labeling or "
            "packaging error."
        )

    return f"The product was recalled for the following reason: {reason}"

def fetch_records_to_enrich(
    connection: psycopg2.extensions.connection,
) -> list[dict[str, Any]]:
    """Fetch records that do not already have enrichment rows."""

    query = """
        SELECT
            recall_number,
            classification,
            product_description,
            reason_for_recall
        FROM stg_fda_recalls AS recalls
        WHERE NOT EXISTS (
            SELECT 1
            FROM ai_recall_enrichment AS enrichment
            WHERE enrichment.recall_number = recalls.recall_number
        )
        ORDER BY recall_initiation_date DESC
        LIMIT %s;
    """

    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (BATCH_SIZE,))
        return list(cursor.fetchall())

def insert_enrichment_result(
    connection: psycopg2.extensions.connection,
    recall_number: str,
    enrichment: dict[str, Any],
) -> None:
    """Insert or update one enrichment result."""

    raw_ai_response = json.dumps(enrichment)

    query = """
        INSERT INTO ai_recall_enrichment (
            recall_number,
            ai_category,
            hazard_type,
            hazard_name,
            ai_severity,
            ai_summary,
            ai_confidence,
            model_name,
            prompt_version,
            processed_at_utc,
            raw_ai_response
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
        )
        ON CONFLICT (recall_number)
        DO UPDATE SET
            ai_category = EXCLUDED.ai_category,
            hazard_type = EXCLUDED.hazard_type,
            hazard_name = EXCLUDED.hazard_name,
            ai_severity = EXCLUDED.ai_severity,
            ai_summary = EXCLUDED.ai_summary,
            ai_confidence = EXCLUDED.ai_confidence,
            model_name = EXCLUDED.model_name,
            prompt_version = EXCLUDED.prompt_version,
            processed_at_utc = EXCLUDED.processed_at_utc,
            raw_ai_response = EXCLUDED.raw_ai_response;
    """

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            (
                recall_number,
                enrichment["ai_category"],
                enrichment["hazard_type"],
                enrichment["hazard_name"],
                enrichment["ai_severity"],
                enrichment["ai_summary"],
                enrichment["ai_confidence"],
                MODEL_NAME,
                PROMPT_VERSION,
                datetime.utcnow(),
                raw_ai_response,
            ),
        )

def main() -> None:
    """Run the rule-based enrichment prototype."""

    load_dotenv()
    
    with get_database_connection() as connection:
        records = fetch_records_to_enrich(connection)

        if not records:
            print("No records found for enrichment.")
            return

        print(f"Records selected for enrichment: {len(records)}")

        if DRY_RUN:
            print("DRY_RUN is True. Preview mode only. No database changes will be made.")

        category_counts = {}

        for record in records:
            enrichment = classify_recall(
                product_description=record["product_description"],
                reason_for_recall=record["reason_for_recall"],
                classification=record["classification"],
            )

            category = enrichment["ai_category"]
            category_counts[category] = category_counts.get(category, 0) + 1

            print(
                f"{record['recall_number']} -> "
                f"{enrichment['ai_category']} | "
                f"{enrichment['hazard_type']} | "
                f"{enrichment['hazard_name']} | "
                f"{enrichment['ai_severity']}"
            )

            if not DRY_RUN:
                insert_enrichment_result(
                    connection=connection,
                    recall_number=record["recall_number"],
                    enrichment=enrichment,
            )
        print("\nBatch category summary:")

        for category, count in sorted(category_counts.items(), key=lambda item: item[1], reverse=True):
            print(f"{category}: {count}")
        if DRY_RUN:
            print("Dry run completed. No rows were inserted or updated.")
        else:
            connection.commit()
            print("Rule-based enrichment completed successfully.")

if __name__ == "__main__":
    main()