"""Cliente HTTP hacia tender-api para el bot."""

from __future__ import annotations

import httpx

from tender_telegram_bot.config import settings


class TenderApiClient:
    def __init__(self, base_url: str | None = None, *, timeout: float = 30.0) -> None:
        self.base_url = (base_url or settings.api_url).rstrip("/")
        self.timeout = timeout

    def _client(self) -> httpx.Client:
        """Crea el cliente httpx. Monkeypatcheable en tests."""
        return httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def get_top(self, limit: int | None = None) -> list[dict]:
        with self._client() as client:
            resp = client.get("/api/tenders/top", params={"limit": limit or settings.top_limit})
            resp.raise_for_status()
            return resp.json()

    def get_urgent(self, days: int | None = None) -> list[dict]:
        with self._client() as client:
            resp = client.get("/api/tenders/urgent", params={"days": days or settings.urgent_days})
            resp.raise_for_status()
            return resp.json()

    def get_stats(self) -> dict:
        with self._client() as client:
            resp = client.get("/api/tenders/stats")
            resp.raise_for_status()
            return resp.json()

    def get_pending_alerts(self, limit: int = 10) -> list[dict]:
        """Oportunidades GO aún no alertadas (para el push inmediato)."""
        with self._client() as client:
            resp = client.get("/api/tenders/pending-alerts", params={"limit": limit})
            resp.raise_for_status()
            return resp.json()

    def get_alert_matches(self, days: int = 1) -> list[dict]:
        """Licitaciones recientes que cumplen alguna alerta guardada."""
        with self._client() as client:
            resp = client.get("/api/alerts/matches", params={"days": days})
            resp.raise_for_status()
            return resp.json()

    def search(self, q: str, limit: int = 5) -> list[dict]:
        with self._client() as client:
            resp = client.get(
                "/api/tenders/search", params={"q": q, "order": "score", "limit": limit}
            )
            resp.raise_for_status()
            return resp.json()

    def get_closing_soon(self, days: int = 7) -> list[dict]:
        with self._client() as client:
            resp = client.get("/api/tenders/closing-soon", params={"days": days})
            resp.raise_for_status()
            return resp.json()

    def mark_reminded(self, tender_id: str) -> None:
        with self._client() as client:
            client.post(f"/api/tenders/{tender_id}/mark-reminded").raise_for_status()

    def mark_alerted(self, tender_id: str) -> None:
        with self._client() as client:
            client.post(f"/api/tenders/{tender_id}/mark-alerted").raise_for_status()

    def get_tender(self, tender_id: str) -> dict:
        with self._client() as client:
            resp = client.get(f"/api/tenders/{tender_id}")
            resp.raise_for_status()
            return resp.json()

    def get_score(self, tender_id: str) -> dict | None:
        """Último score de la licitación, o None si aún no tiene."""
        with self._client() as client:
            resp = client.get(f"/api/tenders/{tender_id}/score")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    def ask(self, tender_id: str, question: str, top_k: int = 3) -> dict:
        """Pregunta sobre el pliego (visual-rag o extractivo, según configuración de la API)."""
        with self._client() as client:
            resp = client.post(
                f"/api/tenders/{tender_id}/ask",
                json={"question": question, "top_k": top_k},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()

    def post_action(
        self, tender_id: str, action: str, *, actor: str | None = None, note: str | None = None
    ) -> dict:
        with self._client() as client:
            resp = client.post(
                f"/api/tenders/{tender_id}/actions",
                json={"action": action, "actor": actor, "note": note},
            )
            resp.raise_for_status()
            return resp.json()
