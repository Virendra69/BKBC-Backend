# Generated by Django 4.2.2 on 2023-07-07 11:54

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Photo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        upload_to="App2\\static\\uploaded_photo\\uploaded_photo.jpg"
                    ),
                ),
            ],
        ),
    ]
