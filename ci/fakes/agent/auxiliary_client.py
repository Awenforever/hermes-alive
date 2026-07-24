async def async_call_llm(**_kwargs):
    raise RuntimeError(
        "portable CI fake auxiliary_client must be monkeypatched by a test"
    )
