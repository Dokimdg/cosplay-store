import re

from django import forms

from .models import ShippingAddress


class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ('full_name', 'phone', 'city', 'address', 'postal_code', 'comment')
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '+380501234567'}),
            'address': forms.TextInput(attrs={'placeholder': 'Вулиця, будинок або відділення Нової пошти'}),
            'comment': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        digits = re.sub(r'\D', '', phone)
        if not 10 <= len(digits) <= 15:
            raise forms.ValidationError('Введіть коректний номер телефону.')
        return phone

    def clean_postal_code(self):
        code = self.cleaned_data['postal_code'].strip()
        if code and not code.isdigit():
            raise forms.ValidationError('Індекс має складатися лише з цифр.')
        return code
