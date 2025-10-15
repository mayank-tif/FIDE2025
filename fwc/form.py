from django import forms
from .models import *
import os
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result



class PlayerRegistrationForm(forms.ModelForm):
    # Make food_allergies required
    food_allergies = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter any food allergies or dietary restrictions. If none, please write "None".',
            'rows': 3
        })
    )
    
    documents = MultipleFileField(
        required=False,
        label='Express Check-in Documents',
        help_text='You can select multiple files. Maximum 10MB per file.'
    )
    
    accompanying_persons = forms.CharField(
        required=False,
        label='Are you traveling with any accompanying person(s)?',
        widget=forms.TextInput(attrs={
            'placeholder': '(e.g., John Doe, Jane Smith)',
        }),
        help_text='If traveling with family members or companions, please enter their full names separated by commas.'
    )
    
    # country = forms.ModelChoiceField(
    #     queryset=CountryMst.objects.filter(status_flag=1),
    #     required=True,
    #     label="Country",
    #     empty_label="Select your country",
    #     widget=forms.Select(attrs={'class': 'country-select'})
    # )
    
    class Meta:
        model = Players
        fields = [
            'name', 'email', 'fide_id', 'room_cleaning_preference', 'accompanying_persons'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter your full name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter your email address'}),
            'fide_id': forms.NumberInput(attrs={'placeholder': 'Enter your FIDE ID'}),
            'accompanying_persons': forms.TextInput(attrs={
                'placeholder': '(e.g., John Doe, Jane Smith)'
            }),
        }
        labels = {
            'name': 'Player Name',
            'fide_id': 'Player FIDE ID',
            'room_cleaning_preference': 'Room Cleaning Preference',
            'accompanying_persons': 'Are you traveling with any accompanying person(s)?',
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['email'].required = True
        self.fields['fide_id'].required = True
        self.fields['room_cleaning_preference'].required = True
        # self.fields['country'].required = True
        self.fields['food_allergies'].required = True
        self.fields['documents'].required = False
        self.fields['accompanying_persons'].required = False

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

    def clean_documents(self):
        documents = self.cleaned_data.get('documents')
        print("documents", documents)
        if not documents:
            return []
        
        if not isinstance(documents, list):
            documents = [documents]
        
        total_size = 0
        
        for document in documents:
            # Check file size for each document (10MB limit)
            if document.size > 10 * 1024 * 1024:  # 10MB in bytes
                raise forms.ValidationError(f'File "{document.name}" exceeds 10 MB size limit.')
            
            # Check file type
            allowed_types = ['.pdf', '.jpg', '.jpeg', '.png', '.docs', '.docx']
            file_ext = os.path.splitext(document.name)[1].lower()
            if file_ext not in allowed_types:
                raise forms.ValidationError(f'File "{document.name}" has invalid type. Allowed types: PDF, JPG, JPEG, PNG...')
            
            total_size += document.size
        
        # Check total size (50MB total limit)
        if total_size > 50 * 1024 * 1024:  # 50MB total limit
            raise forms.ValidationError('Total file size exceeds 50 MB limit.')
        
        return documents
    
    def clean_accompanying_persons(self):
        accompanying_persons = self.cleaned_data.get('accompanying_persons', '').strip()
        print("accompanying_persons", accompanying_persons)
        if accompanying_persons:
            # Split by comma and clean up names
            names = [name.strip() for name in accompanying_persons.split(',') if name.strip()]
            # Validate each name (basic validation)
            for name in names:
                if len(name) < 1:
                    raise forms.ValidationError(f'Name "{name}" is too short.')
                if len(name) > 100:
                    raise forms.ValidationError(f'Name "{name}" is too long.')
            # Return as comma-separated string for saving
            return ', '.join(names)
        return ''

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

    # def clean_country(self):
    #     country = self.cleaned_data.get('country')
    #     if not country:
    #         raise forms.ValidationError('Please select your country.')
    #     return country

    def create_audit_log(self, submission_status='SUCCESS', uploaded_documents=None, player_instance=None, error_message=None, validation_errors=None):
        """Create an audit log entry for this form submission"""
        try:
            # Prepare form data for logging
            form_data = {}
            if hasattr(self, 'cleaned_data') and self.cleaned_data:
                form_data = self.cleaned_data.copy()
            
                # Convert file objects to serializable dictionaries
                if 'documents' in form_data and form_data['documents']:
                    documents_list = []
                    for doc in form_data['documents']:
                        documents_list.append({
                            'name': doc.name,
                            'size': doc.size,
                            'content_type': doc.content_type,
                            'size_mb': round(doc.size / (1024 * 1024), 2)
                        })
                    form_data['documents'] = documents_list
            else:
                # Use raw form data if cleaned_data is not available
                form_data = dict(self.data)
                # Remove CSRF token
                form_data.pop('csrfmiddlewaretoken', None)
            
            # Get request information
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
                # 'countryid': form_data.get('country', {}).get('id') if isinstance(form_data.get('country'), dict) else None,
                
                # Additional form fields
                'food_allergies': form_data.get('food_allergies'),
                'document_file_name': ', '.join(uploaded_documents) if uploaded_documents else None,
                # 'document_file_size': form_data.get('document', {}).get('size') if isinstance(form_data.get('document'), dict) else None,
                
                # Audit log specific fields
                'submission_data': form_data,
                'user_agent': user_agent,
                'submission_status': submission_status,
                'error_message': error_message,
                'validation_errors': validation_errors or {},
                'accompanying_persons': form_data.get('accompanying_persons'),
            }
            
            print("audit_log_data", audit_log_data)
            
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
        uploaded_documents = []  # Store document info for email
        try:
            instance = super().save(commit=False)
            
            # Set default values for required fields
            instance.status = Players.STATUS_ACTIVE
            
            instance.details = self.cleaned_data.get('food_allergies', '')
            
            # Generate loginname from email if not provided
            # if not instance.loginname:
            #     instance.loginname = self.cleaned_data['email'].split('@')[0]
            
            # Set countryid from the country field
            # instance.countryid = self.cleaned_data['country']
            
            # Set other required fields with default values
            instance.status_flag = 1
            
            if commit:
                instance.save()
                
                documents = self.request.FILES.getlist('documents') if self.request else []
                fide_id = self.cleaned_data.get('fide_id')
                
                for document in documents:
                    # Create new filename with FIDE ID prefix
                    original_name = document.name
                    new_filename = f"{fide_id}_{original_name}"
                    # Store original filename for email
                    uploaded_documents.append(original_name)
                    
                    # Create PlayerDocument record
                    player_doc = PlayerDocument(
                        player=instance,
                        reg_document=document,
                        original_filename=original_name,
                        file_size=document.size,
                        document_type='IDENTIFICATION'  # You can make this dynamic if needed
                    )
                    # Rename the file
                    player_doc.reg_document.name = new_filename
                    player_doc.save()

                audit_log_instance = self.create_audit_log(
                    submission_status='SUCCESS',
                    player_instance=instance,
                    uploaded_documents=uploaded_documents
                )
                
                
            # Send welcome email
            domain = self.request.get_host()
            protocol = 'https' if self.request.is_secure() else 'http'
            image_url = f"{protocol}://{domain}/static/email/FIDE_Elements-min.png"
            
            
            html_message = render_to_string(
               'welcome.html',
               {
                   'player_name': instance.name,
                   'fide_id': instance.fide_id,
                   'email': instance.email,
                   'food_allergies': instance.details,
                   'room_cleaning_preference': instance.room_cleaning_preference,
                   'accompanying_persons': instance.accompanying_persons,
                   'uploaded_documents': uploaded_documents,  # List of document names
                   'document_count': len(uploaded_documents),
                   'image_url': image_url
               }
            )
            
            subject = "Welcome to FIDE World Cup 2025"
            
            # Create email log entry
            email_log = EmailLog.objects.create(
                email_type='WELCOME',
                subject=subject,
                recipient_email=instance.email,
                status='PENDING',
                player=instance,
                audit_log=audit_log_instance,
                html_content=html_message,
                text_content="",  # You can generate a text version if needed
            )

            send_mail(
                subject="Welcome to FIDE World Cup 2025",
                message="",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                html_message=html_message,
                fail_silently=False,
            )
            # Update email log with success
            email_log.status = 'SENT'
            email_log.save()
            
            email_log1 = EmailLog.objects.create(
                email_type='WELCOME',
                subject=subject,
                recipient_email='mayankary.ma@gmail.com',
                status='PENDING',
                player=instance,
                audit_log=audit_log_instance,
                html_content=html_message,
                text_content="",  # You can generate a text version if needed
            )
            send_mail(
                subject="Welcome to FIDE World Cup 2025",
                message="",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=["chesswc2025@gmail.com"],
                html_message=html_message,
                fail_silently=False,
            )
            # Update email log with success
            email_log1.status = 'SENT'
            email_log1.save()
            return instance
            
        except Exception as e:
            # Create failed audit log with the error
            self.create_audit_log(
                submission_status='FAILED',
                player_instance=instance,
                error_message=str(e)
            )
            raise e