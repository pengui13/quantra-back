from django.db import models

class Network(models.Model):
    name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=200)
    confirmations = models.IntegerField(default=0)
    min_deposit_amount = models.DecimalField(max_digits=15, decimal_places=8, default=0)
    min_deposit_time = models.IntegerField(default=0)

    # ✅ Add APR range here
    apr_low = models.FloatField(default=0)
    apr_high = models.FloatField(default=0)

    class Meta:
        db_table = 'networks'

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Network name={self.name}>"

class Asset(models.Model):
    symbol = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=20, decimal_places=6, default=0)
    networks = models.ManyToManyField(Network, related_name="assets", blank=True)

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