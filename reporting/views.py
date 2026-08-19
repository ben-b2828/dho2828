import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .forms import FilterForm, UploadForm
from .importers import TEMPLATE_HEADERS, ImportError_, run_import
from .models import DataRecord, Facility, Program, ReportingPeriod, UploadBatch

staff_required = user_passes_test(lambda user: user.is_active and user.is_staff)


def _selected(request, name, queryset):
    """Return the object selected in the querystring, ignoring unknown ids."""
    raw = request.GET.get(name, "").strip()
    if not raw.isdigit():
        return None
    return queryset.filter(pk=int(raw)).first()


def _filter_options():
    return (
        Facility.objects.filter(is_active=True),
        Program.objects.filter(is_active=True),
        ReportingPeriod.objects.all(),
    )


def _filtered_records(request):
    facilities, programs, periods = _filter_options()
    facility = _selected(request, "facility", facilities)
    program = _selected(request, "program", programs)
    period = _selected(request, "period", periods)

    records = DataRecord.objects.select_related("facility", "program", "indicator", "period")
    if facility:
        records = records.filter(facility=facility)
    if program:
        records = records.filter(program=program)
    if period:
        records = records.filter(period=period)
    return records, facility, program, period


@login_required
def dashboard(request):
    facilities, programs, periods = _filter_options()
    records, facility, program, period = _filtered_records(request)

    form = FilterForm(
        request.GET or None,
        facilities=facilities,
        programs=programs,
        periods=periods,
    )

    context = {
        "form": form,
        "records": records,
        "total": records.aggregate(total=Sum("value"))["total"],
        "selected_facility": facility,
        "selected_program": program,
        "selected_period": period,
        "query_string": request.GET.urlencode(),
    }
    return render(request, "reporting/dashboard.html", context)


@login_required
def export_csv(request):
    records, _facility, _program, _period = _filtered_records(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="report.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["facility_code", "facility", "program", "indicator", "unit", "period", "value"]
    )
    for record in records:
        writer.writerow(
            [
                record.facility.code,
                record.facility.name,
                record.program.name,
                record.indicator.name,
                record.indicator.unit,
                record.period.name,
                record.value,
            ]
        )
    return response


@login_required
@staff_required
def upload(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = form.cleaned_data["dataset"]
            try:
                batch, result = run_import(dataset, form.cleaned_data["file"], user=request.user)
            except ImportError_ as exc:
                messages.error(request, str(exc))
            else:
                if result.ok:
                    messages.success(
                        request,
                        f"Imported {batch.file_name}: {result.created} created, "
                        f"{result.updated} updated.",
                    )
                    return redirect("reporting:upload")
                messages.error(
                    request,
                    f"Import rejected — {len(result.errors)} problem(s) found, nothing was saved.",
                )
                return render(
                    request,
                    "reporting/upload.html",
                    {
                        "form": form,
                        "errors": result.errors[:50],
                        "batches": UploadBatch.objects.all()[:20],
                        "templates": TEMPLATE_HEADERS,
                    },
                )
    else:
        form = UploadForm()

    return render(
        request,
        "reporting/upload.html",
        {
            "form": form,
            "batches": UploadBatch.objects.all()[:20],
            "templates": TEMPLATE_HEADERS,
        },
    )


@login_required
@staff_required
def download_template(request, dataset):
    headers = TEMPLATE_HEADERS.get(dataset)
    if headers is None:
        return HttpResponse("Unknown data set", status=404)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{dataset}_template.csv"'
    csv.writer(response).writerow(headers)
    return response
