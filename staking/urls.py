from django.urls import path, include
from . import views


urlpatterns = [


    # path("staking_tx/", views.GetStakingTx.as_view(), name="staking_tx"),
    path("stake_asset/", views.StakeAsset.as_view(), name="stake_asset"),
    
    path("unstake_asset/", views.UnStakeAsset.as_view(), name="unstake_asset"),
    path(
        "get_total_reward/", views.GetRewardBalance.as_view(), name="get_total_reward"
    ),
]