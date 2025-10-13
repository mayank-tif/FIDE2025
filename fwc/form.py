from django import forms
from .models import *
import os

class PlayerRegistrationForm(forms.ModelForm):
    # Make food_allergies required
    food_allergies = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter any food allergies or dietary restrictions. If none, please write "None".',
            'rows': 3
        })
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
            'name', 'email', 'fide_id', 'room_cleaning_preference'
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
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['email'].required = True
        self.fields['fide_id'].required = True
        self.fields['room_cleaning_preference'].required = True
        self.fields['country'].required = True
        self.fields['food_allergies'].required = True

    def clean_fide_id(self):
        fide_id = self.cleaned_data.get('fide_id')
        
        if not fide_id:
            raise forms.ValidationError('FIDE ID is required.')
            
        # Check if FIDE ID is already registered in Players table
        if Players.objects.filter(fide_id=fide_id).exists():
            raise forms.ValidationError('This FIDE ID is already registered.')
        
        # Check if FIDE ID exists in FideIdMst table
        try:
            fide_record = FideIDMst.objects.get(fide_id=fide_id, status_flag=1)
            self.fide_record = fide_record
        except FideIDMst.DoesNotExist:
            raise forms.ValidationError(
                'Invalid FIDE ID. Please check your FIDE ID or contact administrators.'
            )
        
        return fide_id

    def clean_document(self):
        document = self.cleaned_data.get('document')
        if not document:
            raise forms.ValidationError('Please upload a document.')
        
        # Get FIDE ID to prepend to filename
        fide_id = self.cleaned_data.get('fide_id')
        if fide_id and document:
            # Get the original filename and extension
            original_name = document.name
            name, ext = os.path.splitext(original_name)
            
            # Create new filename with FIDE ID prefix
            new_filename = f"{fide_id}_{original_name}"
            
            # Rename the file
            document.name = new_filename
        
        return document

    def clean(self):
        """Override clean to capture all validation errors"""
        cleaned_data = super().clean()
        
        # If there are validation errors, create audit log
        if self.errors:
            validation_errors = {}
            for field, errors in self.errors.items():
                validation_errors[field] = [str(error) for error in errors]
            
            self.create_audit_log(
                submission_status='VALIDATION_ERROR',
                error_message='Form validation failed',
                validation_errors=validation_errors
            )
        
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError('Email is required.')
        if Players.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError('Player name is required.')
        return name

    def clean_food_allergies(self):
        food_allergies = self.cleaned_data.get('food_allergies')
        if not food_allergies:
            raise forms.ValidationError('Please provide information about food allergies. If none, please write "None".')
        return food_allergies

    def clean_room_cleaning_preference(self):
        preference = self.cleaned_data.get('room_cleaning_preference')
        if not preference:
            raise forms.ValidationError('Please select a room cleaning preference.')
        return preference

    def clean_country(self):
        country = self.cleaned_data.get('country')
        if not country:
            raise forms.ValidationError('Please select your country.')
        return country

    def create_audit_log(self, submission_status='SUCCESS', player_instance=None, error_message=None, validation_errors=None):
        """Create an audit log entry for this form submission"""
        try:
            # Prepare form data for logging
            form_data = {}
            if hasattr(self, 'cleaned_data') and self.cleaned_data:
                form_data = self.cleaned_data.copy()
                # Handle file object for JSON serialization
                if 'document' in form_data and form_data['document']:
                    form_data['document'] = {
                        'name': form_data['document'].name,
                        'size': form_data['document'].size,
                        'content_type': form_data['document'].content_type
                    }
                # Handle country object
                if 'country' in form_data and form_data['country']:
                    form_data['country'] = {
                        'id': form_data['country'].country_id,
                        'name': form_data['country'].country_name
                    }
            else:
                # Use raw form data if cleaned_data is not available
                form_data = dict(self.data)
                # Remove CSRF token
                form_data.pop('csrfmiddlewaretoken', None)
            
            # Get request information
            ip_address = None
            user_agent = None
            if self.request:
                user_agent = self.request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length
            
            # Create audit log entry
            audit_log_data = {
                # Basic player fields from form
                'name': form_data.get('name'),
                'email': form_data.get('email'),
                'fide_id': form_data.get('fide_id'),
                'room_cleaning_preference': form_data.get('room_cleaning_preference'),
                'countryid': form_data.get('country', {}).get('id') if isinstance(form_data.get('country'), dict) else None,
                
                # Additional form fields
                'food_allergies': form_data.get('food_allergies'),
                'document_file_name': form_data.get('document', {}).get('name') if isinstance(form_data.get('document'), dict) else form_data.get('document'),
                'document_file_size': form_data.get('document', {}).get('size') if isinstance(form_data.get('document'), dict) else None,
                
                # Audit log specific fields
                'submission_data': form_data,
                'user_agent': user_agent,
                'submission_status': submission_status,
                'error_message': error_message,
                'validation_errors': validation_errors or {},
            }
            
            # Add player ID if successful
            if player_instance:
                audit_log_data['player_id'] = player_instance.id
            
            audit_log = PlayerRegistrationAuditLog(**audit_log_data)
            
            # Set default values for required fields
            audit_log.status_flag = 1
            audit_log.status = Players.STATUS_ACTIVE
            
            audit_log.save()
            return audit_log
            
        except Exception as e:
            print(f"Failed to create audit log: {str(e)}")
            return None


    def save(self, commit=True):
        """Override save to ensure audit log is created even if save fails"""
        instance = None
        try:
            instance = super().save(commit=False)
            
            # Set default values for required fields
            instance.status = Players.STATUS_ACTIVE
            
            # Generate loginname from email if not provided
            if not instance.loginname:
                instance.loginname = self.cleaned_data['email'].split('@')[0]
            
            # Set countryid from the country field
            instance.countryid = self.cleaned_data['country']
            
            # Set other required fields with default values
            instance.status_flag = 1
            
            if commit:
                instance.save()
                
                # Handle file upload - the filename already has FIDE ID prefix from clean_document method
                document = self.cleaned_data.get('document')
                if document:
                    instance.documents = document
                    instance.save()
                
                # Create success audit log
                self.create_audit_log(
                    submission_status='SUCCESS',
                    player_instance=instance
                )
            
            return instance
            
        except Exception as e:
            # Create failed audit log with the error
            self.create_audit_log(
                submission_status='FAILED',
                player_instance=instance,
                error_message=str(e)
            )
            raise e