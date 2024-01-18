import base64
import webcolors

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from recipes.models import (Favorite, Ingredient, IngredientsRecipes, Recipe,
                            ShoppingCart, Subscription, Tag, TagsRecipes)

EMAIL_MAX_LENGTH = 254
USERNAME_MAX_LENGTH = 150
PASSWORD_MAX_LENGTH = 150
FIRST_NAME_MAX_LENGTH = 150
LAST_NAME_MAX_LENGTH = 150

USER_FIELDS = {
    'email': EMAIL_MAX_LENGTH,
    'username': USERNAME_MAX_LENGTH,
    'password': PASSWORD_MAX_LENGTH,
    'first_name': FIRST_NAME_MAX_LENGTH,
    'last_name': LAST_NAME_MAX_LENGTH,
}

RECIPE_FIELDS = [
    'tags',
    'ingredients',
    'name',
    'image',
    'text',
    'cooking_time',
]

User = get_user_model()


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


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), 'tmp.' + ext)
        return super().to_internal_value(data)


class CustomUserSerializer(UserSerializer):
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
        if Subscription.objects.filter(author=obj).first():
            return True
        return False


class CustomUserCreateSerializer(UserCreateSerializer):
    """ Сериализатор для создания Пользователя"""
    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 'password'
        )

    def validate_user_field(self, attrs, field_name):
        field_value = attrs.get(field_name)
        if not field_value:
            raise serializers.ValidationError(
                f'Поле {field_name} не может быть пустым!')
        if len(field_value) > USER_FIELDS[field_name]:
            raise serializers.ValidationError(
                f'Длина {field_name} превышает '
                f'максимальную длину {USER_FIELDS[field_name]}!'
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
        for field_name in USER_FIELDS:
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
    color = Hex2NameColor()

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """ Сериализатор для Ингредиентов """
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientsRecipesSerializer(serializers.ModelSerializer):
    """ Сериализатор для Ингредиент-Рецепт """
    id = serializers.IntegerField(
        required=False,
        source='ingredient.id',
        read_only=True
    )
    name = serializers.CharField(
        required=False,
        source='ingredient.name',
        read_only=True
    )
    measurement_unit = serializers.CharField(
        required=False,
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = IngredientsRecipes
        fields = ('id', 'name', 'measurement_unit', 'amount',)


class RecipeSerializer(serializers.ModelSerializer):
    """ Сериализатор для Рецептов """
    ingredients = IngredientsRecipesSerializer(
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
        if not self.context['request'].user.is_anonymous:
            user = self.context['request'].user
        else:
            user = None
        return Favorite.objects.filter(
            recipe=obj, user=user).count() > 0

    def get_is_in_shopping_cart(self, obj):
        if not self.context['request'].user.is_anonymous:
            user = self.context['request'].user
        else:
            user = None
        return ShoppingCart.objects.filter(
            recipe=obj, user=user).count() > 0

    def validate_recipe_field(self, initial_data, data, field_name):
        field_value = initial_data.get(field_name)
        if not field_value:
            raise serializers.ValidationError(
                f'Поле {field_name} не может быть пустым!')

        if field_name == 'ingredients':
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
        if field_name == 'tags':
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
        if field_name == 'image':
            pass
        else:
            data[field_name] = field_value
        return data

    def validate(self, data):
        """ Приводим данные к нужному формату для записи """
        request = self.context['request']
        data['author'] = request.user
        for field_name in RECIPE_FIELDS:
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


class SubscriptionSerializer(serializers.ModelSerializer):
    """ Сериализатор для подписок """
    email = serializers.EmailField(
        required=False,
        source='author.email',
        read_only=True
    )
    id = serializers.IntegerField(
        required=False,
        source='author.id',
        read_only=True
    )
    username = serializers.CharField(
        required=False,
        source='author.username',
        read_only=True
    )
    first_name = serializers.CharField(
        required=False,
        source='author.first_name',
        read_only=True
    )
    last_name = serializers.CharField(
        required=False,
        source='author.last_name',
        read_only=True
    )
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
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
        if Subscription.objects.filter(author=obj.author).first():
            return True
        return False

    def get_recipes_count(self, obj):
        return obj.author.author_recipes.count()

    def get_recipes(self, obj):
        recipes_limit = self.context.get('recipes_limit')
        if recipes_limit is not None:
            recipes = obj.author.author_recipes.all()[:int(recipes_limit)]
        else:
            recipes = obj.author.author_recipes.all()
        return SubscriptionRecipeSerializer(
            recipes,
            many=True).data


class FavoriteSerializer(serializers.ModelSerializer):
    """ Сериализатор для Избранных рецептов """
    id = serializers.IntegerField(
        required=False,
        source='recipe.id',
        read_only=True
    )
    name = serializers.CharField(
        required=False,
        source='recipe.name',
        read_only=True
    )
    image = Base64ImageField(
        required=False,
        source='recipe.image',
        read_only=True
    )
    cooking_time = serializers.IntegerField(
        required=False,
        source='recipe.cooking_time',
        read_only=True
    )

    class Meta:
        model = Favorite
        fields = ('id', 'name', 'image', 'cooking_time',)


class ShoppingCartSerializer(serializers.ModelSerializer):
    """ Сериализатор для Списка покупок """

    class Meta:
        model = ShoppingCart
        fields = '__all__'
