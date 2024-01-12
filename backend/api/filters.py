from django_filters import rest_framework
from recipes.models import Recipe, Tag


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

    def filter_favorited(self, queryset, name, value):
        if value == 1:
            expr = True
        elif value == 0:
            expr = False
        return queryset.filter(is_favorited=expr)

    def filter_shopping_cart(self, queryset, name, value):
        if value == 1:
            expr = True
        elif value == 0:
            expr = False
        return queryset.filter(is_in_shopping_cart=expr)

    class Meta:
        model = Recipe
        fields = [
            'author',
            'tags',
            'is_favorited',
            'is_in_shopping_cart'
        ]
