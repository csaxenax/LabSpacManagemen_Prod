# Generated by Django 3.2 on 2023-10-05 16:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('allocationapp', '0009_auto_20230927_2330'),
    ]

    operations = [
        migrations.AddField(
            model_name='allocationdetailsmodel',
            name='RejectedBy',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='allocationdetailsmodel',
            name='RejectedDate',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
