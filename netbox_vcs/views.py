from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from core.models import Job
from netbox.views import generic
from utilities.exceptions import AbortTransaction
from utilities.views import ViewTab, register_model_view

from . import forms, tables
from .models import Context, ObjectChange


class ContextListView(generic.ObjectListView):
    queryset = Context.objects.all()
    # filterset = filtersets.ContextFilterSet
    # filterset_form = forms.ContextFilterForm
    table = tables.ContextTable


@register_model_view(Context)
class ContextView(generic.ObjectView):
    queryset = Context.objects.all()

    def get_extra_context(self, request, instance):
        return {
            'rebase_form': forms.RebaseContextForm(),
            'apply_form': forms.ApplyContextForm(),
        }


@register_model_view(Context, 'edit')
class ContextEditView(generic.ObjectEditView):
    queryset = Context.objects.all()
    form = forms.ContextForm


@register_model_view(Context, 'delete')
class ContextDeleteView(generic.ObjectDeleteView):
    queryset = Context.objects.all()
    default_return_url = 'plugins:netbox_vcs:context_list'


@register_model_view(Context, 'diff')
class ContextDiffView(generic.ObjectView):
    queryset = Context.objects.all()
    template_name = 'netbox_vcs/context_diff.html'
    tab = ViewTab(
        label=_('Diff'),
        permission='netbox_vcs.view_context'
    )

    def get_extra_context(self, request, instance):
        return {
            'diff': instance.diff()
        }


def _get_change_count(obj):
    return ObjectChange.objects.using(obj.connection_name).count()


@register_model_view(Context, 'replay')
class ContextReplayView(generic.ObjectView):
    queryset = Context.objects.all()
    template_name = 'netbox_vcs/context_replay.html'
    tab = ViewTab(
        label=_('Replay'),
        badge=_get_change_count,
        permission='netbox_vcs.view_context'
    )

    def get_extra_context(self, request, instance):
        replay = []
        for change in ObjectChange.objects.using(instance.connection_name).order_by('time'):
            replay.append({
                'model': change.changed_object_type.model_class(),
                'change': change,
                'data': change.diff(),
            })

        return {
            'replay': replay
        }


@register_model_view(Context, 'rebase')
class ContextRebaseView(generic.ObjectView):
    queryset = Context.objects.all()

    def post(self, request, **kwargs):
        context = self.get_object(**kwargs)
        form = forms.RebaseContextForm(request.POST)

        if form.is_valid():
            # Enqueue a background job to rebase the Context
            Job.enqueue(
                import_string('netbox_vcs.jobs.rebase_context'),
                instance=context,
                name='Rebase context',
                commit=form.cleaned_data['commit']
            )
            messages.success(request, f"Rebasing of context {context} in progress")

        return redirect(context.get_absolute_url())


@register_model_view(Context, 'apply')
class ContextApplyView(generic.ObjectView):
    queryset = Context.objects.all()

    def post(self, request, **kwargs):
        context = self.get_object(**kwargs)
        form = forms.ApplyContextForm(request.POST)

        if form.is_valid():
            try:
                context.apply(form.cleaned_data['commit'])
                messages.success(request, f"Applied context {context}!")
                return redirect(context.get_absolute_url())
            except ValidationError as e:
                messages.error(self.request, ", ".join(e.messages))
            except AbortTransaction:
                messages.info(request, f"Applied & rolled back context {context}")

        return redirect(context.get_absolute_url())
