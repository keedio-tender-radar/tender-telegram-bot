import pytest


def tender_with_score(tid="t1", score=92, rec="go", **t) -> dict:
    tender = {
        "id": tid,
        "source": "placsp",
        "title": "Plataforma de datos sanitarios",
        "budget_amount": 620000.0,
        "currency": "EUR",
        "deadline": "2026-07-15T23:59:00Z",
        "buyer": "Servicio de Salud",
        "cpv": ["72300000"],
        "status": "scored",
        "url": "https://example/PLACSP-184",
    }
    tender.update(t)
    score_obj = (
        None
        if score is None
        else {
            "total": score,
            "recommendation": rec,
            "factors": [{"kind": "positive", "message": "CPV preferido"}],
        }
    )
    return {"tender": tender, "score": score_obj}


@pytest.fixture
def items():
    return [
        tender_with_score("a", 92, "go"),
        tender_with_score("b", 81, "revisar", title="Integración de APIs"),
    ]
