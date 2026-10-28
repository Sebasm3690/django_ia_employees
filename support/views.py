from datetime import time
from django.shortcuts import get_object_or_404, render
import json
from django.http import JsonResponse
from support.models import Conversation, Message
from orders.models import Order
from .agents import run_support_agent
from django.contrib.admin.views.decorators import staff_member_required
from django.http import StreamingHttpResponse
from support.event_queue import subscribe, unsubscribe, publish 
from support.langchain_agents import run_support_agent_langchain

# Create your views here.
def chat(request, order_id):
  if request.method == "POST":
    data = json.loads(request.body)
    user_message = data.get("message")

    if not user_message:
      return JsonResponse({"error":"Empty message"}, status=400)

    order = get_object_or_404(Order, id=order_id, user=request.user)
    conversation, created = Conversation.objects.get_or_create(order=order, user=request.user)
    Message.objects.create(conversation=conversation, role="user", content=user_message)

    # Publish customer message in real time to subscribers (admin dashboard)
    event = {"type":"user_message","message":user_message,"name":request.user.first_name}
    publish(conversation.id, event)

    #reply = run_support_agent(user_message, conversation.id, order.id, request.user.id)
    reply = run_support_agent_langchain(user_message, conversation.id, order.id, request.user.id)
    Message.objects.create(conversation=conversation, role="assistant", content=reply)

    return JsonResponse({"reply": reply})

@staff_member_required
def dashboard(request):
  conversations = Conversation.objects.all().order_by("-created_at")
  print("all conversations: ====================>",conversations)
  context = {
    'conversations': conversations
  }
  return render(request, "support/dashboard.html",context)

@staff_member_required
def conversation_detail(request, conversation_id):
  conversation = Conversation.objects.get(id=conversation_id)
  messages = conversation.messages.order_by("created_at")
  agentlogs = conversation.agentlogs.order_by("created_at")
  print("conversation ==================>",conversation)
  print("messages ==================>",messages)
  print("agentlogs ==================>",agentlogs)
  context = {
    "conversation": conversation,
    "messages": messages,
    "agentlogs": agentlogs,
  }
  return render(request, "support/conversation_detail.html", context)



# A generator function, generates a value one by one
# When we use yield keyword in a function, that function will become generator function
# Normal functions return the response but generator functions yield the response (it will give you the response one by one)
@staff_member_required
def conversation_stream(request, conversation_id):
  def event_stream(conversation_id):
    q = subscribe(conversation_id) 
    try:
      while True: #I don't know how many event are going to come
        event = q.get() #Wait for the next event unless you unsubscribe

        yield f"data: {json.dumps(event)}\n\n"
    finally:
      unsubscribe(conversation_id, q) 

  response = StreamingHttpResponse(event_stream(conversation_id), content_type="text/event-stream")
  response['Cache-Control'] = 'no-cache'
  response['X-Accel-Buffering'] = 'no'
  return response