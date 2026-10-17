import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dj_ai_employee_main.settings")
django.setup()

from django.contrib.auth.models import User
from orders.models import Order
from support.models import Conversation, Message
from support.agents import run_support_agent

def main():
    order = Order.objects.first()
    if not order:
        print("No order found")
        return
    user = order.user

    conv, _ = Conversation.objects.get_or_create(user=user, order=order)
    user_msg = "Hi"
    Message.objects.create(conversation=conv, role="user", content=user_msg)
    
    print(f"Testing run_support_agent with order #{order.id}, user #{user.id}...")
    reply = run_support_agent(user_msg, conv.id, order.id, user.id)
    print("Agent reply:", reply)

if __name__ == "__main__":
    main()
