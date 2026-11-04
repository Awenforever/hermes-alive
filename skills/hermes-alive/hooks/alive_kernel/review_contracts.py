"""Immutable scope names; neither a verdict nor execution authority."""
LEGACY_SPLIT_SOURCE_REVIEW = 'boundaries-and-source-v1'
FIRST_FACTS_AND_FIT_REVIEW = 'boundaries-and-source-v2'
FIRST_CONVERSATIONAL_REVIEW = 'boundaries-and-source-v3'
SPLIT_SOURCE_REVIEW = 'boundaries-and-source-v4'
SPLIT_SOURCE_REVIEW_CONTRACTS = (
    LEGACY_SPLIT_SOURCE_REVIEW, FIRST_FACTS_AND_FIT_REVIEW, FIRST_CONVERSATIONAL_REVIEW, SPLIT_SOURCE_REVIEW)
BOUNDARY_ASSESSMENT = 'required-boundaries-v1'
FACTS_AND_FIT_ASSESSMENT = 'factual-support-and-communication-fit-v1'
CONVERSATIONAL_FIT_ASSESSMENT = 'factual-support-and-communication-fit-v2'
GROUNDED_FIT_ASSESSMENT = 'factual-support-and-communication-fit-v3'
FACTS_AND_FIT_ASSESSMENTS = (FACTS_AND_FIT_ASSESSMENT, CONVERSATIONAL_FIT_ASSESSMENT, GROUNDED_FIT_ASSESSMENT)
