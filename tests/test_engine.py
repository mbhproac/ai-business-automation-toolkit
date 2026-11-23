import asyncio

import pytest

from ai_business_automation.engine import process_job, render, validate_destination
from ai_business_automation.storage import Store


def test_template_is_not_eval():
    assert render("Hi ${company}: ${missing}", {"company": "Acme"}) == "Hi Acme: ${missing}"


@pytest.mark.parametrize("url", ["http://example.com", "https://127.0.0.1/hook",
                                       "https://user:pass@example.com/", "https://other.com/hook"])
def test_url_rejection(url):
    with pytest.raises(ValueError):
        validate_destination(url, {"example.com"})


def test_process_record(settings):
    store = Store(settings.database_path)
    job = store.enqueue("lead_intake", {"company": "Acme"}, None)
    claimed = store.claim(120)
    asyncio.run(process_job(store, settings, claimed))
    assert store.get(job["id"])["status"] == "succeeded"
    assert any(e["kind"] == "action_done" for e in store.events(job["id"]))
