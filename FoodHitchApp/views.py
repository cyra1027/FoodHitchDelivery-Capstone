from django.shortcuts import render, redirect, get_object_or_404
from .models import Customer, Restaurant, Menu, CartItem, Favorite, Rider,CustomersFeedback, Delivery, DeliveryItem, Order, StoreOwner
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CustomerRegisterForm, CustomerLoginForm, UserUpdateForm, CustomerProfileUpdateForm, RiderRegisterForm, MenuForm, RestaurantForm, RiderUpdateForm, StoreOwnerRegisterForm, StoreOwnerUpdateForm
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse, Http404
import json
import random
from django.contrib.auth.hashers import make_password
from .forms import PasswordResetForm, PasswordSetForm
import logging
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.conf import settings
from decimal import Decimal
from django.utils.timezone import now
from calendar import month_name
from django.db.models import Sum
import requests
from geopy.distance import geodesic
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.views.decorators.cache import never_cache
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime
from PIL import Image, ImageFilter
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Q
import matplotlib
matplotlib.use('Agg')

def is_blurred(image_file: InMemoryUploadedFile) -> bool:
    img = Image.open(image_file).convert('RGB')  # Ensure the image is in RGB format
    sharpened = img.filter(ImageFilter.SHARPEN)

    original_data = list(img.getdata())
    sharpened_data = list(sharpened.getdata())

    # Calculate the differences for each channel in the RGB tuples
    differences = sum(
        sum(abs(o - s) for o, s in zip(original_pixel, sharpened_pixel))
        for original_pixel, sharpened_pixel in zip(original_data, sharpened_data)
    )

    threshold = 5000  # Adjust this value based on your needs

    return differences < threshold  # Return True if blurred
def customer_register(request):
    if request.method == 'POST':
        form = CustomerRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account has been created successfully!')
            return redirect('customer_login')
        else:
            messages.error(request, 'There was an error with your registration. Please check the form and try again.')
            print(form.errors)
    else:
        form = CustomerRegisterForm()

    return render(request, 'customer_register.html', {'form': form})
def rider_register(request):
    if request.method == 'POST':
        form = RiderRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            picture = form.cleaned_data['picture']
            license_file = form.cleaned_data['license']

            # Check if the uploaded images are blurred
            if is_blurred(picture):
                return JsonResponse({'status': 'error', 'message': 'Profile picture is blurred. Please upload a clearer image.'})
            if is_blurred(license_file):
                return JsonResponse({'status': 'error', 'message': 'Driver\'s license image is blurred. Please upload a clearer image.'})

            user = form.save(commit=False)
            user.save()

            Rider.objects.create(
                user=user,
                FullName=form.cleaned_data['fullname'],
                Username=form.cleaned_data['username'],
                Email=form.cleaned_data['email'],
                Phone=form.cleaned_data['phone'],
                PlateNumber=form.cleaned_data['platenumber'],
                ProfilePicture=form.cleaned_data['picture'],
                License=form.cleaned_data['license'],
                Status='pending'
            )

            # Success message
            return JsonResponse({'status': 'success', 'message': 'Your application has been sent. You will be receiving an email about your application.'})
        else:
            errors = {field: errors for field, errors in form.errors.items()}
            return JsonResponse({'status': 'error', 'errors': errors})
    else:
        form = RiderRegisterForm()

    return render(request, 'rider_register.html', {'form': form})
def owners_register(request):
    if request.method == 'POST':
        form = StoreOwnerRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            # Get the cleaned data
            username = form.cleaned_data.get('username')  # Make sure this matches the field name in the form
            
            user = User.objects.create_user(
                username=username,
                email=form.cleaned_data.get('email'),
                password=form.cleaned_data.get('password1')  # Assuming this is the correct field
            )
            
            owner = form.save(commit=False)
            owner.user = user
            owner.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = StoreOwnerRegisterForm()

    return render(request, 'owner_register.html', {'form': form})

def owner_base(request):
    return render(request, "owner_base.html")

@login_required
def owner_add_restaurant(request):
    store_owner = get_object_or_404(StoreOwner, user=request.user)

    if request.method == 'POST':
        form = RestaurantForm(request.POST, request.FILES)
        if form.is_valid():
            address = form.cleaned_data['Address']

            # Google Maps Geocoding API
            google_maps_api_key = 'AIzaSyAahMs9GBd2ChJopz74dhOjL8a0ZxXo9-k'  # Ilisi kini sa imong API key
            geocode_url = f'https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={google_maps_api_key}'

            response = requests.get(geocode_url)
            data = response.json()

            # Create restaurant instance
            restaurant = form.save(commit=False)
            restaurant.OwnerID = StoreOwner.objects.get(user=request.user)

            # Populate latitude and longitude if location is found
            if data['status'] == 'OK':
                restaurant.Latitude = data['results'][0]['geometry']['location']['lat']
                restaurant.Longitude = data['results'][0]['geometry']['location']['lng']
            
            restaurant.save()
            return JsonResponse({'status': 'success', 'message': 'Restaurant added successfully!'})
        else:
            return JsonResponse({'status': 'error', 'message': 'There was an error with your submission.'})
    else:
        form = RestaurantForm()

    return render(request, 'owner_add_restaurant.html', {'restaurant_form': form, 'store_owner': store_owner,})

@login_required
def owner_view_restaurant(request):
    # Get the StoreOwner instance for the logged-in user
    store_owner = get_object_or_404(StoreOwner, user=request.user)
    
    # Get the restaurants that belong to the logged-in StoreOwner
    restaurants = Restaurant.objects.filter(OwnerID=store_owner)
    
    # Include store_owner in the context to access the picture in the template
    context = {
        'restaurants': restaurants,
        'store_owner': store_owner,  # Pass the store owner object
    }
    return render(request, 'owner_view_restaurant.html', context)

def delete_restaurant(request, restaurant_id):
    # Fetch the restaurant object or return a 404 error if not found
    restaurant = get_object_or_404(Restaurant, RestaurantID=restaurant_id)

    # Delete the restaurant
    restaurant.delete()

    # Check if the request is an AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Restaurant deleted successfully!'})
    
    # Flash a success message and redirect to the restaurant view page
    messages.success(request, 'Restaurant deleted successfully!')
    return redirect('owner_view_restaurant')


@login_required
def owner_edit_restaurant(request, restaurant_id):
    # Get the restaurant by the given ID
    restaurant = get_object_or_404(Restaurant, RestaurantID=restaurant_id)
    store_owner = get_object_or_404(StoreOwner, user=request.user)


    # Check if the restaurant status is 'Pending' (disallow edits if pending)
    if restaurant.Status == 'Pending':
        messages.error(request, 'Cannot edit a restaurant with pending status.')
        return redirect('owner_view_restaurant')

    # Handle the form submission
    if request.method == 'POST':
        form = RestaurantForm(request.POST, request.FILES, instance=restaurant)

        if form.is_valid():
            # Save the restaurant name and image from the form
            restaurant = form.save(commit=False)

            # Automatically set the OwnerID to the related StoreOwner of the logged-in user
            store_owner = getattr(request.user, 'storeowner', None)  # Get the StoreOwner instance

            if store_owner is not None:
                restaurant.OwnerID = store_owner  # Set the StoreOwner as the owner
            else:
                messages.error(request, 'You do not have a valid StoreOwner account.')
                return redirect('owner_view_restaurant')
            
            # Keep the existing status unchanged
            # No need to modify restaurant.Status here since we're only editing name and image
            
            # Save the restaurant instance
            restaurant.save()

            # Show a success message and redirect
            messages.success(request, 'Restaurant updated successfully!')
            return JsonResponse({'success': True, 'message': 'Restaurant updated successfully!', 'redirect_url': reverse('owner_view_restaurant')})
        else:
            # Log form errors for debugging
            print(form.errors)  # Debug line to see what errors are present
            messages.error(request, 'Please correct the errors below.')
            return JsonResponse({'success': False, 'error': form.errors.as_json()})  # Send errors back to the front end
    else:
        # Prepopulate the form with the existing restaurant details
        form = RestaurantForm(instance=restaurant)

    return render(request, 'owner_edit_restaurant.html', {'form': form, 'restaurant': restaurant, 'store_owner': store_owner,})

