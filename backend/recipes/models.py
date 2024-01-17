from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

MIN_TIME_COOKING = 1
MAX_TIME_COOKING = 360
MIN_INGREDIENT_AMOUNT = 1
MAX_INGREDIENT_AMOUNT = 1000

User = get_user_model()


class Tag(models.Model):
    """ Модель тэг """
    name = models.CharField(
        default='Тэг',
        max_length=256,
        unique=True,
        verbose_name='Заголовок тэга',
    )
    color = models.CharField(
        default='#49B64E',
        max_length=7,
        unique=True,
        verbose_name='Цвет',
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name='Слаг',
    )

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """ Модель Ингредиент """
    name = models.CharField(
        default='Ингредиент',
        max_length=256,
        verbose_name='Наименование ингредиента',
    )
    measurement_unit = models.CharField(
        default='шт.',
        max_length=210,
        verbose_name='Единица измерения',
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """ Модель рецепт """
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='author_recipes',
        verbose_name='Автор рецепта',
    )
    name = models.CharField(
        default='Название',
        max_length=200,
        verbose_name='Наименование',
    )
    image = models.ImageField(
        upload_to='media/',
        verbose_name='Фото готового блюда',
    )
    text = models.CharField(
        max_length=150,
        null=False,
        blank=False,
        verbose_name='Текст рецепта',
        help_text='Введите текст рецепта',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        related_name='recipes_ingredients',
        through='IngredientsRecipes',
        verbose_name='Ингредиенты',
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='tagged_recipes',
        through='TagsRecipes',
        verbose_name='Тэги',
    )
    cooking_time = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(limit_value=MIN_TIME_COOKING),
            MaxValueValidator(limit_value=MAX_TIME_COOKING),
        ],
        verbose_name='Время приготовления',
        help_text='Введите время приготовления в минутах'
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации рецепта',
        help_text='Дата и время публикации данного рецепта'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('pub_date',)

    def __str__(self):
        return self.name


class TagsRecipes(models.Model):
    """ Модель связи тэг-рецепт """
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        verbose_name='Тэг',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'Тэгированный рецепт'
        verbose_name_plural = 'Тэгированные рецепты'
        ordering = ('tag',)
        constraints = [
            models.UniqueConstraint(
                fields=['tag', 'recipe'],
                name='unique_tag_in_recipe',
            )
        ]

    def __str__(self):
        return f'{self.tag} {self.recipe}'


class IngredientsRecipes(models.Model):
    """ Модель связи ингредиент-рецепт """
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
        related_name='recipe_ingredients'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='ingredient_recipes'
    )
    amount = models.PositiveIntegerField(
        validators=[
            MinValueValidator(limit_value=MIN_INGREDIENT_AMOUNT),
            MaxValueValidator(limit_value=MAX_INGREDIENT_AMOUNT),
        ],
        verbose_name='Количество ингредиента',
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'
        ordering = ('recipe',)
        constraints = [
            models.UniqueConstraint(
                fields=['ingredient', 'recipe'],
                name='unique_ingredient',
            )
        ]

    def __str__(self):
        return f'{self.ingredient} {self.recipe}'


class Subscription(models.Model):
    """ Модель подписка """
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='author_subscriptions',
        verbose_name='Автор',
    )
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='author_followers',
        verbose_name='Подписчик'
    )
    creation_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата оформления подписки',
        help_text='Дата и время оформления подписки'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ('author',)
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'follower'],
                name='unique_following',
            ),
            models.CheckConstraint(
                check=~models.Q(author=models.F('follower')),
                name='self_following',
            )
        ]

    def __str__(self) -> str:
        return f'{self.author} {self.follower}'


class Favorite(models.Model):
    """ Модель связи избранных автор-рецепт """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='user_favorites'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='recipe_favorites'
    )
    creation_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добаления в избранное',
        help_text='Дата и время добавления рецепта в избранное'
    )

    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        ordering = ('user',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite',
            )
        ]

    def __str__(self) -> str:
        return f'{self.user} {self.recipe}'


class ShoppingCart(models.Model):
    """ Модель списка покупок """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='user_shopping_carts'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='recipe_shopping_carts'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
        related_name='ingredient_shopping_carts'
    )
    amount = models.PositiveIntegerField(
        validators=[
            MinValueValidator(limit_value=MIN_INGREDIENT_AMOUNT),
            MaxValueValidator(limit_value=MAX_INGREDIENT_AMOUNT),
        ],
        verbose_name='Количество ингредиента',
    )
    creation_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания списка покупок',
        help_text='Дата и время создания списка покупок'
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        ordering = ('user',)

    def __str__(self) -> str:
        return f'Список покупок пользователя {self.user}'
