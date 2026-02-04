from django.urls import path

from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('inscription/', views.register, name='register'),
    path('inscription/merci/', views.register_success, name='register_success'),
    path('connexion/', views.login_view, name='login'),
    path('connexion/otp/', views.otp_verify, name='otp_verify'),
    path('deconnexion/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profil/', views.profile, name='profile'),
    path('profil/otp/', views.password_otp, name='password_otp'),
    path('beneficiaires/', views.beneficiaries, name='beneficiaries'),
    path('virements/nouveau/', views.transfer_create, name='transfer_create'),
    path('virements/', views.transfers, name='transfers'),
    path('virements/<int:transfer_id>/', views.transfer_detail, name='transfer_detail'),
    path('virements/<int:transfer_id>/pdf/', views.download_transfer_pdf, name='transfer_pdf'),
    path('rib/pdf/', views.download_rib_pdf, name='rib_pdf'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/supprimer/<int:notification_id>/', views.notification_delete, name='notification_delete'),
    path('notifications/supprimer-tout/', views.notifications_clear, name='notifications_clear'),
    path('contact/', views.contact, name='contact'),
    path('parametres/', views.parameters, name='parameters'),
    path('support/', views.support_chat, name='support_chat'),
]
