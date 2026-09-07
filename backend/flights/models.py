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


class ScanJob(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "pending"),
        (STATUS_RUNNING, "running"),
        (STATUS_COMPLETED, "completed"),
        (STATUS_CANCELLED, "cancelled"),
        (STATUS_FAILED, "failed"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    provider = models.CharField(max_length=32, blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    cancel_requested = models.BooleanField(default=False)
    attach_bookings = models.BooleanField(default=True)
    offer_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    snapshot = models.ForeignKey(
        ScanSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="jobs",
    )

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"ScanJob #{self.id} {self.status}"


class ScanTask(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "pending"),
        (STATUS_RUNNING, "running"),
        (STATUS_SUCCEEDED, "succeeded"),
        (STATUS_FAILED, "failed"),
        (STATUS_CANCELLED, "cancelled"),
    ]

    job = models.ForeignKey(ScanJob, on_delete=models.CASCADE, related_name="tasks")
    origin = models.CharField(max_length=8)
    dest = models.CharField(max_length=8)
    depart_date = models.DateField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    offer_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    result_payload = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["job", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.origin}->{self.dest} {self.depart_date} {self.status}"