@login_required
def owner_view_menu(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, RestaurantID=restaurant_id)
    menu_items = Menu.objects.filter(restaurant=restaurant)
    store_owner = get_object_or_404(StoreOwner, user=request.user)

    return render(request, 'owner_view_menu.html', {
        'restaurant': restaurant,
        'menu_items': menu_items,
        'store_owner': store_owner,  # Include this variable
    })



def owner_add_menu(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, RestaurantID=restaurant_id)
    store_owner = get_object_or_404(StoreOwner, user=request.user)

    # Check if the restaurant status is pending
    if restaurant.Status == 'pending':
        return JsonResponse({
            'status': 'error',
            'message': 'Cannot add menu items. The restaurant status is pending.'
        })

    if request.method == 'POST':
        menu_item_form = MenuForm(request.POST, request.FILES)
        if menu_item_form.is_valid():
            menu_item = menu_item_form.save(commit=False)
            menu_item.restaurant = restaurant  # Link the restaurant
            menu_item.save()
            return JsonResponse({'status': 'success', 'message': 'Menu item added successfully!'})
        else:
            # Capture validation errors and return them in JSON format
            errors = menu_item_form.errors.as_json()
            return JsonResponse({
                'status': 'error',
                'message': 'There was an error with your submission.',
                'errors': errors
            })
    else:
        menu_item_form = MenuForm()

    context = {
        'menu_item_form': menu_item_form,
        'restaurant': restaurant,
        'store_owner': store_owner,
    }
    return render(request, 'owner_add_menu.html', context)

def owner_edit_menu(request, restaurant_id, food_id):
    # Get the menu item by the given FoodID
    menu_item = get_object_or_404(Menu, FoodID=food_id)
    store_owner = get_object_or_404(StoreOwner, user=request.user)

    # Handle the form submission
    if request.method == 'POST':
        form = MenuForm(request.POST, request.FILES, instance=menu_item)

        # Ensure restaurant is associated correctly
        if form.is_valid():
            form.instance.restaurant = menu_item.restaurant  # Keep the existing restaurant
            form.save()
            messages.success(request, 'Menu item updated successfully!')
            return JsonResponse({
                'success': True,
                'message': 'Menu item updated successfully!',
                'redirect_url': reverse('owner_view_menu', kwargs={'restaurant_id': restaurant_id})
            })
        else:
            messages.error(request, 'Please correct the errors below.')
            print(form.errors)  # Log errors for debugging
            return JsonResponse({'success': False, 'error': form.errors.as_json()})

    else:
        form = MenuForm(instance=menu_item)

    return render(request, 'owner_edit_menu.html', {
        'menu_form': form,
        'menu_item': menu_item,
        'store_owner': store_owner,
    })
logger = logging.getLogger(__name__)

