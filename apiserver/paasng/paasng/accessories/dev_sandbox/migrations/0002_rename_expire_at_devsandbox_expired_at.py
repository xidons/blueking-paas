# Generated by Django 4.2.16 on 2024-11-11 07:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dev_sandbox', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='devsandbox',
            old_name='expire_at',
            new_name='expired_at',
        ),
    ]