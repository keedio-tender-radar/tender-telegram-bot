from tender_telegram_bot.bot import keyboards


def test_callback_roundtrip():
    data = keyboards.callback_data("interested", "t1")
    assert keyboards.parse_callback(data) == ("interested", "t1")


def test_parse_invalid():
    assert keyboards.parse_callback("garbage") is None
    assert keyboards.parse_callback("other:x:y") is None
    assert keyboards.parse_callback("action::t1") is None


def test_tender_id_with_uuid_dashes():
    tid = "5f1c1e2a-0a1b-4c3d-9e4f-1a2b3c4d5e6f"
    data = keyboards.callback_data("partner", tid)
    # split con maxsplit=2 preserva los guiones del UUID
    assert keyboards.parse_callback(data) == ("partner", tid)


def test_item_buttons_shape():
    rows = keyboards.item_buttons("t1")
    assert len(rows) == 3  # 6 botones, 2 por fila
    assert all(len(r) == 2 for r in rows)
    label, data = rows[0][0]
    assert label == "✅ Interesa"
    assert data == "action:interested:t1"


def test_outcome_buttons():
    rows = keyboards.outcome_buttons("t1")
    assert len(rows) == 1 and len(rows[0]) == 3  # Presentada / Ganada / Perdida
    labels = [label for label, _ in rows[0]]
    assert "🏆 Ganada" in labels and "❌ Perdida" in labels
    # el callback de resultado se parsea (action res_*, tender_id)
    _, data = rows[0][1]
    assert keyboards.parse_callback(data) == ("res_ganada", "t1")


def test_ficha_buttons_includes_prepare_and_link():
    rows = keyboards.ficha_buttons("t1", "https://dash")
    flat = [(label, data) for row in rows for label, data in row]
    assert any(label == "🛠️ Preparar oferta" and data == "action:prepare_offer:t1"
               for label, data in flat)
    assert any(data.startswith("https://dash/tenders/t1") for _, data in flat)
