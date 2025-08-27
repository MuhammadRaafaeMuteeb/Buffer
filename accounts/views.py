from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages


@login_required(login_url='login')  # uses the URL name 'login'
def dashboard(request):
    return render(request, 'dashboard.html')


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        pwd1 = request.POST.get('password1')
        pwd2 = request.POST.get('password2')

        # Check if passwords match
        if pwd1 != pwd2:
            messages.error(request, 'Passwords do not match')
            return redirect('register')

        # Check if user exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken')
            return redirect('register')

        # if User.objects.filter(email=email).exists():
        #     messages.error(request, 'Email already registered')
        #     return redirect('register')

        # Create user
        user = User.objects.create_user(username=username, email=email, password=pwd1)
        login(request, user)
        messages.success(request, f"Welcome, {username}! Your account has been created.")
        return redirect('dashboard')

    return render(request, 'accounts/signup.html')


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {username}!")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("login")

    return render(request, "accounts/login.html")  # ✅ Fixed path


def logout_view(request):
    logout(request)
    storage = get_messages(request)
    for _ in storage:
        pass  # iterate to clear
    storage.used = True  # make sure messages are marked as used

    messages.success(request, "You have been logged out successfully.")
    return redirect("login")