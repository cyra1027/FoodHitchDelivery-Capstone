from django.shortcuts import render, redirect, get_object_or_404
from .models import Customer, Restaurant, Menu, CartItem, Favorite, Rider,CustomersFeedback, Delivery, DeliveryItem, Order, StoreOwner, Message
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CustomerRegisterForm, CustomerLoginForm, UserUpdateForm, CustomerProfileUpdateForm, RiderRegisterForm, MenuForm, RestaurantForm, RiderUpdateForm, StoreOwnerRegisterForm, StoreOwnerUpdateForm
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse, Http404
import json
from paypal.standard.models import ST_PP_COMPLETED  # Import PayPal status
import random
from django.db.models.functions import ExtractMonth, TruncMonth, TruncDate, TruncDay, TruncWeek
from django.contrib.auth.hashers import make_password
from .forms import PasswordResetForm, PasswordSetForm
import logging
from datetime import datetime, timedelta
import os
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
from django.db.models import Q
from paypal.standard.forms import PayPalPaymentsForm

def customer_register(request):
    if request.method == 'POST':
        form = CustomerRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account has been created successfully!')
            return redirect('customer_login')
        else:
            # Handle form errors and display them
            error_messages = []
            password_errors = []

            # Collect errors
            for field, errors in form.errors.items():
                # Handle password1 errors
                if field == 'password1':
                    for error in errors:
                        password_errors.append(f"Password: {error}")
                # Handle password2 errors separately
                elif field == 'password2':
                    for error in errors:
                        password_errors.append(f"Password: {error}")
                # Handle other fields normally
                else:
                    error_messages.append(f"{field.capitalize()}: {errors[0]}")

            # Combine all error messages
            if password_errors:
                error_messages.extend(password_errors)

            # Join all error messages with a line break
            if error_messages:
                messages.error(request, '<br>'.join(set(error_messages)))  # Use set to avoid duplicates

            print(form.errors)  # Optional: for debugging
    else:
        form = CustomerRegisterForm()

    return render(request, 'customer_register.html', {'form': form})

def rider_register(request):
    if request.method == 'POST':
        form = RiderRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])  # Set the password
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

            # Send a success response with a message
            return JsonResponse({
                'status': 'success',
                'message': 'Rider registration successful. Your application is pending approval.'
            })

        else:
            # Return the errors if the form is invalid
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
    menu_item = get_object_or_404(Menu, FoodID=food_id)
    store_owner = get_object_or_404(StoreOwner, user=request.user)

    # Handle the form submission
    if request.method == 'POST':
        form = MenuForm(request.POST, request.FILES, instance=menu_item)

        # Ensure restaurant is associated correctly
        if form.is_valid():
            form.save()  # This will also save the restaurant since it's part of the Menu model
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
        form = MenuForm(instance=menu_item)  # Use the existing menu item instance here

    return render(request, 'owner_edit_menu.html', {
        'menu_form': form,
        'menu_item': menu_item,
        'store_owner': store_owner,
    })
# Initialize logger
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

