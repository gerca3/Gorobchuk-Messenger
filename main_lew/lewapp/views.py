from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import AuthenticationForm
from os.path import join
from django.http import JsonResponse, HttpResponseBadRequest
from .models import User, Chat
from lewapp.models import Media
from lewapp.forms import CreateUserForm
def index(request):
    user = request.user

    if not user.is_authenticated:
        return redirect(login_user)

    return render(request, "index.html")

def get_favicon(request):
    file_path = join(settings.BASE_DIR, "lewapp\\static\\img", "favicon.jpg")

    return FileResponse(open(file_path, "rb"), content_type="image/png")


def download_media(request):
    media_id = request.GET.get("id")

    if media_id is not None:
        media = Media.objects.filter(id=media_id).first()

        if media is not None:
            file = media.file
            response = FileResponse(file.open("rb"), as_attachment=True)

            return response

    return HttpResponse("NOT OK")

@login_required
def my_groups(request):
    groups = Chat.objects.filter(users=request.user).values('id', 'name', 'description')
    return JsonResponse(list(groups), safe=False)
# @login_required
def group_test(request):
    return render(request, 'group_test.html')

@login_required
@require_http_methods(["POST"])
def create_group_chat(request):
    name = request.POST.get('name')
    description = request.POST.get('description')
    user_ids = request.POST.getlist('user_ids')

    if not name or not description:
        return HttpResponseBadRequest("Name and description are required.")

    chat = Chat.objects.create(name=name, description=description)

    chat.users.add(request.user)

    if user_ids:
        try:
            user_ids_int = [int(uid) for uid in user_ids]
        except ValueError:
            return HttpResponseBadRequest("Invalid user IDs.")
        users_to_add = User.objects.filter(id__in=user_ids_int)
        chat.users.add(*users_to_add)

    return JsonResponse({
        'id': chat.id,
        'name': chat.name,
        'description': chat.description,
        'users': list(chat.users.values_list('id', flat=True))
    })

def register_user(request):
    if request.method == 'POST':
        form = CreateUserForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(request, user)
            messages.success(request, 'Вы зарегестрированы')

            return redirect('index')
    else:
        form = CreateUserForm()

    return render(request, 'register.html', {'form': form})


def login_user(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)

        if form.is_valid():
            user = form.get_user()

            login(request, user)
            messages.success(request, 'Вы вошли')

            return redirect('index')
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def logout_user(request):
    logout(request)

    messages.success(request, 'Вы вышли из аккаунта')

    return redirect('login')
