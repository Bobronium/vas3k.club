# Generated by Django 3.1 on 2020-08-09 16:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comments', '0005_auto_20200424_1144'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='metadata',
            field=models.JSONField(null=True),
        ),
        migrations.AlterField(
            model_name='historicalcomment',
            name='metadata',
            field=models.JSONField(null=True),
        ),
    ]