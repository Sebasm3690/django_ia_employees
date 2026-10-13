from django.apps import AppConfig
from django.contrib import admin


class SuportConfig(AppConfig):
  default_auto_field = "django.db.models.BigAutoField"
  name = "support"

  def ready(self):
    from .models import Conversation, Message, AgentLog
    try:
      admin.site.register(Conversation)
      admin.site.register(Message)
      admin.site.register(AgentLog)
    except Exception:
      pass
