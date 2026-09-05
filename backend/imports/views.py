"""Staged transaction imports and portable household backup endpoints."""

from __future__ import annotations

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from django.http import FileResponse
from django.utils.text import slugify
from rest_framework.response import Response
from rest_framework.views import APIView

from base.events import broadcast_object
from base.households import active_household
from base.models import File
from base.permissions import IsAuthenticatedHousehold
from base.queue import enqueue
from base.serializers import FileSerializer
from imports.serializers import (
    CommitImportSerializer,
    ReclassifySerializer,
    TransactionImportSerializer,
)


class TransactionImportView(APIView):
    """
    `POST /api/imports/transactions/` (multipart: file, account)

    Stores the CSV in MinIO and queues the background import. The response is
    the `File` object – the frontend then follows its `status` over the
    WebSocket or by polling `/api/files/{id}/`.
    """

    permission_classes = [IsAuthenticatedHousehold]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request) -> Response:
        serializer = TransactionImportSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        file_obj = serializer.save()
        broadcast_object(file_obj, "created")

        from imports.tasks import analyse_import_file

        queued = enqueue(analyse_import_file, str(file_obj.pk))
        file_obj.refresh_from_db()
        return Response(
            {"queued": queued, "file": FileSerializer(file_obj, context={"request": request}).data},
            status=status.HTTP_201_CREATED,
        )

    def get(self, request) -> Response:
        """Recent imports, newest first."""
        household = active_household(request.user)
        files = File.objects.filter(
            household=household,
            purpose__in=[File.Purpose.TRANSACTION_IMPORT, File.Purpose.BACKUP_IMPORT],
        ).select_related("account")[:50]
        return Response(
            {"results": FileSerializer(files, many=True, context={"request": request}).data}
        )


class ReclassifyView(APIView):
    """`POST /api/imports/reclassify/` – run the classifier again."""

    permission_classes = [IsAuthenticatedHousehold]

    def post(self, request) -> Response:
        serializer = ReclassifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from imports.tasks import reclassify_transactions

        ids = [str(item) for item in data.get("transactions", [])]
        household = active_household(request.user)
        queued = enqueue(
            reclassify_transactions,
            ids or None,
            data.get("only_review", True),
            str(household.pk),
        )
        return Response({"queued": queued})


class ImportPreviewView(APIView):
    permission_classes = [IsAuthenticatedHousehold]

    def get(self, request, file_id: str) -> Response:
        household = active_household(request.user)
        file_obj = File.objects.filter(pk=file_id, household=household).first()
        if file_obj is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("Import nicht gefunden.")
        rows = list((file_obj.processed_data or {}).get("rows", []))
        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            page_size = max(1, min(int(request.query_params.get("page_size", 20)), 100))
        except ValueError:
            page, page_size = 1, 20
        start = (page - 1) * page_size
        return Response(
            {
                "count": len(rows),
                "page": page,
                "page_size": page_size,
                "results": rows[start:start + page_size],
            }
        )


class CommitImportView(APIView):
    permission_classes = [IsAuthenticatedHousehold]

    def post(self, request, file_id: str) -> Response:
        serializer = CommitImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        household = active_household(request.user)
        file_obj = File.objects.filter(pk=file_id, household=household).first()
        if file_obj is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("Import nicht gefunden.")
        if file_obj.status != File.Status.READY:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": "Dieser Import wurde bereits gestartet."})
        restore = serializer.validated_data["confirm_restore"]
        if file_obj.purpose == File.Purpose.BACKUP_IMPORT and not restore:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"confirm_restore": "Die vollständige Wiederherstellung muss bestätigt werden."}
            )
        from imports.tasks import commit_import

        file_obj.mark(
            File.Status.PROCESSING,
            stats={**file_obj.stats, "stage": "queued"},
        )
        broadcast_object(file_obj, "updated")
        queued = enqueue(commit_import, str(file_obj.pk), str(request.user.pk), restore)
        file_obj.refresh_from_db()
        return Response(
            {
                "queued": queued,
                "file": FileSerializer(file_obj, context={"request": request}).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ExportView(APIView):
    permission_classes = [IsAuthenticatedHousehold]

    def get(self, request):
        from imports.services.backup import build_backup

        household = active_household(request.user)
        filename = f"{slugify(household.name) or 'haushalt'}.fin"
        return FileResponse(
            build_backup(household),
            as_attachment=True,
            filename=filename,
            content_type="application/x-fin-household",
        )


class ImportStatusView(APIView):
    """`GET /api/imports/status/` – small summary for the settings page."""

    permission_classes = [IsAuthenticatedHousehold]

    def get(self, request) -> Response:
        from django.db.models import Count

        from base.models import Setting
        from base.settings_registry import OPENAI_API_KEY, OPENAI_MODEL
        from finance.models import Transaction

        household = active_household(request.user)
        counts = File.objects.filter(
            household=household,
            purpose__in=[File.Purpose.TRANSACTION_IMPORT, File.Purpose.BACKUP_IMPORT],
        ).values(
            "status"
        ).annotate(total=Count("id"))
        return Response(
            {
                "files": {row["status"]: row["total"] for row in counts},
                "needs_review": Transaction.objects.filter(
                    account__household=household, needs_review=True
                ).count(),
                "ai_configured": bool(
                    (Setting.get(OPENAI_API_KEY, "", household=household) or "").strip()
                ),
                "model": Setting.get(OPENAI_MODEL, "", household=household),
            }
        )
