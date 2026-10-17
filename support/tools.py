from django.utils import timezone
from orders.models import RefundRequest, Order
from .tracking_data import DELIVERY_DATA

def get_order_details(order_id: int):
  try:
    order = Order.objects.get(id=order_id)
    return {
      "order_id": order.id,
      "product_name": order.product_name,
      "amount": float(order.amount),
      "status": order.status,
      "carrier": order.carrier,
      "tracking_number": order.tracking_number,
      "delivery": order.delivery,
      "ordered_on": order.created_at.strftime("%d %b %Y"),
      "days_since_order": (timezone.now() - order.created_at).days
    }
  except Order.DoesNotExist:
    return {"error": "Order not found"}


def get_refund_history(user_id):
  refunds = RefundRequest.objects.filter(user_id=user_id)
  history = []
  for refund in refunds:
    history.append({
      "order_id": refund.order.id,
      "product_name":refund.order.product_name,
      "reason": refund.reason,
      "status": refund.status,
      "requested_on": refund.created_at.strftime("%d %b %Y"), # 13 October 2026 
    })
  return {
    "total_refund_requets": len(history),
    "history": history,
  }


def check_delivery_status(tracking_number, carrier):
  default_response = {
    "status": "Unknown",
    "last_location": "Tracking info unavailable",
    "last_update": "N/A",
    "estimated_delivery": "Contact carrier directly",
    "delay_reason": "No updates from carrier",
  }
  result = DELIVERY_DATA.get(tracking_number, default_response).copy()
  result["tracking_number"] = tracking_number
  result["carrier"] = carrier
  return result


  


