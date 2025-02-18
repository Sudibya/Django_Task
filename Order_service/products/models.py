from django.db import models

class CustomUser(models.Model):  # Renamed to avoid conflict with Django's built-in User model
    username = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username  # Returns the username when printed


class Item(models.Model):
    name = models.CharField(max_length=100)  # Changed itemname to name for consistency
    image = models.ImageField(upload_to='items/')  # Renamed to image (cleaner)
    likes = models.PositiveIntegerField(default=0)  # Ensures likes are non-negative

    def __str__(self):
        return self.name  # Returns the item name when printed
