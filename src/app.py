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

STRIKE_INTERVAL = 100
STRIKE_DISTANCE = 500
ORDER_SIZE = 2
CHECK_INTERVAL = 5
PRICE_OFFSET = 50
MIN_MARK_PRICE = 500
# =========================================

delta_client = DeltaRestClient(
    base_url=BASE_URL,
    api_key=API_KEY,
    api_secret=API_SECRET
)

IST = timezone(timedelta(hours=5, minutes=30))

# ---------- HELPERS ----------

def get_expiry():
    expiry = datetime(2026, 4, 24)
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


# ---------- MAIN ----------
print("🚀 CALL OPTION BUY BOT STARTED")

while True:
    try:
        expiry = get_expiry()

        btc = delta_client.get_ticker("ETHUSD")
        spot = float(btc["spot_price"])
        atm = get_atm_strike(spot)

        call_strike = atm - STRIKE_DISTANCE
        call_symbol = f"C-ETH-{call_strike}-{expiry}"

        print(f"\n🔁 Spot {spot} | ATM {atm}")
        print(f"📌 CALL {call_strike} | Expiry {expiry}")

        call_id = get_product_id(call_symbol)

        if not position_exists(call_id):
            call_ticker = delta_client.get_ticker(call_symbol)
            call_mark = float(call_ticker["mark_price"])

            if call_mark >= MIN_MARK_PRICE:
                call_price = round_by_tick_size(call_mark + PRICE_OFFSET, 0.5)

                call_order = create_order_format(
                    product_id=call_id,
                    size=ORDER_SIZE,
                    side="buy",
                    price=call_price
                )

                delta_client.batch_create(call_id, [call_order])
                print(f"✅ CALL BOUGHT | {call_symbol} @ {call_price}")
            else:
                print(f"⚠️ CALL skipped (mark {call_mark} < {MIN_MARK_PRICE})")
        else:
            print("⏭️ CALL position already exists")

    except Exception as e:
        print("❌ Error:", e)

    time.sleep(CHECK_INTERVAL)