def owner_delete_menu(request, restaurant_id, food_id):
    logger.info(f"Request method: {request.method}")  # Debugging line
    logger.info(f"Restaurant ID: {restaurant_id}, Food ID: {food_id}")  # Debugging line

    if request.method == 'POST':
        menu_item = get_object_or_404(Menu, FoodID=food_id)
        restaurant = get_object_or_404(Restaurant, RestaurantID=restaurant_id)

        if restaurant.Status == 'Pending':
            return JsonResponse({'success': False, 'message': 'Cannot delete menu items for a restaurant with pending status.'})

        menu_item.delete()
        return JsonResponse({'success': True, 'message': 'Menu item deleted successfully!'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required
def partner_request_list(request):
    partner_requests = Restaurant.objects.filter(Status='pending')
    notifications = request.session.get('notifications', get_notifications())
    notification_count = len(notifications)

    context = {
        'partner_requests': partner_requests,
        'notification_count': notification_count,
    }
    return render(request, 'admin_partner_request_table.html', context)

@login_required
def manage_business_request(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, RestaurantID=restaurant_id)
    notifications = get_notifications()  # Get notifications
    notification_count = len(notifications)  # Count notifications

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            restaurant.Status = 'approved'
            restaurant.save()

            if restaurant.OwnerID and restaurant.OwnerID.Email:
                # Send approval email
                send_mail(
                    'Your Partnership Request Approved',
                    'Congratulations! Your request to partner with us has been approved. You can now add your menu.',
                    settings.DEFAULT_FROM_EMAIL,
                    [restaurant.OwnerID.Email],
                    fail_silently=False,
                )
            
        elif action == 'decline':
            restaurant.Status = 'rejected'
            restaurant.save()

            if restaurant.OwnerID and restaurant.OwnerID.Email:
                # Send rejection email
                send_mail(
                    'Your Partnership Request Rejected',
                    'We regret to inform you that your request to partner with us has been declined.',
                    settings.DEFAULT_FROM_EMAIL,
                    [restaurant.OwnerID.Email],
                    fail_silently=False,
                )
        
        return redirect('partner_request_list')  # Redirect to the partner request list

    # Get all partner requests to display in the template
    partner_requests = Restaurant.objects.filter(Status='pending')  # Adjust filter as needed

    # Render the admin_request.html with the restaurant details and partner requests
    return render(request, 'admin_request.html', {
        'restaurant': restaurant,
        'partner_requests': partner_requests,
        'notification_count': notification_count,  # Include notification count
    })

@never_cache
@login_required
def admin_rider_table(request):
    
    riders = Rider.objects.all()
    notifications = request.session.get('notifications', get_notifications())
    notification_count = len(notifications)

    return render(request, 'admin_rider_table.html', {
        'riders': riders,
        'notification_count': notification_count,
    })

@login_required
def manage_rider_application(request, RiderID):
    rider = get_object_or_404(Rider, pk=RiderID)
    notifications = get_notifications()
    notification_count = len(notifications)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if rider.Status == 'declined':
            messages.error(request, "You cannot approve a rider whose application has been declined.")
            return redirect('admin_home')

        if action == 'approve':
            rider.Status = 'accepted'
            subject = 'Your Rider Application has been Approved'
            message = 'Congratulations! Your rider application has been approved.'
        elif action == 'decline':
            rider.Status = 'declined'
            subject = 'Your Rider Application has been Declined'
            message = 'We regret to inform you that your rider application has been declined.'
        else:
            return redirect('admin_home')

        rider.save()
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [rider.Email], fail_silently=False)
        return redirect('admin_home')

    return render(request, 'admin_rider_details.html', {
        'rider': rider,
        'notification_count': notification_count,
    })


def generate_otp():
    """Generate a 6-digit OTP."""
    return random.randint(100000, 999999)

def customer_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                
                # Check if the user is a superuser/admin
                if user.is_superuser:
                    return JsonResponse({"success": True, "redirect_url": reverse('admin_home')})

                # Check if the user is a StoreOwner
                if StoreOwner.objects.filter(user=user).exists():
                    storeowner = StoreOwner.objects.get(user=user)
                    request.session['owner_id'] = storeowner.OwnerID
                    return handle_store_owner_login(storeowner, request)

                # Check if the user is a Customer
                if Customer.objects.filter(user=user).exists():
                    customer = Customer.objects.get(user=user)
                    return handle_customer_login(customer, request)

                # Check if the user is a Rider
                if Rider.objects.filter(user=user).exists():
                    rider = Rider.objects.get(user=user)
                    try:
                        rider.latitude = float(latitude) if latitude else None
                        rider.longitude = float(longitude) if longitude else None
                        rider.save()
                    except ValueError:
                        return JsonResponse({"success": False, "message": "Invalid location data."})

                    return handle_rider_login(rider, request)

                # If none of the above, return login failed
                return JsonResponse({"success": False, "message": "Login failed. User not recognized."})

            # Invalid credentials
            return JsonResponse({"success": False, "message": "Invalid username or password."})

    # Render login form if not a POST request
    form = AuthenticationForm()
    return render(request, 'customer_login.html', {'form': form})

def handle_customer_login(customer, request):
    """Handle login flow for customers."""
    if request.COOKIES.get(f'verified_{customer.CustomerID}'):
        return JsonResponse({"success": True, "redirect_url": reverse('customer_home')})
    
    otp = generate_otp()
    request.session['otp'] = otp
    request.session['customer_id'] = customer.CustomerID
    send_mail('Your OTP Code', f'Your OTP code is {otp}', settings.DEFAULT_FROM_EMAIL, [customer.user.email])
    
    return JsonResponse({"success": True, "message": "OTP sent to your email", "redirect_url": reverse('otp_verification')})

def handle_rider_login(rider, request):
    """Handle login flow for riders."""
    if rider.Status == 'accepted':
        if request.COOKIES.get(f'verified_{rider.RiderID}'):
            return JsonResponse({"success": True, "redirect_url": reverse('rider_home')})

        otp = generate_otp()
        request.session['otp'] = otp
        request.session['rider_id'] = rider.RiderID
        send_mail('Your OTP Code', f'Your OTP code is {otp}', settings.DEFAULT_FROM_EMAIL, [rider.user.email])

        return JsonResponse({"success": True, "message": "OTP sent to your email", "redirect_url": reverse('otp_verification')})

    elif rider.Status == 'pending':
        return JsonResponse({"success": False, "message": "Your rider application is currently under review."})

    return JsonResponse({"success": False, "message": "Your rider application has been declined."})

def handle_store_owner_login(storeowner, request):
    """Handle login flow for store owners."""
    if request.COOKIES.get(f'verified_{storeowner.OwnerID}'):
        return JsonResponse({"success": True, "redirect_url": reverse('owner_view_restaurant')})

    otp = generate_otp()
    request.session['otp'] = otp
    request.session['owner_id'] = storeowner.OwnerID
    send_mail('Your OTP Code', f'Your OTP code is {otp}', settings.DEFAULT_FROM_EMAIL, [storeowner.user.email])

    return JsonResponse({"success": True, "message": "OTP sent to your email", "redirect_url": reverse('otp_verification')})

def otp_verification(request):
    """Verify the OTP for customers, riders, and store owners."""
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        stored_otp = request.session.get('otp')
        customer_id = request.session.get('customer_id', None)
        rider_id = request.session.get('rider_id', None)
        owner_id = request.session.get('owner_id', None)

        # Verify OTP for customer, rider, or store owner
        if entered_otp == str(stored_otp):
            try:
                if customer_id:
                    customer = Customer.objects.get(CustomerID=customer_id)
                    user = customer.user
                    login(request, user)

                    response = redirect('customer_home')  # Redirect to customer home after OTP verification
                    response.set_cookie(f'verified_{customer.CustomerID}', True, max_age=2*24*60*60)  # 2 days
                    return response
                
                elif rider_id:
                    rider = Rider.objects.get(RiderID=rider_id)
                    user = rider.user
                    login(request, user)

                    response = redirect('rider_home')  # Redirect to rider home after OTP verification
                    response.set_cookie(f'verified_{rider.RiderID}', True, max_age=2*24*60*60)  # 2 days
                    return response
                
                elif owner_id:
                    storeowner = StoreOwner.objects.get(OwnerID=owner_id)
                    user = storeowner.user
                    login(request, user)

                    response = redirect('owner_view_restaurant')  # Redirect to store owner home after OTP verification
                    response.set_cookie(f'verified_{storeowner.OwnerID}', True, max_age=2*24*60*60)  # 2 days
                    return response

            except (Customer.DoesNotExist, Rider.DoesNotExist, StoreOwner.DoesNotExist):
                messages.error(request, "Invalid OTP or user not found.")
        else:
            messages.error(request, "Invalid OTP.")

    return render(request, 'otp_verification.html')

def customer_base(request):
    return render(request, "customer_base.html")@login_required
def customer_track_order(request):
    # Fetch all delivery information, excluding deliveries with status 'Received'
    deliveries = Delivery.objects.select_related('RiderID', 'RestaurantID').exclude(DeliveryStatus='Received')

    # Check if any deliveries exist
    if not deliveries.exists():
        messages.info(request, "No deliveries available for tracking.")

    # Pass the filtered deliveries to the template
    return render(request, 'customer_track_order.html', {'deliveries': deliveries})

logger = logging.getLogger(__name__)

def get_rider_location(request, RiderID):
    try:
        rider = Rider.objects.get(id=RiderID)  # Assuming Rider is your model
        location_data = {
            'latitude': rider.current_latitude,
            'longitude': rider.current_longitude,
        }
        return JsonResponse(location_data)
    except Rider.DoesNotExist:
        return JsonResponse({'error': 'Rider not found'}, status=404)

@login_required
def customer_reward_points(request):
    customer = Customer.objects.get(user=request.user)
    points = customer.Points
    context = {
        'points': points,
        'customer_name': customer.CustomerName
    }
    return render(request, 'customer_rewards_points.html', context)

def rider_base(request):
    return render(request, "rider_base.html")
@login_required
def rider_home(request):
    # Retrieve notifications from the session
    rider_notifications = request.session.get('rider_notifications', [])
    notification_count = len(rider_notifications)

    # Retrieve feedbacks
    feedbacks = CustomersFeedback.objects.filter(Status='approved').order_by('-Date')

    # Retrieve the current rider's availability status
    rider = Rider.objects.get(user=request.user)

    # Pass notification count and rider's availability to the context
    context = {
        'feedbacks': feedbacks,
        'notification_count': notification_count,
        'rider': rider,  # Add the rider object here
    }

    # Render the template with the context
    return render(request, 'rider_home.html', context)

@login_required
def rider_earnings(request):
    rider_notifications = request.session.get('rider_notifications', [])
    notification_count = len(rider_notifications)
    
    # Get the Rider instance linked to the logged-in user
    rider = Rider.objects.get(user=request.user)

    # Get the selected date
    selected_date = request.GET.get('date', None)
    
    # Initialize earnings variables
    daily_earnings = weekly_earnings = monthly_earnings = 0
    earnings = []
    
    if selected_date:
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

        # Handle Daily Earnings
        daily_earnings_records = Delivery.objects.filter(RiderID=rider, Date=selected_date)
        daily_earnings = sum(earning.DeliveryFee for earning in daily_earnings_records)

        # Handle Weekly Earnings
        start_of_week = selected_date - timedelta(days=selected_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        weekly_earnings_records = Delivery.objects.filter(RiderID=rider, Date__range=[start_of_week, end_of_week])
        weekly_earnings = sum(earning.DeliveryFee for earning in weekly_earnings_records)

        # Handle Monthly Earnings
        start_of_month = selected_date.replace(day=1)
        next_month = (start_of_month.replace(month=start_of_month.month % 12 + 1, day=1) 
                      if start_of_month.month < 12 else 
                      (start_of_month.replace(year=start_of_month.year + 1, month=1, day=1)))
        end_of_month = next_month - timedelta(days=1)
        monthly_earnings_records = Delivery.objects.filter(RiderID=rider, Date__range=[start_of_month, end_of_month])
        monthly_earnings = sum(earning.DeliveryFee for earning in monthly_earnings_records)

        # Use daily records for the detailed list
        earnings = daily_earnings_records
    
    # Pass the rider object to the context
    context = {
        'selected_date': selected_date,
        'daily_earnings': daily_earnings,
        'weekly_earnings': weekly_earnings,
        'monthly_earnings': monthly_earnings,
        'earnings': earnings,
        'notification_count': notification_count,
        'rider': rider,  # Add the rider object to the context
    }

    return render(request, 'rider_earnings.html', context)
@login_required
def update_rider_profile(request):
    # Retrieve notifications from the session
    rider_notifications = request.session.get('rider_notifications', [])
    notification_count = len(rider_notifications)

    rider_profile = get_object_or_404(Rider, user=request.user)
    error_message = None

    if request.method == 'POST':
        form = RiderUpdateForm(request.POST, request.FILES, instance=rider_profile)
        if form.is_valid():
            # Check if the new password is being set
            if form.cleaned_data.get('password1'):
                # Save the user with the new password
                form.save()
                messages.success(request, "Your password changed successfully. You will be logged out and enter your new password.")
                logout(request)  # Log the user out
                return HttpResponseRedirect(reverse('customer_login') + '?success=password')  # Redirect to login page with parameter
            else:
                # Update the profile without changing the password
                form.save()
                messages.success(request, "Profile updated successfully.")
                return HttpResponseRedirect(reverse('update_rider_profile') + '?success=true')
        else:
            non_field_errors = form.non_field_errors()
            error_message = str(non_field_errors[0]) if non_field_errors else None

    else:
        initial_data = {
            'username': request.user.username,
            'email': request.user.email,
            'fullname': rider_profile.FullName,
            'phone': rider_profile.Phone,
            'platenumber': rider_profile.PlateNumber,
        }
        form = RiderUpdateForm(instance=rider_profile, initial=initial_data)

    success = 'success' in request.GET
    
    # Pass the notification_count to the template
    return render(request, 'rider_profile_update.html', {
        'form': form,
        'rider': rider_profile,
        'success': success,
        'error_message': error_message,
        'notification_count': notification_count,  # Include the notification count here
    })

@login_required
def update_store_owner_profile(request):
    # Retrieve notifications from the session
    owner_notifications = request.session.get('owner_notifications', [])
    notification_count = len(owner_notifications)

    store_owner = get_object_or_404(StoreOwner, user=request.user)
    error_message = None

    if request.method == 'POST':
        form = StoreOwnerUpdateForm(request.POST, request.FILES, instance=store_owner)
        if form.is_valid():
            # Check if the new password is being set
            if form.cleaned_data.get('password1'):
                # Save the user with the new password
                form.save()
                messages.success(request, "Your password changed successfully. You will be logged out and enter your new password.")
                logout(request)  # Log the user out
                return redirect(reverse('customer_login') + '?success=password')  # Redirect to login page with parameter
            else:
                # Update the profile without changing the password
                form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect(reverse('update_store_owner_profile') + '?success=true')
        else:
            non_field_errors = form.non_field_errors()
            error_message = str(non_field_errors[0]) if non_field_errors else None

    else:
        initial_data = {
            'username': request.user.username,
            'email': request.user.email,
            'first_name': store_owner.FirstName,
            'last_name': store_owner.LastName,
            'phone': store_owner.Phone,
            'picture': store_owner.Picture,
        }
        form = StoreOwnerUpdateForm(instance=store_owner, initial=initial_data)

    success = 'success' in request.GET

    # Pass the notification_count to the template
    return render(request, 'owner_profile.html', {
        'form': form,
        'store_owner': store_owner,
        'success': success,
        'error_message': error_message,
        'notification_count': notification_count,  # Include the notification count here
    })

@login_required
def customer_home(request):
    # Fetch all restaurants
    restaurants = Restaurant.objects.filter(Status='approved')

    # Fetch the customer profile using the User object
    try:
        customer_profile = Customer.objects.get(user=request.user)
        fullname = customer_profile.CustomerName
    except Customer.DoesNotExist:
        fullname = "Unknown"

    # Prepare context with necessary data
    context = {
        'restaurants': restaurants,
        'fullname': fullname,
    }
    
    return render(request, 'customer_home.html', context)

@login_required
def view_menu(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, RestaurantID=restaurant_id)
    menu_items = Menu.objects.filter(restaurant=restaurant)

    # Fetch favorite items for the customer
    customer = Customer.objects.filter(user=request.user).first()
    favorites = Favorite.objects.filter(CustomerID=customer).values_list('FoodID', flat=True) if customer else []

    # Add favorite status to each menu item
    for item in menu_items:
        item.is_favorite = item.FoodID in favorites
    
    return render(request, 'customer_menu.html', {
        'restaurant': restaurant,
        'menu_items': menu_items,
    })

@login_required
@require_POST
def toggle_favorite(request):
    data = json.loads(request.body)
    food_id = data.get('food_id')
    status = data.get('status')
    
    if not food_id:
        return JsonResponse({'success': False, 'message': 'No food ID provided.'})

    try:
        menu_item = Menu.objects.get(FoodID=food_id)
        customer = Customer.objects.get(user=request.user)
        
        if status == 'add':
            favorite, created = Favorite.objects.get_or_create(
                CustomerID=customer,
                FoodID=menu_item,
                defaults={'FoodName': menu_item.FoodName}
            )
            is_favorite = created
        elif status == 'remove':
            Favorite.objects.filter(CustomerID=customer, FoodID=menu_item).delete()
            is_favorite = False
        else:
            return JsonResponse({'success': False, 'message': 'Invalid status'})

        return JsonResponse({'success': True, 'is_favorite': is_favorite})
    
    except Menu.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Menu item not found.'})
    
@login_required
def remove_favorite(request, food_id):
    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Fetch the favorite item for the current customer (adjust the field to CustomerID)
            favorite = get_object_or_404(Favorite, CustomerID=request.user.customer, FoodID=food_id)
            
            # Delete the favorite item
            favorite.delete()

            # Return a JSON response indicating success
            return JsonResponse({'success': True})
        
        except Favorite.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Favorite item not found'}, status=404)
    
    # If it's not an AJAX request, redirect to the favorites page (fallback)
    return redirect('view_favorites')



@login_required
@require_POST
def add_to_cart(request):
    food_id = request.POST.get('food_id')
    if not food_id:
        return JsonResponse({'success': False, 'message': 'Item ID is required.'})

    try:
        item = Menu.objects.get(FoodID=food_id)
        cart_item, created = CartItem.objects.get_or_create(CustomerID=request.user.customer, FoodID=item)
        if not created:
            cart_item.Quantity += 1
            cart_item.save()

        cart_count = CartItem.objects.filter(CustomerID=request.user.customer).count()

        return JsonResponse({'success': True, 'cart_count': cart_count})
    except Menu.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found.'})


@login_required
def get_cart_count(request):
    try:
        # Get the customer associated with the current user
        customer = Customer.objects.get(user=request.user)
        
        # Count the cart items for that customer
        cart_count = CartItem.objects.filter(CustomerID=customer).count()
        
        return JsonResponse({'success': True, 'cart_count': cart_count})
    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Customer not found.'})

@login_required
def view_cart(request):
    # Retrieve the logged-in customer's profile
    customer = Customer.objects.get(user=request.user)
    
    # Fetch all cart items related to the current customer
    cart_items = CartItem.objects.filter(CustomerID=customer)
    
    # Calculate the total price of items in the cart
    total_price = sum(item.FoodID.Price * item.Quantity for item in cart_items)

    if cart_items.exists():
        # Get the restaurant of the first menu item
        first_restaurant = cart_items[0].FoodID.restaurant
        
        # Check if all menu items in the cart are from the same restaurant
        all_same_restaurant = all(item.FoodID.restaurant == first_restaurant for item in cart_items)
        
        if all_same_restaurant:
            restaurant = first_restaurant
        else:
            restaurant = None
    else:
        restaurant = None

    # Pass the required data to the template
    context = {
        'cart_items': cart_items,
        'fullname': customer.CustomerName,
        'total_price': total_price,
        'restaurant': restaurant,
    }
    
    # Render the cart page with the context
    return render(request, 'customer_cart.html', context)

@login_required
@require_POST
def update_cart_item_quantity(request, item_id):
    action = request.POST.get('action')
    cart_item = get_object_or_404(CartItem, id=item_id)
    
    # Fetch the customer related to the logged-in user
    customer = get_object_or_404(Customer, user=request.user)
    
    # Ensure the cart item belongs to the logged-in user
    if cart_item.CustomerID != customer:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    if action == 'increase':
        cart_item.Quantity += 1
    elif action == 'decrease':
        if cart_item.Quantity > 1:
            cart_item.Quantity -= 1
        else:
            cart_item.delete()
            return JsonResponse({'success': True, 'removed': True})
    
    cart_item.save()
    
    return JsonResponse({'success': True, 'removed': False})

@login_required
@require_POST
def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    
    # Fetch the customer related to the logged-in user
    customer = get_object_or_404(Customer, user=request.user)
    
    # Ensure the cart item belongs to the logged-in user
    if cart_item.CustomerID != customer:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    cart_item.delete()
    
    return JsonResponse({'success': True})

def search_results(request):
    query = request.GET.get('query', '')
    menu_items = Menu.objects.filter(FoodName__icontains=query)
    restaurants = Restaurant.objects.filter(RestaurantName__icontains=query)

    context = {
        'query': query,
        'menu_items': menu_items,
        'restaurants': restaurants,
    }
    return render(request, 'search_results.html', context)

@login_required
def add_to_cart_from_search(request):
    if request.method == 'POST':
        food_id = request.POST.get('food_id')
        if not food_id:
            return redirect(reverse('search_results') + '?error=Food+ID+is+required.')

        try:
            # Get the menu item by FoodID
            item = Menu.objects.get(FoodID=food_id)
            
            # Get the current customer
            customer = Customer.objects.get(user=request.user)
            
            # Create or update the cart item for the customer
            cart_item, created = CartItem.objects.get_or_create(
                CustomerID=customer,
                FoodID=item,
                defaults={'FoodName': item.FoodName, 'Quantity': 1}
            )
            if not created:
                # If the item is already in the cart, increase the quantity
                cart_item.Quantity += 1
                cart_item.save()

            # Return the updated cart count
            cart_count = CartItem.objects.filter(CustomerID=customer).count()
            return JsonResponse({'success': True, 'cart_count': cart_count})
        
        except Menu.DoesNotExist:
            # Handle case where the menu item does not exist
            return redirect(reverse('search_results') + '?error=Item+not+found.')

    # If the request method is not POST, redirect with an error
    return redirect(reverse('search_results') + '?error=Invalid+request.')

@login_required
def get_cart_count(request):
    try:
        customer = Customer.objects.get(user=request.user)
        cart_count = CartItem.objects.filter(CustomerID=customer).count()
        return JsonResponse({'success': True, 'cart_count': cart_count})
    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Customer not found'})

@login_required
@require_POST
def update_cart_item_quantity(request, item_id):
    # Get the customer based on the logged-in user
    customer = get_object_or_404(Customer, user=request.user)
    
    # Get the CartItem based on the customer and item_id (FoodID)
    cart_item = get_object_or_404(CartItem, id=item_id, CustomerID=customer)
    
    action = request.POST.get('action')

    if action == 'increase':
        cart_item.Quantity += 1
    elif action == 'decrease':
        if cart_item.Quantity > 1:
            cart_item.Quantity -= 1
        else:
            cart_item.delete()  # Remove the item if the quantity is 0
            return JsonResponse({'success': True, 'removed': True})

    cart_item.save()

    return JsonResponse({'success': True, 'removed': False})

@login_required
def view_favorites(request):
    # Get all favorite items for the logged-in customer
    customer_profile = get_object_or_404(Customer, user=request.user)
    favorites = Favorite.objects.filter(CustomerID=customer_profile)

    context = {
        'favorites': favorites,
        'username': request.user.username,
        'fullname': customer_profile.CustomerName,
    }
    return render(request, 'customer_favorites.html', context)

# View for adding a favorite item to the cart via Ajax
@login_required
def add_favorite_to_cart(request, food_id):
    if request.method == "POST":
        customer_profile = get_object_or_404(Customer, user=request.user)
        food_item = get_object_or_404(Menu, pk=food_id)

        # Check if the item is already in the cart
        cart_item, created = CartItem.objects.get_or_create(
            CustomerID=customer_profile,
            FoodID=food_item,
            defaults={'FoodName': food_item.FoodName, 'Quantity': 1}
        )

        if not created:
            cart_item.Quantity += 1
            cart_item.save()

        # Return JSON response with cart count (Assuming cart count logic is implemented)
        cart_count = CartItem.objects.filter(CustomerID=customer_profile).count()

        return JsonResponse({'success': True, 'cart_count': cart_count})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def profile_settings(request):
    customer_profile = get_object_or_404(Customer, user=request.user)
    error_message = None

    if request.method == 'POST':
        form = CustomerProfileUpdateForm(request.POST, request.FILES, instance=customer_profile)
        if form.is_valid():
            # Check if the new password is being set
            if form.cleaned_data.get('password1'):
                form.save()
                messages.success(request, "Your password changed successfully. You will be logged out and enter your new password.")
                logout(request)
                return HttpResponseRedirect(reverse('customer_login') + '?success=password')
            else:
                form.save()
                messages.success(request, "Profile updated successfully.")
                return HttpResponseRedirect(reverse('profile_settings') + '?success=true')
        else:
            non_field_errors = form.non_field_errors()
            error_message = str(non_field_errors[0]) if non_field_errors else None
            messages.error(request, error_message)

    else:
        initial_data = {
            'username': request.user.username,
            'email': request.user.email,
            'fullname': customer_profile.CustomerName,  # Updated here
            'phone': customer_profile.Phone,
        }
        form = CustomerProfileUpdateForm(instance=customer_profile, initial=initial_data)

    success = 'success' in request.GET
    return render(request, 'customer_profile.html', {
        'form': form,
        'customer': customer_profile,
        'success': success,
        'error_message': error_message
    })


def admin_base(request):
    return render(request, "admin_base.html")

def restaurant_partners(request):
    restaurants = Restaurant.objects.filter(Status='approved')  # Adjust filter as needed
    notifications = request.session.get('notifications', get_notifications())
    notification_count = len(notifications)


    return render(request, 'restaurant_partners.html', {
        'restaurants': restaurants,
        'notification_count': notification_count,
    })

@login_required
def admin_home(request):
    total_restaurants = Restaurant.objects.count()
    total_customers = Customer.objects.count()
    total_riders = Rider.objects.count()
    total_deliveries = Delivery.objects.count()
    total_users = total_customers

    today = now().date()

    # Monthly Earnings Data (Corrected)
    months = list(month_name)[1:]  # Jan-Dec
    monthly_earnings = [0.0] * 12
    monthly_data = Delivery.objects.annotate(month=TruncMonth('Date')).values('month').annotate(total=Sum('DeliveryFee')).order_by('month')
    
    for entry in monthly_data:
        month_index = entry['month'].month - 1  # Ensure it matches Jan (1) to Dec (12)
        monthly_earnings[month_index] = float(entry['total'] or 0)

    # Daily Earnings Data (last 7 days, corrected)
    last_week = today - timedelta(days=6)  # Show last 7 days including today
    days = [(last_week + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    daily_earnings = [0.0] * 7

    daily_data = Delivery.objects.filter(Date__date__gte=last_week, Date__date__lte=today) \
                                  .annotate(day=TruncDay('Date')).values('day') \
                                  .annotate(total=Sum('DeliveryFee')).order_by('day')

    for entry in daily_data:
        day_str = entry['day'].strftime('%Y-%m-%d')
        if day_str in days:
            day_index = days.index(day_str)  # Find the correct day index
            daily_earnings[day_index] = float(entry['total'] or 0)

    # Weekly Earnings Data (last 4 weeks, corrected)
    weekly_earnings = [0.0] * 4
    weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
    for i in range(4):
        week_start = today - timedelta(days=(i * 7 + 6))  # 1st week will have latest days
        week_end = week_start + timedelta(days=6)
        week_data = Delivery.objects.filter(Date__date__gte=week_start, Date__date__lte=week_end).aggregate(total=Sum('DeliveryFee'))
        weekly_earnings[3 - i] = float(week_data['total'] or 0)  # Reverse the week order

    # Plot Charts (Daily, Weekly, Monthly)
    # Daily Earnings Chart
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(days, daily_earnings, marker='o', color='g', linestyle='-', markersize=10, label="Daily Earnings")
    ax.set_xlabel('Day')
    ax.set_ylabel('Earnings (₱)')
    ax.set_title('Daily Earnings (Last 7 Days)')
    ax.legend()
    daily_image_path = os.path.join(settings.MEDIA_ROOT, 'charts', 'daily_earnings.png')
    os.makedirs(os.path.dirname(daily_image_path), exist_ok=True)
    fig.savefig(daily_image_path)
    plt.close(fig)

    # Weekly Earnings Chart
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(weeks, weekly_earnings, marker='o', color='r', linestyle='-', markersize=10, label="Weekly Earnings")
    ax.set_xlabel('Week')
    ax.set_ylabel('Earnings (₱)')
    ax.set_title('Weekly Earnings (Last 4 Weeks)')
    ax.legend()
    weekly_image_path = os.path.join(settings.MEDIA_ROOT, 'charts', 'weekly_earnings.png')
    fig.savefig(weekly_image_path)
    plt.close(fig)

    # Monthly Earnings Chart
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(months, monthly_earnings, marker='o', color='b', linestyle='-', markersize=10, label="Monthly Earnings")
    ax.set_xlabel('Month')
    ax.set_ylabel('Earnings (₱)')
    ax.set_title('Monthly Earnings Overview')
    ax.legend()
    monthly_image_path = os.path.join(settings.MEDIA_ROOT, 'charts', 'monthly_earnings.png')
    fig.savefig(monthly_image_path)
    plt.close(fig)

    notifications = request.session.get('notifications', get_notifications())
    notification_count = len(notifications)


    # Pass the image paths and stats to the template
    context = {
        'total_riders': total_riders,
        'total_restaurants': total_restaurants,
        'total_users': total_users,
        'notification_count': notification_count,
        'monthly_earnings_image': os.path.join(settings.MEDIA_URL, 'charts', 'monthly_earnings.png'),
        'daily_earnings_image': os.path.join(settings.MEDIA_URL, 'charts', 'daily_earnings.png'),
        'weekly_earnings_image': os.path.join(settings.MEDIA_URL, 'charts', 'weekly_earnings.png'),
    }

    return render(request, 'admin_home.html', context)

def foodhitch(request):
    return render(request, "foodhitch.html")

def partner(request):
    return render(request, "partner.html")

@login_required
def admin_feedback_list(request):
    feedbacks = CustomersFeedback.objects.filter(Status='pending')
    notifications = request.session.get('notifications', get_notifications())
    notification_count = len(notifications)

    return render(request, 'admin_feedback_list.html', {
        'feedbacks': feedbacks,
        'notification_count': notification_count,
    })

def approve_feedback(request, feedback_id):
    feedback = get_object_or_404(CustomersFeedback, pk=feedback_id)
    feedback.Status = 'approved'
    feedback.save()
    return redirect('admin_feedback_list')

def reject_feedback(request, feedback_id):
    feedback = get_object_or_404(CustomersFeedback, pk=feedback_id)
    feedback.Status = 'rejected'
    feedback.save()
    return redirect('admin_feedback_list')
@login_required
def check_out(request):
    customer = request.user.customer
    cart_items = CartItem.objects.filter(CustomerID=customer)

    if not cart_items.exists():
        messages.error(request, "Your cart is empty! Can't proceed to checkout.")
        return redirect('customer_home')

    cart_data = []
    cart_total = 0
    delivery_fee = 0  # Initialize delivery fee

    for item in cart_items:
        subtotal = item.FoodID.Price * item.Quantity
        cart_data.append({
            'food': item.FoodID,
            'food_name': item.FoodID.FoodName,
            'quantity': item.Quantity,
            'subtotal': subtotal
        })
        cart_total += subtotal

    total_amount = cart_total + delivery_fee  # Delivery fee will be updated via AJAX

    context = {
        'cart_items': cart_data,
        'cart_total': cart_total,
        'delivery_fee': delivery_fee,  # Initially 0
        'total_amount': total_amount,
        'customer': customer,
    }

    return render(request, 'check_out.html', context)

@login_required
def calculate_delivery_fee(request):
    latitude = request.GET.get('latitude')
    longitude = request.GET.get('longitude')

    customer = request.user.customer
    customer.Latitude = latitude
    customer.Longitude = longitude
    customer.save()

    cart_items = CartItem.objects.filter(CustomerID=customer)

    delivery_fee = 0
    for item in cart_items:
        # Use latitude and longitude from the restaurant
        restaurant_location = (item.FoodID.restaurant.Latitude, item.FoodID.restaurant.Longitude)
        customer_location = (float(latitude), float(longitude))
        distance = geodesic(restaurant_location, customer_location).km

        # Calculate delivery fee based on distance
        if distance <= 5:
            delivery_fee = 30
        elif distance <= 10:
            delivery_fee = 50
        else:
            delivery_fee = 80

    return JsonResponse({'delivery_fee': delivery_fee})

@login_required
def place_order(request):
    if request.method == 'POST':
        customer = request.user.customer
        cart_items = CartItem.objects.filter(CustomerID=customer)

        # Check if the customer has any pending deliveries
        if Delivery.objects.filter(CustomerID=customer, DeliveryStatus='Pending').exists():
            messages.error(request, "You cannot place an order while you have a pending delivery.")
            return redirect('customer_home')

        if not cart_items.exists():
            messages.error(request, "Your cart is empty! Can't place an order.")
            return redirect('customer_home')

        # Check if all cart items are from the same restaurant
        restaurant_ids = {item.FoodID.restaurant.RestaurantID for item in cart_items}
        if len(restaurant_ids) > 1:
            messages.error(request, "You cannot place an order with items from different restaurants.")
            return redirect('customer_home')

        # Get order details
        payment_option = request.POST.get('payment-option')
        address = request.POST.get('address')
        subtotal = float(request.POST.get('subtotal', 0))
        delivery_fee = float(request.POST.get('delivery-fee', 0))
        total_amount = float(request.POST.get('total-payable-amount', 0))

        if not address:
            messages.error(request, "Address is required to place an order.")
            return redirect('place_order')

        # Prepare order details for email
        order_details = []
        total_order_amount = 0  # Total for all food items

        # Create a single order record
        order = Order(
            CustomerID=customer,
            OrderTotal=total_order_amount,  # Start with 0, will update later
            Date=timezone.now(),
            TransactionID='',  # Placeholder for Transaction ID
        )
        order.save()  # Save the order to get OrderID

        # Loop through cart items and calculate total order amount
        for item in cart_items:
            order_total = item.Quantity * item.FoodID.Price
            total_order_amount += order_total  # Add to the total order amount
            order_details.append(f"{item.FoodID.FoodName} (Quantity: {item.Quantity})")

        # Update order total after calculating all items
        order.OrderTotal = total_order_amount
        order.save()

        # Create a single delivery record for the entire order
        rider = order.get_assigned_rider()  # Assuming this method retrieves the assigned rider instance
        if rider is not None:
            delivery = Delivery.objects.create(
                CustomerID=customer,
                RiderID=rider,
                RestaurantID=cart_items.first().FoodID.restaurant,
                Address=address,
                OrderTotal=total_order_amount,  # Use total_order_amount for the entire delivery
                DeliveryFee=delivery_fee,
                TotalPayableAmount=total_amount,
                DeliveryStatus='Pending',
                OrderID=order  # Link the order instance here
            )

            # Create delivery items for each order
            for item in cart_items:
                DeliveryItem.objects.create(
                    Delivery=delivery,  # Link the delivery instance
                    FoodID=item.FoodID,
                    Quantity=item.Quantity
                )

            # Send email notification to the assigned rider
            rider_email = rider.user.email
            subject = 'New Order Notification'

            # Get customer's full name
            customer_name = f"{customer.CustomerName}"
            restaurant_name = cart_items.first().FoodID.restaurant.RestaurantName  # Get restaurant name

            # Format message with customer name, restaurant name, and order details
            order_items = ", ".join(order_details)
            message = (
                f"You have a new order from {customer_name}.\n"
                f"Restaurant: {restaurant_name}\n"
                f"Items: {order_items}\n"
                f"Address: {address}\n"
                f"Delivery ID: {delivery.DeliveryID}"  # Include the delivery ID for reference
            )

            # Send email notification
            try:
                send_mail(subject, message, settings.EMAIL_HOST_USER, [rider_email])
            except Exception as e:
                messages.error(request, "Failed to send email notification.")
                print(f"Email send error: {e}")  # Log error to console

            # Add notification to rider's session
            rider_notifications = request.session.get('rider_notifications', [])
            rider_notifications.append({
                'message': f"New order from {customer_name} at {restaurant_name}: {order_items}.",
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            request.session['rider_notifications'] = rider_notifications

        else:
            messages.error(request, "No rider is assigned to this order.")
            return redirect('customer_home')

        # Calculate points earned based on total_amount
        points_earned = 0
        if total_amount < 50:
            points_earned = 0.1
        elif 50 <= total_amount < 100:
            points_earned = 0.5
        else:
            points_earned = (total_amount // 100) * 1.0
            remaining_amount = total_amount % 100
            if remaining_amount >= 50:
                points_earned += 0.5

        # Update customer's points
        customer.Points += points_earned
        customer.save()

        # Clear the cart after placing the order
        cart_items.delete()

        # Show success message with points earned
        messages.success(request, f"Your order has been placed successfully! You earned {points_earned:.1f} points.")
        return redirect('customer_home')

    return redirect('customer_home')
    print(order_id)  # Debugging statement
def reorder(request, order_id):
    # Get the order using OrderID
    order = get_object_or_404(Order, OrderID=order_id)

    # Retrieve deliveries associated with this order
    deliveries = Delivery.objects.filter(OrderID=order)

    # Retrieve delivery items for all deliveries
    delivery_items = DeliveryItem.objects.filter(Delivery__in=deliveries)

    # Check if the user is authenticated
    if request.user.is_authenticated:
        # Assuming that request.user has a related Customer instance
        customer = request.user.customer  # Get the Customer instance from the User

        for item in delivery_items:
            cart_item, created = CartItem.objects.get_or_create(
                CustomerID=customer,  # Use the Customer instance
                FoodID=item.FoodID,  # Use FoodID to link with the menu item
                defaults={'FoodName': item.FoodID.FoodName, 'Quantity': item.Quantity}  # Set defaults
            )
            if not created:
                cart_item.Quantity += item.Quantity  # Update quantity based on Quantity in DeliveryItem
                cart_item.save()

    # Redirect to the cart or a success page
    return redirect('view_cart')


def order_history(request):
    # Get the customer instance based on the logged-in user
    customer = Customer.objects.get(user=request.user)
    
    # Get all deliveries related to the current customer with status 'Received'
    deliveries = Delivery.objects.filter(CustomerID=customer, DeliveryStatus='Received').prefetch_related('delivery_items').select_related('RiderID', 'RestaurantID')

    # Create a list to store the order details
    order_details = []
    for delivery in deliveries:
        # Create a dictionary to store the unique delivery info
        order_info = {
            'OrderID': delivery.OrderID,  # Make sure this is the OrderID from the Order model
            'RestaurantName': delivery.delivery_items.first().FoodID.restaurant.RestaurantName,
            'RiderID': delivery.RiderID,
            'Date': delivery.Date,
            'DeliveryStatus': delivery.DeliveryStatus,
            'TotalPayableAmount': delivery.TotalPayableAmount,
            'Items': []
        }
        
        # Add each item to the Items list
        for item in delivery.delivery_items.all():
            order_info['Items'].append({
                'FoodID': item.FoodID,
                'Quantity': item.Quantity
            })

        order_details.append(order_info)

    # Pass the order details to the template
    return render(request, 'customer_order_history.html', {'orders': order_details})
@login_required
def submit_feedback(request, delivery_id):
    if request.method == 'POST':
        # Retrieve the feedback message from the form
        message = request.POST.get('feedback_message')

        if not message:
            # Handle the case where no message is provided
            return render(request, 'customer_feedback.html', {
                'delivery_id': delivery_id,
                'error': 'Feedback message is required.'
            })

        # Get the relevant delivery
        delivery = get_object_or_404(Delivery, DeliveryID=delivery_id)

        # Get the customer object (assuming a `Customer` model is linked to the user)
        customer = Customer.objects.get(user=request.user)

        # Create feedback instance and save it
        feedback = CustomersFeedback(
            DeliveryID=delivery,
            CustomerID=customer,
            CustomerName=customer.CustomerName,  # Assuming FullName is a field in the Customer model
            RiderID=delivery.RiderID,
            Message=message
        )
        feedback.save()

        # Redirect to the customer home after successful submission
        return redirect('customer_home')

    return render(request, 'customer_feedback.html', {'delivery_id': delivery_id})
def logout_view(request):
    if request.user.is_authenticated:
        # Check if the user is a rider
        try:
            rider = Rider.objects.get(user=request.user)
            rider.Availability = 'unavailable'  # Set availability to unavailable on logout
            rider.save()
        except Rider.DoesNotExist:
            pass  # If the user is not a rider, do nothing

    logout(request) 
    return redirect('foodhitch')  

def get_notifications():
    notifications = []
    store_owners = StoreOwner.objects.all()

    # Filter notifications from the last 24 hours
    for owner in store_owners:
        new_restaurants = Restaurant.objects.filter(OwnerID=owner, updated_at__gte=timezone.now() - timedelta(days=1))
        for restaurant in new_restaurants:
            notifications.append({
                'message': f'New restaurant "{restaurant.RestaurantName}" added by {owner.FirstName} {owner.LastName}.',
                'timestamp': restaurant.updated_at,  # Store the datetime object
            })

        edited_restaurants = Restaurant.objects.filter(OwnerID=owner, updated_at__gte=timezone.now() - timedelta(days=1))
        for restaurant in edited_restaurants:
            notifications.append({
                'message': f'Restaurant "{restaurant.RestaurantName}" was edited by {owner.FirstName} {owner.LastName}.',
                'timestamp': restaurant.updated_at,  # Store the datetime object
            })

        new_menus = Menu.objects.filter(restaurant__OwnerID=owner, updated_at__gte=timezone.now() - timedelta(days=1))
        for menu in new_menus:
            notifications.append({
                'message': f'New menu item "{menu.FoodName}" added to restaurant "{menu.restaurant.RestaurantName}" by {owner.FirstName}.',
                'timestamp': menu.updated_at,  # Store the datetime object
            })

    return notifications

def get_rider_notifications(rider_id):
    notifications = []
    
    # Fetch the rider using the provided rider ID
    try:
        rider = Rider.objects.get(RiderID=rider_id)
    except Rider.DoesNotExist:
        return notifications  # Return an empty list if the rider does not exist

    # Fetch new orders for this rider from the last 24 hours
    new_orders = Delivery.objects.filter(RiderID=rider, DeliveryStatus='Pending', Date__gte=timezone.now() - timedelta(days=1))
    
    for order in new_orders:
        notifications.append({
            'message': f'You have a new order from {order.CustomerID.CustomerName} at {order.RestaurantID.RestaurantName}.',
            'timestamp': order.Date,
        })

    return notifications

@login_required
def admin_notifications(request):
    notifications = request.session.get('notifications', get_notifications())
    notification_count = len(notifications)

    if request.method == 'POST':
        request.session['notifications'] = []  # Clear notifications
        return redirect('admin_notifications')

    # Filter notifications to get only the latest
    latest_notifications = notifications[-10:]  # Limit to the latest 10 notifications

    context = {
        'notifications': latest_notifications,
        'notification_count': notification_count,
    }
    return render(request, 'admin_notifications.html', context)

@login_required
def rider_notifications(request):
    # Get the rider associated with the current user
    rider = request.user.rider  # Ensure that the User model has a related Rider object

    # Fetch notifications for the rider using RiderID
    rider_notifications = get_rider_notifications(rider.RiderID)  
    notification_count = len(rider_notifications)

    if request.method == 'POST':
        request.session['rider_notifications'] = []  # Clear notifications
        return redirect('rider_notifications')  # Redirect after clearing notifications

    # Limit to the latest 10 notifications
    latest_notifications = rider_notifications[-10:]

    context = {
        'notifications': latest_notifications,
        'notification_count': notification_count,
    }
    return render(request, 'rider_notifications.html', context)

@login_required
def rider_profile_update(request):
    rider = get_object_or_404(Rider, user=request.user)

    if request.method == 'POST':
        form = RiderUpdateForm(request.POST, request.FILES, instance=rider)

        if form.is_valid():
            old_password = form.cleaned_data.get('old_password')
            new_password1 = form.cleaned_data.get('new_password1')
            new_password2 = form.cleaned_data.get('new_password2')

            if old_password and new_password1 and new_password2:
                if not request.user.check_password(old_password):
                    messages.error(request, "Current password is incorrect.")
                elif new_password1 != new_password2:
                    messages.error(request, "New passwords do not match.")
                else:
                    request.user.set_password(new_password1)
                    request.user.save()
                    messages.success(request, "Password updated successfully. Please log in again.")
                    return redirect('login')

            form.save()  # Save the profile after password check
            messages.success(request, "Profile updated successfully.")
            return redirect('rider_profile_update')

    else:
        form = RiderUpdateForm(instance=rider)

    return render(request, 'rider_profile_update.html', {'form': form, 'rider': rider})

@login_required
def rider_delivery_history(request):
    rider = request.user.rider 
    rider_notifications = get_rider_notifications(rider.RiderID)
    notification_count = len(rider_notifications)

    # Get the deliveries that are delivered
    deliveries = Delivery.objects.filter(RiderID=rider, DeliveryStatus='Received')

    latest_notifications = rider_notifications[-10:]

    context = {
        'deliveries': deliveries,
        'notifications': latest_notifications,
        'notification_count': notification_count,
        'rider': rider,  # Add the rider object to the context
    }
    
    return render(request, 'rider_delivery_history.html', context)

@login_required
def rider_transactions(request):
    rider_notifications = request.session.get('rider_notifications', [])
    notification_count = len(rider_notifications)

    # Get the logged-in rider
    rider = request.user.rider

    # Get all delivery records assigned to this rider excluding 'Received' status
    deliveries = Delivery.objects.filter(RiderID=rider).exclude(DeliveryStatus='Received').prefetch_related('delivery_items')

    # Pass the deliveries and rider to the template
    context = {
        'deliveries': deliveries,
        'notification_count': notification_count,
        'rider': rider,
    }

    return render(request, "rider_transactions.html", context)

@csrf_exempt  # Ensure that CSRF protection issues are handled correctly
def update_delivery_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)  # Load JSON data from the request body
            delivery_id = data.get('delivery_id')
            status = data.get('status')

            delivery = Delivery.objects.get(DeliveryID=delivery_id)

            # Update the status based on the incoming request
            if status == 'Delivered':
                delivery.DeliveryStatus = 'Delivered'
                delivery.save()
                return JsonResponse({'success': True})

            elif status == 'On Transit':
                delivery.DeliveryStatus = 'On Transit'
                delivery.save()
                return JsonResponse({'success': True})

            elif status == 'Received':
                if delivery.DeliveryStatus == 'Delivered':
                    delivery.DeliveryStatus = 'Received'
                    delivery.save()
                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({'success': False, 'error': 'Delivery must be marked as Delivered first.'})

            else:
                return JsonResponse({'success': False, 'error': 'Invalid status provided.'})

        except Delivery.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Delivery not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@never_cache
@login_required
def view_riders(request):
    query = request.GET.get('query', '')  # Get the search query from the URL parameters
    if query:
        # Search for riders based on full name or email
        riders = Rider.objects.filter(Q(FullName__icontains=query) | Q(Email__icontains=query))
    else:
        riders = Rider.objects.all()
    
    notifications = request.session.get('notifications', get_notifications())
    notification_count = len(notifications)

    
    return render(request, 'admin_riders.html', {
        'riders': riders,
        'notification_count': notification_count
    })

# View to handle delete request
def delete_rider(request, rider_id):
    if request.method == 'POST':
        # Use RiderID instead of id
        rider = get_object_or_404(Rider, RiderID=rider_id)
        rider.delete()
        messages.success(request, 'Rider deleted successfully.')
        return redirect('view_riders')  # Redirect after deletion
    else:
        return redirect('view_riders')
    
@csrf_exempt
def update_availability(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)  # Get the JSON data from the request
            availability_status = data.get('availability')  # Extract availability from the request data
            
            # Retrieve the current rider
            rider = Rider.objects.get(user=request.user)  # Assuming the user is authenticated
            
            # Update the availability
            rider.Availability = availability_status
            rider.save()

            return JsonResponse({'success': True})
        except Exception as e:
            print(e)
            return JsonResponse({'success': False})
    return JsonResponse({'success': False})

def password_reset_request(request):
    form = PasswordResetForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data.get('username')
            try:
                user = User.objects.get(username=username)
                request.session['reset_username'] = username  # Save username in session
                return redirect('password_reset_set')
            except User.DoesNotExist:
                return render(request, 'password_reset_request.html', {'form': form, 'username_error': True})

    return render(request, 'password_reset_request.html', {'form': form})

def check_username(request):
    username = request.GET.get('username', '')
    user_exists = User.objects.filter(username=username).exists()
    return JsonResponse({'exists': user_exists})    

def password_reset_set(request):
    if 'reset_username' not in request.session:
        return redirect('password_reset_request')

    username = request.session.get('reset_username')
    try:
        user = User.objects.get(username=username)

        if request.method == 'POST':
            form = PasswordSetForm(request.POST)
            if form.is_valid():
                new_password = form.cleaned_data.get('new_password')
                user.password = make_password(new_password)
                user.save()
                messages.success(request, 'Password has been reset successfully!')
                return redirect('customer_login')
        else:
            form = PasswordSetForm()

        return render(request, 'password_reset_set.html', {'form': form})

    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('password_reset_request')