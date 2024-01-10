from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters import rest_framework
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import Favorite, Ingredient, Recipe, Subscription, Tag
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from api.permissions import IsAuthorOrReadOnly
from api.serializers import (CustomUserSerializer, FavoriteSerializer,
                             IngredientSerializer, RecipeSerializer,
                             SubscriptionSerializer, TagSerializer)

User = get_user_model()


class TagViewSet(mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 viewsets.GenericViewSet
                 ):
    """ Вьюсет Тэгов """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly,]
    pagination_class = None


class IngredientViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """ Вьюсет Ингредиентов """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly,]
    pagination_class = None
    filter_backends = (filters.SearchFilter, DjangoFilterBackend)
    search_fields = ('$name',)
    filterset_fields = ('name',)


class RecipeFilter(rest_framework.FilterSet):
    tags = rest_framework.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    is_favorited = rest_framework.BooleanFilter(
        field_name='is_favorited'
    )
    is_in_shopping_cart = rest_framework.BooleanFilter(
        field_name='is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']


class RecipeViewSet(viewsets.ModelViewSet):
    """ Вьюсет Рецептов """
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly]
    http_method_names = ['get', 'post', 'patch', 'delete']
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter


class SubscriptionViewSet(viewsets.ModelViewSet):
    """ Вьюсет Подписок """
    # queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly]
    http_method_names = ['get', 'post', 'delete']

    def perform_create(self, serializer):
        author = get_object_or_404(User, id=self.kwargs.get('user_id'))
        if author == self.request.user:
            raise ValidationError(
                'Нельзя подписаться на самого себя!'
            )
        if Subscription.objects.filter(
                author=author,
                follower=self.request.user).first():
            raise ValidationError(
                'Подписаться на автора можно только один раз!'
            )
        serializer.save(follower=self.request.user, author=author)

    def get_queryset(self):
        qs = Subscription.objects.all(follower=self.request.user)
        return qs


class CustomUserViewSet(UserViewSet):
    @action(
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
            detail=False,
            url_path='subscriptions',
            permission_classes=[IsAuthenticated]
    )
    def current_user_subscriptions(self, request):
        if request.method == 'GET':
            subsciptions = Subscription.objects.filter(follower=request.user)
            page = self.paginate_queryset(subsciptions)
            if page is not None:
                serializer = SubscriptionSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = SubscriptionSerializer(subsciptions, many=True)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FavoriteViewSet(viewsets.ModelViewSet):
    """ Вьюсет Рецептов """
    queryset = Favorite.objects.all()
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        recipe = Recipe.objects.filter(id=self.kwargs.get('recipe_id')).first()
        if recipe is None:
            raise ValidationError(
                'Нельзя добавить несуществующий рецепт в избранное!'
            )
        if recipe.author == self.request.user:
            raise ValidationError(
                'Нельзя добавить собственный рецепт в избранное!'
            )
        if Favorite.objects.filter(
                user=self.request.user,
                recipe=recipe).first():
            raise ValidationError(
                'Добавить рецепт в избранное можно только один раз!'
            )
        serializer.save(user=self.request.user, recipe=recipe)
