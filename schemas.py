from pydantic import BaseModel, EmailStr, validator, model_validator
from typing import List, Optional
from datetime import datetime

class Amount(BaseModel):
    value: str
    currency: str

class Customer(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    @model_validator(mode='after')
    def check_at_least_one_contact(self):
        if self.email is None and self.phone is None:
            raise ValueError('At least one of email or phone must be provided for the customer.')
        return self

class CartItem(BaseModel):
    product_id: str
    quantity: int = 1
    size: str

class PaymentCreate(BaseModel):
    amount: Amount
    description: str
    returnUrl: str
    items: List[CartItem]

    @validator('returnUrl')
    def validate_return_url(cls, v):
        if "://" not in v:
            raise ValueError('returnUrl must be a valid URL containing ://')
        return v

class Delivery(BaseModel):
    cost: str
    estimatedTime: str
    tracking_number: Optional[str] = None

class OrderItemResponse(BaseModel):
    id: str
    name: str
    price: str
    size: str
    image: str
    delivery: Delivery

    class Config:
        orm_mode = True

class OrderResponse(BaseModel):
    id: str
    number: str
    total: str
    date: datetime
    status: str
    items: List[OrderItemResponse]

    class Config:
        orm_mode = True
