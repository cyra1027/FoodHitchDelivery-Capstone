from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from django.utils import timezone
import random
import string
import requests

class Customer(models.Model):
    CustomerID = models.BigAutoField(primary_key=True)
    CustomerName = models.CharField(max_length=100)
    Username = models.CharField(max_length=100, unique=True, default='default_username')
    Email = models.EmailField(default='example@example.com')
    Phone = models.CharField(max_length=15, null=True, blank=True)
    Picture = models.ImageField(upload_to='profile_pictures', null=True, blank=True)
    Password = models.CharField(max_length=128, default='')
    Points = models.IntegerField(default=0)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Hash password only when the customer instance is created
        if self.pk is None and self.Password:
            self.Password = make_password(self.Password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.CustomerName

class Rider(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]
    
    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
    ]

    RiderID = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    FullName = models.CharField(max_length=100)
    Username = models.CharField(max_length=100, unique=True)
    Email = models.EmailField()
    Phone = models.CharField(max_length=15)
    ProfilePicture = models.ImageField(upload_to='rider_pictures', null=True, blank=True)
    License = models.ImageField(upload_to='rider_pictures', null=True, blank=True)
    PlateNumber = models.CharField(max_length=20)
    Status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    Availability = models.CharField(max_length=12, choices=AVAILABILITY_CHOICES, default='unavailable')
    latitude = models.FloatField(null=True, blank=True)  # Latitude field
    longitude = models.FloatField(null=True, blank=True)  # Longitude field

    def __str__(self):
        return self.FullName

class Restaurant(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    RestaurantID = models.BigAutoField(primary_key=True)
    RestaurantName = models.CharField(max_length=100)
    Image = models.ImageField(upload_to='restaurant_images', null=True, blank=True)
    OwnerID = models.ForeignKey('StoreOwner', on_delete=models.CASCADE, null=True, blank=True)
    BusinessPermit = models.ImageField(upload_to='businesspermit_images', null=True, blank=True)
    Status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    updated_at = models.DateTimeField(auto_now=True)
    Address = models.CharField(max_length=255, null=True, blank=True)
    Latitude = models.FloatField(null=True, blank=True)  # Add this line
    Longitude = models.FloatField(null=True, blank=True)  # Add this line

    def __str__(self):
        return self.RestaurantName

    def get_menu_url(self):
        return reverse('view_menu', args=[self.RestaurantID])
    
    def get_owner_menu_url(self):
        return reverse('owner_view_menu', args=[self.RestaurantID])

    def save(self, *args, **kwargs):
        self.set_latitude_longitude()
        super().save(*args, **kwargs)

    def set_latitude_longitude(self):
        if self.Address:
            api_key = 'AIzaSyAahMs9GBd2ChJopz74dhOjL8a0ZxXo9-k'  # Replace with your actual API key
            url = f'https://maps.googleapis.com/maps/api/geocode/json?address={self.Address}&key={api_key}'
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    location = data['results'][0]['geometry']['location']
                    self.Latitude = location['lat']
                    self.Longitude = location['lng']
class Menu(models.Model):
    FoodID = models.BigAutoField(primary_key=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    FoodName = models.CharField(max_length=100)
    Price = models.DecimalField(max_digits=10, decimal_places=2)
    Image = models.ImageField(upload_to='menu_images', null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)  # Track updates

    def __str__(self):
        return self.FoodName

class Favorite(models.Model):
    FavoriteID = models.BigAutoField(primary_key=True)
    CustomerID = models.ForeignKey('Customer', on_delete=models.CASCADE)
    FoodID = models.ForeignKey('Menu', on_delete=models.CASCADE)
    FoodName = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.FoodName} (by {self.CustomerID.CustomerName})"

class CartItem(models.Model):
    CustomerID = models.ForeignKey('Customer', on_delete=models.CASCADE)
    FoodID = models.ForeignKey('Menu', on_delete=models.CASCADE)
    FoodName = models.CharField(max_length=255)
    Quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.FoodName} (x{self.Quantity})"


