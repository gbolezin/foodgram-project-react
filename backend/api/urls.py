from django.urls import include, path
from rest_framework import routers
from api.views import (CustomUserViewSet, IngredientViewSet, RecipeViewSet,
                       TagViewSet)

app_name = 'api'

router_v1 = routers.DefaultRouter()
router_v1.register(
    prefix='users',
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
