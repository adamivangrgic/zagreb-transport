from django.db import models


class StaticFeed(models.Model):
    provider = models.CharField(max_length=10)
    last_update = models.DateTimeField()
