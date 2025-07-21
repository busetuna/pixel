from django.db import models

class SelectedCell(models.Model):
    col = models.IntegerField()
    row = models.IntegerField()

    def __str__(self):
        return f"Cell ({self.col}, {self.row})"


# class SelectedCellForUser(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     col = models.IntegerField()
#     row = models.IntegerField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         unique_together = ('user', 'col', 'row')

# Veritabanına kaydetmedim.