class Delivery(models.Model):
    DELIVERY_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('On Transit', 'On Transit'),
        ('Delivered', 'Delivered'),
        ('Received', 'Received'),
    ]

    DeliveryID = models.BigAutoField(primary_key=True)
    OrderID = models.ForeignKey('Order', on_delete=models.CASCADE)  # A delivery can be linked to an order
    CustomerID = models.ForeignKey('Customer', on_delete=models.CASCADE)
    RiderID = models.ForeignKey('Rider', on_delete=models.CASCADE)
    RestaurantID = models.ForeignKey('Restaurant', on_delete=models.CASCADE, default=1)
    Date = models.DateTimeField(auto_now_add=True)
    Address = models.CharField(max_length=255, null=True)
    OrderTotal = models.DecimalField(max_digits=10, decimal_places=2)
    DeliveryFee = models.DecimalField(max_digits=10, decimal_places=2)
    TotalPayableAmount = models.DecimalField(max_digits=10, decimal_places=2)
    DeliveryStatus = models.CharField(max_length=50, choices=DELIVERY_STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"Delivery {self.DeliveryID}"


class Order(models.Model):
    OrderID = models.BigAutoField(primary_key=True)
    CustomerID = models.ForeignKey('Customer', on_delete=models.CASCADE)
    OrderTotal = models.DecimalField(max_digits=10, decimal_places=2)
    Date = models.DateTimeField(auto_now_add=True)
    TransactionID = models.CharField(max_length=20, unique=True, default='')

    def save(self, *args, **kwargs):
        if not self.TransactionID:
            self.TransactionID = self.generate_transaction_id()
        super().save(*args, **kwargs)

    def generate_transaction_id(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

    def get_assigned_rider(self):
        return Rider.objects.first()  # Implement logic to get the assigned rider

    def __str__(self):
        return str(self.OrderID)
    
    


class DeliveryItem(models.Model):
    Delivery = models.ForeignKey(Delivery, related_name='delivery_items', on_delete=models.CASCADE)
    FoodID = models.ForeignKey(Menu, on_delete=models.CASCADE)
    Quantity = models.IntegerField()

    class Meta:
        unique_together = ('Delivery', 'FoodID')  # Prevents duplication of food items in the same delivery

    def __str__(self):
        return f"{self.FoodID.FoodName} (x{self.Quantity})"



class CustomersFeedback(models.Model):
    FEEDBACK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    FeedbackID = models.BigAutoField(primary_key=True)
    CustomerID = models.ForeignKey(Customer, on_delete=models.CASCADE)
    CustomerName = models.CharField(max_length=100)
    RiderID = models.ForeignKey(Rider, on_delete=models.CASCADE)
    Message = models.TextField()
    DeliveryID = models.ForeignKey(Delivery, on_delete=models.CASCADE, null=True, blank=True)   # Add this field if needed
    Date = models.DateTimeField(default=timezone.now)
    Status = models.CharField(max_length=10, choices=FEEDBACK_STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Feedback from {self.CustomerName} about Rider {self.RiderID.FullName}"

    class Meta:
        verbose_name_plural = "Customers Feedback"

class StoreOwner(models.Model):
    OwnerID = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    FirstName = models.CharField(max_length=50)
    LastName = models.CharField(max_length=50)
    Username = models.CharField(max_length=100, unique=True)
    Email = models.EmailField(unique=True)
    Phone = models.CharField(max_length=15, unique=True)
    Picture = models.ImageField(upload_to='owner_pictures', null=True, blank=True)
    Password = models.CharField(max_length=128, default='')
    HasBIR203 = models.BooleanField(default=False, verbose_name="Do you have a BIR 203?")

    def save(self, *args, **kwargs):
        if self.pk is None and self.Password:
            self.Password = make_password(self.Password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.FirstName} {self.LastName} ({self.OwnerID})"

    class Meta:
        verbose_name_plural = "Store Owners"