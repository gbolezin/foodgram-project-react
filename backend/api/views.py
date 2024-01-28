import csv

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (CustomUserSerializer, FavoriteSerializer,
                             IngredientSerializer,
                             RecipeCreateUpdateSerializer,
                             RecipeListRetrieveSerializer,
                             ShoppingCartSerializer,
                             SubscriptionCreateDeleteSerializer,
                             SubscriptionListSerializer, TagListSerializer)
from recipes.models import (Favorite, Ingredient, IngredientsRecipes, Recipe,
                            ShoppingCart, Subscription, Tag, User)


class CustomPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'


class CustomUserViewSet(UserViewSet):
    """ Вьюсет пользователя """
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )

    def get_permissions(self):
        if self.action == 'me':
            return (IsAuthenticated(),)
        return UserViewSet.get_permissions(self)

    @action(
        methods=['get'],
        detail=False,
        url_path='subscriptions',
        permission_classes=(IsAuthenticated,)
    )
    def current_user_subscriptions(self, request):
        if request.method == 'GET':
            authors = User.objects.filter(
                id__in=Subscription.objects.filter(
                    follower=request.user).values('author_id')
            )
            page = self.paginate_queryset(authors)
            serializer = SubscriptionListSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

    @action(
        methods=['post'],
        detail=True,
        url_path='subscribe',
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=self.kwargs.get('id'))
        follower = request.user
        subscription = {}
        subscription['author'] = author.id
        subscription['follower'] = follower.id
        serializer = SubscriptionCreateDeleteSerializer(
            data=subscription,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def subscribe_delete(self, request, id=None):
        author = get_object_or_404(User, id=self.kwargs.get('id'))
        follower = request.user
        subscription_count, subscription = Subscription.objects.filter(
            author=author, follower=follower
        ).delete()
        if not subscription_count:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ Вьюсет Тэгов """
    queryset = Tag.objects.all()
    serializer_class = TagListSerializer
    http_method_names = ['get']
    permission_classes = (IsAuthenticatedOrReadOnly, )
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ Вьюсет Ингредиентов """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    http_method_names = ['get']
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    pagination_class = None
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """ Вьюсет Рецептов """
    queryset = Recipe.objects.all()
    http_method_names = ['get', 'post', 'patch', 'delete']
    permission_classes = (IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly,)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return RecipeListRetrieveSerializer
        return RecipeCreateUpdateSerializer

    @action(
        methods=['post'],
        detail=True,
        url_path='favorite',
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        favorite = {}
        favorite['recipe'] = self.kwargs.get('pk')
        favorite['user'] = request.user.id
        serializer = FavoriteSerializer(data=favorite)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @favorite.mapping.delete
    def favorite_delete(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('pk'))
        user = request.user
        favorite_count, favorite = Favorite.objects.filter(
            user=user, recipe=recipe
        ).delete()
        if not favorite_count:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['post'],
        detail=True,
        url_path='shopping_cart',
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        shopping_cart = {}
        shopping_cart['recipe'] = self.kwargs.get('pk')
        shopping_cart['user'] = request.user.id
        serializer = ShoppingCartSerializer(data=shopping_cart)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @shopping_cart.mapping.delete
    def shopping_cart_delete(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('pk'))
        user = request.user
        shopping_cart_count, shopping_cart = ShoppingCart.objects.filter(
            user=user, recipe=recipe
        ).delete()
        if not shopping_cart_count:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['get'],
        detail=False,
        url_path='download_shopping_cart',
        permission_classes=(IsAuthenticated,)
    )
    def download_shopping_cart(self, request, id=None):
        response = HttpResponse(
            content_type='text/csv',
            headers={
                'Content-Disposition': 'attachment; '
                f'filename="tmp/{request.user}/shopping_cart.csv"'
            },
        )
        writer = csv.writer(response)
        ingredients = IngredientsRecipes.objects.filter(
            recipe_id__in=ShoppingCart.objects.filter(
                user=request.user).values('recipe_id')
        ).values('ingredient__name', 'ingredient__measurement_unit'
                 ).annotate(sum_amount=Sum('amount'))
        for ingredient in ingredients:
            writer.writerow(
                [
                    f'{ingredient["ingredient__name"]} '
                    f'{ingredient["sum_amount"]} '
                    f'{ingredient["ingredient__measurement_unit"]}'
                ]
            )

        return response