def owner_restaurants(request, owner_id):
    owner = get_object_or_404(StoreOwner, OwnerID=owner_id)
    restaurants = Restaurant.objects.filter(OwnerID=owner, Status='approved')  # Get all restaurants by this owner
    
    notifications = request.session.get('notifications', get_notifications())
    notification_count = len(notifications)

    context = {
        'owner': owner,
        'restaurants': restaurants,
        'notification_count': notification_count,
    }

    return render(request, 'owner_restaurants.html', context)

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
    notifications = get_notifications()
    notification_count = len(notifications)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            restaurant.Status = 'approved'
            restaurant.save()

            if restaurant.OwnerID and restaurant.OwnerID.Email:
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
                send_mail(
                    'Your Partnership Request Rejected',
                    'We regret to inform you that your request to partner with us has been declined.',
                    settings.DEFAULT_FROM_EMAIL,
                    [restaurant.OwnerID.Email],
                    fail_silently=False,
                )
        
        return redirect('partner_request_list')

    return render(request, 'admin_request.html', {
        'restaurant': restaurant,
        'notification_count': notification_count,
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

    feedbacks = CustomersFeedback.objects.filter(Status='approved').order_by('-Date')[:10]

    rider = Rider.objects.get(user=request.user)

    context = {
        'feedbacks': feedbacks,
        'notification_count': notification_count,
        'rider': rider,
    }

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
    daily_earnings_records = []
    weekly_earnings_records = []
    monthly_earnings_records = []

    # Set the selected date if one is provided
    if selected_date:
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
    else:
        selected_date = datetime.today().date()  # Default to today if no date is selected

    # Handle Daily Earnings
    daily_earnings_records = Delivery.objects.filter(RiderID=rider, Date__date=selected_date)
    daily_earnings = sum(earning.DeliveryFee for earning in daily_earnings_records)

    # Handle Weekly Earnings
    start_of_week = selected_date - timedelta(days=selected_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    weekly_earnings_records = Delivery.objects.filter(RiderID=rider, Date__date__range=[start_of_week, end_of_week])
    weekly_earnings = sum(earning.DeliveryFee for earning in weekly_earnings_records)

    # Handle Monthly Earnings
    start_of_month = selected_date.replace(day=1)
    next_month = (start_of_month.replace(month=start_of_month.month % 12 + 1, day=1) 
                  if start_of_month.month < 12 else 
                  (start_of_month.replace(year=start_of_month.year + 1, month=1, day=1)))
    end_of_month = next_month - timedelta(days=1)
    monthly_earnings_records = Delivery.objects.filter(RiderID=rider, Date__date__range=[start_of_month, end_of_month])
    monthly_earnings = sum(earning.DeliveryFee for earning in monthly_earnings_records)

    # Convert records to a serializable format
    daily_earnings_records = [
        {
            'Date': earning.Date.strftime("%Y-%m-%d"),
            'Address': earning.Address,
            'DeliveryFee': float(earning.DeliveryFee),
        } for earning in daily_earnings_records
    ]

    weekly_earnings_records = [
        {
            'Date': earning.Date.strftime("%Y-%m-%d"),
            'Address': earning.Address,
            'DeliveryFee': float(earning.DeliveryFee),
        } for earning in weekly_earnings_records
    ]

    monthly_earnings_records = [
        {
            'Date': earning.Date.strftime("%Y-%m-%d"),
            'Address': earning.Address,
            'DeliveryFee': float(earning.DeliveryFee),
        } for earning in monthly_earnings_records
    ]

    # Serialize QuerySets to JSON
    daily_earnings_records_json = json.dumps(daily_earnings_records)
    weekly_earnings_records_json = json.dumps(weekly_earnings_records)
    monthly_earnings_records_json = json.dumps(monthly_earnings_records)

    # Pass the rider object to the context
    context = {
        'selected_date': selected_date,
        'daily_earnings': daily_earnings,
        'weekly_earnings': weekly_earnings,
        'monthly_earnings': monthly_earnings,
        'earnings': daily_earnings_records,  # or keep this if needed for something else
        'notification_count': notification_count,
        'daily_earnings_records': daily_earnings_records_json,
        'weekly_earnings_records': weekly_earnings_records_json,
        'monthly_earnings_records': monthly_earnings_records_json,
        'rider': rider,
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
    owner_notifications = request.session.get('owner_notifications', [])
    notification_count = len(owner_notifications)

    store_owner = get_object_or_404(StoreOwner, user=request.user)
    error_message = None

    if request.method == 'POST':
        form = StoreOwnerUpdateForm(request.POST, request.FILES, instance=store_owner)
        if form.is_valid():
            # Validate the current password before updating any changes
            if form.cleaned_data.get('password'):
                if not request.user.check_password(form.cleaned_data.get('password')):
                    error_message = "Current password is incorrect."
                else:
                    # If a new password is being set, save the new password
                    new_password = form.cleaned_data.get('password1')
                    if new_password:
                        store_owner.user.set_password(new_password)  # Update the password
                        messages.success(request, "Your password has been changed. Please log in with the new password.")
                        store_owner.save()
                        logout(request)
                        return redirect(reverse('customer_login') + '?success=password')
                    else:
                        form.save()
                        messages.success(request, "Profile updated successfully.")
                        return redirect(reverse('update_store_owner_profile') + '?success=true')
            else:
                # Save profile without password change
                form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect(reverse('update_store_owner_profile') + '?success=true')
        else:
            error_message = form.errors

    else:
        initial_data = {
            'username': request.user.username,
            'email': request.user.email,
            'first_name': store_owner.FirstName,
            'last_name': store_owner.LastName,
            'phone': store_owner.Phone,
        }
        form = StoreOwnerUpdateForm(instance=store_owner, initial=initial_data)

    success = 'success' in request.GET

    return render(request, 'owner_profile.html', {
        'form': form,
        'store_owner': store_owner,
        'success': success,
        'error_message': error_message,
        'notification_count': notification_count,
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
            cart_item.save()  # Save the updated quantity
        
        # Return the updated cart count
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
    total_price = 0

    # Calculate total prices for each cart item
    for item in cart_items:
        item_total_price = item.FoodID.Price * item.Quantity  # Calculate item total
        total_price += item_total_price  # Accumulate total price
        item.item_total_price = item_total_price  # Add total price for item to pass to template

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

def update_cart_item_quantity(request, item_id):
    if request.method == 'POST':
        action = request.POST.get('action')
        cart_item = get_object_or_404(CartItem, id=item_id)

        if action == 'increase':
            cart_item.Quantity += 1
        elif action == 'decrease':
            cart_item.Quantity -= 1
            if cart_item.Quantity <= 0:
                cart_item.delete()  # Remove the item if quantity is 0
                return JsonResponse({'success': True})
        cart_item.save()
        
        return JsonResponse({'success': True})
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
    # Fetch all store owners, regardless of restaurant status
    store_owners = StoreOwner.objects.all()  # Get all store owners

    notifications = request.session.get('notifications', get_notifications())
    notification_count = len(notifications)

    context = {
        'owners': store_owners,  # Pass store owners to the template
        'notification_count': notification_count,
    }

    return render(request, 'restaurant_partners.html', context)

@login_required
def admin_home(request):
    # Fetch total counts
    total_storeowners = StoreOwner.objects.values('user').distinct().count()
    total_customers = Customer.objects.count()
    total_riders = Rider.objects.filter(Status='accepted').count()
    total_deliveries = Delivery.objects.count()
    total_users = total_customers + total_riders

    # Fetch the selected date from GET request
    selected_date = request.GET.get('date')

    # If no date is selected, use today's date as default
    if selected_date:
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    else:
        selected_date = timezone.now().date()

    # Prepare a full list of months and initialize earnings (unchanged monthly earnings)
    months = list(month_name)[1:]  # Get all month names (January to December)
    earnings = [0.0] * 12  # Initialize earnings for all months

    # Monthly earnings calculation (always for the whole year, unaffected by selected_date)
    monthly_data = Delivery.objects.annotate(month=ExtractMonth('Date')).values('month').annotate(total=Sum('DeliveryFee')).order_by('month')
    for entry in monthly_data:
        month_index = entry['month'] - 1  # Convert to 0-based index
        earnings[month_index] = float(entry['total'] or 0)  # Convert Decimal to float

    # Fix for daily earnings (specific to the selected date)
    daily_earnings = []
    for i in range(7):
        day = selected_date - timedelta(days=i)
        daily_total = Delivery.objects.filter(Date__date=day).aggregate(Sum('DeliveryFee'))['DeliveryFee__sum'] or 0
        daily_earnings.append(float(daily_total))
    daily_earnings.reverse()  # To show in the correct order (oldest to newest)

    # Fix for weekly earnings (start from Monday of the selected week)
    start_week = selected_date - timedelta(days=selected_date.weekday())  # Start of the selected week (Monday)
    weekly_earnings = []
    for i in range(7):  # Loop for 7 days of the week
        day = start_week + timedelta(days=i)
        weekly_total = Delivery.objects.filter(Date__date=day).aggregate(Sum('DeliveryFee'))['DeliveryFee__sum'] or 0
        weekly_earnings.append(float(weekly_total))

    notifications = request.session.get('notifications', get_notifications())
    notification_count = len(notifications)

    context = {
        'total_deliveries': total_deliveries,
        'total_storeowners': total_storeowners,  # StoreOwner count
        'total_riders': total_riders,
        'total_customers': total_customers,
        'total_users': total_users,
        'months': json.dumps(months),
        'earnings': json.dumps(earnings),  # Monthly data stays the same
        'daily_earnings': json.dumps(daily_earnings),  # List of daily earnings for the last 7 days
        'weekly_earnings': json.dumps(weekly_earnings),  # List of weekly earnings for the selected week
        'notification_count': notification_count,
        'selected_date': selected_date,  # Pass the selected date to the template
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
        'customer_points': customer.Points,
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

        # Get order details from POST data and convert them to Decimal
        payment_option = request.POST.get('payment-option')
        address = request.POST.get('address')
        subtotal = Decimal(request.POST.get('subtotal', '0'))
        delivery_fee = Decimal(request.POST.get('delivery-fee', '0'))
        total_amount = Decimal(request.POST.get('total-payable-amount', '0'))

        if not address:
            messages.error(request, "Address is required to place an order.")
            return redirect('place_order')

        # Create a single order record
        total_order_amount = Decimal(0)  # Initialize total amount as Decimal
        order_details = []

        # Create the order with a zero amount to finalize later
        order = Order(
            CustomerID=customer,
            OrderTotal=total_order_amount,
            Date=timezone.now(),
            TransactionID='',
        )
        order.save()

        # Loop through cart items to calculate total order amount and details
        for item in cart_items:
            item_total = Decimal(item.Quantity) * item.FoodID.Price  # Ensure calculation uses Decimal
            total_order_amount += item_total
            order_details.append(f"{item.FoodID.FoodName} (Quantity: {item.Quantity})")

        # Finalize order total after adding all cart items
        order.OrderTotal = total_order_amount
        order.save()

        # Calculate the total payable amount (subtotal + delivery fee)
        total_amount = total_order_amount + delivery_fee

        # Handle payment options
        if payment_option == 'paypal':
            paypal_dict = {
                'business': settings.PAYPAL_RECEIVER_EMAIL,
                'amount': total_amount,  # Use Decimal for accurate calculation
                'item_name': f'Order from {customer.CustomerName}',
                'invoice': order.OrderID,
                'notify_url': request.build_absolute_uri('/paypal-ipn/'),
                'return': request.build_absolute_uri('/order-completed/'),
                'cancel_return': request.build_absolute_uri('/order-cancelled/'),
                'address_override': 1,
                'address': address,
            }
            form = PayPalPaymentsForm(initial=paypal_dict)
            rendered_form = form.render()

        # Create a delivery record for the order
        rider = order.get_assigned_rider()  # Assuming method to get assigned rider
        if rider is not None:
            delivery = Delivery.objects.create(
                CustomerID=customer,
                RiderID=rider,
                RestaurantID=cart_items.first().FoodID.restaurant,
                Address=address,
                OrderTotal=total_order_amount,
                DeliveryFee=delivery_fee,
                TotalPayableAmount=total_amount,
                DeliveryStatus='Pending',
                OrderID=order
            )

            # Create delivery items for each cart item
            for item in cart_items:
                DeliveryItem.objects.create(
                    Delivery=delivery,
                    FoodID=item.FoodID,
                    Quantity=item.Quantity
                )

            # Notify rider via email
            rider_email = rider.user.email
            subject = 'New Order Notification'
            customer_name = f"{customer.CustomerName}"
            restaurant_name = cart_items.first().FoodID.restaurant.RestaurantName
            order_items = ", ".join(order_details)
            message = (
                f"You have a new order from {customer_name}.\n"
                f"Restaurant: {restaurant_name}\n"
                f"Items: {order_items}\n"
                f"Address: {address}\n"
                f"Delivery ID: {delivery.DeliveryID}"
            )

            try:
                send_mail(subject, message, settings.EMAIL_HOST_USER, [rider_email])
            except Exception as e:
                messages.error(request, "Failed to send email notification.")
                print(f"Email send error: {e}")

            # Store rider notifications in session
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
            points_earned = Decimal(0.1)
        elif 50 <= total_amount < 100:
            points_earned = Decimal(0.5)
        else:
            points_earned = (total_amount // Decimal(100)) * Decimal(1.0)
            remaining_amount = total_amount % Decimal(100)
            if remaining_amount >= Decimal(50):
                points_earned += Decimal(0.5)

        # Update customer's points
        customer.Points += points_earned
        customer.save()

        # Clear the cart after placing the order
        cart_items.delete()

        # Show success message with points earned
        messages.success(request, f"Your order has been placed successfully! You earned {points_earned:.1f} points.")
        return redirect('customer_home')

    return redirect('customer_home')



@login_required
def order_completed(request):
    order_id = request.GET.get('invoice')  # Get the order ID from PayPal's response

    if order_id:
        try:
            order = Order.objects.get(OrderID=order_id)

            # Validate payment here using PayPal API or other means

            # Retrieve customer and cart items
            customer = request.user.customer
            cart_items = CartItem.objects.filter(CustomerID=customer)

            # Create the delivery record
            rider = order.get_assigned_rider()  # You may need to adjust this based on your logic
            
            if rider is not None:
                delivery = Delivery.objects.create(
                    CustomerID=customer,
                    RiderID=rider,
                    RestaurantID=cart_items.first().FoodID.restaurant,
                    Address=order.Address,  # Ensure you stored the address in the order
                    OrderTotal=order.OrderTotal,
                    DeliveryFee=order.DeliveryFee,
                    TotalPayableAmount=order.OrderTotal,  # Assuming total amount here
                    DeliveryStatus='Pending',
                    OrderID=order  # Reference to the order
                )

                # Create delivery items for each order
                for item in cart_items:
                    DeliveryItem.objects.create(
                        Delivery=delivery,
                        FoodID=item.FoodID,
                        Quantity=item.Quantity
                    )

                messages.info(request, "Your order has been placed successfully, and delivery has been scheduled.")
                
                # Clear the cart after successful delivery creation
                cart_items.delete()  # Clear the cart items for the customer

            else:
                messages.error(request, "No rider is assigned to this order.")
                return redirect('customer_home')

        except Order.DoesNotExist:
            messages.error(request, "The order does not exist.")
            return redirect('customer_home')
    else:
        messages.error(request, "Invalid order ID.")
        return redirect('customer_home')

    return redirect('customer_home')


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

    # Get the deliveries that are delivered and not archived
    deliveries = Delivery.objects.filter(RiderID=rider, DeliveryStatus='Received', is_archived=False)

    latest_notifications = rider_notifications[-10:]

    context = {
        'deliveries': deliveries,
        'notifications': latest_notifications,
        'notification_count': notification_count,
        'rider': rider,
    }
    
    return render(request, 'rider_delivery_history.html', context)

@login_required
def rider_archived_deliveries(request):
    rider = request.user.rider
    rider_notifications = get_rider_notifications(rider.RiderID)
    notification_count = len(rider_notifications)

    # Get the deliveries that are archived
    archived_deliveries = Delivery.objects.filter(RiderID=rider, is_archived=True)

    latest_notifications = rider_notifications[-10:]

    context = {
        'archived_deliveries': archived_deliveries,
        'notifications': latest_notifications,
        'notification_count': notification_count,
        'rider': rider,
    }
    
    return render(request, 'rider_archived_deliveries.html', context)

@login_required
def archive_delivery(request, delivery_id):
    delivery = get_object_or_404(Delivery, pk=delivery_id)
    if request.method == 'POST':
        delivery.is_archived = True
        delivery.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

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
        # Search for accepted riders based on full name or email
        riders = Rider.objects.filter(
            Q(FullName__icontains=query) | Q(Email__icontains=query),
            Status='accepted'  # Filter only accepted riders
        )
    else:
        # Display all accepted riders
        riders = Rider.objects.filter(Status='accepted')  # Filter only accepted riders
    
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
        except Rider.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Rider not found'})
        except Exception as e:
            print(e)
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

def password_reset_request(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
            otp = generate_otp()
            request.session['reset_otp'] = otp  # Store OTP in session
            request.session['reset_username'] = username  # Store username in session

            # Send OTP via email
            send_mail(
                'Password Reset OTP',
                f'Your OTP for password reset is {otp}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            # Return JSON response instead of rendering the template
            return JsonResponse({'success': True, 'email': user.email})

        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Username not found. Please check your input.'})

    return render(request, 'password_reset_request.html')

def check_username(request):
    username = request.GET.get('username')
    try:
        user = User.objects.get(username=username)
        return JsonResponse({'exists': True, 'email': user.email})
    except User.DoesNotExist:
        return JsonResponse({'exists': False})

def verify_otp(request):
    user_otp = request.GET.get('otp')
    session_otp = request.session.get('reset_otp')
    
    if str(user_otp) == str(session_otp):
        return JsonResponse({'verified': True})
    else:
        return JsonResponse({'verified': False})

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

@login_required
def customer_chat(request, rider_id):
    try:
        customer = Customer.objects.get(user=request.user)
        rider = Rider.objects.get(RiderID=rider_id)

        # Fetch all messages between the logged-in customer and the rider
        messages = Message.objects.filter(
            Q(sender=rider.user) | Q(receiver=rider.user)
        ).order_by('timestamp')

        # Pass data to the template
        context = {
            'customer': customer,
            'rider': rider,
            'messages': messages,
        }

        return render(request, 'customer_chat.html', context)

    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)
    except Rider.DoesNotExist:
        return JsonResponse({'error': 'Rider not found'}, status=404)

@login_required
def rider_chat(request, rider_id):
    try:
        rider = get_object_or_404(Rider, RiderID=rider_id)

        # Fetch all messages involving this rider (either as sender or receiver)
        messages = Message.objects.filter(
            Q(sender=rider.user) | Q(receiver=rider.user)
        ).order_by('timestamp')

        # Get all customers in the chat
        customers_in_chat = set()
        for message in messages:
            if message.sender != rider.user:
                customers_in_chat.add(message.sender)
            if message.receiver != rider.user:
                customers_in_chat.add(message.receiver)

        # Retrieve Customer data (name and profile picture)
        customer_profiles = {}
        for customer in customers_in_chat:
            customer_profile = get_object_or_404(Customer, user=customer)
            customer_profiles[customer] = {
                'name': customer_profile.CustomerName,
                'profile_picture': customer_profile.Picture.url if customer_profile.Picture else 'default_profile.jpg'
            }

        # Pass data to template
        context = {
            'rider': rider,
            'messages': messages,
            'customer_profiles': customer_profiles,
        }

        return render(request, 'rider_chat.html', context)

    except Rider.DoesNotExist:
        return JsonResponse({'error': 'Rider not found'}, status=404)

@login_required
def send_message(request):
    if request.method == 'POST':
        try:
            # Parse the incoming JSON data
            data = json.loads(request.body)
            message_content = data.get('message')
            rider_id = data.get('rider_id')

            if not message_content or not rider_id:
                return JsonResponse({'error': 'Message content or rider_id missing'}, status=400)

            # Fetch the rider and create the message
            rider = Rider.objects.get(RiderID=rider_id)
            message = Message.objects.create(sender=request.user, receiver=rider.user, message=message_content)

            # Return the new message in the response
            return JsonResponse({
                'message': message.message,  # Make sure message is returned here
            })

        except Rider.DoesNotExist:
            return JsonResponse({'error': 'Rider not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def delete_conversation(request):
    if request.method == 'POST':
        try:
            # Parse the request body for the RiderID (which is the username in this case)
            data = json.loads(request.body)
            rider_username = data.get('RiderID')  # Using the rider's username

            if not rider_username:
                return JsonResponse({'success': False, 'error': 'RiderID (username) is required'})

            # Debugging: Check if the rider_username is correctly passed
            print(f"Received RiderID (username): {rider_username}")

            # Filter messages where the rider's username is either the sender or receiver
            messages = Message.objects.filter(
                Q(sender=rider_username) | Q(receiver=rider_username)
            )

            # Debugging: Output the filtered messages
            print(f"Messages found: {messages}")

            # Check if there are messages to delete
            if messages.exists():
                messages.delete()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'No messages found for this RiderID (username)'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})