from django.db import models

from search.models import Agency


class StaticFeed(models.Model):
    provider = models.CharField(max_length=10)
    last_update = models.DateTimeField()
    agency = models.OneToOneField(Agency, related_name="static_feed", on_delete=models.CASCADE, null=True, blank=True)
