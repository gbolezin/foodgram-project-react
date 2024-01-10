from django.urls import include, path
from rest_framework import routers

from api.views import (CustomUserViewSet, FavoriteViewSet, IngredientViewSet,
                       RecipeViewSet, SubscriptionViewSet, TagViewSet)

app_name = 'api'

router_v1 = routers.DefaultRouter()
router_v1.register(
    prefix='users',
    viewset=CustomUserViewSet,
    basename='users'
)
router_v1.register(
    prefix=r'users/(?P<user_id>\d+)/subscribe',
    viewset=SubscriptionViewSet,
    basename='subscribe'
)
router_v1.register(
    prefix=r'recipes/(?P<recipe_id>\d+)/favorite',
    viewset=FavoriteViewSet,
    basename='favorite'
)
router_v1.register(
    prefix=r'recipes/(?P<recipe_id>\d+)/shopping_cart',
    viewset=FavoriteViewSet,
    basename='favorite'
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
