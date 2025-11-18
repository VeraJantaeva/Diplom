    sudo pip3 install  --upgrade pip
    
    sudo pip3 install -r requirements.txt
    
    python3 manage.py makemigrations
     
    python3 manage.py migrate
    
    python3 manage.py createsuperuser
      
# Данные суперпользователя
#    admin@ya.ru
#    admin
 
# Проверяем работоспособность
   
    python3 manage.py runserver 0.0.0.0:8000

# API
 api/v1/ partner/update [name='partner-update']
api/v1/ partner/state [name='partner-state']
api/v1/ partner/orders [name='partner-orders']
api/v1/ user/register [name='user-register']
api/v1/ user/register/confirm [name='user-register-confirm']
api/v1/ user/details [name='user-details']
api/v1/ user/contact [name='user-contact']
api/v1/ user/login [name='user-login']
api/v1/ user/password_reset [name='password-reset']
api/v1/ user/password_reset/confirm [name='password-reset-confirm']
api/v1/ categories [name='categories']
api/v1/ shops [name='shops']
api/v1/ products [name='shops']
api/v1/ basket [name='basket']
api/v1/ order [name='order'] 

# Curl-запросы для проверки

1. Регистрация пользователя

curl -X POST http://localhost:8000/api/v1/user/register -H "Content-Type: application/json" -d '{"email": "test@example.com", "password": "StrongPassword123", "password_confirm": "StrongPassword123", "first_name": "John", "last_name": "Doe", "company": "Test Company", "position": "Manager"}'

2. Подтверждение email

curl -X POST http://localhost:8000/api/v1/user/register/confirm -H "Content-Type: application/json" -d '{"email": "test@example.com", "token": "your-confirmation-token"}'

3. Авторизация

curl -X POST http://localhost:8000/api/v1/user/login -H "Content-Type: application/json" -d '{"email": "test@example.com", "password": "StrongPassword123"}'

4. Данные пользователя

curl -X GET http://localhost:8000/api/v1/user/details -H "Authorization: Token your-auth-token" -H "Content-Type: application/json"

5. Добавление контакта

curl -X POST http://localhost:8000/api/v1/user/contact -H "Authorization: Token your-auth-token" -H "Content-Type: application/json" -d '{"type": "phone", "value": "+79991234567"}'

6. Список категорий

curl -X GET http://localhost:8000/api/v1/categories -H "Content-Type: application/json"

7. Список магазинов

curl -X GET http://localhost:8000/api/v1/shops -H "Content-Type: application/json"

8. Список товаров

curl -X GET http://localhost:8000/api/v1/products -H "Content-Type: application/json"

9. Товары с фильтрацией

curl -X GET "http://localhost:8000/api/v1/products?category_id=1&shop_id=1" -H "Content-Type: application/json"

10. Добавление в корзину

curl -X POST http://localhost:8000/api/v1/basket -H "Authorization: Token your-auth-token" -H "Content-Type: application/json" -d '{"items": [{"product": 1, "shop": 1, "quantity": 2}]}'

11. Просмотр корзины

curl -X GET http://localhost:8000/api/v1/basket -H "Authorization: Token your-auth-token" -H "Content-Type: application/json"

12. Подтверждение заказа

curl -X POST http://localhost:8000/api/v1/order -H "Authorization: Token your-auth-token" -H "Content-Type: application/json" -d '{"contact_id": 1}'

13. Регистрация партнера

curl -X POST http://localhost:8000/api/v1/partner/state -H "Content-Type: application/json" -d '{"email": "shop@example.com", "password": "StrongPassword123", "password_confirm": "StrongPassword123", "first_name": "Shop", "last_name": "Owner", "company": "Test Shop", "position": "Owner", "type": "shop"}'

14. Обновление прайс-листа

curl -X POST http://localhost:8000/api/v1/partner/update -H "Authorization: Token partner-auth-token" -H "Content-Type: application/json" -d '{"url": "https://example.com/price-list.yaml"}'

15. Заказы партнера

curl -X GET http://localhost:8000/api/v1/partner/orders -H "Authorization: Token partner-auth-token" -H "Content-Type: application/json"

16. Запрос сброса пароля

curl -X POST http://localhost:8000/api/v1/user/password_reset -H "Content-Type: application/json" -d '{"email": "test@example.com"}'

17. Подтверждение сброса пароля

curl -X POST http://localhost:8000/api/v1/user/password_reset/confirm -H "Content-Type: application/json" -d '{"email": "test@example.com", "token": "reset-token", "password": "NewPassword123", "password_confirm": "NewPassword123"}'
