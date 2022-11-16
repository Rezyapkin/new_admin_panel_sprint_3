from django.db.models import Q
from django.conf import settings
from django.http import JsonResponse
from django.contrib.postgres.aggregates import ArrayAgg
from django.views.generic.list import BaseListView
from django.views.generic.detail import BaseDetailView

from movies.models import FilmWork, PersonFilmWork


class MoviesApiMixin:
    model = FilmWork
    http_method_names = ["get"]
    movies_simple_fields_in_result = [
        "id",
        "title",
        "description",
        "creation_date",
        "rating",
        "type",
    ]
    movies_roles_in_result = {
        "actors": PersonFilmWork.Roles.ACTOR,
        "directors": PersonFilmWork.Roles.DIRECTOR,
        "writes": PersonFilmWork.Roles.WRITER,
    }

    def get_queryset(self):
        queryset = super().get_queryset().values(*self.movies_simple_fields_in_result)
        return queryset.annotate(genres=ArrayAgg("genres__name", distinct=True), **{
            field_name: ArrayAgg("persons__full_name", distinct=True, filter=Q(personfilmwork__role=role))
            for field_name, role in self.movies_roles_in_result.items()
        })

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(context)


class MoviesListApi(MoviesApiMixin, BaseListView):
    paginate_by = settings.MOVIES_PAGE_SIZE

    def get_context_data(self, *, object_list=None, **kwargs):
        paginator, page, queryset, is_paginated = self.paginate_queryset(self.get_queryset(), self.paginate_by)

        context = {
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "prev": page.previous_page_number() if page.has_previous() else None,
            "next": page.next_page_number() if page.has_next() else None,
            "results": list(queryset),
        }
        return context


class MoviesDetailApi(MoviesApiMixin, BaseDetailView):
    def get_context_data(self, **kwargs):
        return self.object
