from rest_framework import serializers
from .models import *


class ClickCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClickCount
        fields = ['username', 'count']
