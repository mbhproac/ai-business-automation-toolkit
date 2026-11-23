from ai_business_automation.storage import Store


def test_dedup_and_claim(settings):
    store = Store(settings.database_path)
    first = store.enqueue("lead_intake", {"company": "A"}, "lead_intake:1")
    second = store.enqueue("lead_intake", {"company": "B"}, "lead_intake:1")
    assert first["id"] == second["id"]
    claimed = store.claim(120)
    assert claimed["id"] == first["id"]
    assert claimed["attempts"] == 1
    assert store.claim(120) is None
    store.complete(first["id"])
    assert store.get(first["id"])["status"] == "succeeded"


def test_retries_to_dead_letter(settings):
    store = Store(settings.database_path)
    job = store.enqueue("lead_intake", {}, None)
    store.claim(120)
    store.failed(job["id"], "Error", max_retries=1)
    assert store.get(job["id"])["status"] == "failed"
