document.addEventListener('DOMContentLoaded', function() {
    // Modal functionality
    const modal = document.getElementById('action-modal');
    const closeBtn = document.querySelector('.close');
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const actionForm = document.getElementById('action-form');
    const modalTitle = document.getElementById('modal-title');
    const getLocationBtn = document.getElementById('get-location');
    
    if (loginBtn) {
        loginBtn.addEventListener('click', function() {
            modalTitle.textContent = 'Check In';
            actionForm.action = '/staff/login';
            modal.style.display = 'block';
        });
    }
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            modalTitle.textContent = 'Check Out';
            actionForm.action = '/staff/logout';
            modal.style.display = 'block';
        });
    }
    
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }
    
    if (modal) {
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
    
    // Get location functionality
    if (getLocationBtn) {
        getLocationBtn.addEventListener('click', function() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        document.getElementById('lat').value = position.coords.latitude;
                        document.getElementById('lng').value = position.coords.longitude;
                        
                        // Reverse geocoding to get address
                        fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${position.coords.latitude}&lon=${position.coords.longitude}`)
                            .then(response => response.json())
                            .then(data => {
                                const address = data.display_name || 'Location obtained';
                                document.getElementById('location').value = address;
                            })
                            .catch(error => {
                                console.error('Error getting address:', error);
                                document.getElementById('location').value = `Lat: ${position.coords.latitude}, Lng: ${position.coords.longitude}`;
                            });
                    },
                    function(error) {
                        console.error('Error getting location:', error);
                        alert('Unable to get your location. Please enter it manually.');
                    }
                );
            } else {
                alert('Geolocation is not supported by this browser.');
            }
        });
    }
    
    // Form submission
    if (actionForm) {
        actionForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(actionForm);
            const action = actionForm.action;
            
            fetch(action, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Action completed successfully!');
                    modal.style.display = 'none';
                    window.location.reload();
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
            });
        });
    }
    
    // Camera functionality for mobile devices
    const photoInput = document.getElementById('photo');
    if (photoInput) {
        photoInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    // You could display a preview here if needed
                    console.log('Photo selected');
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Real-time clock for dashboard
    function updateClock() {
        const now = new Date();
        const clockElement = document.getElementById('current-time');
        if (clockElement) {
            clockElement.textContent = now.toLocaleTimeString();
        }
    }
    
    setInterval(updateClock, 1000);
    updateClock();
    
    // Initialize any date pickers
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (!input.value) {
            input.valueAsDate = new Date();
        }
    });
});