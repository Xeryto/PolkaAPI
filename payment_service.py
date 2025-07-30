
import hmac
import hashlib
import random
import string
import uuid
from typing import List
from yookassa import Configuration, Payment
from dotenv import load_dotenv
import os
from sqlalchemy.orm import Session
from models import Order, OrderItem, Payment as PaymentModel, OrderStatus, Product
import ipaddress

import schemas

load_dotenv()

Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

YOOKASSA_IP_ADDRESSES = [
    ipaddress.ip_network('185.71.76.0/27'),
    ipaddress.ip_network('185.71.77.0/27'),
    ipaddress.ip_network('77.75.153.0/25'),
    ipaddress.ip_network('77.75.154.128/25'),
    ipaddress.ip_network('77.75.156.11'),
    ipaddress.ip_network('77.75.156.35'),
    ipaddress.ip_network('2a02:5180::/32'),
]

def verify_webhook_ip(ip: str) -> bool:
    ip_address = ipaddress.ip_address(ip)
    for network in YOOKASSA_IP_ADDRESSES:
        if ip_address in network:
            return True
    return False

def generate_order_number(db: Session) -> str:
    while True:
        order_number = ''.join(random.choices(string.digits, k=5))
        if not db.query(Order).filter(Order.order_number == order_number).first():
            return order_number

def create_payment(db: Session, user_id: str, amount: float, currency: str, description: str, return_url: str, items: List[schemas.CartItem]):
    idempotence_key = str(uuid.uuid4())

    order_number = generate_order_number(db)

    order = Order(
        user_id=user_id,
        order_number=order_number,
        total_amount=str(amount),
        currency=currency,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise Exception(f"Product with id {item.product_id} not found")

        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=product.price,
            size=item.size
        )
        db.add(order_item)

    db.commit()

    payment = Payment.create({
        "amount": {
            "value": "{:.2f}".format(amount),
            "currency": currency
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"{return_url}?payment_id={order.id}"
        },
        "capture": True,
        "description": description,
        "metadata": {
            "order_id": order.id
        }
    }, idempotence_key)

    payment_model = PaymentModel(
        id=payment.id,
        order_id=order.id,
        amount=payment.amount.value,
        currency=payment.amount.currency,
        status=payment.status
    )
    db.add(payment_model)
    db.commit()

    return payment.confirmation.confirmation_url

def get_payment(payment_id: str):
    return Payment.find_one(payment_id)

def get_yookassa_payment_status(payment_id: str):
    try:
        yookassa_payment = Payment.find_one(payment_id)
        return yookassa_payment.status
    except Exception as e:
        print(f"Error fetching YooKassa payment status for {payment_id}: {e}")
        return None

def update_order_status(db: Session, order_id: str, status: OrderStatus):
    print(f"Attempting to update order {order_id} to status {status.value}")
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        print(f"Found order {order_id}. Current status: {order.status.value}. New status: {status.value}")
        order.status = status
        # db.commit() # Removed commit from here
        print(f"Order {order_id} status updated to {order.status.value}")
    else:
        print(f"Order {order_id} not found in database.")

