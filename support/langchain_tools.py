from langchain.tools import tool

from .tools import (
  get_order_details as _get_order_details,
  get_refund_history as _get_refund_history,
  check_delivery_status as _check_delivery_status,
  get_customer_risk_profile as _get_customer_risk_profile,
  search_knowledge_base as _search_knowledge_base,
)


@tool
def get_order_details(order_id: int) -> dict:
  """Fetch complete order details including product, status, tracking, and refund history for a specific order. Use this when customer mentions their order or complains about delays, damage, or refund requests. Input is order ID"""
  return _get_order_details(order_id)

@tool
def get_refund_history(user_id: int) -> dict:
  """Fetch complete refund history for a specific user. Use this when customer mentions their refund history or complains about refunds. Input is user ID."""
  return _get_refund_history(user_id)

@tool
def check_delivery_status(tracking_number:str, carrier:str) -> dict:
  """Check delivery status for a specific order. Use this when customer mentions their order or complains about delays, damage, or refund requests. Input is tracking number and carrier."""
  return _check_delivery_status(tracking_number, carrier)

@tool
def get_customer_risk_profile(user_id:int) -> dict:
  """Get complete risk profile for a customer including order history, refund patterns and ratio. Use this to assess fraud risk."""
  return _get_customer_risk_profile(user_id)

@tool
def search_knowledge_base(query:str) -> dict:
  """Search CoolBreeze AC company documents including refund policy, warranty policy, and product FAQs. Use this when customer asks about company policies, warranty coverage, warranty claims, refund eligibility, or any general product information that requires accurate company documentation."""
  return _search_knowledge_base(query)


