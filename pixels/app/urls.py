from django.urls import include, path
from django.contrib.auth import views as auth_views
from app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),  
    path('map/', views.map, name='map'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='app/logout.html'), name='logout'),
    path('api/save-selection', views.save_selected_cells, name='save-selection'),
    path('api/purchase', views.purchase_area, name='purchase'),
    path('api/purchased-cells', views.purchased_cells_view, name='purchased-cells'),
    path('api/my-purchases', views.my_purchases, name='my-purchases'),
    path('purchase/', views.purchase_page, name='purchase_page'),
    path('api/complete-purchase', views.complete_purchase, name='complete_purchase'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)