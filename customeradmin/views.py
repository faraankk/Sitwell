from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
# from .models import Customer 
from .forms import CustomAuthenticationForm 

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def login_to_account(request):
    if request.user.is_authenticated and request.user.is_superuser:
         return redirect('admin_dashboard')

    if request.method == 'POST':
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            if not user.is_superuser:
                messages.error(request, 'Only admin users can log in here.')
                return render(request, 'admin_login.html', {'form': form})
            
            login(request, user)
            username = user.first_name.title() if user.first_name else user.username
            messages.success(request, f"Login Successful. Welcome, {username}!")
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
            return render(request, 'admin_login.html', {'form': form})
    
    form = CustomAuthenticationForm()
    return render(request, 'admin_login.html', {'form': form})


@login_required
def admin_dashboard(request):
  
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('/') 

    # context = {
    #     'username': request.user.username,
    # }
    return render(request, 'admin_dashboard.html')


@login_required
def customer_view(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission.")
        return redirect('/')
    
    customers = Customer.objects.all().order_by('last_name', 'first_name')

    return render(request, 'customers/customer_list.html',{'customers': customers})

