"""Finite background cognition budgets, independent of provider/model choice.

Core task/candidate configuration still owns individual request timeouts. The
stage allowance covers ordinary slow responses and some Core-owned recovery;
it neither retries work nor promises every configured ladder will fit.
"""
DEFAULT_REQUEST_SECONDS = 180
DEFAULT_STAGE_SECONDS = 600
MAX_STAGE_SECONDS = 600
