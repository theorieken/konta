from django.urls import path

from imports.views import (
    CommitImportView,
    ExportView,
    ImportPreviewView,
    ImportStatusView,
    ReclassifyView,
    TransactionImportView,
)

urlpatterns = [
    path("imports/transactions/", TransactionImportView.as_view(), name="import-transactions"),
    path("imports/reclassify/", ReclassifyView.as_view(), name="import-reclassify"),
    path("imports/status/", ImportStatusView.as_view(), name="import-status"),
    path("imports/export/", ExportView.as_view(), name="import-export"),
    path("imports/<uuid:file_id>/preview/", ImportPreviewView.as_view(), name="import-preview"),
    path("imports/<uuid:file_id>/commit/", CommitImportView.as_view(), name="import-commit"),
]
