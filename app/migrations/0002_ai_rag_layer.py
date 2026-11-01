# Assignment 3A: AI / RAG layer schema

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='ingestion_status',
            field=models.CharField(
                choices=[('not_ingested', 'Not ingested'), ('ingested', 'Ingested'), ('failed', 'Failed')],
                default='not_ingested',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='chunk_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='document',
            name='ingested_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='DocumentChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chunk_index', models.PositiveIntegerField()),
                ('chunk_text', models.TextField()),
                ('start_char', models.PositiveIntegerField(default=0)),
                ('end_char', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='app.document')),
            ],
            options={
                'ordering': ['document_id', 'chunk_index'],
                'constraints': [
                    models.UniqueConstraint(fields=('document', 'chunk_index'), name='uniq_document_chunk_index'),
                ],
            },
        ),
        migrations.CreateModel(
            name='AIQueryLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query_type', models.CharField(choices=[('ask_ai', 'Ask AI'), ('rag_query', 'RAG Query')], max_length=20)),
                ('input_text', models.TextField()),
                ('response_text', models.TextField()),
                ('sources', models.JSONField(blank=True, default=list)),
                ('prompt_template', models.CharField(max_length=100)),
                ('model_name', models.CharField(max_length=100)),
                ('input_tokens', models.PositiveIntegerField(blank=True, null=True)),
                ('output_tokens', models.PositiveIntegerField(blank=True, null=True)),
                ('latency_ms', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_query_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at', '-id'],
                'indexes': [models.Index(fields=['user', '-created_at'], name='ai_query_user_created_idx')],
            },
        ),
    ]
