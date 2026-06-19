from django.db import migrations, models


def set_existing_di_false(apps, schema_editor):
    BankAccount = apps.get_model('bank', 'BankAccount')
    BankAccount.objects.all().update(is_di=False)


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0005_protect_transfer_beneficiary'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankaccount',
            name='is_di',
            field=models.BooleanField(default=True, verbose_name='Dossier Incomplet (DI)'),
        ),
        migrations.AddField(
            model_name='bankaccount',
            name='di_note',
            field=models.TextField(blank=True, verbose_name='Note DI'),
        ),
        migrations.RunPython(set_existing_di_false, migrations.RunPython.noop),
    ]
