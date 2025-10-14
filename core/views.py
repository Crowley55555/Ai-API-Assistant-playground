from django.shortcuts import render


def welcome(request):
    """Главная страница приложения."""
    return render(request, 'core/welcome.html')
