# Pending Review Analysis

## Purpose

This document explains why some FDA recall records remain in the `Other` category after rule-based enrichment.

The goal of the rule-based classifier is not to force every recall into a category. Instead, the system classifies high-confidence repeated patterns and flags unclear or ambiguous records for hybrid review.

## Current Status

Total FDA recall records processed: 5,000

Rule-based approved records: 4,728

Pending review records: 272

Rule-based classification coverage: 94.56%

Pending hybrid review rate: 5.44%

## Why Records Remain Pending

Records remain pending when the recall reason does not provide enough clear hazard information, or when the text describes a business action, voluntary withdrawal, vague quality concern, or unclear regulatory issue.

These records are intentionally marked as:

```text
needs_review = true
review_status = pending
classification_source = rule_based
```

These records are displayed in the Streamlit dashboard's Hybrid Review Queue.

## Why Not Classify Everything with Rules?

The goal is not to reduce `Other` to zero.

Over-expanding hardcoded rules can create incorrect classifications. A recall reason may mention a product, ingredient, supplier, or label but still not clearly explain whether the issue is an allergen, pathogen, chemical concern, foreign material issue, temperature issue, or general quality problem.

Forcing unclear records into a category would create false confidence.

## Rule Improvement Summary

The classifier was improved by analyzing repeated patterns in the pending review queue.

Initial pending review count: 471 records

After the first rule improvement: 351 records

After the second rule improvement: 272 records

Overall reduction: 199 records moved out of pending review

This shows that repeated high-confidence patterns were promoted into rule-based classification, while unclear records stayed in the review queue.

## Hybrid Review Strategy

The remaining pending records are candidates for:

1. LLM-assisted enrichment
2. Manual review
3. Future rule promotion if the same pattern appears repeatedly

This creates a practical hybrid workflow:

```text
Rule-based classifier
    ↓
High-confidence match
    → Approved classification

Unclear or ambiguous match
    → Pending review
    → LLM/manual review candidate
``` 