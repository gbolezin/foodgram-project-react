import csv
import json

from django.core.management.base import BaseCommand, CommandError

from recipes.models import Ingredient

MODEL = Ingredient
LABEL = 'Ингредиент'
INGREDIENT_FIELDS = ('name', 'measurement_unit')


class Command(BaseCommand):
    help = 'Load test data from file'

    def load_csv(self, csvfile):
        data_fields = (INGREDIENT_FIELDS)
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            data_obj = dict(zip(data_fields, row))
            MODEL.objects.create(**data_obj)

    def load_json(self, jsonfile):
        data = json.load(jsonfile)
        for data_obj in data:
            MODEL.objects.create(**data_obj)

    def add_arguments(self, parser):
        parser.add_argument('filename', nargs='+', type=str)

    def handle(self, *args, **options):
        filenames = options['filename']
        try:
            for filename in filenames:
                with open(filename, 'r', newline='') as file:
                    extension = filename.split('/')[-1].split('.')[-1]
                    if extension == 'csv':
                        self.load_csv(file)
                    elif extension == 'json':
                        self.load_json(file)
                    else:
                        print(f'Неизвестный формат файла {extension}')
                file.close()
        except CommandError:
            raise CommandError('Ошибка при загрузке данных '
                               f'из файла {filename}!')
