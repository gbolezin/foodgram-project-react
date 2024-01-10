from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (CustomUserSerializer, FavoriteSerializer,
                             IngredientSerializer, RecipeSerializer,
                             ShoppingCartSerializer, SubscriptionSerializer,
                             TagSerializer)
from recipes.models import (
    Favorite, Ingredient, Recipe, Subscription, Tag, ShoppingCart)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
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
            if page is not None:
                serializer = SubscriptionSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = SubscriptionSerializer(subsciptions, many=True)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


class IngredientViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """ Вьюсет Ингредиентов """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    http_method_names = ['get']
    permission_classes = [IsAuthenticatedOrReadOnly,]
    pagination_class = None
    filter_backends = (filters.SearchFilter, DjangoFilterBackend)
    search_fields = ('$name',)
    filterset_fields = ('name',)


class RecipeViewSet(viewsets.ModelViewSet):
    """ Вьюсет Рецептов """
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    permission_classes = [IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter


class SubscriptionViewSet(viewsets.ModelViewSet):
    """ Вьюсет Подписок """
    serializer_class = SubscriptionSerializer
    http_method_names = ['post', 'delete']
    permission_classes = [IsAuthorOrReadOnly, IsAuthenticated]

    def get_queryset(self):
        qs = Subscription.objects.filter(follower=self.request.user)
        return qs

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

    # not working
    def perform_destroy(self, instance):
        author = get_object_or_404(User, id=self.kwargs.get('user_id'))
        follower = get_object_or_404(User, id=self.request.user)
        Subscription.objects.filter(author=author, follower=follower).delete()


class FavoriteViewSet(viewsets.ModelViewSet):
    """ Вьюсет Избранных Рецептов """
    queryset = Favorite.objects.all()
    serializer_class = FavoriteSerializer
    http_method_names = ['get', 'post', 'delete']
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


class ShoppingCartViewSet(viewsets.ModelViewSet):
    """ Вьюсет Рецептов """
    queryset = ShoppingCart.objects.all()
    serializer_class = ShoppingCartSerializer
    http_method_names = ['post', 'delete']
    permission_classes = [IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly]
