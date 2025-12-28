from django.db import models

from decimal import Decimal
class Network(models.Model):
    name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=200)
    confirmations = models.IntegerField(default=0)
    min_deposit_amount = models.DecimalField(max_digits=15, decimal_places=8, default=0)
    min_deposit_time = models.IntegerField(default=0)

    apr_low = models.FloatField(default=0)
    apr_high = models.FloatField(default=0)

    class Meta:
        db_table = 'networks'

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Network name={self.name}>"


class Transaction(models.Model):
    """Model to track all cryptocurrency transactions (deposits, withdrawals, etc.)"""
    
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    TRANSFER = 'transfer'
    
    TRANSACTION_TYPES = [
        (DEPOSIT, 'Deposit'),
        (WITHDRAWAL, 'Withdrawal'),
        (TRANSFER, 'Transfer'),
    ]
    
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey( 'users.User', on_delete=models.CASCADE, related_name='transactions')
    asset = models.ForeignKey('Asset', on_delete=models.PROTECT, related_name='transactions')
    network = models.ForeignKey('Network', on_delete=models.PROTECT, related_name='transactions')
    
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0'))
    
    from_address = models.CharField(max_length=255, blank=True, null=True)
    to_address = models.CharField(max_length=255, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    timestamp = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    blockchain_hash = models.CharField(max_length=255, blank=True, null=True, unique=True)
    confirmations = models.IntegerField(default=0)
    
    description = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['status', 'type']),
            models.Index(fields=['asset', 'user']),
        ]
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.amount} {self.asset.symbol} ({self.get_status_display()})"
    
    def mark_completed(self, blockchain_hash=None):
        from django.utils import timezone
        self.status = self.COMPLETED
        self.completed_at = timezone.now()
        if blockchain_hash:
            self.blockchain_hash = blockchain_hash
        self.save()
    
    def mark_failed(self, error_message=None):
        """Mark transaction as failed and restore balance"""
        from django.utils import timezone
        self.status = self.FAILED
        self.completed_at = timezone.now()
        if error_message:
            self.error_message = error_message
        self.save()
        
        if self.type == self.WITHDRAWAL:
            balance = Balance.objects.get(user=self.user, asset=self.asset)
            balance.available += self.amount
            balance.pending_withdrawal -= self.amount
            balance.save()

class Asset(models.Model):
    symbol = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=20, decimal_places=6, default=0)
    networks = models.ManyToManyField(Network, related_name="assets", blank=True)
    fiat = models.BooleanField(default = False)
    staking = models.BooleanField(default = False)
    class Meta:
        db_table = 'assets'

    def __str__(self):
        return self.symbol

    def __repr__(self):
        return f"<Asset name={self.name}>"

class Balance(models.Model):
    asset = models.ForeignKey(Asset, related_name="balances", on_delete=models.CASCADE)
    available = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    network = models.ForeignKey(Network, related_name = 'balances', null = True, on_delete = models.CASCADE)
    user = models.ForeignKey(
        'users.User', related_name="user_balances", on_delete=models.CASCADE
    )
    public= models.CharField(max_length=200, blank=True, null=True)
    private = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'balances'

    def __str__(self):
        return f"{self.asset.symbol} Balance"
    
    def __repr__(self):
        return f"Asset={self.asset.symbol}, Total={self.total}>"
    

class Quote(models.Model):
    id = models.BigAutoField(primary_key=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    interval = models.CharField(max_length=10, null=True, blank=True)
    bid = models.DecimalField(max_digits=20, decimal_places=8)
    ask = models.DecimalField(max_digits=20, decimal_places=8)
    lp = models.DecimalField(
        max_digits=20, decimal_places=8, default=0, null=True, blank=True
    )
    volume = models.DecimalField(max_digits=20, decimal_places=8)

    open_price = models.DecimalField(max_digits=20, decimal_places=10)
    high_price = models.DecimalField(max_digits=20, decimal_places=10)
    low_price = models.DecimalField(max_digits=20, decimal_places=10)
    prev_close_price = models.DecimalField(
        max_digits=20, decimal_places=10, blank=True, null=True
    )
    max_24h = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    min_24h = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    is_closed = models.BooleanField(default=False)
    time = models.DateTimeField(auto_now_add=True)
    perc_24 = models.FloatField(default=0)
    value_in_usd = models.DecimalField(max_digits=20, decimal_places=8, default=0)

    class Meta:
        db_table = "quotes"
        unique_together = ("asset", "interval")

    def __str__(self):
        return f"{self.symbol}"