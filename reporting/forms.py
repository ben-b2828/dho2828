from django import forms

from .models import UploadBatch

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class UploadForm(forms.Form):
    dataset = forms.ChoiceField(choices=UploadBatch.DATASET_CHOICES, label="Data set")
    file = forms.FileField(label="CSV or Excel file")

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        name = uploaded.name.lower()
        if not name.endswith((".csv", ".xlsx", ".xlsm")):
            raise forms.ValidationError("Upload a .csv or .xlsx file.")
        if uploaded.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError("File is larger than the 10 MB limit.")
        return uploaded


class FilterForm(forms.Form):
    """Viewer filters. Choices are populated from what the admin has uploaded."""

    facility = forms.ChoiceField(required=False)
    program = forms.ChoiceField(required=False)
    period = forms.ChoiceField(required=False)

    def __init__(self, *args, facilities=None, programs=None, periods=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["facility"].choices = [("", "All facilities")] + [
            (str(facility.pk), str(facility)) for facility in facilities or []
        ]
        self.fields["program"].choices = [("", "All programs")] + [
            (str(program.pk), str(program)) for program in programs or []
        ]
        self.fields["period"].choices = [("", "All periods")] + [
            (str(period.pk), str(period)) for period in periods or []
        ]
