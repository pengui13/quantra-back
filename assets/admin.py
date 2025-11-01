from django.contrib import admin

from .models import Asset, Network, Balance

admin.site.register(Asset)
admin.site.register(Network)
admin.site.register(Balance)