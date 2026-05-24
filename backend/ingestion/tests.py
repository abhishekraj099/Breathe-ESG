from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AuditLog, EmissionRecord

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"


class IngestionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def upload(self, source_type, filename):
        return self.client.post(
            "/api/upload/",
            {
                "source_type": source_type,
                "uploaded_by": "test.analyst",
                "file": SimpleUploadedFile(
                    filename,
                    (SAMPLE_DIR / filename).read_bytes(),
                    content_type="text/csv",
                ),
            },
            format="multipart",
            HTTP_HOST="localhost",
        )

    def test_sap_upload_preserves_raw_rows_and_flags_bad_data(self):
        response = self.upload("SAP_FUEL", "sap_fuel_procurement.csv")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["summary"]["total_rows"], 8)
        self.assertEqual(response.data["summary"]["suspicious_rows"], 5)
        self.assertTrue(
            any("duplicate_document_number" in record.flags for record in EmissionRecord.objects.all())
        )
        self.assertIn("Werks", EmissionRecord.objects.first().raw_data)

    def test_sap_upload_accepts_common_export_date_and_plant_variants(self):
        csv_content = (
            "Werks,Buchungsdatum,Bewegungsart,Material,Menge,Einheit,Kostenstelle,Dokument\n"
            "Plant 1000,05-01-2026,261,DIESEL-500,1200,L,CC-OPS-DEL,4900010001\n"
            "2000.0,01/07/2026,261,PETROL-91,850,LTR,CC-FLEET-MUM,4900010002\n"
        ).encode()

        response = self.client.post(
            "/api/upload/",
            {
                "source_type": "SAP_FUEL",
                "uploaded_by": "test.analyst",
                "file": SimpleUploadedFile(
                    "sap_variant.csv",
                    csv_content,
                    content_type="text/csv",
                ),
            },
            format="multipart",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["summary"]["total_rows"], 2)
        self.assertEqual(response.data["summary"]["suspicious_rows"], 0)
        all_flags = [flag for record in EmissionRecord.objects.all() for flag in record.flags]
        self.assertNotIn("unknown_plant_code", all_flags)
        self.assertNotIn("invalid_posting_date", all_flags)

    def test_utility_and_travel_uploads_map_scopes(self):
        utility_response = self.upload("UTILITY_ELECTRICITY", "utility_electricity.csv")
        travel_response = self.upload("CORPORATE_TRAVEL", "corporate_travel.csv")

        self.assertEqual(utility_response.status_code, 201)
        self.assertEqual(travel_response.status_code, 201)
        self.assertTrue(EmissionRecord.objects.filter(scope="SCOPE_2").exists())
        self.assertTrue(EmissionRecord.objects.filter(scope="SCOPE_3").exists())
        self.assertTrue(
            any(
                "missing_international_or_unknown_distance" in record.flags
                for record in EmissionRecord.objects.all()
            )
        )

    def test_review_action_updates_record_and_writes_audit_log(self):
        self.upload("SAP_FUEL", "sap_fuel_procurement.csv")
        record = EmissionRecord.objects.filter(review_status="PENDING").first()

        response = self.client.patch(
            f"/api/records/{record.id}/review/",
            {"review_status": "APPROVED", "reviewed_by": "lead.analyst"},
            format="json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.review_status, "APPROVED")
        self.assertTrue(record.locked_for_audit)
        self.assertIsNotNone(record.locked_at)
        self.assertTrue(AuditLog.objects.filter(action="RECORD_APPROVED").exists())
