from django.urls import path, include
from . import views 
  
urlpatterns = [ 
    path('menu-items', views.MenuItemView.as_view()),
    path('menu-items/<int:pk>', views.SingleMenuItemView.as_view()),
    path('cart/menu-items', views.CartView.as_view()),
    path('orders', views.OrderView.as_view()),
    path('orders/<int:pk>', views.SingleOrderView.as_view()),
    path('users/', include('djoser.urls')), 
    path('groups/manager/users', views.Managers.as_view()),
	path('groups/manager/users/<int:pk>', views.ManagerDelete.as_view()),
    path('groups/delivery-crew/users', views.DeliveryCrews.as_view()),
	path('groups/delivery-crew/users/<int:pk>', views.DeliveryCrewDelete.as_view()),
] 