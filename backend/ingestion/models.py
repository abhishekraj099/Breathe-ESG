from django.db import models


class Client(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DataSource(models.Model):
    class SourceType(models.TextChoices):
        SAP_FUEL = "SAP_FUEL", "SAP fuel and procurement"
        UTILITY_ELECTRICITY = "UTILITY_ELECTRICITY", "Utility electricity"
        CORPORATE_TRAVEL = "CORPORATE_TRAVEL", "Corporate travel"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="data_sources")
    source_type = models.CharField(max_length=40, choices=SourceType.choices)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("client", "source_type", "name")

    def __str__(self):
        return f"{self.client.slug}:{self.source_type}"


class IngestionBatch(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="batches")
    data_source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="batches")
    original_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING)
    total_rows = models.PositiveIntegerField(default=0)
    accepted_rows = models.PositiveIntegerField(default=0)
    suspicious_rows = models.PositiveIntegerField(default=0)
    rejected_rows = models.PositiveIntegerField(default=0)
    error_summary = models.JSONField(default=list, blank=True)
    uploaded_by = models.CharField(max_length=255, default="analyst")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.data_source.source_type} batch {self.id}"


class EmissionRecord(models.Model):
    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    class Scope(models.TextChoices):
        SCOPE_1 = "SCOPE_1", "Scope 1"
        SCOPE_2 = "SCOPE_2", "Scope 2"
        SCOPE_3 = "SCOPE_3", "Scope 3"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="emission_records")
    data_source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="emission_records")
    ingestion_batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name="records")
    source_record_id = models.CharField(max_length=255, blank=True)
    source_type = models.CharField(max_length=40, choices=DataSource.SourceType.choices)
    scope = models.CharField(max_length=20, choices=Scope.choices)
    activity_date = models.DateField(null=True, blank=True)
    category = models.CharField(max_length=120, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    unit = models.CharField(max_length=40, blank=True)
    emissions_kg_co2e = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    raw_data = models.JSONField()
    normalized_data = models.JSONField(default=dict, blank=True)
    suspicious = models.BooleanField(default=False)
    flags = models.JSONField(default=list, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )
    locked_for_audit = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.CharField(max_length=255, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["client", "review_status"]),
            models.Index(fields=["client", "source_type"]),
            models.Index(fields=["suspicious"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source_type}:{self.source_record_id or self.id}"


class AuditLog(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="audit_logs")
    emission_record = models.ForeignKey(
        EmissionRecord, on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True
    )
    ingestion_batch = models.ForeignKey(
        IngestionBatch, on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True
    )
    action = models.CharField(max_length=80)
    actor = models.CharField(max_length=255, default="system")
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
