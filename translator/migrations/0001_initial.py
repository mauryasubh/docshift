from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='TranslationJob',
            fields=[
                ('id',            models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('is_guest',      models.BooleanField(default=True)),
                ('original_file', models.FileField(upload_to='translator/originals/')),
                ('result_file',   models.FileField(blank=True, null=True, upload_to='translator/results/')),
                ('original_name', models.CharField(blank=True, default='', max_length=255)),
                ('original_size', models.BigIntegerField(default=0)),
                ('result_size',   models.BigIntegerField(default=0)),
                ('source_lang',   models.CharField(default='auto', max_length=10)),
                ('target_lang',   models.CharField(default='en', max_length=10)),
                ('status',        models.CharField(choices=[('pending','Pending'),('processing','Processing'),('done','Done'),('failed','Failed')], default='pending', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('char_count',    models.IntegerField(default=0)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('expires_at',    models.DateTimeField(blank=True, null=True)),
                ('user',          models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='translation_jobs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
