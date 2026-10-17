from django.db import models


class BotSession(models.Model):
    """Per-chat conversation state for multi-step flows (e.g. sending a hazard report)."""

    chat_id = models.BigIntegerField(unique=True)
    state = models.CharField(max_length=32, blank=True)
    data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def reset(self):
        self.state, self.data = "", {}
        self.save()
