"""
URL configuration for drm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from alsafi_drm import views

urlpatterns = [
    path("", views.home, name="home"),
    path("chat/", views.chat, name="chat"),
    path("dashboard/", views.home, name="home"),
    path("api/chat/", views.chat_api),
    path("lcr/", views.lcr, name="lcr"),
    path("assets/", views.get_assets, name="assets"),
    path("liabilities/", views.get_liabilities, name="liabilities"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path('liquidity/', views.get_liquidity, name='liquidity'),
    path('liquidity/assets/', views.tab_assets, name='tab_assets'),
    path('liquidity/liabilities/', views.tab_liabilities, name='tab_liabilities'),
    path('liquidity/bank_buffers/', views.get_bank_buffers, name='tab_bank_buffers'),
    path('clear-cache/', views.clear_cache, name='clear_cache'),
]
