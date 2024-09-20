from django.db import models


class ClickCount(models.Model):
    username = models.CharField(max_length=256, default="User")
    count = models.IntegerField(default=0)


class TokenPathMapping(models.Model):
    image_path = models.CharField(max_length=255, unique=True)
    token = models.CharField(max_length=255, unique=True)
