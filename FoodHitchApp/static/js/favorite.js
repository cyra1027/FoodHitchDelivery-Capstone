document.addEventListener('DOMContentLoaded', () => {
    const favoriteIcons = document.querySelectorAll('.favorite-icon');

    favoriteIcons.forEach(icon => {
        icon.addEventListener('click', () => {
            const foodId = icon.getAttribute('data-id'); // Changed itemId to foodId
            const isActive = icon.classList.contains('active');
            const newStatus = isActive ? 'remove' : 'add';

            // Toggle the icon's class immediately
            icon.classList.toggle('active');
            icon.setAttribute('name', isActive ? 'heart-outline' : 'heart');

            // Send the AJAX request to update the server
            fetch('/toggle_favorite/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value
                },
                body: JSON.stringify({ food_id: foodId, status: newStatus }) // Changed item_id to food_id
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.error('Error toggling favorite status');
                    // Revert the icon's class if there was an error
                    icon.classList.toggle('active');
                    icon.setAttribute('name', isActive ? 'heart-outline' : 'heart');
                } else {
                    // If on the Favorites page and the icon was un-favorited, remove the item from the DOM
                    if (newStatus === 'remove' && window.location.pathname === '/customer_favorites/') {
                        const storeCard = icon.closest('.store-card');
                        storeCard.parentNode.removeChild(storeCard);
                    }
                }
            });
        });
    });
});
