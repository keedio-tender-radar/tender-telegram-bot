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
        # Si la API exige token en lecturas (READ_API_TOKEN), los servicios internos se
        # autentican con RUN_TOKEN. Inofensivo si la API no lo exige.
        headers = {"X-Run-Token": settings.run_token} if settings.run_token else {}
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=httpx.HTTPTransport(retries=2),
            headers=headers,
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

    def get_expedientes(self) -> list[dict]:
        """Bandeja de expedientes en curso (seguimiento) con su completitud."""
        resp = self._request("GET", "/api/tenders/expedientes")
        resp.raise_for_status()
        return resp.json()

    def get_outcomes_summary(self) -> dict:
        """Resumen del pipeline: presentadas/ganadas/perdidas, win-rate y valor adjudicado."""
        resp = self._request("GET", "/api/tenders/outcomes-summary")
        resp.raise_for_status()
        return resp.json()

    def record_decision(
        self, tender_id: str, decision: str, outcome: str, actor: str | None = None
    ) -> None:
        """Registra el resultado de una licitación (decisión + outcome) desde Telegram."""
        self._request(
            "POST", f"/api/tenders/{tender_id}/decision",
            json={"decision": decision, "outcome": outcome, "actor": actor},
        ).raise_for_status()

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

    def get_documents(self, tender_id: str) -> list[dict]:
        """Ficheros del expediente (para indicar en el recordatorio si la oferta está lista)."""
        try:
            resp = self._request("GET", f"/api/tenders/{tender_id}/documents")
            resp.raise_for_status()
            return resp.json().get("files", [])
        except Exception:  # noqa: BLE001 — el recordatorio no debe fallar por esto
            return []

    def mark_alerted(self, tender_id: str) -> None:
        self._request("POST", f"/api/tenders/{tender_id}/mark-alerted").raise_for_status()

    def get_tender(self, tender_id: str) -> dict:
        resp = self._request("GET", f"/api/tenders/{tender_id}")
        resp.raise_for_status()
        return resp.json()

    def market_context(self, tender_id: str) -> dict:
        """Contexto de mercado del expediente: quién suele ganar la categoría + baja esperada."""
        resp = self._request("GET", f"/api/market/tender/{tender_id}/context")
        resp.raise_for_status()
        return resp.json()

    def market_overview(self) -> dict:
        """Resumen global de mercado (adjudicaciones, baja media, líderes)."""
        resp = self._request("GET", "/api/market/overview")
        resp.raise_for_status()
        return resp.json()

    def market_competitors(self, limit: int = 5) -> list[dict]:
        """Competidores más frecuentes (con cuota y baja)."""
        resp = self._request("GET", "/api/market/competitors", params={"limit": limit})
        resp.raise_for_status()
        return resp.json().get("competitors", [])

    def competitor_profile(self, name: str) -> dict | None:
        """Perfil de un adjudicatario (None si no tiene adjudicaciones)."""
        resp = self._request("GET", "/api/market/competitor", params={"name": name})
        if resp.status_code == 404:
            return None
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
