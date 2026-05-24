from rest_framework import serializers

from .models import AuditLog, DataSource, EmissionRecord, IngestionBatch


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ["id", "source_type", "name"]


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "action", "actor", "before", "after", "message", "created_at"]


class IngestionBatchSerializer(serializers.ModelSerializer):
    data_source = DataSourceSerializer(read_only=True)

    class Meta:
        model = IngestionBatch
        fields = [
            "id",
            "data_source",
            "original_filename",
            "status",
            "total_rows",
            "accepted_rows",
            "suspicious_rows",
            "rejected_rows",
            "error_summary",
            "uploaded_by",
            "created_at",
        ]


class EmissionRecordSerializer(serializers.ModelSerializer):
    data_source_name = serializers.CharField(source="data_source.name", read_only=True)
    batch_id = serializers.IntegerField(source="ingestion_batch_id", read_only=True)

    class Meta:
        model = EmissionRecord
        fields = [
            "id",
            "batch_id",
            "data_source_name",
            "source_record_id",
            "source_type",
            "scope",
            "activity_date",
            "category",
            "quantity",
            "unit",
            "emissions_kg_co2e",
            "raw_data",
            "normalized_data",
            "suspicious",
            "flags",
            "validation_errors",
            "review_status",
            "locked_for_audit",
            "locked_at",
            "reviewed_by",
            "reviewed_at",
            "created_at",
        ]


class ReviewSerializer(serializers.Serializer):
    review_status = serializers.ChoiceField(choices=EmissionRecord.ReviewStatus.choices)
    reviewed_by = serializers.CharField(max_length=255, required=False, default="analyst")
    note = serializers.CharField(required=False, allow_blank=True)
