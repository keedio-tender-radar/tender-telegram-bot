"""Formato de los mensajes del bot (funciones puras, sin dependencia de Telegram).

Ver tender-platform-docs/telegram-notification-format.md.
"""

from __future__ import annotations

_REC_LABEL = {
    "go": "GO",
    "revisar": "REVISAR",
    "partner": "PARTNER",
    "no_go": "NO-GO",
}


def _money(amount, currency: str = "EUR") -> str:
    if amount is None:
        return "s/d"
    return f"{amount:,.0f} {currency}".replace(",", ".")


def _date(value) -> str:
    if not value:
        return "s/d"
    return str(value)[:10]


def _rec(score: dict | None) -> str:
    if not score:
        return "sin score"
    return _REC_LABEL.get(score.get("recommendation", ""), score.get("recommendation", "?"))


def _days_left(value) -> int | None:
    if not value:
        return None
    from datetime import UTC, datetime

    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return (dt - datetime.now(UTC)).days
    except Exception:  # noqa: BLE001
        return None


def _progress_bar(pct: int) -> str:
    filled = max(0, min(5, round(pct / 20)))
    return "▰" * filled + "▱" * (5 - filled)


def format_expedientes(rows: list[dict]) -> str:
    """Bandeja de expedientes en curso (progreso hacia la oferta) para Telegram."""
    if not rows:
        return "📂 No hay expedientes en curso. Marca una licitación como «Interesa» para empezar."
    ordered = sorted(
        rows, key=lambda r: r.get("days_remaining") if r.get("days_remaining") is not None else 9999
    )
    lines = ["📂 Expedientes en curso", ""]
    for r in ordered:
        t = r.get("tender", {})
        pct = r.get("completeness", 0)
        days = r.get("days_remaining")
        cierre = f" · cierra en {days}d" if isinstance(days, int) and days >= 0 else ""
        lines.append(f"{_progress_bar(pct)} {pct}% — {t.get('title', '')[:48]}{cierre}")
    return "\n".join(lines)


def format_expediente_item(r: dict) -> str:
    """Línea de UN expediente (para enviarlo con botones de resultado)."""
    t = r.get("tender", {})
    pct = r.get("completeness", 0)
    days = r.get("days_remaining")
    cierre = f" · cierra en {days}d" if isinstance(days, int) and days >= 0 else ""
    return f"{_progress_bar(pct)} {pct}% — {t.get('title', '')[:60]}{cierre}"


def format_pipeline_line(expedientes: list[dict], outcomes: dict) -> str:
    """Línea compacta del estado del pipeline (expedientes en curso + win-rate) para /estado."""
    parts = [f"📂 {len(expedientes)} expediente(s) en curso"]
    wr = (outcomes or {}).get("win_rate")
    if wr is not None:
        parts.append(f"🏆 win-rate {wr}%")
    elif (outcomes or {}).get("presented"):
        parts.append(f"{outcomes['presented']} presentada(s)")
    return " · ".join(parts)


def format_outcomes(s: dict) -> str:
    """Resumen del pipeline (win-rate) para Telegram."""
    if not s or s.get("total_decisions", 0) == 0:
        return (
            "📊 Aún no hay decisiones registradas. Marca el resultado "
            "(presentada / ganada / perdida) en la ficha de cada licitación."
        )
    wr = s.get("win_rate")
    lines = [
        "📊 Resultados del pipeline",
        "",
        f"Presentadas: {s.get('presented', 0)}",
        f"Ganadas: {s.get('won', 0)} · Perdidas: {s.get('lost', 0)}",
        f"Win-rate: {wr}%" if wr is not None else "Win-rate: s/d (sin decididas aún)",
    ]
    if s.get("won_value"):
        lines.append(f"Valor adjudicado: {_money(s['won_value'])}")
    return "\n".join(lines)


def format_reminder(tw: dict, docs_ready: int = 0) -> str:
    """Recordatorio de cierre rico: urgencia por días restantes + estado del expediente."""
    t = tw.get("tender", {})
    s = tw.get("score")
    days = _days_left(t.get("deadline"))
    if days is None:
        urg, cierre = "⏰", "cierre s/d"
    elif days <= 0:
        urg, cierre = "🔴", "cierra HOY"
    elif days == 1:
        urg, cierre = "🔴", "cierra MAÑANA"
    elif days <= 3:
        urg, cierre = "🟠", f"cierra en {days} días"
    else:
        urg, cierre = "🟡", f"cierra en {days} días"
    score_txt = f" · Score {s['total']}/100 ({_rec(s)})" if s else ""
    exp = (
        f"📁 Expediente: {docs_ready} documento(s) listos"
        if docs_ready
        else "📁 Expediente: sin preparar"
    )
    return "\n".join([
        f"{urg} {cierre} (en seguimiento)",
        "",
        t.get("title", "(sin título)"),
        f"⏳ {_date(t.get('deadline'))}{score_txt}",
        f"💶 {_money(t.get('budget_amount'), t.get('currency', 'EUR'))}",
        exp,
    ])


