import time
from datetime import datetime, timedelta, timezone

from delta_rest_client import (
    DeltaRestClient,
    create_order_format,
    round_by_tick_size
)

# ================= CONFIG =================
API_KEY = "TcwdPNNYGjjgkRW4BRIAnjL7z5TLyJ"
API_SECRET = "B5ALo5Mh8mgUREB6oGD4oyX3y185oElaz1LoU6Y3X5ZX0s8TvFZcX4YTVToJ"

BASE_URL = "https://api.india.delta.exchange"

STRIKE_INTERVAL = 400
ORDER_SIZE = 1
CHECK_INTERVAL = 5
PRICE_OFFSET = 100
# =========================================

delta_client = DeltaRestClient(
    base_url=BASE_URL,
    api_key=API_KEY,
    api_secret=API_SECRET
)

IST = timezone(timedelta(hours=5, minutes=30))

# ---------- HELPERS ----------

def get_expiry():
    now = datetime.now(IST)
    if now.hour > 17 or (now.hour == 17 and now.minute >= 30):
        expiry = now.date() + timedelta(days=3)
    else:
        expiry = now.date() + timedelta(days=2)
    return expiry.strftime("%d%m%y")


def get_atm_strike(spot):
    return int(round(float(spot) / STRIKE_INTERVAL) * STRIKE_INTERVAL)


def get_product_id(symbol):
    return delta_client.get_product(symbol)["id"]


def position_exists(product_id):
    pos = delta_client.get_position(product_id)
    if not pos:
        return False
    return abs(float(pos.get("size", 0))) > 0


def straddle_exists_for(atm, expiry):
    """
    Check if BOTH CALL & PUT exist
    for SAME strike and SAME expiry
    """
    call_symbol = f"C-BTC-{atm}-{expiry}"
    put_symbol  = f"P-BTC-{atm}-{expiry}"

    try:
        call_id = get_product_id(call_symbol)
        put_id  = get_product_id(put_symbol)
    except Exception:
        return False

    if position_exists(call_id) and position_exists(put_id):
        return True

    return False


# ---------- MAIN ----------
print("🚀 SELL STRADDLE BOT STARTED")

while True:
    try:
        # -------- MARKET DATA --------
        expiry = get_expiry()

        btc = delta_client.get_ticker("BTCUSD")
        spot = float(btc["spot_price"])
        atm = get_atm_strike(spot)

        print(f"🔁 Spot {spot} | ATM {atm} | Expiry {expiry}")

        # -------- CHECK EXISTING STRADDLE --------
        if straddle_exists_for(atm, expiry):
            print("✅ Existing STRADDLE found — skipping entry")
            time.sleep(CHECK_INTERVAL)
            continue

        # -------- PLACE NEW STRADDLE --------
        call_symbol = f"C-BTC-{atm}-{expiry}"
        put_symbol  = f"P-BTC-{atm}-{expiry}"

        call_id = get_product_id(call_symbol)
        put_id  = get_product_id(put_symbol)

        call_ticker = delta_client.get_ticker(call_symbol)
        put_ticker  = delta_client.get_ticker(put_symbol)

        call_price = round_by_tick_size(
            float(call_ticker["mark_price"]) - PRICE_OFFSET, 0.5
        )
        put_price = round_by_tick_size(
            float(put_ticker["mark_price"]) - PRICE_OFFSET, 0.5
        )

        call_order = create_order_format(
            product_id=call_id,
            size=ORDER_SIZE,
            side="sell",
            price=float(call_price)
        )

        put_order = create_order_format(
            product_id=put_id,
            size=ORDER_SIZE,
            side="sell",
            price=float(put_price)
        )

        delta_client.batch_create(call_id, [call_order])
        delta_client.batch_create(put_id, [put_order])

        print(
            f"✅ NEW STRADDLE SOLD | "
            f"{call_symbol} @ {call_price} | "
            f"{put_symbol} @ {put_price}"
        )

    except Exception as e:
        print("❌ Error:", e)

    time.sleep(CHECK_INTERVAL)
