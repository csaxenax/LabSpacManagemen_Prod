# Generated by Django 3.2 on 2024-03-12 04:31

import allocationapp.models
from django.db import migrations, models
import djongo.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('allocationapp', '0011_auto_20240212_1208'),
    ]

    operations = [
        migrations.CreateModel(
            name='BoardAllocationDataModel',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('Program', models.CharField(blank=True, max_length=100)),
                ('Sku', models.CharField(blank=True, max_length=100)),
                ('Team', models.CharField(blank=True, max_length=255)),
                ('Vendor', models.CharField(blank=True, max_length=255)),
                ('TotalBoard', models.IntegerField(default=0)),
                ('createdBy', models.CharField(blank=True, max_length=255)),
                ('createdDate', models.DateTimeField(auto_now_add=True, null=True)),
                ('modifiedBy', models.CharField(blank=True, max_length=255, null=True)),
                ('modifiedDate', models.DateTimeField(auto_now_add=True, null=True)),
                ('deletedBy', models.CharField(blank=True, max_length=255)),
                ('deletedDate', models.DateTimeField(auto_now_add=True, null=True)),
                ('isdeleted', models.BooleanField(default=False)),
                ('year', models.PositiveIntegerField()),
                ('January', djongo.models.fields.JSONField()),
                ('February', djongo.models.fields.JSONField()),
                ('March', djongo.models.fields.JSONField()),
                ('April', djongo.models.fields.JSONField()),
                ('May', djongo.models.fields.JSONField()),
                ('June', djongo.models.fields.JSONField()),
                ('July', djongo.models.fields.JSONField()),
                ('August', djongo.models.fields.JSONField()),
                ('September', djongo.models.fields.JSONField()),
                ('October', djongo.models.fields.JSONField()),
                ('November', djongo.models.fields.JSONField()),
                ('December', djongo.models.fields.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='BoardAllocationDataModelTrackData',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('instance_id', models.IntegerField()),
                ('Program', models.CharField(blank=True, max_length=100)),
                ('Sku', models.CharField(blank=True, max_length=100)),
                ('Team', models.CharField(blank=True, max_length=255)),
                ('Vendor', models.CharField(blank=True, max_length=255)),
                ('TotalBoard', models.IntegerField(default=0)),
                ('createdBy', models.CharField(blank=True, max_length=255)),
                ('createdDate', models.DateTimeField(auto_now_add=True, null=True)),
                ('modifiedBy', models.CharField(blank=True, max_length=255, null=True)),
                ('modifiedDate', models.DateTimeField(auto_now_add=True, null=True)),
                ('deletedBy', models.CharField(blank=True, max_length=255)),
                ('deletedDate', models.DateTimeField(auto_now_add=True, null=True)),
                ('isdeleted', models.BooleanField(default=False)),
                ('year', models.PositiveIntegerField()),
                ('January', djongo.models.fields.JSONField()),
                ('February', djongo.models.fields.JSONField()),
                ('March', djongo.models.fields.JSONField()),
                ('April', djongo.models.fields.JSONField()),
                ('May', djongo.models.fields.JSONField()),
                ('June', djongo.models.fields.JSONField()),
                ('July', djongo.models.fields.JSONField()),
                ('August', djongo.models.fields.JSONField()),
                ('September', djongo.models.fields.JSONField()),
                ('October', djongo.models.fields.JSONField()),
                ('November', djongo.models.fields.JSONField()),
                ('December', djongo.models.fields.JSONField()),
                ('action', models.CharField(choices=[('insert', 'Insert'), ('update', 'Update'), ('delete', 'Delete')], max_length=250)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='BroadcastModel',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('Subject', models.CharField(blank=True, max_length=100, null=True)),
                ('Content', models.CharField(blank=True, max_length=100, null=True)),
                ('BroadCast_by', djongo.models.fields.ArrayField(blank=True, model_container=allocationapp.models.AllocatedToModel, null=True)),
                ('NewUser', djongo.models.fields.ArrayField(blank=True, model_container=allocationapp.models.AllocatedToModel, null=True)),
                ('CreatedDate', models.DateTimeField(auto_now_add=True, null=True)),
                ('User_mail_list', djongo.models.fields.JSONField(blank=True, null=True)),
            ],
        ),
    ]
