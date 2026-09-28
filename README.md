# URL Shortener

A Django-based URL Shortener that converts long URLs into compact, easy-to-share links.

The project provides URL management through a REST API along with authentication, custom aliases, expiration handling, click tracking, Redis caching, and background processing with Celery.

## Features

- Shorten long URLs using Base62-based short codes
- Create custom aliases for short URLs
- Set expiration dates for links
- Redirect users from short URLs to the original destination
- Track link clicks
- User authentication using JWT
- REST API for URL management
- Redis caching for frequently accessed URLs
- Celery background task support
- URL analytics
- Django admin support
- Rate limiting
- Database indexing for faster lookups
- Responsive web interface
- Automated tests for core functionality

## How It Works

The application follows a simple URL-shortening flow:

1. The user submits a long URL.
2. The API validates the URL.
3. A unique short code is generated.
4. The original URL and short code are stored in the database.
5. Frequently accessed URLs can be served through Redis.
6. When someone opens the short URL, the application finds the original URL.
7. The user is redirected to the original destination.
8. The visit is recorded for analytics.

## Technology Stack

### Backend

- Python
- Django
- Django REST Framework

### Authentication

- JWT Authentication
- `djangorestframework-simplejwt`

### Database

- SQLite for local development
- Django ORM
- Database indexes for URL lookup

### Caching

- Redis
- `django-redis`

### Background Processing

- Celery
- Redis as the message broker

### Frontend

- HTML
- CSS
- JavaScript
- Django Templates

## Project Structure

```text
url_shortener/
│
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── shortener/
│   ├── migrations/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── tasks.py
│   ├── tests.py
│   ├── utils.py
│   └── views.py
│
├── templates/
│   └── index.html
│
├── manage.py
├── requirements.txt
└── .gitignore
