from pathlib import Path

from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from reporting.importers import run_import
from reporting.models import UploadBatch

SAMPLES = Path(__file__).resolve().parents[3] / "sample_data"


class Command(BaseCommand):
    help = "Create demo admin/viewer accounts and import the sample CSV files."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="hmis12345")

    def handle(self, *args, **options):
        password = options["password"]

        viewers, _ = Group.objects.get_or_create(name="Viewers")

        admin, created = User.objects.get_or_create(
            username="hmisadmin",
            defaults={"is_staff": True, "is_superuser": True, "email": "admin@example.com"},
        )
        if created:
            admin.set_password(password)
            admin.save()

        viewer, created = User.objects.get_or_create(
            username="hmisviewer", defaults={"email": "viewer@example.com"}
        )
        if created:
            viewer.set_password(password)
            viewer.save()
        viewer.groups.add(viewers)

        for dataset, filename in (
            (UploadBatch.FACILITIES, "facilities.csv"),
            (UploadBatch.PROGRAMS, "programs.csv"),
            (UploadBatch.DATA, "program_data.csv"),
        ):
            path = SAMPLES / filename
            upload = ContentFile(path.read_bytes(), name=filename)
            _batch, result = run_import(dataset, upload, user=admin)
            if result.ok:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{filename}: {result.created} created, {result.updated} updated"
                    )
                )
            else:
                self.stderr.write(f"{filename} failed:\n" + "\n".join(result.errors))

        self.stdout.write(
            self.style.SUCCESS(f"Accounts ready: hmisadmin / hmisviewer (password: {password})")
        )
