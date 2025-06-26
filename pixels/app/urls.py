from django.urls import include, path

from app import views


urlpatterns = [
    path('', views.index, name='index'),  
    path('map/', views.map, name='map'),
    path('api/save-cells/', views.save_selected_cells, name='save_selected_cells')
]
