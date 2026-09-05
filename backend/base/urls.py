from django.urls import include, path
from rest_framework.routers import DefaultRouter

from base.views import (
    FileViewSet,
    HouseholdViewSet,
    ObjectBatchView,
    ObjectSchemaView,
    ObjectView,
    SettingViewSet,
    TagViewSet,
    health,
)

router = DefaultRouter()
router.register("tags", TagViewSet, basename="tag")
router.register("settings", SettingViewSet, basename="setting")
router.register("files", FileViewSet, basename="file")
router.register("households", HouseholdViewSet, basename="household")

urlpatterns = [
    path("health/", health, name="health"),
    # Generic object access – the frontend's single entry point for drawers
    # and the /objects/[reference] page.
    path("objects/schema/", ObjectSchemaView.as_view(), name="object-schema"),
    path("objects/", ObjectBatchView.as_view(), name="object-batch"),
    path("objects/<str:reference>/", ObjectView.as_view(), name="object-detail"),
    path("", include(router.urls)),
]
