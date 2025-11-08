from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class UserRegisterForm(UserCreationForm):
    """
    Este formulario extiende el UserCreationForm nativo para
    incluir el campo de email y hacerlo obligatorio.
    """
    # 1. Añadimos el campo de email que no viene por defecto
    email = forms.EmailField(required=True, label="Correo Electrónico")

    class Meta(UserCreationForm.Meta):
        # 2. Le decimos al formulario que se base en el modelo 'User'
        model = User
        # 3. Le decimos qué campos mostrar: los originales MÁS nuestro campo 'email'
        fields = UserCreationForm.Meta.fields + ('email',)
        
class UserProfileUpdateForm(forms.ModelForm):
    """
    Formulario para que los usuarios actualicen su información personal.
    """
    email = forms.EmailField(required=True, label="Correo Electrónico")
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super(UserProfileUpdateForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['first_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Tu nombre'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Tus apellidos'})