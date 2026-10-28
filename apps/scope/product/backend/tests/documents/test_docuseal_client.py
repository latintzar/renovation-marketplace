"""Unit tests for `documents.docuseal.client` — HTTP interactions mocked."""
from __future__ import annotations

import pytest

try:
    import respx  # noqa: F401
except ImportError:
    pytest.skip("respx not installed", allow_module_level=True)

import httpx
import respx

from documents import DocusealAttachment, DocusealClient, DocusealSubmitter

pytestmark = pytest.mark.asyncio


@pytest.fixture
def client() -> DocusealClient:
    return DocusealClient(
        api_key="docuseal_test_key",
        base_url="https://api.docuseal.example",
    )


@respx.mock
async def test_create_submission_posts_to_api(client: DocusealClient) -> None:
    route = respx.post("https://api.docuseal.example/submissions").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "sub_abc",
                "status": "pending",
                "template_id": "tpl_1",
                "external_id": "q_abc:v1",
                "submitters": [
                    {"email": "a@b.com", "role": "homeowner", "name": None, "phone": None},
                ],
            },
        )
    )
    sub = await client.create_submission(
        template_id="tpl_1",
        submitters=[DocusealSubmitter(email="a@b.com", role="homeowner")],
        external_id="q_abc:v1",
        attachments=[
            DocusealAttachment(
                filename="agreement.pdf", content=b"%PDF-fake",
            )
        ],
    )
    assert route.called
    assert sub.id == "sub_abc"
    assert sub.external_id == "q_abc:v1"


@respx.mock
async def test_create_submission_sends_auth_header(client: DocusealClient) -> None:
    route = respx.post("https://api.docuseal.example/submissions").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "x",
                "status": "pending",
                "template_id": "t",
                "external_id": "e",
                "submitters": [],
            },
        )
    )
    await client.create_submission(
        template_id="t",
        submitters=[DocusealSubmitter(email="x@y.com", role="homeowner")],
        external_id="e",
    )
    assert route.calls[0].request.headers["X-Auth-Token"] == "docuseal_test_key"


@respx.mock
async def test_get_submission(client: DocusealClient) -> None:
    respx.get("https://api.docuseal.example/submissions/sub_x").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "sub_x",
                "status": "completed",
                "template_id": "tpl_1",
                "external_id": "q:v1",
                "submitters": [],
                "signed_document_url": "https://s3/x.pdf",
            },
        )
    )
    sub = await client.get_submission("sub_x")
    assert sub.status == "completed"
    assert sub.signed_document_url == "https://s3/x.pdf"


@respx.mock
async def test_get_document_urls(client: DocusealClient) -> None:
    respx.get("https://api.docuseal.example/submissions/sub_x/documents").mock(
        return_value=httpx.Response(
            200,
            json={"documents": [
                {"url": "https://s3/1.pdf"},
                {"url": "https://s3/2.pdf"},
            ]},
        )
    )
    urls = await client.get_document_urls("sub_x")
    assert urls == ["https://s3/1.pdf", "https://s3/2.pdf"]


@respx.mock
async def test_cancel_submission(client: DocusealClient) -> None:
    route = respx.delete("https://api.docuseal.example/submissions/sub_x").mock(
        return_value=httpx.Response(204)
    )
    await client.cancel_submission("sub_x")
    assert route.called
