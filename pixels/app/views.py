from django.shortcuts import redirect, render
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .forms import UsernameOnlyUserCreationForm
from .models import PurchasedArea, SelectedCell
import json
from django.db import transaction


def index(request):
    return render(request, 'app/index.html')


def map(request):
    return render(request, 'app/map.html')
from django.views.decorators.csrf import csrf_exempt

def register(request):
    if request.method == 'POST':
        form = UsernameOnlyUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Kayıt başarılı!")
            return redirect('login')
        else:
            print("Form hataları:", form.errors)
            messages.error(request, "Form geçersiz. Lütfen bilgileri kontrol edin.")
    else:
        form = UsernameOnlyUserCreationForm()

    return render(request, 'app/register.html', {'form': form})




@login_required
def save_selected_cells(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            cells = data.get('cells', [])

            if not isinstance(cells, list):
                return JsonResponse({'status': 'error', 'detail': 'cells listesi bekleniyor'}, status=400)

            SelectedCell.objects.filter(user=request.user).delete()

            for key in cells:
                try:
                    col_str, row_str = key.split(",")
                    col = int(col_str)
                    row = int(row_str)
                    SelectedCell.objects.create(user=request.user, col=col, row=row)
                except Exception as item_error:
                    print(f"🚫 Hatalı hücre verisi: {key} -> {item_error}")

            return JsonResponse({'status': 'success', 'saved': len(cells)})

        except Exception as e:
            print("❌ Genel hata:", str(e))
            return JsonResponse({'status': 'error', 'detail': str(e)}, status=500)

    return JsonResponse({'error': 'Sadece POST destekleniyor'}, status=405)


@login_required
def purchase_area(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            logo_url = data.get('logo_url', '')

            selected_cells = SelectedCell.objects.filter(user=request.user)
            if not selected_cells.exists():
                return JsonResponse({"error": "Satın alınacak hücre bulunamadı"}, status=400)

            selected_keys = [f"{cell.col},{cell.row}" for cell in selected_cells]

            already_purchased = PurchasedArea.objects.filter(cell__in=selected_keys)
            if already_purchased.exists():
                taken_cells = [area.cell for area in already_purchased]
                return JsonResponse({
                    "error": "Bazı hücreler zaten satın alınmış",
                    "taken": taken_cells
                }, status=400)

            with transaction.atomic():
                for key in selected_keys:
                    PurchasedArea.objects.create(
                        user=request.user,
                        cell=key,
                        logo_url=logo_url
                    )

                selected_cells.delete()

            return JsonResponse({
                "status": "success",
                "message": f"{len(selected_keys)} hücre başarıyla satın alındı",
                "cells": selected_keys
            })

        except Exception as e:
            return JsonResponse({
                "error": "Satın alma sırasında hata oluştu",
                "details": str(e)
            }, status=500)

    return JsonResponse({'error': 'Sadece POST destekleniyor'}, status=405)


def purchased_cells_view(request):
    # Giriş zorunlu değil, herkes görebilir
    try:
        purchased_areas = PurchasedArea.objects.select_related('user').all()

        cells_data = [{
            'cell': area.cell,
            'owner': area.user.username,
            'logo_url': area.logo_url,
            'purchased_at': getattr(area, 'created_at', None)
        } for area in purchased_areas]

        return JsonResponse({
            "cells": [area.cell for area in purchased_areas],
            "detailed_data": cells_data,
            "total_count": len(cells_data)
        })

    except Exception as e:
        return JsonResponse({
            "error": "Veri alınırken hata oluştu",
            "details": str(e)
        }, status=500)


@login_required
def my_purchases(request):
    try:
        user_purchases = PurchasedArea.objects.filter(user=request.user)

        cells_data = [{
            'cell': purchase.cell,
            'logo_url': purchase.logo_url,
            'purchased_at': getattr(purchase, 'created_at', None)
        } for purchase in user_purchases]

        return JsonResponse({
            "purchases": cells_data,
            "total_count": len(cells_data)
        })

    except Exception as e:
        return JsonResponse({
            "error": "Satın alımlar alınırken hata oluştu",
            "details": str(e)
        }, status=500)


from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.utils.text import slugify
import os
from datetime import datetime

@login_required
@csrf_exempt  # Eğer formdan POST geliyorsa ve CSRF token kullanmıyorsan geçici olarak eklenebilir.
def complete_purchase(request):
    if request.method == 'POST':
        try:
            cells = request.POST.get('cells')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            company_name = request.POST.get('company_name')
            notes = request.POST.get('notes')
            logo_file = request.FILES.get('logo')

            if not cells:
                return JsonResponse({"error": "Hücre bilgisi eksik"}, status=400)

            cell_list = json.loads(cells)

            # Logo kaydetme işlemi
            logo_url = ""
            if logo_file:
                filename = f"{slugify(company_name)}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{logo_file.name}"
                save_path = os.path.join('logos', filename)
                path = default_storage.save(save_path, logo_file)
                logo_url = default_storage.url(path) 

            # Hücrelerin daha önce satın alınıp alınmadığını kontrol et
            already_taken = PurchasedArea.objects.filter(cell__in=cell_list)
            if already_taken.exists():
                taken = [item.cell for item in already_taken]
                return JsonResponse({
                    "error": "Bazı hücreler zaten satın alınmış",
                    "taken": taken
                }, status=400)

            # Satın alma işlemi
            with transaction.atomic():
                for cell in cell_list:
                    PurchasedArea.objects.create(
                        user=request.user,
                        cell=cell,
                        logo_url=logo_url
                    )

            return JsonResponse({
                "status": "success",
                "message": "Satın alma başarıyla tamamlandı!",
                "cells": cell_list
            })

        except Exception as e:
            return JsonResponse({
                "error": "Satın alma sırasında hata oluştu",
                "details": str(e)
            }, status=500)

    return JsonResponse({'error': 'Sadece POST destekleniyor'}, status=405)

@login_required
def purchase_page(request):
    return render(request, 'app/purchase.html')
