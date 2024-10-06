from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('FoodHitchApp.urls')),
    path('paypal/', include('paypal.standard.ipn.urls')),  # Added PayPal IPN URL
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
