from django.urls import path
from .views import AssetListView, Deposit

urlpatterns = [
    path("assets/", AssetListView.as_view(), name="asset-list"),
    path("<str:symbol>/<str:network>/deposit/", Deposit.as_view(), name = 'deposit')
]
