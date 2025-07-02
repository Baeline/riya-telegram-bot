import razorpay
import os
import uuid

# Load Razorpay keys from env
RAZORPAY_KEY = os.getenv("RAZORPAY_KEY")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

def create_order(amount, user_id):
    try:
        receipt_id = f"tg_{user_id}_{uuid.uuid4().hex[:8]}"
        order_data = {
            "amount": amount * 100,  # in paise
            "currency": "INR",
            "receipt": receipt_id,
            "payment_capture": 1
        }
        order = client.order.create(order_data)
        return order["id"]
    except Exception as e:
        print("Failed to create Razorpay order:", str(e))
        return None
