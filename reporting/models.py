from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Facility(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    district = models.CharField(max_length=255, blank=True)
    facility_type = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "facilities"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Program(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Indicator(TimeStampedModel):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="indicators")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    unit = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["program__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["program", "code"], name="unique_indicator_per_program"),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class ReportingPeriod(TimeStampedModel):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    PERIOD_TYPES = [
        (MONTHLY, "Monthly"),
        (QUARTERLY, "Quarterly"),
        (ANNUAL, "Annual"),
    ]

    code = models.CharField(max_length=50, unique=True, help_text="e.g. 2025-01, 2025-Q1, 2025")
    name = models.CharField(max_length=255)
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPES, default=MONTHLY)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({"end_date": "End date must not be before start date."})


class UploadBatch(TimeStampedModel):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
    ]

    FACILITIES = "facilities"
    PROGRAMS = "programs"
    DATA = "data"
    DATASET_CHOICES = [
        (FACILITIES, "Facilities"),
        (PROGRAMS, "Programs"),
        (DATA, "Program data"),
    ]

    dataset = models.CharField(max_length=20, choices=DATASET_CHOICES)
    file_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="upload_batches",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    rows_created = models.PositiveIntegerField(default=0)
    rows_updated = models.PositiveIntegerField(default=0)
    error_log = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "upload batches"

    def __str__(self):
        return f"{self.get_dataset_display()} - {self.file_name}"


class DataRecord(TimeStampedModel):
    """A single reported value for a facility/program/indicator/period combination."""

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="records")
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="records")
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name="records")
    period = models.ForeignKey(ReportingPeriod, on_delete=models.CASCADE, related_name="records")
    value = models.DecimalField(max_digits=18, decimal_places=2)
    batch = models.ForeignKey(
        UploadBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="records"
    )

    class Meta:
        ordering = ["period__start_date", "facility__name", "indicator__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "program", "indicator", "period"],
                name="unique_record_per_facility_program_indicator_period",
            ),
        ]
        indexes = [
            models.Index(fields=["facility", "program", "period"]),
        ]

    def __str__(self):
        return f"{self.facility} / {self.indicator} / {self.period}: {self.value}"
