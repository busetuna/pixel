from pyexpat.errors import messages
from django.shortcuts import redirect, render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import UserCreationForm
# app/views.py
from .forms import UsernameOnlyUserCreationForm  # ✅ DOĞRU

from .models import SelectedCell


def index(request):
    
    return render(request, 'app/index.html')

def map(request):
    
    return render(request, 'app/map.html')


@csrf_exempt
def save_selected_cells(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        cells = data.get('cells', [])
        SelectedCell.objects.all().delete()
        for key in cells:
            col_str, row_str = key.split(",")
            col = int(col_str)
            row = int(row_str)
            SelectedCell.objects.create(col=col, row=row)
        return JsonResponse({'status': 'success', 'saved': len(cells)})
    return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=400)

def register(request):
    if request.method == 'POST':
        form = UsernameOnlyUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
     #       messages.success(request, "Kayıt başarılı!")
            return redirect('login')  # veya 'index'
        else:
            print("Form hataları:", form.errors)  # Hataları terminale yaz
          #  messages.error(request, "Form geçersiz.")
    else:
        form = UsernameOnlyUserCreationForm()
    return render(request, 'app/register.html', {'form': form})