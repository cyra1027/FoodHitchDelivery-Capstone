from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from .models import Customer, Restaurant, Menu, Rider,Delivery, Order, CustomersFeedback, StoreOwner

class CustomerRegisterForm(UserCreationForm):
    fullname = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Juan Dela Cruz'}))
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'placeholder': 'Enter a username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'example@gmail.com'}))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'placeholder': '09*********'}))
    picture = forms.ImageField(required=False)  # Optional profile picture field
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Choose a strong password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Re-enter your password'}))

    class Meta:
        model = User
        fields = ['fullname', 'username', 'email', 'phone', 'picture', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['fullname']
        if commit:
            user.save()
            customer = Customer(
                CustomerName=self.cleaned_data['fullname'],
                Username=self.cleaned_data['username'],
                Email=self.cleaned_data['email'],
                Phone=self.cleaned_data['phone'],
                user=user
            )
            if self.cleaned_data.get('picture'):
                customer.Picture = self.cleaned_data['picture']
            customer.save()
        return user

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        errors = []

        if password1:
            if len(password1) < 8:
                errors.append("This password is too short. It must contain at least 8 characters.")
            if password1 in ['12345678', 'password', '123456']:
                errors.append("This password is too common.")

        if errors:
            raise forms.ValidationError(errors)

        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")

        return password2
    
class CustomerLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))

