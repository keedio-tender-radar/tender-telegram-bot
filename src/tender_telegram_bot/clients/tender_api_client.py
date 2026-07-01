"""Cliente HTTP hacia tender-api para el bot.

Tolerante a *cold start* (scale-to-zero): la API puede estar dormida y la primera petición la
despierta (y agota el tiempo). Por eso el timeout es holgado, el transporte reintenta errores de
conexión y `_request` reintenta una vez ante un timeout de lectura.
"""

from __future__ import annotations

import logging

import httpx

from tender_telegram_bot.config import settings

logger = logging.getLogger("tender_telegram_bot")


class TenderApiClient:
    def __init__(self, base_url: str | None = None, *, timeout: float = 60.0) -> None:
        self.base_url = (base_url or settings.api_url).rstrip("/")
        self.timeout = timeout

    def _client(self) -> httpx.Client:
        """Crea el cliente httpx. Monkeypatcheable en tests.

        `retries=2` reintenta errores de conexión (máquina despertando de scale-to-zero).
        """
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=httpx.HTTPTransport(retries=2),
        )

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Envía la petición reintentando UNA vez ante timeout de lectura (cold start)."""
        last: httpx.TimeoutException | None = None
        # Solo reintentamos GET (idempotente): despierta la máquina dormida y la 2ª acierta. Un POST
        # largo (p. ej. /ask) NO se reintenta, para no bloquear el webhook el doble de tiempo.
        attempts = 2 if method.upper() == "GET" else 1
        for attempt in range(attempts):
            try:
                with self._client() as client:
                    return client.request(method, path, **kwargs)
            except httpx.TimeoutException as exc:
                last = exc
                logger.warning(
                    "Timeout en %s %s (intento %d/%d)", method, path, attempt + 1, attempts
                )
        raise last  # type: ignore[misc]

    def get_top(self, limit: int | None = None) -> list[dict]:
        resp = self._request(
            "GET", "/api/tenders/top", params={"limit": limit or settings.top_limit}
        )
        resp.raise_for_status()
        return resp.json()

    def get_urgent(self, days: int | None = None) -> list[dict]:
        resp = self._request(
            "GET", "/api/tenders/urgent", params={"days": days or settings.urgent_days}
        )
        resp.raise_for_status()
        return resp.json()

    def get_stats(self) -> dict:
        resp = self._request("GET", "/api/tenders/stats")
        resp.raise_for_status()
        return resp.json()

    def get_pending_alerts(self, limit: int = 10) -> list[dict]:
        """Oportunidades GO aún no alertadas (para el push inmediato)."""
        resp = self._request("GET", "/api/tenders/pending-alerts", params={"limit": limit})
        resp.raise_for_status()
        return resp.json()

    def get_alert_matches(self, days: int = 1) -> list[dict]:
        """Licitaciones recientes que cumplen alguna alerta guardada."""
        resp = self._request("GET", "/api/alerts/matches", params={"days": days})
        resp.raise_for_status()
        return resp.json()

    def search(self, q: str, limit: int = 5) -> list[dict]:
        resp = self._request(
            "GET", "/api/tenders/search", params={"q": q, "order": "score", "limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    def get_closing_soon(self, days: int = 7) -> list[dict]:
        resp = self._request("GET", "/api/tenders/closing-soon", params={"days": days})
        resp.raise_for_status()
        return resp.json()

    def mark_reminded(self, tender_id: str) -> None:
        self._request("POST", f"/api/tenders/{tender_id}/mark-reminded").raise_for_status()

    def mark_alerted(self, tender_id: str) -> None:
        self._request("POST", f"/api/tenders/{tender_id}/mark-alerted").raise_for_status()

    def get_tender(self, tender_id: str) -> dict:
        resp = self._request("GET", f"/api/tenders/{tender_id}")
        resp.raise_for_status()
        return resp.json()

    def get_score(self, tender_id: str) -> dict | None:
        """Último score de la licitación, o None si aún no tiene."""
        resp = self._request("GET", f"/api/tenders/{tender_id}/score")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def ask(self, tender_id: str, question: str, top_k: int = 3) -> dict:
        """Pregunta sobre el pliego (visual-rag o extractivo, según configuración de la API)."""
        resp = self._request(
            "POST",
            f"/api/tenders/{tender_id}/ask",
            json={"question": question, "top_k": top_k},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    def post_action(
        self, tender_id: str, action: str, *, actor: str | None = None, note: str | None = None
    ) -> dict:
        resp = self._request(
            "POST",
            f"/api/tenders/{tender_id}/actions",
            json={"action": action, "actor": actor, "note": note},
        )
        resp.raise_for_status()
        return resp.json()
