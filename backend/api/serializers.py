import webcolors
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from django.shortcuts import get_object_or_404
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

import recipes.constants as constants
from recipes.models import (Favorite, Ingredient, IngredientsRecipes, Recipe,
                            ShoppingCart, Subscription, Tag, TagsRecipes, User)


class Hex2NameColor(serializers.Field):
    def to_representation(self, value):
        return value

    def to_internal_value(self, data):
        try:
            data = webcolors.hex_to_name(data)
        except ValueError:
            raise serializers.ValidationError(
                'Для этого цвета нет имени'
            )
        return data


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
            self.context.get('request') and
            self.context['request'].user.is_authenticated and
            Subscription.objects.filter(
                author=obj,
                follower=self.context['request'].user).first()
        )

    def validate_user_field(self, attrs, field_name):
        field_value = attrs.get(field_name)
        if not field_value:
            raise serializers.ValidationError(
                f'Поле {field_name} не может быть пустым!')
        if len(field_value) > constants.USER_FIELDS[field_name]:
            raise serializers.ValidationError(
                f'Длина {field_name} превышает '
                f'максимальную длину {constants.USER_FIELDS[field_name]}!'
            )
        if field_name == 'email':
            if User.objects.filter(email=field_value):
                raise serializers.ValidationError(
                    f'Почтовый адрес {field_value} уже используется!')
        if field_name == 'username':
            if User.objects.filter(username=field_value):
                raise serializers.ValidationError(
                    f'Имя пользователя {field_value} уже используется!')

    def validate(self, attrs):
        user = User(**attrs)
        password = attrs.get("password")
        for field_name in constants.USER_FIELDS:
            self.validate_user_field(attrs, field_name)
        try:
            validate_password(password, user)
        except django_exceptions.ValidationError as e:
            serializer_error = serializers.as_serializer_error(e)
            raise serializers.ValidationError(
                {"password": serializer_error["non_field_errors"]}
            )
        return attrs


class TagSerializer(serializers.ModelSerializer):
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
    id = serializers.ReadOnlyField(source='ingredient.id')
    amount = serializers.IntegerField(
        min_value=constants.MIN_INGREDIENT_AMOUNT,
        max_value=constants.MAX_INGREDIENT_AMOUNT
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
    tags = TagSerializer(read_only=True, many=True)
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
            self.context.get('request') and
            self.context['request'].user.is_authenticated and
            Favorite.objects.filter(
                recipe=obj,
                user=self.context['request'].user).count() > 0
        )

    def get_is_in_shopping_cart(self, obj):
        return bool(
            self.context.get('request') and
            self.context['request'].user.is_authenticated and
            ShoppingCart.objects.filter(
                recipe=obj,
                user=self.context['request'].user).count() > 0
        )


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """ Сериализатор для создания и обновления Рецептов """
    ingredients = IngredientsRecipesCreateSerializer(
        many=True, source='ingredient_recipes',
        read_only=True
    )
    tags = TagSerializer(read_only=True, many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'ingredients',
                  'name', 'image', 'text', 'cooking_time',
                  )

    def to_representation(self, value):
        return RecipeListRetrieveSerializer(value).data

    def validate_recipe_ingredients(self, field_value):
        ingredients = field_value
        ingredient_ids = []
        for ingredient in ingredients:
            if not Ingredient.objects.filter(id=ingredient['id']).first():
                raise serializers.ValidationError(
                    f'Ингредиента с id={ingredient["id"]} не существует!')
            if int(ingredient['amount']) < 1:
                raise serializers.ValidationError(
                    f'Количество ингредиента id={ingredient["id"]} '
                    'не может быть меньше 1!')
            ingredient_ids.append(ingredient['id'])
        ingredient_set = set(ingredient_ids)
        if len(ingredient_set) != len(ingredient_ids):
            raise serializers.ValidationError(
                'Ингредиенты в рецепте должны быть уникальны!'
            )

    def validate_recipe_tags(self, field_value):
        tags = field_value
        for tag in tags:
            if not Tag.objects.filter(id=tag).first():
                raise serializers.ValidationError(
                    f'Тэга с id={tag} не существует!')
        tag_set = set(tags)
        if len(tag_set) != len(tags):
            raise serializers.ValidationError(
                'Тэги в рецепте должны быть уникальны!'
            )

    def validate_recipe_field(self, initial_data, data, field_name):
        field_value = initial_data.get(field_name)
        if not field_value:
            raise serializers.ValidationError(
                f'Поле {field_name} не может быть пустым!')
        if field_name == 'ingredients':
            self.validate_recipe_ingredients(field_value)
        if field_name == 'tags':
            self.validate_recipe_tags(field_value)
        if field_name == 'image':
            pass
        else:
            data[field_name] = field_value
        return data

    def validate(self, data):
        """ Приводим данные к нужному формату для записи """
        request = self.context['request']
        data['author'] = request.user
        for field_name in constants.RECIPE_FIELDS:
            self.validate_recipe_field(self.initial_data, data, field_name)
        return data

    def create(self, validated_data):
        """ Создаем запись в БД о рецепте """
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        for ingredient in ingredients:
            IngredientsRecipes.objects.create(
                ingredient=get_object_or_404(
                    Ingredient, id=ingredient['id']
                ),
                recipe=recipe,
                amount=ingredient['amount'])
        for tag in tags:
            TagsRecipes.objects.create(
                tag=get_object_or_404(Tag, id=tag), recipe=recipe)
        return recipe

    def update(self, instance, validated_data):
        """ Обновляем запись в БД о рецепте """
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.image = validated_data.get('image')
        instance.name = validated_data.get('name')
        instance.text = validated_data.get('text')
        instance.cooking_time = validated_data.get('cooking_time')
        IngredientsRecipes.objects.filter(recipe=instance).delete()
        TagsRecipes.objects.filter(recipe=instance).delete()
        for ingredient in ingredients:
            IngredientsRecipes.objects.create(
                ingredient=get_object_or_404(
                    Ingredient, id=ingredient['id']
                ),
                recipe=instance,
                amount=ingredient['amount'])
        for tag in tags:
            TagsRecipes.objects.create(
                tag=get_object_or_404(Tag, id=tag), recipe=instance)
        instance.save()
        return instance


class SubscriptionRecipeSerializer(serializers.ModelSerializer):
    """ Сериализатор для Рецептов в подписке """
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time',)


class SubscriptionListSerializer(CustomUserSerializer):
    """ Сериализатор для подписок """
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
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
        recipes_limit = self.context.get('recipes_limit')
        if recipes_limit is not None:
            try:
                int_recipes_limit = int(recipes_limit)
            except ValueError:
                raise serializers.ValidationError(
                    'recipes_limit должно быть целым числом'
                )
            recipes = obj.author_recipes.all()[:int(int_recipes_limit)]
        else:
            recipes = obj.author_recipes.all()
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
            context={'recipes_limit': self.context.get('recipes_limit')}
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
        if not Recipe.objects.get(id=recipe.id):
            raise serializers.ValidationError(
                f'Рецепт \'{recipe}\' не существует!'
            )
        recipes = ShoppingCart.objects.filter(user=user, recipe=recipe.id)
        if recipes.count() > 0:
            raise serializers.ValidationError(
                f'Рецепт \'{recipe}\' уже в списке покупок!'
            )
        return data
