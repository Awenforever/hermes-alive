"""Release Core stores under a test-owned directory before removing it."""


def close_test_stores(directory):
    try:
        from persistence_assembly import close_stores_under
    except ModuleNotFoundError as error:
        if error.name != 'persistence_assembly':
            raise
        from hermes_state_registry import close_all_under as close_stores_under
    close_stores_under(directory)
