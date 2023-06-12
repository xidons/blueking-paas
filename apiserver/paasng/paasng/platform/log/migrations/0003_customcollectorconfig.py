# Generated by Django 3.2.12 on 2023-05-04 02:32

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0006_auto_20220509_1544'),
        ('log', '0002_auto_20230413_1744'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomCollectorConfig',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True, verbose_name='UUID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('name_en', models.CharField(help_text='5-50个字符，仅包含字母数字下划线, 查询索引是 name_en-*', max_length=50, unique=True, verbose_name='自定义采集项名称')),
                ('collector_config_id', models.BigIntegerField(help_text='采集配置ID', unique=True, verbose_name='采集配置ID')),
                ('index_set_id', models.BigIntegerField(help_text='查询时使用', verbose_name='索引集ID', null=True)),
                ('bk_data_id', models.BigIntegerField(verbose_name='数据管道ID')),
                ('log_paths', models.JSONField(verbose_name='日志采集路径')),
                ('log_type', models.CharField(max_length=32, verbose_name='日志类型')),
                ('module', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='modules.module')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]