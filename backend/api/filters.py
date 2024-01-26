from django.db.models import Exists, OuterRef, Value
from django_filters import rest_framework
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag

FILTER_FLAGS = {0, 1}


class IngredientFilter(rest_framework.FilterSet):
    name = rest_framework.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(rest_framework.FilterSet):
    tags = rest_framework.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    is_favorited = rest_framework.NumberFilter(
        field_name='is_favorited',
        method='filter_favorited'
    )
    is_in_shopping_cart = rest_framework.NumberFilter(
        field_name='is_in_shopping_cart',
        method='filter_shopping_cart'
    )

    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            qs = Recipe.objects.all().annotate(
                is_favorited=Value(False),
                is_in_shopping_cart=Value(False)
            )
        else:
            qs = Recipe.objects.all().annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(
                        user=user,
                        recipe_id=OuterRef("id")
                    )
                ),
                is_in_shopping_cart=Exists(ShoppingCart.objects.filter(
                    user=user,
                    recipe_id=OuterRef("id")))
            )
        return qs

    def filter_favorited(self, queryset, name, value):
        if not self.request.user.is_anonymous:
            if value in FILTER_FLAGS:
                queryset = self.get_queryset()
                return queryset.filter(is_favorited=value)
        return queryset.none()

    def filter_shopping_cart(self, queryset, name, value):
        if not self.request.user.is_anonymous:
            if value in FILTER_FLAGS:
                queryset = self.get_queryset()
                return queryset.filter(is_in_shopping_cart=value)
        return queryset.none()

    class Meta:
        model = Recipe
        fields = [
            'author',
            'tags',
            'is_favorited',
            'is_in_shopping_cart'
        ]
