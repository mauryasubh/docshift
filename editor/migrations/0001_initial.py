from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EditorSession',
            fields=[
                ('id',            models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('is_guest',      models.BooleanField(default=True)),
                ('original_file', models.FileField(upload_to='editor/originals/')),
                ('original_name', models.CharField(blank=True, default='', max_length=255)),
                ('original_size', models.BigIntegerField(default=0)),
                ('pdf_type',      models.CharField(choices=[('unknown','Unknown'),('generated','Generated'),('scanned','Scanned'),('mixed','Mixed')], default='unknown', max_length=20)),
                ('page_count',    models.IntegerField(default=0)),
                ('status',        models.CharField(choices=[('analysing','Analysing'),('ready','Ready'),('saving','Saving'),('saved','Saved'),('failed','Failed')], default='analysing', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('blocks_json',   models.JSONField(default=list)),
                ('images_json',   models.JSONField(default=list)),
                ('result_file',   models.FileField(blank=True, null=True, upload_to='editor/results/')),
                ('result_size',   models.BigIntegerField(default=0)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('expires_at',    models.DateTimeField(blank=True, null=True)),
                ('user',          models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='editor_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
