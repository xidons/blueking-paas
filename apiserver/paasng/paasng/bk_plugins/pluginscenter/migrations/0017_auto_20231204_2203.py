# Generated by Django 3.2.12 on 2023-12-04 14:03

from django.db import migrations
import paasng.bk_plugins.pluginscenter.models.definitions


class Migration(migrations.Migration):

    dependencies = [
        ('pluginscenter', '0016_auto_20231204_2121'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pluginbasicinfodefinition',
            name='extra_fields_en',
            field=paasng.bk_plugins.pluginscenter.models.definitions.PluginExtraFieldField(default=dict),
        ),
        migrations.AlterField(
            model_name='pluginmarketinfodefinition',
            name='extra_fields_en',
            field=paasng.bk_plugins.pluginscenter.models.definitions.PluginExtraFieldField(default=dict),
        ),
    ]