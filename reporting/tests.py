import io
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from .importers import run_import
from .models import DataRecord, Facility, Indicator, Program, ReportingPeriod, UploadBatch

FACILITIES_CSV = b"""code,name,district,facility_type,is_active
FAC001,Kasungu District Hospital,Kasungu,District Hospital,true
FAC002,Chulu Health Centre,Kasungu,Health Centre,true
"""

PROGRAMS_CSV = b"""code,name,description,is_active
PRG-HIV,HIV/AIDS,HIV services,true
PRG-TB,Tuberculosis,TB services,true
"""

DATA_CSV = b"""facility_code,program_code,indicator_code,indicator_name,indicator_unit,period_code,period_name,period_type,period_start,period_end,value
FAC001,PRG-HIV,HIV-TST,Clients tested for HIV,clients,2025-01,January 2025,monthly,2025-01-01,2025-01-31,412
FAC002,PRG-HIV,HIV-TST,Clients tested for HIV,clients,2025-01,January 2025,monthly,2025-01-01,2025-01-31,188
FAC001,PRG-TB,TB-NOT,TB cases notified,cases,2025-02,February 2025,monthly,2025-02-01,2025-02-28,19
"""


def upload_file(content: bytes, name: str) -> ContentFile:
    return ContentFile(content, name=name)


class ImportTests(TestCase):
    def import_baseline(self):
        run_import(UploadBatch.FACILITIES, upload_file(FACILITIES_CSV, "facilities.csv"))
        run_import(UploadBatch.PROGRAMS, upload_file(PROGRAMS_CSV, "programs.csv"))
        return run_import(UploadBatch.DATA, upload_file(DATA_CSV, "data.csv"))

    def test_imports_facilities_programs_and_data(self):
        batch, result = self.import_baseline()

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(batch.status, UploadBatch.COMPLETED)
        self.assertEqual(Facility.objects.count(), 2)
        self.assertEqual(Program.objects.count(), 2)
        self.assertEqual(Indicator.objects.count(), 2)
        self.assertEqual(ReportingPeriod.objects.count(), 2)
        self.assertEqual(DataRecord.objects.count(), 3)

        record = DataRecord.objects.get(
            facility__code="FAC001", program__code="PRG-HIV", period__code="2025-01"
        )
        self.assertEqual(record.value, Decimal("412"))

    def test_reupload_updates_existing_values(self):
        self.import_baseline()
        revised = DATA_CSV.replace(b",412", b",500")

        _batch, result = run_import(UploadBatch.DATA, upload_file(revised, "data.csv"))

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(DataRecord.objects.count(), 3)
        record = DataRecord.objects.get(
            facility__code="FAC001", program__code="PRG-HIV", period__code="2025-01"
        )
        self.assertEqual(record.value, Decimal("500"))

    def test_unknown_facility_rejects_whole_file(self):
        self.import_baseline()
        bad = DATA_CSV.replace(b"FAC002", b"NOPE")

        batch, result = run_import(UploadBatch.DATA, upload_file(bad, "data.csv"))

        self.assertFalse(result.ok)
        self.assertEqual(batch.status, UploadBatch.FAILED)
        self.assertIn("unknown facility_code 'NOPE'", result.errors[0])
        self.assertEqual(DataRecord.objects.count(), 3)

    def test_non_numeric_value_is_reported(self):
        run_import(UploadBatch.FACILITIES, upload_file(FACILITIES_CSV, "facilities.csv"))
        run_import(UploadBatch.PROGRAMS, upload_file(PROGRAMS_CSV, "programs.csv"))
        bad = DATA_CSV.replace(b",412", b",abc")

        _batch, result = run_import(UploadBatch.DATA, upload_file(bad, "data.csv"))

        self.assertFalse(result.ok)
        self.assertIn("is not a number", result.errors[0])
        self.assertEqual(DataRecord.objects.count(), 0)

    def test_missing_column_is_reported(self):
        _batch, result = run_import(
            UploadBatch.FACILITIES, upload_file(b"code,district\nFAC001,Kasungu\n", "f.csv")
        )

        self.assertFalse(result.ok)
        self.assertIn("Missing required column(s): name", result.errors[0])
        self.assertEqual(Facility.objects.count(), 0)

    def test_excel_upload(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["code", "name", "district", "facility_type", "is_active"])
        sheet.append(["FAC009", "Mponela Health Centre", "Dowa", "Health Centre", "yes"])
        buffer = io.BytesIO()
        workbook.save(buffer)

        _batch, result = run_import(
            UploadBatch.FACILITIES, upload_file(buffer.getvalue(), "facilities.xlsx")
        )

        self.assertTrue(result.ok, result.errors)
        self.assertTrue(Facility.objects.filter(code="FAC009", is_active=True).exists())


class ViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", password="pw", is_staff=True)
        self.viewer = User.objects.create_user("viewer", password="pw")
        run_import(UploadBatch.FACILITIES, upload_file(FACILITIES_CSV, "facilities.csv"))
        run_import(UploadBatch.PROGRAMS, upload_file(PROGRAMS_CSV, "programs.csv"))
        run_import(UploadBatch.DATA, upload_file(DATA_CSV, "data.csv"))

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("reporting:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_upload_page_is_staff_only(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("reporting:upload"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("reporting:upload")).status_code, 200)

    def test_filters_return_only_the_selected_combination(self):
        self.client.force_login(self.viewer)
        facility = Facility.objects.get(code="FAC001")
        program = Program.objects.get(code="PRG-HIV")
        period = ReportingPeriod.objects.get(code="2025-01")

        response = self.client.get(
            reverse("reporting:dashboard"),
            {"facility": facility.pk, "program": program.pk, "period": period.pk},
        )

        records = list(response.context["records"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].value, Decimal("412"))
        self.assertEqual(response.context["total"], Decimal("412"))

    def test_filter_choices_come_from_uploaded_data(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("reporting:dashboard"))

        facility_labels = [label for _value, label in response.context["form"].fields["facility"].choices]
        self.assertIn("Kasungu District Hospital (FAC001)", facility_labels)
        period_labels = [label for _value, label in response.context["form"].fields["period"].choices]
        self.assertIn("January 2025", period_labels)

    def test_inactive_facility_is_not_selectable(self):
        Facility.objects.filter(code="FAC002").update(is_active=False)
        self.client.force_login(self.viewer)
        hidden = Facility.objects.get(code="FAC002")

        response = self.client.get(reverse("reporting:dashboard"), {"facility": hidden.pk})

        self.assertIsNone(response.context["selected_facility"])
        self.assertEqual(len(response.context["records"]), 3)

    def test_export_respects_filters(self):
        self.client.force_login(self.viewer)
        period = ReportingPeriod.objects.get(code="2025-02")

        response = self.client.get(reverse("reporting:export"), {"period": period.pk})

        body = response.content.decode()
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("TB cases notified", body)
        self.assertNotIn("Clients tested for HIV", body)

    def test_admin_can_upload_through_the_form(self):
        self.client.force_login(self.admin)
        extra = (
            b"code,name,district,facility_type,is_active\n"
            b"FAC010,Nkhotakota District Hospital,Nkhotakota,District Hospital,true\n"
        )

        response = self.client.post(
            reverse("reporting:upload"),
            {"dataset": UploadBatch.FACILITIES, "file": upload_file(extra, "facilities.csv")},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Facility.objects.filter(code="FAC010").exists())
