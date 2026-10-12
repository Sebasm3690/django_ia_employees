from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Order, RefundRequest

# Create your views here.

@login_required #To avoid the user get access to orders without login
def orders_list(request):
  orders = Order.objects.filter(user=request.user)
  context = {
    'orders': orders
  }
  return render(request, 'orders_list.html', context)


def order_detail(request, order_id):
  order = get_object_or_404(Order, id=order_id, user=request.user)

  # get refund history for the order
  refunds = RefundRequest.objects.filter(order=order).order_by(
    '-created_at'  #latest refund first
  )

  context = {
    'order': order,
    'refunds': refunds
  }
  return render(request, 'order_detail.html', context)

 
