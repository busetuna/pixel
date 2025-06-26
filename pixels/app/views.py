from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
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