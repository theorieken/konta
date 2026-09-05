from django.urls import include, path
from rest_framework.routers import DefaultRouter

from finance.views import (
    AccountViewSet,
    CategoryViewSet,
    ContractViewSet,
    DashboardView,
    JobViewSet,
    LoanViewSet,
    PlanRegenerateView,
    TransactionViewSet,
)

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("categories", CategoryViewSet, basename="category")
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("contracts", ContractViewSet, basename="contract")
router.register("loans", LoanViewSet, basename="loan")
router.register("jobs", JobViewSet, basename="job")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("plan/regenerate/", PlanRegenerateView.as_view(), name="plan-regenerate"),
    path("", include(router.urls)),
]
