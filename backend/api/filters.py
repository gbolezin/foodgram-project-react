from django_filters import rest_framework

from recipes.models import Ingredient, Recipe, ShoppingCart, Tag


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
        method='filter_favorited'
    )
    is_in_shopping_cart = rest_framework.NumberFilter(
        method='filter_shopping_cart'
    )

    def filter_favorited(self, queryset, name, value):
        try:
            if self.request.user.is_authenticated and value:
                return queryset.filter(
                    recipe_favorites__user=self.request.user
                )
        except ValueError:
            pass
        return queryset

    def filter_shopping_cart(self, queryset, name, value):
        try:
            if self.request.user.is_authenticated and value:
                return queryset.filter(
                    id__in=ShoppingCart.objects.filter(
                        user=self.request.user).values('recipe_id'))
        except ValueError:
            pass
        return queryset

    class Meta:
        model = Recipe
        fields = [
            'author',
            'tags',
            'is_favorited',
            'is_in_shopping_cart'
        ]
