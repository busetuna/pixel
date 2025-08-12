from django.shortcuts import redirect, render
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .forms import UsernameOnlyUserCreationForm
from .models import PurchasedArea, SelectedCell
import json
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.utils.text import slugify
import os
from datetime import datetime


def index(request):
    return render(request, 'app/index.html')


def map(request):
    return render(request, 'app/map.html')


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
    try:
        purchased_areas = PurchasedArea.objects.select_related('user').all()

        cells_data = [{
            'cell': area.cell,
            'owner': area.user.username,
            'logo_url': area.logo_url,
            'company_name': area.company_name,
            'notes': area.notes,
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


@login_required
@csrf_exempt
def complete_purchase(request):
    if request.method == 'POST':
        try:
            # Debug: İstek içeriğini logla
            print("📋 POST Data:", dict(request.POST))
            print("📁 FILES:", list(request.FILES.keys()) if request.FILES else "No files")
            
            cells_data = request.POST.get('cells')
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            company_name = request.POST.get('company_name', '').strip()
            notes = request.POST.get('notes', '').strip()
            logo_file = request.FILES.get('logo')

            # Validasyon
            if not cells_data:
                print("❌ Hücre verisi bulunamadı")
                return JsonResponse({"error": "Hücre bilgisi eksik"}, status=400)

            if not email:
                print("❌ Email bulunamadı")
                return JsonResponse({"error": "E-posta bilgisi gerekli"}, status=400)

            try:
                cell_list = json.loads(cells_data)
                print("✅ Cells parsed:", cell_list)
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse hatası: {e}")
                return JsonResponse({"error": "Hücre verisi geçersiz format"}, status=400)

            if not cell_list:
                return JsonResponse({"error": "En az bir hücre seçmelisiniz"}, status=400)

            # Logo kaydetme işlemi
            logo_url = ""
            if logo_file:
                print(f"📷 Logo yükleniyor: {logo_file.name} ({logo_file.size} bytes)")
                try:
                    # Dosya uzantısını al
                    file_ext = os.path.splitext(logo_file.name)[1].lower()
                    if not file_ext:
                        file_ext = '.jpg'  # Varsayılan uzantı
                    
                    # Güvenli dosya adı oluştur
                    safe_company = slugify(company_name) if company_name else 'company'
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{safe_company}_{timestamp}{file_ext}"
                    
                    save_path = os.path.join('logos', filename)
                    path = default_storage.save(save_path, logo_file)
                    logo_url = default_storage.url(path)
                    
                    print(f"✅ Logo kaydedildi: {logo_url}")
                    
                except Exception as logo_error:
                    print(f"❌ Logo kaydetme hatası: {logo_error}")
                    return JsonResponse({
                        "error": "Logo yükleme sırasında hata oluştu",
                        "details": str(logo_error)
                    }, status=500)

            # Hücrelerin daha önce satın alınıp alınmadığını kontrol et
            already_taken = PurchasedArea.objects.filter(cell__in=cell_list)
            if already_taken.exists():
                taken = [item.cell for item in already_taken]
                print(f"❌ Zaten alınmış hücreler: {taken}")
                return JsonResponse({
                    "error": "Bazı hücreler zaten satın alınmış",
                    "taken": taken
                }, status=400)

            # Satın alma işlemi
            with transaction.atomic():
                created_count = 0
                for cell in cell_list:
                    try:
                        purchase = PurchasedArea.objects.create(
                            user=request.user,
                            cell=cell,
                            logo_url=logo_url,      
                            company_name=company_name,
                            notes=notes
                        )
                        created_count += 1
                        print(f"✅ Hücre oluşturuldu: {cell} -> ID: {purchase.id}")
                    except Exception as cell_error:
                        print(f"❌ Hücre oluşturma hatası ({cell}): {cell_error}")
                        raise cell_error

                print(f"🎉 Toplam {created_count} hücre satın alındı")

            # Başarılı yanıt
            return JsonResponse({
                "status": "success",
                "message": f"Satın alma başarıyla tamamlandı! {len(cell_list)} hücre satın alındı.",
                "cells": cell_list,
                "logo_url": logo_url,
                "purchased_count": len(cell_list)
            })

        except json.JSONDecodeError:
            print("❌ JSON decode hatası")
            return JsonResponse({
                "error": "Geçersiz veri formatı"
            }, status=400)
            
        except Exception as e:
            print(f"❌ Genel satın alma hatası: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return JsonResponse({
                "error": "Satın alma sırasında hata oluştu",
                "details": str(e)
            }, status=500)

    return JsonResponse({'error': 'Sadece POST destekleniyor'}, status=405)


@login_required
def purchase_page(request):
    return render(request, 'app/purchase.html')



@login_required
def purchased_cells_view(request):
    items = PurchasedArea.objects.select_related('user').all()
    cells_data = [{
        "cell": it.cell,
        "owner": it.user.username,
        "logo_url": it.logo_url,
        "company_name": it.company_name,
        "notes": it.notes,
        "purchased_at": it.created_at.isoformat() if it.created_at else None,
    } for it in items]
    return JsonResponse({
        "cells": [it.cell for it in items],
        "detailed_data": cells_data,
        "total_count": len(cells_data),
    })

@login_required
def selected_cells_view(request):
    qs = SelectedCell.objects.filter(user=request.user)
    cells = [f"{c.col},{c.row}" for c in qs]
    return JsonResponse({"cells": cells, "count": len(cells)})