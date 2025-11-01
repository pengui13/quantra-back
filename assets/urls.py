from django.urls import path
from .views import AssetListView

urlpatterns = [
    path("assets/", AssetListView.as_view(), name="asset-list"),
    
]
