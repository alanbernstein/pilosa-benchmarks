# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-10-03 03:13
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Benchmark',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('config', django.contrib.postgres.fields.jsonb.JSONField()),
                ('stats', django.contrib.postgres.fields.jsonb.JSONField()),
                ('extra', django.contrib.postgres.fields.jsonb.JSONField()),
                ('name', models.CharField(max_length=250)),
                ('stats_total_us', models.BigIntegerField()),
                ('stats_max_us', models.BigIntegerField()),
                ('stats_min_us', models.BigIntegerField()),
                ('stats_num', models.BigIntegerField()),
                ('stats_mean_us', models.BigIntegerField()),
                ('config_index', models.CharField(max_length=250)),
                ('agentnum', models.IntegerField()),
                ('error', models.CharField(max_length=250)),
                ('duration_us', models.BigIntegerField()),
                ('pilosa_version', models.CharField(max_length=250)),
            ],
        ),
        migrations.CreateModel(
            name='Run',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('config', django.contrib.postgres.fields.jsonb.JSONField()),
                ('uuid', models.CharField(max_length=250)),
                ('pi_version', models.CharField(max_length=250)),
                ('pi_build_time', models.DateTimeField()),
                ('spawn_file', models.URLField()),
            ],
        ),
        migrations.AddField(
            model_name='benchmark',
            name='run',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Run'),
        ),
    ]
