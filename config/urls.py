from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.home, name='home'),
    path('inicio/', core_views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('usuarios/', core_views.UsuarioListView.as_view(), name='usuarios_listar'),
    path('usuarios/nuevo/', core_views.UsuarioCreateView.as_view(), name='usuarios_crear'),
    path('usuarios/<int:pk>/editar/', core_views.UsuarioUpdateView.as_view(), name='usuarios_editar'),
    path('usuarios/<int:pk>/eliminar/', core_views.UsuarioDeleteView.as_view(), name='usuarios_eliminar'),
    path('medicos/', include('medicos.urls')),
    path('boxes/', include('boxes.urls')),
    path('agenda/', include('agenda.urls')),
    path('disponibilidad/', include('disponibilidad.urls')),
]
