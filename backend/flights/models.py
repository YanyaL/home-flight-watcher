from django.db import models


class ScanSnapshot(models.Model):
    scanned_at = models.DateTimeField(auto_now_add=True)
    provider = models.CharField(max_length=32)
    offer_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.provider} #{self.id} ({self.offer_count})"


class FlightOfferRecord(models.Model):
    snapshot = models.ForeignKey(
        ScanSnapshot,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    offer_id = models.CharField(max_length=255)
    origin = models.CharField(max_length=8)
    dest = models.CharField(max_length=8)
    depart_date = models.DateField()
    price = models.FloatField()
    currency = models.CharField(max_length=8)
    stops = models.PositiveSmallIntegerField()
    duration_min = models.PositiveIntegerField()
    airlines = models.CharField(max_length=64)
    score = models.FloatField(default=0)
    payload = models.JSONField()

    class Meta:
        ordering = ["-score", "price"]
        indexes = [
            models.Index(fields=["origin", "dest", "depart_date", "snapshot"]),
        ]

    def __str__(self) -> str:
        return f"{self.origin}->{self.dest} {self.depart_date} {self.price}"


class Alert(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=32)
    message = models.TextField()
    offer_id = models.CharField(max_length=255, blank=True)
    price = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.message
