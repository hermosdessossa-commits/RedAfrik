"""Pagination par défaut de l'API RedAfrik."""

from rest_framework.pagination import PageNumberPagination


class PaginationStandard(PageNumberPagination):
    """Pagination par numéro de page, configurable via le paramètre page_size."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
