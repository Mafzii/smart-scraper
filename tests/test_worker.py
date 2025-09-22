import pytest
import asyncio
from worker import run_extraction, convert_snapshot, query_slm

@pytest.mark.asyncio
async def test_run_extraction_returns_dict(monkeypatch):
    # Mock fetch_page and query_slm to avoid network calls
    async def mock_fetch_page(url, playwright):
        return "[depth:2][0] type: text; text: 'Test'"
    def mock_query_slm(user_input, url_snapshot):
        return ({"input": user_input, "output": "Test output"}, "DONE")
    # Patch the functions
    import worker
    monkeypatch.setattr(worker, "fetch_page", mock_fetch_page)
    monkeypatch.setattr(worker, "query_slm", mock_query_slm)
    result = await run_extraction("Test input", "http://example.com")
    assert isinstance(result, dict)
    assert result["output"] == "Test output"