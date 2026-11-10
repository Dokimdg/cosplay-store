from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Product

SORT_OPTIONS = {
    'price_asc': 'price',
    'price_desc': '-price',
    'newest': '-created',
}


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()

    products_list = (
        Product.objects.filter(available=True)
        .select_related('category')
        .prefetch_related('images')
    )

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products_list = products_list.filter(category=category)

    query = request.GET.get('q', '').strip()
    if query:
        products_list = products_list.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    sort = request.GET.get('sort', '')
    if sort in SORT_OPTIONS:
        products_list = products_list.order_by(SORT_OPTIONS[sort])
    else:
        sort = ''

    paginator = Paginator(products_list, 12)
    page = request.GET.get('page', 1)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    # Параметри q/sort без page — для посилань пагінації та категорій
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'shop/product/list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'query': query,
        'sort': sort,
        'querystring': params.urlencode(),
    })


def product_detail(request, id, slug):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images'),
        id=id, slug=slug, available=True,
    )
    return render(request, 'shop/product/detail.html', {'product': product})
