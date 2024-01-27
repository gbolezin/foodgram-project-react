from drf_extra_fields.fields import Base64FieldMixin, Base64ImageField

from rest_framework import serializers

from recipes.models import (Favorite, Ingredient, IngredientsRecipes, Recipe,
                            ShoppingCart, Subscription, Tag, User)


class CustomUserSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения Пользователя"""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name',
            'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        return bool(
            self.context.get('request')
            and self.context['request'].user.is_authenticated
            and Subscription.objects.filter(
                author=obj,
                follower=self.context['request'].user).exists()
        )


class TagListSerializer(serializers.ModelSerializer):
    """ Сериализатор для Тэга """

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """ Сериализатор для Ингредиентов """
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientsRecipesListSerializer(serializers.ModelSerializer):
    """ Сериализатор для Ингредиент-Рецепт """
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientsRecipes
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientsRecipesCreateSerializer(serializers.ModelSerializer):
    """ Сериализатор для Ингредиент-Рецепт """
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient.id',
        queryset=Ingredient.objects.all()
    )

    class Meta:
        model = IngredientsRecipes
        fields = ('id', 'amount')


class RecipeListRetrieveSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения Рецептов """
    ingredients = IngredientsRecipesListSerializer(
        many=True, source='ingredient_recipes',
        read_only=True
    )
    tags = TagListSerializer(read_only=True, many=True)
    image = Base64ImageField(allow_null=False)
    author = CustomUserSerializer(required=False)
    is_favorited = serializers.SerializerMethodField(
        required=False, default=False
    )
    is_in_shopping_cart = serializers.SerializerMethodField(
        required=False, default=False
    )

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time',
                  )

    def get_is_favorited(self, obj):
        return bool(
            self.context.get('request')
            and self.context['request'].user.is_authenticated
            and Favorite.objects.filter(
                recipe=obj,
                user=self.context['request'].user).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        return bool(
            self.context.get('request')
            and self.context['request'].user.is_authenticated
            and ShoppingCart.objects.filter(
                recipe=obj,
                user=self.context['request'].user).exists()
        )


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """ Сериализатор для создания и обновления Рецептов """
    ingredients = IngredientsRecipesCreateSerializer(
        many=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )

    image = Base64ImageField(
        required=True,
        allow_empty_file=False,
        allow_null=False
    )

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'ingredients',
                  'name', 'image', 'text', 'cooking_time',
                  )

    def to_representation(self, value):
        return RecipeListRetrieveSerializer(value).data

    def validate_image(self, value):
        if value in Base64FieldMixin.EMPTY_VALUES:
            raise serializers.ValidationError(
                'Поле не может быть пустым'
            )
        else:
            return value

    def validate_empty_tags_ingredients(self, field_name, field_values):
        if len(field_values) == 0:
            raise serializers.ValidationError(
                f'Поле {field_name} не может быть пустым!'
            )
        field_ids = []
        for field in field_values:
            if field in field_ids:
                raise serializers.ValidationError(
                    f'{field_name} в рецепте должны быть уникальны!'
                )
            field_ids.append(field)

    def validate(self, data):
        if 'ingredients' not in data:
            raise serializers.ValidationError(
                'Поле ingredients не может быть пустым!'
            )
        self.validate_empty_tags_ingredients(
            'ingredients',
            data['ingredients']
        )
        if 'tags' not in data:
            raise serializers.ValidationError(
                'Поле tags не может быть пустым!'
            )
        self.validate_empty_tags_ingredients(
            'tags',
            data['tags']
        )
        return data

    def make_tags_ingredients(self, recipe, ingredients, tags):
        ingredient_objs = [
            IngredientsRecipes(
                ingredient=ingredient['ingredient']['id'],
                recipe=recipe,
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        ]
        IngredientsRecipes.objects.bulk_create(ingredient_objs)
        recipe.tags.set(tags)

    def create(self, validated_data):
        """ Создаем запись в БД о рецепте """
        request = self.context['request']
        validated_data['author'] = request.user
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self.make_tags_ingredients(recipe, ingredients, tags)
        return recipe

    def update(self, instance, validated_data):
        """ Обновляем запись в БД о рецепте """
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        IngredientsRecipes.objects.filter(recipe=instance).delete()
        self.make_tags_ingredients(instance, ingredients, tags)
        super().update(instance, validated_data)
        return instance


class SubscriptionRecipeSerializer(serializers.ModelSerializer):
    """ Сериализатор для Рецептов в подписке """
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time',)


class SubscriptionListSerializer(CustomUserSerializer):
    """ Сериализатор для подписок """
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        model = User
        fields = CustomUserSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )

    def get_is_subscribed(self, obj):
        if Subscription.objects.filter(author=obj).first():
            return True
        return False

    def get_recipes_count(self, obj):
        return obj.author_recipes.count()

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.GET.get('recipes_limit')
        recipes = obj.author_recipes.all()
        if recipes_limit is not None:
            try:
                int_recipes_limit = int(recipes_limit)
                recipes = obj.author_recipes.all()[:int(int_recipes_limit)]
            except ValueError:
                pass
        return SubscriptionRecipeSerializer(
            recipes,
            many=True).data


class SubscriptionCreateDeleteSerializer(serializers.ModelSerializer):
    """ Сериализатор для подписок """

    class Meta(CustomUserSerializer.Meta):
        model = Subscription
        fields = (
            'author',
            'follower'
        )

    def to_representation(self, value):
        return SubscriptionListSerializer(
            value.author,
            context={'request': self.context.get('request')}
        ).data

    def validate(self, data):
        author = data['author']
        follower = data['follower']
        if author == follower:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя!'
            )
        if Subscription.objects.filter(
                author=author,
                follower=follower).first():
            raise serializers.ValidationError(
                'Подписаться на автора можно только один раз!'
            )
        return data


class FavoriteSerializer(serializers.ModelSerializer):
    """ Сериализатор для Избранных рецептов """

    class Meta:
        model = Favorite
        fields = ('recipe', 'user')

    def to_representation(self, value):
        return SubscriptionRecipeSerializer(value.recipe).data

    def validate(self, data):
        user = data.get('user')
        recipe = data.get('recipe')
        if Favorite.objects.filter(
                user=user,
                recipe=recipe).first():
            raise serializers.ValidationError(
                'Добавить рецепт в избранное можно только один раз!'
            )
        return data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """ Сериализатор для Списка покупок """

    class Meta:
        model = ShoppingCart
        fields = ('recipe', 'user')

    def to_representation(self, value):
        return SubscriptionRecipeSerializer(value.recipe).data

    def validate(self, data):
        user = data.get('user')
        recipe = data.get('recipe')
        if ShoppingCart.objects.filter(user=user, recipe=recipe.id).exists():
            raise serializers.ValidationError(
                f'Рецепт \'{recipe}\' уже в списке покупок!'
            )
        return data
