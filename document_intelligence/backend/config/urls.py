from django.urls import include, path

urlpatterns = [
    path("api/", include("api.urls")),
    path("mock/", include("mock_issuer_services.urls")),
]
