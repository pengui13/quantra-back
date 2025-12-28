from django.urls import path
from .views import AssetListView, Deposit, ValidateAddressView, WithdrawView, WithdrawalHistoryView, WithdrawalStatusView

urlpatterns = [
    path("assets/", AssetListView.as_view(), name="asset-list"),
    path("<str:symbol>/<str:network>/deposit/", Deposit.as_view(), name = 'deposit'),
    path('assets/validate-address/', ValidateAddressView.as_view(), name='validate-address'),
    path('assets/withdraw/', WithdrawView.as_view(), name='withdraw'),
    path('assets/withdrawal-history/', WithdrawalHistoryView.as_view(), name='withdrawal-history'),
    path('withdrawal-status/<int:transaction_id>/', WithdrawalStatusView.as_view(), name='withdrawal-status'),
]
