from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DefaultPagination(PageNumberPagination):
    """`?page=2&page_size=100` – `page_size=0` returns everything (bounded)."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000

    def get_page_size(self, request):
        raw = request.query_params.get(self.page_size_query_param)
        if raw in ("0", "all"):
            return self.max_page_size
        return super().get_page_size(request)

    def get_paginated_response(self, data) -> Response:
        return Response(
            {
                "count": self.page.paginator.count,
                "pages": self.page.paginator.num_pages,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
