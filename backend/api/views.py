import csv

from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (CustomUserSerializer, FavoriteSerializer,
                             IngredientSerializer, RecipeSerializer,
                             SubscriptionRecipeSerializer,
                             SubscriptionSerializer, TagSerializer)
from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, IngredientsRecipes, Recipe,
                            ShoppingCart, Subscription, Tag)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """ Вьюсет пользователя """

    def check_subscription_data(self, author, follower):
        if author == follower:
            raise ValidationError(
                'Нельзя подписаться на самого себя!'
            )
        if Subscription.objects.filter(
                author=author,
                follower=follower).first():
            raise ValidationError(
                'Подписаться на автора можно только один раз!'
            )

    @action(
            methods=['get', 'post'],
            detail=False,
            url_path='me',
            permission_classes=[IsAuthenticated]
    )
    def current_user(self, request):
        if request.method == 'GET':
            user = request.user
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        user = request.user
        serializer = CustomUserSerializer(
            user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
            methods=['get'],
            detail=False,
            url_path='subscriptions',
            permission_classes=[IsAuthenticated]
    )
    def current_user_subscriptions(self, request):
        if request.method == 'GET':
            subsciptions = Subscription.objects.filter(follower=request.user)
            page = self.paginate_queryset(subsciptions)
            recipes_limit = request.GET.get('recipes_limit')
            if page is not None:
                serializer = SubscriptionSerializer(
                    page,
                    many=True,
                    context={'recipes_limit': recipes_limit}
                )
                return self.get_paginated_response(serializer.data)
            serializer = SubscriptionSerializer(
                subsciptions,
                many=True,
                context={'recipes_limit': recipes_limit}
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
            methods=['post', 'delete'],
            detail=True,
            url_path='subscribe',
            permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=self.kwargs.get('id'))
        follower = request.user
        recipes_limit = request.GET.get('recipes_limit')
        if request.method == 'POST':
            self.check_subscription_data(author, follower)
            subscription = Subscription.objects.create(
                author=author, follower=follower
            )
            serializer = SubscriptionSerializer(
                subscription,
                context={'recipes_limit': recipes_limit}
            )
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                author=author, follower=follower
            ).first()
            if subscription is None:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 viewsets.GenericViewSet
                 ):
    """ Вьюсет Тэгов """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ['get']
    permission_classes = [IsAuthenticatedOrReadOnly,]
    pagination_class = None


class IngredientViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """ Вьюсет Ингредиентов """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    http_method_names = ['get']
    permission_classes = [IsAuthenticatedOrReadOnly,]
    pagination_class = None
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """ Вьюсет Рецептов """
    serializer_class = RecipeSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    permission_classes = [IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def check_shopping_data(self, recipe, user):
        recipes = ShoppingCart.objects.filter(user=user, recipe=recipe)
        if recipes.count() > 0:
            raise ValidationError(
                f'Рецепт \'{recipe.name}\' уже в списке покупок!'
            )

    def check_favorite_data(self, recipe, user):
        if recipe.author == user:
            raise ValidationError(
                'Нельзя добавить собственный рецепт в избранное!'
            )
        if Favorite.objects.filter(
                user=user,
                recipe=recipe).first():
            raise ValidationError(
                'Добавить рецепт в избранное можно только один раз!'
            )

    def get_queryset(self):
        if not self.request.user.is_anonymous:
            user = self.request.user
        else:
            user = None
        qs = Recipe.objects.all().annotate(
            is_favorited=Exists(Favorite.objects.filter(
                user=user,
                recipe_id=OuterRef("id")
                )),
            is_in_shopping_cart=Exists(ShoppingCart.objects.filter(
                user=user,
                recipe_id=OuterRef("id")))
        )
        return qs

    @action(
            methods=['post', 'delete'],
            detail=True,
            url_path='favorite',
            permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = Recipe.objects.filter(id=self.kwargs.get('pk')).first()
        user = request.user
        if request.method == 'POST':
            if recipe is None:
                return Response('Рецепт не существует',
                                status=status.HTTP_400_BAD_REQUEST
                                )
            self.check_favorite_data(recipe, user)
            favorite = Favorite.objects.create(
                user=user, recipe=recipe
            )
            serializer = FavoriteSerializer(favorite)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        elif request.method == 'DELETE':
            if recipe is None:
                return Response('Рецепт не существует',
                                status=status.HTTP_404_NOT_FOUND
                                )
            favorite = Favorite.objects.filter(
                user=user, recipe=recipe
            ).first()
            if favorite is None:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
            methods=['post', 'delete'],
            detail=True,
            url_path='shopping_cart',
            permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = Recipe.objects.filter(id=self.kwargs.get('pk')).first()
        user = request.user
        if request.method == 'POST':
            if recipe is None:
                return Response('Рецепт не существует',
                                status=status.HTTP_400_BAD_REQUEST
                                )
            self.check_shopping_data(recipe, user)
            ingredients = IngredientsRecipes.objects.filter(recipe=recipe)
            for ingredient in ingredients:
                ShoppingCart.objects.create(
                    user=user,
                    recipe=recipe,
                    ingredient=ingredient.ingredient,
                    amount=ingredient.amount
                )
            serializer = SubscriptionRecipeSerializer(recipe)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        elif request.method == 'DELETE':
            if recipe is None:
                return Response('Рецепт не существует',
                                status=status.HTTP_404_NOT_FOUND
                                )
            shopping_carts = ShoppingCart.objects.filter(
                user=user, recipe=recipe
            )
            if shopping_carts.count() <= 0:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            shopping_carts.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
            methods=['get', 'post', 'delete'],
            detail=False,
            url_path='download_shopping_cart',
            permission_classes=[IsAuthenticated]
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
        writer.writerow([f'Список покупок пользователя {request.user}'])

        ingredients = ShoppingCart.objects.filter(
            user=request.user).values(
                'ingredient__name', 'ingredient__measurement_unit'
            ).order_by(
                'ingredient_id'
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
