from api.views import (CustomUserViewSet, IngredientViewSet, RecipeViewSet,
                       TagViewSet)
from django.urls import include, path
from rest_framework import routers

app_name = 'api'

router_v1 = routers.DefaultRouter()
router_v1.register(
    prefix=r'users',
    viewset=CustomUserViewSet,
    basename='users'
)

router_v1.register(prefix='tags', viewset=TagViewSet, basename='tags')
router_v1.register(
    prefix='ingredients', viewset=IngredientViewSet, basename='ingredients')
router_v1.register(
    prefix='recipes', viewset=RecipeViewSet, basename='recipes')

urlpatterns = [
    path('', include(router_v1.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
