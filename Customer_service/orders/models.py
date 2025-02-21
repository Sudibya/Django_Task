from django.db import models

class ItemCopy(models.Model):
    name = models.CharField(max_length=100)
    image = models.URLField(max_length=200)

    def __str__(self):
        return self.name

class Order(models.Model):
    user_id = models.IntegerField(unique=True)  # Storing user ID as a unique integer field instead of ForeignKey
    item_copy = models.IntegerField(unique=True)  # Storing item copy ID as a unique integer field instead of ForeignKey
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id}: User {self.user_id} - {self.item_copy}"