def format_item(tw: dict, index: int | None = None) -> str:
    """Bloque de una oportunidad (para el radar diario)."""
    t = tw.get("tender", {})
    s = tw.get("score")
    prefix = f"{index}. " if index is not None else ""
    score_txt = f"{s['total']}/100 · {_rec(s)}" if s else _rec(s)
    lines = [
        f"{prefix}{t.get('title', '(sin título)')}",
        f"   Score: {score_txt}",
        f"   Presupuesto: {_money(t.get('budget_amount'), t.get('currency', 'EUR'))}"
        f" · Plazo: {_date(t.get('deadline'))}",
    ]
    if t.get("buyer"):
        lines.append(f"   Órgano: {t['buyer']}")
    return "\n".join(lines)


def format_daily_digest(items: list[dict], stats: dict | None = None) -> str:
    head = ["📊 Keedio Tender Radar — Resumen diario", ""]
    if stats:
        head.append(
            f"Analizadas: {stats.get('analyzed', '?')} · "
            f"Relevantes: {stats.get('relevant', '?')} · "
            f"Prioritarias: {stats.get('prioritized', '?')} · "
            f"Descartadas: {stats.get('discarded', '?')}"
        )
        head.append("")
    if not items:
        head.append("Hoy no hay oportunidades destacadas.")
        return "\n".join(head)
    head.append("TOP oportunidades")
    head.append("")
    blocks = [format_item(tw, i + 1) for i, tw in enumerate(items)]
    return "\n".join(head) + "\n" + "\n\n".join(blocks)


def format_digest_header(
    items: list[dict], dashboard_url: str | None = None, new_count: int = 0
) -> str:
    """Cabecera CORTA del radar (sin repetir la lista; el detalle va en los items y el panel)."""
    n = len(items)
    if n == 0:
        msg = "📊 Keedio Tender Radar — hoy no hay oportunidades accionables nuevas."
    else:
        nuevas = f" · 🆕 {new_count} nueva(s)" if new_count else ""
        msg = f"📊 Keedio Tender Radar — {n} oportunidad(es) por revisar{nuevas}:"
    if dashboard_url:
        msg += f"\n🔗 Panel: {dashboard_url}"
    return msg


def ficha_link(dashboard_url: str | None, tender_id: str) -> str:
    return f"{dashboard_url.rstrip('/')}/tenders/{tender_id}" if dashboard_url else ""


def format_answer(question: str, result: dict) -> str:
    """Formatea la respuesta de /ask (visual-rag o extractivo) para Telegram."""
    answer = result.get("answer") or "No encontré una respuesta en el pliego."
    n = len(result.get("sources") or [])
    footer = f"motor: {result.get('backend', '?')} · {n} fuente(s)"
    return "\n".join([f"❓ {question}", "", answer, "", footer])


def format_market_context(tender: dict, ctx: dict) -> str:
    """Contexto de mercado de una licitación para /mercado: quién gana + baja esperada."""
    title = (tender.get("title") or "")[:70]
    lines = [f"📊 Mercado — {title}"]
    sample = ctx.get("sample_size") or 0
    if sample == 0:
        lines.append("")
        lines.append("Sin histórico de adjudicaciones para esta categoría CPV todavía.")
        return "\n".join(lines)

    baja = ctx.get("expected_baja")
    baja_txt = f"{baja * 100:.1f}%" if baja is not None else "s/d"
    lines.append(f"Categoría CPV {ctx.get('cpv_division') or 's/d'} · {sample} adjudicaciones")
    lines.append(f"Baja esperada: {baja_txt}")
    winners = ctx.get("likely_winners") or []
    if winners:
        lines.append("")
        lines.append("Quién suele ganar esto:")
        for w in winners[:5]:
            b = w.get("avg_baja")
            bt = f" · baja {b * 100:.0f}%" if b is not None else ""
            lines.append(f"• {w.get('supplier')} — {w.get('wins')} contrato(s){bt}")
    return "\n".join(lines)


def format_market_overview(ov: dict, competitors: list[dict] | None = None) -> str:
    """Resumen global de mercado para /mercado (sin id) y el digest de mercado."""
    baja = ov.get("avg_baja")
    baja_txt = f"{baja * 100:.1f}%" if baja is not None else "s/d"
    lines = [
        "📊 Inteligencia de mercado",
        f"Adjudicaciones: {ov.get('awards', 0)} · baja media: {baja_txt}",
        f"Importe total: {_money(ov.get('total_awarded'))}",
    ]
    tc = ov.get("top_competitor") or {}
    tb = ov.get("top_buyer") or {}
    tcpv = ov.get("top_cpv_division") or {}
    if tc.get("supplier"):
        cuota = tc.get("share")
        cuota_txt = f" ({cuota * 100:.0f}% cuota)" if cuota is not None else ""
        lines.append(f"Top adjudicatario: {tc['supplier']} — {tc.get('wins')} contr{cuota_txt}")
    if tb.get("buyer"):
        lines.append(f"Top comprador: {tb['buyer'][:45]} ({tb.get('awards')})")
    if tcpv.get("cpv_division"):
        lines.append(f"CPV líder: {tcpv['cpv_division']} ({tcpv.get('awards')} adj)")
    if competitors:
        lines.append("")
        lines.append("Competidores frecuentes:")
        for c in competitors[:5]:
            cuota = c.get("share")
            ct = f" · {cuota * 100:.0f}% cuota" if cuota is not None else ""
            lines.append(f"• {c.get('supplier')} — {c.get('wins')} contr{ct}")
    return "\n".join(lines)


