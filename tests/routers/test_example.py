import httpx
import pytest

from hlpr import create_app


@pytest.mark.asyncio
async def test_example_endpoint():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/example/")
    assert response.status_code == 200
    assert response.json()["message"].startswith("Example endpoint")
