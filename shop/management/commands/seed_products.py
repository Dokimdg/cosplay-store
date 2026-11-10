import random

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from shop.models import Category, Product

TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd', 'е': 'e', 'є': 'ye',
    'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k', 'л': 'l',
    'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ь': '',
    'ю': 'yu', 'я': 'ya', ' ': '-', '-': '-',
}


def make_slug(text):
    text = text.lower().strip()
    return slugify("".join(TRANSLIT.get(ch, ch) for ch in text))


CATEGORIES = ['Костюми', 'Перуки', 'Аксесуари', 'Взуття', 'Крафт']

PRODUCTS = [
    ("Костюм Наруто Узумакі", 'Костюми', 1500),
    ("Перука Годжо Сатору", 'Перуки', 650),
    ("Катана Танджиро Камадо", 'Крафт', 1200),
    ("Чоботи Ерена Єгера", 'Взуття', 950),
    ("Маска Канекі Кена", 'Аксесуари', 350),
    ("Сукня Люсі Хартфілії", 'Костюми', 1800),
    ("Перука Міку Хацуне", 'Перуки', 750),
    ("Кільця Акацукі", 'Аксесуари', 250),
    ("Плащ Леві Аккермана", 'Костюми', 800),
    ("Пов'язка Конохи", 'Аксесуари', 120),
    ("Костюм Тандзіро Камадо", 'Костюми', 1700),
    ("Перука Рем", 'Перуки', 700),
    ("Кросівки Ґона Фрікса", 'Взуття', 900),
    ("Меч Сайто Хадзіме", 'Крафт', 1400),
    ("Капелюх Луффі", 'Аксесуари', 300),
    ("Плащ Хокаге", 'Костюми', 1300),
]


class Command(BaseCommand):
    help = 'Наповнює базу тестовими категоріями та товарами (можна запускати повторно)'

    def handle(self, *args, **kwargs):
        categories = {}
        for name in CATEGORIES:
            categories[name], _ = Category.objects.get_or_create(
                name=name, defaults={'slug': make_slug(name)}
            )

        created_count = 0
        for title, cat_name, price in PRODUCTS:
            _, created = Product.objects.get_or_create(
                name=title,
                category=categories[cat_name],
                defaults={
                    'slug': make_slug(title),
                    'description': f'Якісний товар: {title}.',
                    'price': price,
                    'stock': random.randint(1, 15),
                    'available': True,
                },
            )
            created_count += created

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Нових товарів: {created_count}, усього: {Product.objects.count()}.'
        ))
