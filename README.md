# Cosplay Store (Django)

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
python manage.py makemigrations accounts shop orders
python manage.py migrate
python manage.py seed_products
python manage.py createsuperuser
python manage.py runserver
```

Магазин: http://127.0.0.1:8000/ · Адмінка: http://127.0.0.1:8000/admin/
Тести: `python manage.py test`

## Безпека

Налаштування беруться зі змінних середовища / файлу `.env` (приклад — `.env.example`).
Без змінних проєкт працює в режимі розробки (`DEBUG=True`).

**Чекліст для продакшену**
1. `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` (нове, 50+ символів), `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.
   Без цього в режимі `DEBUG=0` проєкт навмисно не запуститься.
2. HTTPS: у режимі `DEBUG=0` увімкнені редирект на HTTPS, HSTS, `Secure`-cookie. За nginx додайте `DJANGO_BEHIND_PROXY=1` і `NUM_PROXIES=1`.
3. `python manage.py collectstatic`; статику й `media/` віддає nginx.
4. `python manage.py check --deploy` — Django сам перевірить налаштування.
5. Змініть `ADMIN_URL`, реквізити в `COMPANY_DETAILS`, для кількох воркерів задайте `REDIS_URL` (`pip install redis`).

**Що захищено**
- **CSRF:** `CsrfViewMiddleware` + `{% csrf_token %}` у всіх POST-формах; зміни стану (видалення з кошика, скасування, вихід) лише через POST.
- **XSS:** автоекранування шаблонів (`|safe` не використовується), суворий CSP (`script-src 'self'`, без інлайнових скриптів), `HttpOnly`-cookie, екранування тексту в PDF.
- **SQL injection:** лише ORM, без raw SQL; сортування — за білим списком; параметри в URL типізовані (`<int:>`, `<slug:>`).
- **Інше:** `X-Frame-Options: DENY`, `nosniff`, перевірка доступу до чужих замовлень, безпечний `next` при вході, паролі від 10 символів, ліміти розміру запитів.
- **Rate limiting** (`cosplay_store/security.py`): 120 запитів/хв на IP для всього сайту; вхід 10/5 хв; реєстрація 5/год; кошик 60/хв; замовлення 10/10 хв. Відповідь — `429` із `Retry-After`.
  Це захист від перебору паролів і простого флуду. **Справжній DDoS** Django не зупинить: потрібні `limit_req` в nginx, Cloudflare/WAF або захист хостингу.

Bootstrap підключений з CDN. Для додаткового захисту додайте `integrity="sha384-…"` і `crossorigin="anonymous"` до `<link>` у `templates/base.html` (хеш — на getbootstrap.com для версії 5.3.3) або покладіть файл у `static/`.
