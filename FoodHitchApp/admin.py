from django.contrib import admin
from .models import Customer, Restaurant, Menu, Favorite, Rider, CustomersFeedback, Delivery, Order, StoreOwner, Message

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('CustomerID', 'CustomerName', 'user_username', 'user_email', 'Phone')

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Username'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'


class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('RestaurantID', 'OwnerID', 'RestaurantName', 'Image', 'Status')
    search_fields = ('RestaurantName',)


class MenuAdmin(admin.ModelAdmin):
    list_display = ('FoodID', 'restaurant_id', 'restaurant_name', 'FoodName', 'Price', 'Image')
    list_filter = ('restaurant',)
    search_fields = ('FoodName', 'restaurant__RestaurantName')

    def restaurant_id(self, obj):
        return obj.restaurant.RestaurantID
    restaurant_id.short_description = 'RestaurantID'

    def restaurant_name(self, obj):
        return obj.restaurant.RestaurantName
    restaurant_name.short_description = 'Restaurant Name'


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('FavoriteID', 'CustomerID', 'FoodID', 'FoodName')
    list_filter = ('CustomerID', 'FoodID')
    search_fields = ('FoodName', 'CustomerID__CustomerName', 'FoodID__FoodName')


class RiderAdmin(admin.ModelAdmin):
    list_display = ('RiderID', 'FullName', 'Username', 'Email', 'Phone', 'License', 'PlateNumber')
    search_fields = ('FullName', 'Username', 'Email', 'License', 'PlateNumber')


# New Admin for Customer Feedback
class CustomerFeedbackAdmin(admin.ModelAdmin):
    list_display = ('FeedbackID', 'CustomerID', 'CustomerName', 'RiderID', 'Message', 'Date', 'Status')
    list_filter = ('CustomerID', 'RiderID', 'Status')
    search_fields = ('CustomerName', 'Message')
    actions = ['approve_feedback']

    def approve_feedback(self, request, queryset):
        queryset.update(Status='approved')
        self.message_user(request, "Selected feedback has been approved.")
    approve_feedback.short_description = "Approve selected feedback"


class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        'DeliveryID', 'OrderID', 'CustomerID', 'RiderID', 'Date', 
        'Address', 'OrderTotal', 'DeliveryFee', 'TotalPayableAmount', 
        'DeliveryStatus', 'get_food_names'  # Add custom method to display food names
    )
    list_filter = ('DeliveryStatus', 'Date', 'RiderID')
    search_fields = ('OrderID__OrderID', 'CustomerID__CustomerName', 'RiderID__FullName', 'Address')

    def get_food_names(self, obj):
        # Get all related DeliveryItems and join their FoodNames
        return ', '.join([item.FoodID.FoodName for item in obj.delivery_items.all()])

    get_food_names.short_description = 'Food Items'  # Display name in the admin


class OrderAdmin(admin.ModelAdmin):
    list_display = ('OrderID', 'CustomerID', 'OrderTotal', 'Date')  # Removed 'FoodID'
    list_filter = ('Date', 'CustomerID')  # Removed 'FoodID'
    search_fields = ('OrderID', 'CustomerID__CustomerName')  # Removed 'FoodID__FoodName'
    date_hierarchy = 'Date'


# New Admin for Store Owner
class StoreOwnerAdmin(admin.ModelAdmin):
    list_display = ('OwnerID', 'FirstName', 'LastName', 'Username', 'Email', 'Phone', 'HasBIR203')
    search_fields = ('FirstName', 'LastName', 'Username', 'Email')

class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'timestamp', 'message_snippet')
    search_fields = ('sender__username', 'receiver__username', 'message')  # Search by sender/receiver username and message content
    list_filter = ('sender', 'receiver', 'timestamp')  # Filter messages by sender, receiver, and timestamp
    ordering = ('-timestamp',)  # Order by the most recent message first

    def message_snippet(self, obj):
        """Display a short snippet of the message"""
        return obj.message[:50]  # Shows the first 50 characters of the message
    message_snippet.short_description = 'Message Preview'







# Registering all models including StoreOwner
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Restaurant, RestaurantAdmin)
admin.site.register(Menu, MenuAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(Rider, RiderAdmin)
admin.site.register(CustomersFeedback, CustomerFeedbackAdmin)
admin.site.register(Delivery, DeliveryAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(StoreOwner, StoreOwnerAdmin)
admin.site.register(Message, MessageAdmin)