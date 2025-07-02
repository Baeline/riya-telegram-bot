# payment.py
import razorpay
import uuid
import os

# Get keys from environment variables (recommended) or hardcode temporarily
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_live_R92bH8qooQzbGF")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "A6wGGchHsr50VWqdW07Nvf7Y")

# Razorpay client
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_order(user_id: str, amount_paise: int = 4900):
    """
    Create a Razorpay order. Amount is in paise (₹49 = 4900).
    Returns the full order object including order['id']
    """
    receipt_id = f"tg_{user_id}_{str(uuid.uuid4())[:6]}"

    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt_id,
        "payment_capture": 1,
        "notes": {
            "telegram_user_id": user_id
        }
    }

    order = client.order.create(data=order_data)
    return order