class RiderRegisterForm(UserCreationForm):
    fullname = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Full Name'}))
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email'}))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    picture = forms.ImageField(required=False)
    license = forms.ImageField(required=False)
    platenumber = forms.CharField(max_length=10, widget=forms.TextInput(attrs={'placeholder': 'Plate Number'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

    class Meta:
        model = User
        fields = ['fullname', 'username', 'email', 'phone', 'platenumber', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['fullname']
        if commit:
            user.save()
            Rider.objects.create(
                user=user,
                FullName=self.cleaned_data['fullname'],
                Username=self.cleaned_data['username'],
                Email=self.cleaned_data['email'],
                Phone=self.cleaned_data['phone'],
                PlateNumber=self.cleaned_data['platenumber'],
                ProfilePicture=self.cleaned_data['picture'],
                License=self.cleaned_data['license'],
                Status='pending'  # Set status to 'pending'
            )
        return user
class RiderLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))


class RiderUpdateForm(forms.ModelForm):
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'Email'}))
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'placeholder': 'Current Password'}))
    password1 = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'placeholder': 'New Password'}))
    password2 = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'placeholder': 'Confirm New Password'}))
    fullname = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Full Name'}))
    phone = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'accept': 'image/*'}))
    license = forms.ImageField(required=False, widget=forms.FileInput(attrs={'accept': 'image/*'}))
    platenumber = forms.CharField(max_length=10, widget=forms.TextInput(attrs={'placeholder': 'Plate Number'}))

    class Meta:
        model = Rider
        fields = ['fullname', 'phone', 'picture', 'license', 'platenumber']

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get("password")
        new_password = cleaned_data.get("password1")
        confirm_password = cleaned_data.get("password2")

        # Validate current password if provided
        if current_password:
            if not self.instance.user.check_password(current_password):
                raise forms.ValidationError("The current password is incorrect.")

        # Ensure new password matches confirm password
        if new_password and new_password != confirm_password:
            raise forms.ValidationError("New password and confirm password do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = self.instance.user
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']

        # Only set the new password if provided
        if self.cleaned_data['password1']:
            user.set_password(self.cleaned_data['password1'])

        if commit:
            user.save()
            rider_profile = self.instance
            rider_profile.FullName = self.cleaned_data['fullname']
            rider_profile.Phone = self.cleaned_data['phone']
            rider_profile.PlateNumber = self.cleaned_data['platenumber']

            # Save picture and license if provided
            if self.cleaned_data.get('picture'):
                rider_profile.ProfilePicture = self.cleaned_data['picture']
            if self.cleaned_data.get('license'):
                rider_profile.License = self.cleaned_data['license']

            rider_profile.save()

        return user

class UserUpdateForm(forms.ModelForm):
    fullname = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Full Name'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'fullname']

    def save(self, commit=True):
        user = super(UserUpdateForm, self).save(commit=False)
        user.first_name = self.cleaned_data['fullname']
        if commit:
            user.save()
        return user

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if the email is changed and belongs to another user
        if self.instance.email != email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

class CustomerProfileUpdateForm(forms.ModelForm):
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'Email'}))
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'placeholder': 'Current Password'}))
    password1 = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'placeholder': 'New Password'}))
    password2 = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'placeholder': 'Confirm New Password'}))
    fullname = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Full Name'}))
    phone = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'accept': 'image/*'}))

    class Meta:
        model = Customer
        fields = ['fullname', 'phone', 'picture']

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get("password")
        new_password = cleaned_data.get("password1")
        confirm_password = cleaned_data.get("password2")

        if current_password and not self.instance.user.check_password(current_password):
            raise forms.ValidationError("The current password is incorrect.")

        if new_password and new_password != confirm_password:
            raise forms.ValidationError("New password and confirm password do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = self.instance.user
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']

        # Save the new password if provided
        if self.cleaned_data.get('password1'):
            user.set_password(self.cleaned_data['password1'])

        if commit:
            user.save()  # Always save the user

        # Now update the customer profile
        customer_profile = self.instance
        customer_profile.CustomerName = self.cleaned_data['fullname']  # Ensure correct attribute
        customer_profile.Phone = self.cleaned_data['phone']

        if self.cleaned_data.get('picture'):
            customer_profile.Picture = self.cleaned_data['picture']  # Ensure correct attribute

        if commit:
            customer_profile.save()  # Save the customer profile

        return user  # Return the updated profile

    

class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ['RestaurantName', 'Image', 'BusinessPermit', 'Address']  # Exclude Latitude and Longitude
        widgets = {
            'RestaurantName': forms.TextInput(attrs={'placeholder': 'Restaurant Name'}),
            'Image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'BusinessPermit': forms.ClearableFileInput(attrs={'accept': 'businesspermit/*'}),
            'Address': forms.TextInput(attrs={'placeholder': 'Address'}),
        }
        
class MenuForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = ['restaurant', 'FoodName', 'Price', 'Image']
        widgets = {
            'restaurant': forms.Select(attrs={'placeholder': 'Select Restaurant'}),
            'FoodName': forms.TextInput(attrs={'placeholder': 'Food Name'}),
            'Price': forms.NumberInput(attrs={'placeholder': 'Price', 'step': '0.01'}),
            'Image': forms.ClearableFileInput(attrs={'accept': 'image/*'})
        }
    
# Delivery form
class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['OrderID', 'CustomerID', 'RiderID', 'RestaurantID', 'Address', 'OrderTotal', 'DeliveryFee', 'TotalPayableAmount', 'DeliveryStatus']

# Order form
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['CustomerID', 'OrderTotal']

class CustomerFeedbackForm(forms.ModelForm):
    class Meta:
        model = CustomersFeedback
        fields = ['CustomerID', 'CustomerName', 'Message']  # Exclude RiderID
        widgets = {
            'CustomerID': forms.Select(attrs={'placeholder': 'Select Customer'}),
            'CustomerName': forms.TextInput(attrs={'placeholder': 'Customer Name'}),
            'Message': forms.Textarea(attrs={'placeholder': 'Your feedback', 'rows': 4, 'cols': 50}),
        }

class StoreOwnerRegisterForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    username = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email'}))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'accept': 'image/*'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

    # Custom field for HasBIR203 with Yes/No radio buttons
    HasBIR203 = forms.ChoiceField(
        choices=[(True, 'Yes'), (False, 'No')],
        widget=forms.RadioSelect,
        label="Do you have a BIR 203?"
    )

    class Meta:
        model = StoreOwner
        fields = ['first_name', 'last_name', 'username', 'email', 'phone', 'picture', 'HasBIR203']

    def save(self, commit=True):
        owner = super().save(commit=False)
        owner.FirstName = self.cleaned_data['first_name']
        owner.LastName = self.cleaned_data['last_name']
        owner.Username = self.cleaned_data['username']
        owner.Email = self.cleaned_data['email']
        owner.Phone = self.cleaned_data['phone']

        if self.cleaned_data.get('picture'):
            owner.Picture = self.cleaned_data['picture']

        # Hash the password before saving
        owner.Password = make_password(self.cleaned_data['password1'])

        # Save HasBIR203 value (True/False)
        owner.HasBIR203 = self.cleaned_data['HasBIR203'] == 'True'

        if commit:
            owner.save()
        return owner

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if StoreOwner.objects.filter(Email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        return phone

class StoreOwnerUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    username = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email'}))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    picture = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={'accept': 'image/*'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Current Password'}))
    password1 = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'placeholder': 'New Password'}))
    password2 = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'placeholder': 'Confirm New Password'}))

    class Meta:
        model = StoreOwner
        fields = ['first_name', 'last_name', 'username', 'email', 'phone', 'picture', 'password', 'password1', 'password2']

    def save(self, commit=True):
        owner = super().save(commit=False)
        owner.FirstName = self.cleaned_data['first_name']
        owner.LastName = self.cleaned_data['last_name']
        owner.Username = self.cleaned_data['username']
        owner.Email = self.cleaned_data['email']
        owner.Phone = self.cleaned_data['phone']

        if self.cleaned_data.get('picture'):
            owner.Picture = self.cleaned_data['picture']

        # If a new password is provided, hash it and update it
        new_password = self.cleaned_data.get('password1')
        if new_password:
            owner.Password = make_password(new_password)

        if commit:
            owner.save()
        return owner

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if StoreOwner.objects.filter(Email=email).exclude(OwnerID=self.instance.OwnerID).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        return phone

class PasswordResetForm(forms.Form):
    username = forms.CharField(max_length=150)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not User.objects.filter(username=username).exists():
            raise ValidationError("This username does not exist.")
        return username

class PasswordSetForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise ValidationError("Passwords do not match.")

