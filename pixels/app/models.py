from django.db import models

class SelectedCell(models.Model):
    col = models.IntegerField()
    row = models.IntegerField()

    def __str__(self):
        return f"Cell ({self.col}, {self.row})"
