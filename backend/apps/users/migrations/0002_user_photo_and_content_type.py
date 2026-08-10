from django.db import migrations, models


def align_user_content_type(apps, schema_editor):
    """Keep existing user permission IDs while adopting the custom model label."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="auth", model="user").update(app_label="users")


def reverse_content_type(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="users", model="user").update(app_label="auth")


class Migration(migrations.Migration):
    dependencies = [("users", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="photo",
            field=models.ImageField(blank=True, null=True, upload_to="users/photos/%Y/%m/"),
        ),
        migrations.RunPython(align_user_content_type, reverse_content_type),
    ]
