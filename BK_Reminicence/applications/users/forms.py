from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class UserRegisterForm(UserCreationForm):
    """
    Formulario de registro que hereda de UserCreationForm y añade validación para
    la existencia del email y personaliza el mensaje del username.
    """
    email = forms.EmailField(
        required=True,
        label="Correo Electrónico",
        help_text="Obligatorio. Se usará para la recuperación de la cuenta."
    )

    class Meta(UserCreationForm.Meta):
        model = User 
        fields = ('username', 'email')

    def clean_email(self):
        """
        Este método se ejecuta al validar el formulario.
        Comprueba si el email introducido ya existe en la base de datos.
        """
        email = self.cleaned_data.get('email').lower() 
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe una cuenta registrada con este correo electrónico.")
        
        
        return email

    def clean_username(self):
        """
        Este método personaliza el mensaje de error si el username ya existe.
        UserCreationForm ya hace esta validación, pero así el mensaje es más claro.
        """
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso. Por favor, elige otro.")
        
        return username
        
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