from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (Favorite, Ingredient, IngredientsRecipes, Recipe,
                     ShoppingCart, Subscription, Tag, TagsRecipes, User)

admin.site.empty_value_display = 'Не задано'


class CustomUserAdmin(UserAdmin):
    list_filter = ('username', 'email')


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
    )
    list_filter = ('author', 'name', 'tags')
    list_display_links = ('name',)
    readonly_fields = ('favorite_count',)

    def favorite_count(self, obj):
        return Favorite.objects.filter(recipe=obj).count()

    favorite_count.short_description = 'Добавлен в избранное'


class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'measurement_unit'
    )
    list_filter = ('name',)


class IngredientsRecipesAdmin(admin.ModelAdmin):
    list_display = (
        'ingredient',
        'recipe',
        'amount'
    )


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'author',
        'follower'
    )
    list_display_links = ('author', 'follower',)


class FavoritesAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe'
    )
    list_display_links = ('user', 'recipe',)


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
        'ingredient',
        'amount'
    )
    list_display_links = ('user', 'recipe',)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Favorite, FavoritesAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
admin.site.register(IngredientsRecipes, IngredientsRecipesAdmin)
admin.site.register(TagsRecipes)
