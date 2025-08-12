from django.db import models
from django.contrib.auth.models import User

class SelectedCell(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    col = models.IntegerField()
    row = models.IntegerField()

    def __str__(self):
        return f"Cell ({self.col}, {self.row})"


class PurchasedArea(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cell = models.CharField(max_length=20)  
    logo_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.cell} - {self.company_name}"
    
