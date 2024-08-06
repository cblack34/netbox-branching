from django import forms
from django.utils.translation import gettext_lazy as _

from netbox_branching.models import ChangeDiff

__all__ = (
    'BranchActionForm',
)


class BranchActionForm(forms.Form):
    pk = forms.ModelMultipleChoiceField(
        queryset=ChangeDiff.objects.all()
    )
    commit = forms.BooleanField(
        required=False,
        initial=True,
        help_text=_('Apply changes (uncheck to do a dry-run)')
    )

    def __init__(self, branch, *args, **kwargs):
        self.branch = branch
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()

        # Verify that any ChangeDiffs which have conflicts have been acknowledged
        conflicted_diffs = ChangeDiff.objects.filter(
            branch=self.branch,
            conflicts__isnull=False
        )
        selected_diffs = self.cleaned_data.get('pk', list())
        if conflicted_diffs and not set(conflicted_diffs).issubset(selected_diffs):
            raise forms.ValidationError(_("All conflicts must be acknowledged in order to merge the branch."))

        return self.cleaned_data
