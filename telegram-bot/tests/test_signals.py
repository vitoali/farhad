from bot.signals import parse_manual_signal, parse_tradingview_payload


def test_parse_manual_buy():
    text = """
    EURUSD BUY
    entry: 1.0850
    sl: 1.0800
    tp: 1.0950
    tf: M15
    note: ICT Judas
    """
    signal = parse_manual_signal(text)
    assert signal is not None
    assert signal.symbol == "EURUSD"
    assert signal.side == "BUY"
    assert signal.entry == "1.0850"
    assert signal.stop_loss == "1.0800"
    assert signal.take_profit == "1.0950"
    assert signal.timeframe == "M15"
    assert signal.note == "ICT Judas"


def test_parse_manual_sell_persian_keys():
    text = """
    XAUUSD SELL
    ورود: 2350
    حد ضرر: 2340
    حد سود: 2370
    """
    signal = parse_manual_signal(text)
    assert signal is not None
    assert signal.side == "SELL"
    assert signal.entry == "2350"
    assert signal.stop_loss == "2340"
    assert signal.take_profit == "2370"


def test_parse_tv_csv():
    signal = parse_tradingview_payload(
        "XAUUSD,BUY,entry=2350,sl=2340,tp=2370,tf=M5,note=Cardwell"
    )
    assert signal is not None
    assert signal.symbol == "XAUUSD"
    assert signal.side == "BUY"
    assert signal.source == "tradingview"
    assert signal.note == "Cardwell"


def test_parse_tv_json():
    signal = parse_tradingview_payload(
        {
            "ticker": "BTCUSDT",
            "action": "short",
            "entry": 64000,
            "sl": 65000,
            "tp": 62000,
            "timeframe": "15",
        }
    )
    assert signal is not None
    assert signal.symbol == "BTCUSDT"
    assert signal.side == "SELL"
    assert signal.entry == "64000"


def test_invalid_payload():
    assert parse_manual_signal("hello") is None
    assert parse_tradingview_payload({"foo": 1}) is None
