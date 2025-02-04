from django.views.generic import DetailView, ListView, UpdateView
from main_app.models import Sequence
from django.db.models import Q
from main_app.forms import SequenceEditForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from main_app.permissions import (
    user_can_view_sequence,
    user_can_edit_sequences,
)


class SequenceDetailView(DetailView):
    """
    Displays a single Sequence object. Accessed with ``sequences/<int:pk>``
    """

    model = Sequence
    context_object_name = "sequence"
    template_name = "sequence_detail.html"

    def get_context_data(self, **kwargs):
        sequence = self.get_object()
        user = self.request.user

        # if the sequence's source isn't published,
        # only logged-in users should be able to view the sequence's detail page
        if not user_can_view_sequence(user, sequence):
            raise PermissionDenied()

        context = super().get_context_data(**kwargs)
        context["concordances"] = (
            Sequence.objects.filter(cantus_id=sequence.cantus_id)
            .select_related("source")
            .order_by("siglum")
        )
        context["user_can_edit_sequence"] = user_can_edit_sequences(user, sequence)
        return context


class SequenceListView(ListView):
    """
    Displays a list of Sequence objects. Accessed with ``sequences/``
    """

    paginate_by = 100
    context_object_name = "sequences"
    template_name = "sequence_list.html"

    def get_queryset(self):
        queryset = Sequence.objects.select_related("source")
        display_unpublished = self.request.user.is_authenticated
        if display_unpublished:
            q_obj_filter = Q()
        else:
            q_obj_filter = Q(source__published=True)

        if self.request.GET.get("incipit"):
            incipit = self.request.GET.get("incipit")
            q_obj_filter &= Q(incipit__icontains=incipit)
        if self.request.GET.get("siglum"):
            siglum = self.request.GET.get("siglum")
            q_obj_filter &= Q(siglum__icontains=siglum)
        if self.request.GET.get("cantus_id"):
            cantus_id = self.request.GET.get("cantus_id")
            q_obj_filter &= Q(cantus_id__icontains=cantus_id)

        return queryset.filter(q_obj_filter).order_by("siglum", "s_sequence")


class SequenceEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    template_name = "sequence_edit.html"
    model = Sequence
    form_class = SequenceEditForm
    pk_url_kwarg = "sequence_id"

    def form_valid(self, form):
        form.instance.last_updated_by = self.request.user
        messages.success(
            self.request,
            "Sequence updated successfully!",
        )
        return super().form_valid(form)

    def test_func(self):
        user = self.request.user
        sequence = self.get_object()
        return user_can_edit_sequences(user, sequence)
