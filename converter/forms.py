from django import forms
from django.conf import settings


class UploadForm(forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'hidden', 'id': 'file-input'}),
        help_text="Max 50MB"
    )

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f:
            max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024)
            if f.size > max_size:
                raise forms.ValidationError(
                    f"File too large. Maximum size is {max_size // (1024*1024)}MB."
                )
        return f


# ── Modified existing forms ────────────────────────────────────

class CompressPDFForm(UploadForm):
    LEVEL_CHOICES = [
        ('extreme',     'Extreme — Smallest file size'),
        ('recommended', 'Recommended — Best balance'),
        ('less',        'Less — Best quality'),
    ]
    level = forms.ChoiceField(
        choices=LEVEL_CHOICES,
        initial='recommended',
        required=False,
        label='Compression Level'
    )


class PDFToImagesForm(UploadForm):
    DPI_CHOICES = [
        ('72',  '72 DPI — Web / screen'),
        ('150', '150 DPI — Standard quality'),
        ('300', '300 DPI — Print quality'),
    ]
    FORMAT_CHOICES = [
        ('png',  'PNG — Lossless (largest)'),
        ('jpeg', 'JPEG — Smaller size'),
        ('webp', 'WebP — Modern, smallest'),
    ]
    dpi = forms.ChoiceField(
        choices=DPI_CHOICES,
        initial='150',
        required=False,
        label='Resolution'
    )
    img_format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial='png',
        required=False,
        label='Image Format'
    )


class PNGToJPGForm(UploadForm):
    quality = forms.IntegerField(
        min_value=10,
        max_value=95,
        initial=85,
        required=False,
        label='Quality',
        widget=forms.NumberInput(attrs={'type': 'range', 'min': '10', 'max': '95', 'step': '5'})
    )


class SplitPDFForm(UploadForm):
    start_page = forms.IntegerField(
        required=False, min_value=1,
        widget=forms.NumberInput(attrs={'placeholder': '1'}),
        label="Start Page"
    )
    end_page = forms.IntegerField(
        required=False, min_value=1,
        widget=forms.NumberInput(attrs={'placeholder': 'Last page'}),
        label="End Page"
    )


class ResizeImageForm(UploadForm):
    width = forms.IntegerField(
        required=False, min_value=1, max_value=10000,
        widget=forms.NumberInput(attrs={'placeholder': 'Width (px)'}),
        label="Width (px)"
    )
    height = forms.IntegerField(
        required=False, min_value=1, max_value=10000,
        widget=forms.NumberInput(attrs={'placeholder': 'Height (px)'}),
        label="Height (px)"
    )


# ── New forms for Round 1 tools ────────────────────────────────

class PasswordProtectForm(UploadForm):
    user_password = forms.CharField(
        min_length=4,
        max_length=128,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password', 'autocomplete': 'new-password'}),
        label='Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password', 'autocomplete': 'new-password'}),
        label='Confirm Password'
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('user_password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned


class UnlockPDFForm(UploadForm):
    password = forms.CharField(
        required=False,
        max_length=128,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'PDF password (leave blank if none)',
            'autocomplete': 'current-password'
        }),
        label='PDF Password'
    )


class RotatePDFForm(UploadForm):
    ROTATION_CHOICES = [
        ('90',  '90° Clockwise'),
        ('180', '180°'),
        ('270', '90° Counter-clockwise'),
    ]
    PAGE_CHOICES = [
        ('all',  'All pages'),
        ('odd',  'Odd pages only'),
        ('even', 'Even pages only'),
    ]
    rotation = forms.ChoiceField(
        choices=ROTATION_CHOICES,
        initial='90',
        label='Rotation'
    )
    page_range = forms.ChoiceField(
        choices=PAGE_CHOICES,
        initial='all',
        label='Apply to'
    )


class WatermarkPDFForm(UploadForm):
    POSITION_CHOICES = [
        ('diagonal', 'Diagonal (recommended)'),
        ('center',   'Center'),
        ('top',      'Top'),
        ('bottom',   'Bottom'),
    ]
    watermark_text = forms.CharField(
        max_length=50,
        initial='CONFIDENTIAL',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. CONFIDENTIAL, DRAFT, TOP SECRET'}),
        label='Watermark Text'
    )
    opacity = forms.IntegerField(
        min_value=5,
        max_value=80,
        initial=30,
        required=False,
        label='Opacity (%)',
        widget=forms.NumberInput(attrs={'type': 'range', 'min': '5', 'max': '80', 'step': '5'})
    )
    position = forms.ChoiceField(
        choices=POSITION_CHOICES,
        initial='diagonal',
        label='Position'
    )


class PageNumbersForm(UploadForm):
    POSITION_CHOICES = [
        ('bottom-center', 'Bottom center'),
        ('bottom-right',  'Bottom right'),
        ('bottom-left',   'Bottom left'),
        ('top-center',    'Top center'),
        ('top-right',     'Top right'),
        ('top-left',      'Top left'),
    ]
    position = forms.ChoiceField(
        choices=POSITION_CHOICES,
        initial='bottom-center',
        label='Position'
    )
    start_number = forms.IntegerField(
        min_value=1,
        initial=1,
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': '1'}),
        label='Start from'
    )
    font_size = forms.IntegerField(
        min_value=6,
        max_value=24,
        initial=10,
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': '10'}),
        label='Font size (pt)'
    )


# ── New forms for Round 6 tools ────────────────────────────────

class EditMetadataForm(UploadForm):
    title = forms.CharField(required=False, label='Title', widget=forms.TextInput(attrs={'placeholder': 'Document Title'}))
    author = forms.CharField(required=False, label='Author', widget=forms.TextInput(attrs={'placeholder': 'Author Name'}))
    subject = forms.CharField(required=False, label='Subject', widget=forms.TextInput(attrs={'placeholder': 'Subject'}))
    keywords = forms.CharField(required=False, label='Keywords', widget=forms.TextInput(attrs={'placeholder': 'keyword1, keyword2'}))


class CropPDFForm(UploadForm):
    margin_top = forms.IntegerField(required=False, initial=0, label='Top Margin (pt)', widget=forms.NumberInput(attrs={'placeholder': '0'}))
    margin_bottom = forms.IntegerField(required=False, initial=0, label='Bottom Margin (pt)', widget=forms.NumberInput(attrs={'placeholder': '0'}))
    margin_left = forms.IntegerField(required=False, initial=0, label='Left Margin (pt)', widget=forms.NumberInput(attrs={'placeholder': '0'}))
    margin_right = forms.IntegerField(required=False, initial=0, label='Right Margin (pt)', widget=forms.NumberInput(attrs={'placeholder': '0'}))
