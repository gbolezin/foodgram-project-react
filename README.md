Описание проекта

"Фудграм" — сайт, на котором пользователи могут публиковать рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Пользователям сайта также  доступен сервис «Список покупок». Он позволяет создавать список продуктов, которые нужно купить для приготовления выбранных блюд. 

Каждый рецепт имеет ряд параметров, которые условно можно поделить на два типа - одиночные (например, "Название" или "Время приготовления") и множественные (например, "Тэги" и "Ингредиенты"). Вне зависимости от типа все параметры обязательны для заполнения.

Авторизованные пользователи могут добавлять рецепты в избранное, а также добавлять рецепты в "Списки покупок". Также авторизованные пользователи могут подписываться на других авторов рецептов. Неатворизованным пользователям сайт "Фудграм" доступен только для чтения.

Перечень игредиентов и тэгов для последующего присвоения рецепту доступен для редактирования только администратору сайта.


Как развернуть проект в Docker 

Для развертывания проекта на локальном сервере необходимо выполнить несколько шагов:
1. Сделать Fork репозитория gbolezin/foodgram-project-react с github
2. Установить и запустить Docker
3. В корневом каталоге проекта выполнить сборку проекта с указанием файла docker-compose.yml
    docker compose -f docker-compose.yml up -d
4. Для загрузки ингредиентов воспользоваться командой:
    docker compose -d docker-compose.yml exec -it backend python manage.py loadingredients data/ingredisnes.json
    либо 
    docker compose -d docker-compose.yml exec -it backend python manage.py loadingredients data/ingredisnes.csv

Для развертывания проекта на удаленном сервере необходимо выполнить несколько шагов:
1. Сделать Fork репозитория gbolezin/foodgram-project-react с github
2. Сформировать файл корневой_каталог_проекта/.github/worflows/main.yml (можно использовать дефолтный)
3. В разделе GitHub->Settings->Security->Secrets and Variables->Actions добавить необходимые переменные для передачи в workflow (наименование переменных можно посмотреть в файле main.yml, см. п.2)
4. Сделать push исходного кода в свой репозиторий в ветку "master", после чего проверить исполнение в разделе Github->Actions вашего проекта
5. Для загрузки ингредиентов воспользоваться командой:
    docker compose -d docker-compose.production.yml exec -it backend python manage.py loadingredients data/ingredisnes.json
    либо 
    docker compose -d docker-compose.production.yml exec -it backend python manage.py loadingredients data/ingredisnes.csv


Стек используемых технологий

В качестве бэкенда в проекте используется Django
API реализован на Django Rest Framework
Фронтэнд выполнени на стеке React
СУБД PostgreSQL, веб-сервер Nginx
Контейнеризация Docker
Для автоматизации деплоя использован GitHub Actions

Документация

Документация к API проекта доступна по ссылке ваш_сервер:ваш_порт/api/docs/


Пример запросов/ответов

Пример запроса №1
GET https://foodgram.zenith24.ru/api/users/

Пример ответа №1
{
  "count": 123,
  "next": "http://foodgram.example.org/api/users/?page=4",
  "previous": "http://foodgram.example.org/api/users/?page=2",
  "results": [
    {
      "email": "user@example.com",
      "id": 0,
      "username": "string",
      "first_name": "Вася",
      "last_name": "Пупкин",
      "is_subscribed": false
    }
  ]
}

Пример запроса №2:
POST https://foodgram.zenith24.ru/api/recipes/

Пример ответа №2:
{
  "ingredients": [
    {
      "id": 1123,
      "amount": 10
    }
  ],
  "tags": [
    1,
    2
  ],
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==",
  "name": "string",
  "text": "string",
  "cooking_time": 1
}


Автор проекта - Болезин Георгий (Bolezin George)
e-mail: g.bolezin@zenith24.ru
tg: @gbolezin
https://foodgram.zenith24.ru

