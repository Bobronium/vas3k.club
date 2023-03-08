# Generated by Django 3.2.13 on 2023-02-01 14:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comments', '0008_auto_20210911_0827'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='historicalcomment',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical comment', 'verbose_name_plural': 'historical comments'},
        ),
        migrations.AlterField(
            model_name='historicalcomment',
            name='history_date',
            field=models.DateTimeField(db_index=True),
        ),
    ]