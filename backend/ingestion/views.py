from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AuditLog, Client, DataSource, EmissionRecord, IngestionBatch
from .parsers import sap_parser, travel_parser, utility_parser
from .serializers import EmissionRecordSerializer, IngestionBatchSerializer, ReviewSerializer

PARSERS = {
    DataSource.SourceType.SAP_FUEL: sap_parser.parse,
    DataSource.SourceType.UTILITY_ELECTRICITY: utility_parser.parse,
    DataSource.SourceType.CORPORATE_TRAVEL: travel_parser.parse,
}


def get_client(request):
    client_name = request.data.get("client_name") or request.query_params.get("client_name") or "Breathe ESG Demo"
    slug = slugify(client_name)
    client, _ = Client.objects.get_or_create(slug=slug, defaults={"name": client_name})
    return client


@api_view(["POST"])
@transaction.atomic
def upload(request):
    source_type = request.data.get("source_type")
    uploaded_file = request.FILES.get("file")
    uploaded_by = request.data.get("uploaded_by", "analyst")

    if source_type not in PARSERS:
        return Response({"detail": "Unsupported source_type."}, status=status.HTTP_400_BAD_REQUEST)
    if not uploaded_file:
        return Response({"detail": "CSV file is required."}, status=status.HTTP_400_BAD_REQUEST)

    client = get_client(request)
    data_source, _ = DataSource.objects.get_or_create(
        client=client,
        source_type=source_type,
        name=DataSource.SourceType(source_type).label,
    )

    batch = IngestionBatch.objects.create(
        client=client,
        data_source=data_source,
        original_filename=uploaded_file.name,
        uploaded_by=uploaded_by,
    )

    parsed_records, file_errors = PARSERS[source_type](uploaded_file)
    created_records = []
    for parsed in parsed_records:
        record = EmissionRecord.objects.create(
            client=client,
            data_source=data_source,
            ingestion_batch=batch,
            source_record_id=parsed.source_record_id,
            source_type=source_type,
            scope=parsed.scope,
            activity_date=parsed.activity_date,
            category=parsed.category,
            quantity=parsed.quantity,
            unit=parsed.unit,
            emissions_kg_co2e=parsed.emissions_kg_co2e,
            raw_data=parsed.raw_data,
            normalized_data=parsed.normalized_data,
            suspicious=parsed.suspicious,
            flags=parsed.flags,
            validation_errors=parsed.validation_errors,
        )
        created_records.append(record)
        AuditLog.objects.create(
            client=client,
            emission_record=record,
            ingestion_batch=batch,
            action="RECORD_INGESTED",
            actor=uploaded_by,
            after={
                "review_status": record.review_status,
                "suspicious": record.suspicious,
                "flags": record.flags,
                "validation_errors": record.validation_errors,
            },
            message="Row parsed, normalized, and stored with raw source JSON.",
        )

    batch.total_rows = len(parsed_records)
    batch.accepted_rows = len([record for record in created_records if not record.validation_errors])
    batch.suspicious_rows = len([record for record in created_records if record.suspicious])
    batch.rejected_rows = len([record for record in created_records if record.validation_errors])
    batch.error_summary = file_errors
    batch.status = IngestionBatch.Status.COMPLETED if not file_errors else IngestionBatch.Status.FAILED
    batch.save()

    AuditLog.objects.create(
        client=client,
        ingestion_batch=batch,
        action="BATCH_UPLOADED",
        actor=uploaded_by,
        after={
            "source_type": source_type,
            "total_rows": batch.total_rows,
            "suspicious_rows": batch.suspicious_rows,
            "rejected_rows": batch.rejected_rows,
        },
    )

    return Response(
        {
            "batch": IngestionBatchSerializer(batch).data,
            "summary": {
                "total_rows": batch.total_rows,
                "accepted_rows": batch.accepted_rows,
                "suspicious_rows": batch.suspicious_rows,
                "rejected_rows": batch.rejected_rows,
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def records(request):
    client = get_client(request)
    queryset = EmissionRecord.objects.filter(client=client).select_related("data_source", "ingestion_batch")

    review_status = request.query_params.get("review_status")
    if review_status:
        queryset = queryset.filter(review_status=review_status)
    if request.query_params.get("flagged") == "true":
        queryset = queryset.filter(suspicious=True)
    source_type = request.query_params.get("source_type")
    if source_type:
        queryset = queryset.filter(source_type=source_type)

    return Response(EmissionRecordSerializer(queryset[:200], many=True).data)


@api_view(["PATCH"])
@transaction.atomic
def review_record(request, pk):
    client = get_client(request)
    record = get_object_or_404(EmissionRecord.objects.select_for_update(), pk=pk, client=client)
    serializer = ReviewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    if serializer.validated_data["review_status"] == EmissionRecord.ReviewStatus.PENDING:
        return Response(
            {"detail": "Review action must approve or reject the record."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if record.review_status != EmissionRecord.ReviewStatus.PENDING:
        return Response(
            {"detail": "Only pending records can be reviewed."},
            status=status.HTTP_409_CONFLICT,
        )

    before = {
        "review_status": record.review_status,
        "locked_for_audit": record.locked_for_audit,
        "locked_at": record.locked_at.isoformat() if record.locked_at else None,
        "reviewed_by": record.reviewed_by,
        "reviewed_at": record.reviewed_at.isoformat() if record.reviewed_at else None,
    }
    record.review_status = serializer.validated_data["review_status"]
    record.reviewed_by = serializer.validated_data["reviewed_by"]
    record.reviewed_at = timezone.now()
    if record.review_status in {
        EmissionRecord.ReviewStatus.APPROVED,
        EmissionRecord.ReviewStatus.REJECTED,
    }:
        record.locked_for_audit = True
        record.locked_at = record.reviewed_at
    else:
        record.locked_for_audit = False
        record.locked_at = None
    record.save(
        update_fields=["review_status", "reviewed_by", "reviewed_at", "locked_for_audit", "locked_at"]
    )

    AuditLog.objects.create(
        client=record.client,
        emission_record=record,
        ingestion_batch=record.ingestion_batch,
        action=f"RECORD_{record.review_status}",
        actor=record.reviewed_by,
        before=before,
        after={
            "review_status": record.review_status,
            "locked_for_audit": record.locked_for_audit,
            "locked_at": record.locked_at.isoformat() if record.locked_at else None,
            "reviewed_by": record.reviewed_by,
            "reviewed_at": record.reviewed_at.isoformat(),
        },
        message=serializer.validated_data.get("note", ""),
    )
    return Response(EmissionRecordSerializer(record).data)


@api_view(["GET"])
def batches(request):
    client = get_client(request)
    queryset = IngestionBatch.objects.filter(client=client).select_related("data_source")
    return Response(IngestionBatchSerializer(queryset[:50], many=True).data)
