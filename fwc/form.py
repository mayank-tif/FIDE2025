# from django import forms
# from .models import Players

# class PlayerRegistrationForm(forms.ModelForm):
#     # Add additional fields that are in your template but not in the model
#     food_allergies = forms.CharField(
#         required=False,
#         widget=forms.Textarea(attrs={'placeholder': 'Enter any food allergies or dietary restrictions'})
#     )
    
#     document = forms.FileField(
#         required=True,
#         label='Express Check-in Documents'
#     )
    
#     class Meta:
#         model = Players
#         fields = [
#             'name', 'email', 'fide_id', 'room_cleaning_preference'
#         ]
#         widgets = {
#             'name': forms.TextInput(attrs={'placeholder': 'Enter your full name'}),
#             'email': forms.EmailInput(attrs={'placeholder': 'Enter your email address'}),
#             'fide_id': forms.NumberInput(attrs={'placeholder': 'Enter your FIDE ID'}),
#         }
#         labels = {
#             'name': 'Player Name',
#             'fide_id': 'Player FIDE ID',
#             'room_cleaning_preference': 'Room Cleaning Preference',
#         }
    
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Make fields required
#         self.fields['name'].required = True
#         self.fields['email'].required = True
#         self.fields['fide_id'].required = True
#         self.fields['room_cleaning_preference'].required = True
    
#     def clean_fide_id(self):
#         fide_id = self.cleaned_data.get('fide_id')
#         if fide_id and Players.objects.filter(fide_id=fide_id).exists():
#             raise forms.ValidationError('This FIDE ID is already registered.')
#         return fide_id
    
#     def clean_email(self):
#         email = self.cleaned_data.get('email')
#         if email and Players.objects.filter(email=email).exists():
#             raise forms.ValidationError('This email is already registered.')
#         return email
    
#     def save(self, commit=True):
#         instance = super().save(commit=False)
        
#         # Set default values for required fields
#         instance.status = Players.STATUS_ACTIVE
#         instance.loginname = self.cleaned_data['email'].split('@')[0]  # Simple username from email
        
#         if commit:
#             instance.save()
#             # Handle file upload
#             document = self.cleaned_data.get('document')
#             if document:
#                 instance.documents = document
#                 instance.save()
        
#         return instance
    
    
from django import forms
from .models import Players, CountryMst

class PlayerRegistrationForm(forms.ModelForm):
    # Add additional fields that are in your template but not in the model
    food_allergies = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'placeholder': 'Enter any food allergies or dietary restrictions'})
    )
    
    document = forms.FileField(
        required=True,
        label='Express Check-in Documents'
    )
    
    country = forms.ModelChoiceField(
        queryset=CountryMst.objects.filter(status_flag=1),
        required=True,
        label="Country",
        empty_label="Select your country",
        widget=forms.Select(attrs={'class': 'country-select'})
    )
    
    class Meta:
        model = Players
        fields = [
            'name', 'email', 'fide_id', 'room_cleaning_preference', 'country'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter your full name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter your email address'}),
            'fide_id': forms.NumberInput(attrs={'placeholder': 'Enter your FIDE ID'}),
        }
        labels = {
            'name': 'Player Name',
            'fide_id': 'Player FIDE ID',
            'room_cleaning_preference': 'Room Cleaning Preference',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields required
        self.fields['name'].required = True
        self.fields['email'].required = True
        self.fields['fide_id'].required = True
        self.fields['room_cleaning_preference'].required = True
        self.fields['country'].required = True
    
    def clean_fide_id(self):
        fide_id = self.cleaned_data.get('fide_id')
        if fide_id and Players.objects.filter(fide_id=fide_id).exists():
            raise forms.ValidationError('This FIDE ID is already registered.')
        return fide_id
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and Players.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set default values for required fields
        instance.status = Players.STATUS_ACTIVE
        instance.countryid = self.cleaned_data['country']  # Set the country foreign key
        
        if commit:
            instance.save()
            # Handle file upload
            document = self.cleaned_data.get('document')
            if document:
                instance.documents = document
                instance.save()
        
        return instance