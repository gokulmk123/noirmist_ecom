# urls.py
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('',views.user_signup,name='user_signup'),

    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('adminlogout/', views.admin_logout, name='admin_logout'),
    path('home/',views.home,name='home'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('otp_verify/',views.otp_verify,name='otp_verify'),
    path('user_login/',views.user_login,name='user_login'),
    path('user_logout/', views.user_logout, name='user_logout'),
    path('admin_customers/', views.admin_customers_view, name='admin_customers'),

    path('admin_product/', views.admin_product, name='admin_product'),
    path('addproduct/', views.addproduct, name='addproduct'),
    path('toggle_product_status/<int:product_id>/', views.toggle_product_status, name='toggle_product_status'),
    path('delete_product/<int:product_id>/', views.delete_product, name='delete_product'),
    
    path('recover_product/<int:product_id>/', views.recover_product, name='recover_product'),


    path('admin_category/',views.admin_category,name='admin_category'),
    path('toggle_category_status/<int:category_id>/', views.toggle_category_status, name='toggle_category_status'),
    path('delete_category/<int:category_id>/', views.delete_category, name='delete_category'),


    path('admin_brand/',views.admin_brand,name='admin_brand'),
    path('toggle_brand_status/<int:brand_id>/', views.toggle_brand_status, name='toggle_brand_status'),
    path('delete_brand/<int:brand_id>/', views.delete_brand, name='delete_brand'),

    path('admin_banner/',views.admin_banner,name='admin_banner'),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
