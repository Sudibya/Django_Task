# Generated by Django 4.2.6 on 2025-02-20 13:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemcopy',
            name='image',
            field=models.URLField(),
        ),
    ]
