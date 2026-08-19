from django.contrib import admin

from .models import DataRecord, Facility, Indicator, Program, ReportingPeriod, UploadBatch


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "district", "facility_type", "is_active")
    list_filter = ("is_active", "district", "facility_type")
    search_fields = ("code", "name", "district")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "program", "unit")
    list_filter = ("program",)
    search_fields = ("code", "name")


@admin.register(ReportingPeriod)
class ReportingPeriodAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "period_type", "start_date", "end_date")
    list_filter = ("period_type",)
    search_fields = ("code", "name")


@admin.register(UploadBatch)
class UploadBatchAdmin(admin.ModelAdmin):
    list_display = ("file_name", "dataset", "status", "rows_created", "rows_updated", "created_at")
    list_filter = ("dataset", "status")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DataRecord)
class DataRecordAdmin(admin.ModelAdmin):
    list_display = ("facility", "program", "indicator", "period", "value")
    list_filter = ("program", "period", "facility")
    search_fields = ("facility__name", "indicator__name")
