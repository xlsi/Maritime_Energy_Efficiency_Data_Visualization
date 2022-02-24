from django import forms
from django.db import connections
from django.core.cache import cache

DAY_IN_SEC = 24 * 60 * 60


def get_choices(col: str):
    # Try to get choices from cache
    col_choices_key = f'{col}-CHOICES'
#     if col_choices_key in cache:
#         return cache[col_choices_key]

    # If choices are not in cache, query db, set cache and then return
    with connections['default'].cursor() as cursor:
        cursor.execute(f'SELECT DISTINCT {col} FROM co2emission_reduced')
        choices = [('', '---------')]
        for row in cursor.fetchall():
            choices.append((row[0], row[0]))
    cache.set(col_choices_key, choices, timeout=DAY_IN_SEC)
    return choices


class ImoForm(forms.Form):
    imo = forms.IntegerField(label='IMO Number', min_value=1111111, max_value=9999999)
    ship_name = forms.CharField(max_length=64)
    # ship_type = forms.CharField(max_length=64)
    ship_type = forms.ChoiceField(choices=get_choices('ship_type'), required=False)
    issue_date = forms.DateField(widget=forms.widgets.DateInput(attrs={'type': 'date'}), required=False)
    expiry_date = forms.DateField(widget=forms.widgets.DateInput(attrs={'type': 'date'}), required=False)
    eedi = forms.DecimalField(label='EEDI', max_digits=6, min_value=0, required=False)
    
class ShipForm(forms.Form):
    ship_key  = forms.IntegerField(label='Ship Key', min_value=10000, max_value=100000)
    imo = forms.IntegerField(label='IMO Number', min_value=1111111, max_value=9999999)
    ship_name = forms.CharField(max_length=64)
    ship_type = forms.ChoiceField(choices=get_choices('ship_type'), required=False)
    home_port = forms.CharField(label='Home port', max_length=64)
    ice_class = forms.CharField(label='Ice class', max_length=64)
    report_period = forms.CharField(label='Report Period', max_length=64)

class Verifier(forms.Form):
    verifier_key = forms.IntegerField(label='Ship Key', min_value=10000, max_value=100000)
    verfier_num = forms.CharField(label='Verifier Number', max_length=64)
    verify_name = forms.CharField(label='Verifier Name', max_length=64)
    verify_nab = forms.CharField(label='Verifier NAB', max_length=64)
    verify_city = forms.CharField(label='Verifier City', max_length=64)
    verifier_acc = forms.CharField(label='Verifier Accreditation number', max_length=64)
    verifier_country= forms.CharField(label='Verifier Country', max_length=64)

class IssueDate(forms.Form):
    issue_date_key = forms.IntegerField(label='Issue Date Key', min_value=10000, max_value=100000)
    issue_date = forms.DateField(label = 'Issue Date', widget=forms.widgets.DateInput(attrs={'type': 'date'}), required=False)
    issue_year = forms.IntegerField(label='Year', min_value=1900, max_value=2050)
    issue_month = forms.IntegerField(label='Month', min_value=1, max_value=12)
    issue_day = forms.IntegerField(label='Day', min_value=1, max_value=31)

class ExpireDate(forms.Form):
    expire_date_key = forms.IntegerField(label='Expire Date Key', min_value=10000, max_value=100000)
    expiry_date = forms.DateField(label = 'Expire Date', widget=forms.widgets.DateInput(attrs={'type': 'date'}), required=False)
    expire_year = forms.IntegerField(label='Year', min_value=1900, max_value=2050)
    expire_month = forms.IntegerField(label='Month', min_value=1, max_value=12)
    expire_day = forms.IntegerField(label='Day', min_value=1, max_value=31)