def format_competitor_profile(p: dict) -> str:
    """Perfil de un adjudicatario para /competidor."""
    baja = p.get("avg_baja")
    share = p.get("share")
    lines = [
        f"🏢 {p.get('supplier')}",
        f"Contratos: {p.get('wins')} · Importe: {_money(p.get('total_awarded'))}"
        + (f" · cuota {share * 100:.1f}%" if share is not None else "")
        + (f" · baja media {baja * 100:.1f}%" if baja is not None else ""),
    ]
    buyers = p.get("by_buyer") or []
    if buyers:
        top = " · ".join(f"{b['buyer'][:30]} ({b['awards']})" for b in buyers[:4])
        lines.append(f"Órganos: {top}")
    cpvs = p.get("by_cpv") or []
    if cpvs:
        lines.append("CPV: " + " · ".join(f"{c['cpv_division']} ({c['awards']})" for c in cpvs[:5]))
    contracts = p.get("contracts") or []
    if contracts:
        lines.append("")
        lines.append("Últimos contratos:")
        for c in contracts[:5]:
            fecha = f" ({c['award_date']})" if c.get("award_date") else ""
            titulo = (c.get("title") or "—")[:50]
            lines.append(f"• {titulo} — {_money(c.get('awarded_amount'))}{fecha}")
    return "\n".join(lines)


def format_stats(stats: dict) -> str:
    """Resumen de estado del sistema para /estado."""
    by_source = stats.get("by_source", {}) or {}
    fuentes = " · ".join(f"{k}: {v}" for k, v in by_source.items()) or "—"
    ingested = stats.get("last_ingested_at") or "nunca"
    scored = stats.get("last_scored_at") or "nunca"
    return (
        "📡 Estado del radar\n\n"
        f"Licitaciones: {stats.get('total', 0)} · Puntuadas: {stats.get('scored_count', 0)}\n"
        f"🟢 GO: {stats.get('go_count', 0)} · Score medio: {stats.get('avg_score', 0)}\n"
        f"Fuentes → {fuentes}\n"
        f"Última ingesta: {ingested[:16].replace('T', ' ')}\n"
        f"Último scoring: {scored[:16].replace('T', ' ')}"
    )


def format_alert(tw: dict) -> str:
    """Alerta de oportunidad prioritaria (GO recién detectada)."""
    t = tw.get("tender", {})
    s = tw.get("score")
    score_txt = f"{s['total']}/100" if s else "?"
    return (
        "🟢 Nueva oportunidad prioritaria (GO)\n\n"
        f"{t.get('title', '(sin título)')}\n"
        f"Score: {score_txt} · Fuente: {t.get('source', '?')}\n"
        f"Presupuesto: {_money(t.get('budget_amount'), t.get('currency', 'EUR'))}"
        f" · Plazo: {_date(t.get('deadline'))}"
    )


def format_urgent(tw: dict) -> str:
    t = tw.get("tender", {})
    s = tw.get("score")
    score_txt = f"Score {s['total']}/100 ({_rec(s)})" if s else _rec(s)
    return (
        "🚨 Licitación urgente\n\n"
        f"{t.get('title', '(sin título)')} — {score_txt}\n"
        f"⏳ Cierre: {_date(t.get('deadline'))}\n"
        f"Presupuesto: {_money(t.get('budget_amount'), t.get('currency', 'EUR'))}"
    )


def format_tender_detail(tender: dict, score: dict | None = None) -> str:
    lines = [
        tender.get("title", "(sin título)"),
        "",
        f"Dominio/fuente: {tender.get('source', '?')}",
        f"Presupuesto: {_money(tender.get('budget_amount'), tender.get('currency', 'EUR'))}",
        f"Plazo: {_date(tender.get('deadline'))}",
        f"Estado: {tender.get('status', '?')}",
    ]
    if tender.get("cpv"):
        lines.append(f"CPV: {', '.join(tender['cpv'])}")
    if score:
        lines += ["", f"Score: {score['total']}/100 · {_rec(score)}"]
        for f in score.get("factors", [])[:6]:
            mark = "➕" if f.get("kind") == "positive" else "➖"
            lines.append(f"{mark} {f.get('message', '')}")
    if tender.get("url"):
        lines += ["", tender["url"]]
    return "\n".join(lines)
