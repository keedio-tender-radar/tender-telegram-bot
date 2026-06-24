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
