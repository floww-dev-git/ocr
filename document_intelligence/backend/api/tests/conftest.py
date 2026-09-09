import pytest


@pytest.fixture(autouse=True)
def empty_thread_store():
    """The in-memory thread store lives for the whole process, so each test
    starts and ends with nothing left behind by its neighbours."""
    from document_scrutiny.storages.in_memory_scrutiny_thread_storage import (
        clear_scrutiny_threads,
    )

    clear_scrutiny_threads()
    yield
    clear_scrutiny_threads()
