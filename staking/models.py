from django.db import models
from django.contrib.auth import get_user_model
from assets.models import Asset

User = get_user_model()

class StakeTx(models.Model):
    user = models.ForeignKey(
        User, related_name="user_staketx", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    timestamp_of_exit = models.DateTimeField(blank=True, null=True)
    asset = models.ForeignKey(
        Asset, related_name="asset_staked", on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=15, decimal_places=8, default=0)
    rewards = models.DecimalField(max_digits=15, decimal_places=8, default=0)
    type = models.CharField(default="")

    class Meta:
        db_table = "staked_tx"

    def __str__(self):
        return f"{self.user.email}  {self.asset}"


class StakePending(models.Model):
    user = models.ForeignKey(
        User, related_name="user_stake_pend_tx", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    asset = models.ForeignKey(
        Asset, related_name="asset_staked_pend", on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=15, decimal_places=8, default=0)
    rewards = models.DecimalField(max_digits=15, decimal_places=8, default=0)
    updated_timestamp = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "staked_pending"

    def __str__(self):
        return f"{self.user.email}  {self.asset}"


class StakingRewards(models.Model):
    user = models.ForeignKey(
        User, related_name="user_reward_st", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    asset = models.ForeignKey(
        Asset, related_name="asset_reward_st", on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=15, decimal_places=8, default=0)

    class Meta:
        db_table = "staking_reward"