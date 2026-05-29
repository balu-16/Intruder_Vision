document.addEventListener('DOMContentLoaded', function () {
    // DOM Elements
    const startButton = document.getElementById('start-monitoring');
    const stopButton = document.getElementById('stop-monitoring');
    const testCaptureButton = document.getElementById('test-capture');
    const wrongPasswordButton = document.getElementById('wrong-password');
    const toggleCameraButton = document.getElementById('toggle-camera');
    const statusBadge = document.getElementById('status-badge');
    const notification = document.getElementById('notification');
    const notificationMessage = document.getElementById('notification-message');
    const notificationClose = document.getElementById('notification-close');
    const alertsContainer = document.getElementById('alerts-container');

    // Camera state
    let cameraActive = false;

    // Start monitoring
    startButton.addEventListener('click', function () {
        fetch('/start_monitoring', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateMonitoringStatus(true);
                    showNotification('success', 'Monitoring started successfully!');
                } else {
                    showNotification('info', data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('error', 'Failed to start monitoring');
            });
    });

    // Stop monitoring
    stopButton.addEventListener('click', function () {
        fetch('/stop_monitoring', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateMonitoringStatus(false);
                    showNotification('success', 'Monitoring stopped successfully!');
                } else {
                    showNotification('info', data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('error', 'Failed to stop monitoring');
            });
    });

    // Toggle camera
    if (toggleCameraButton) {
        toggleCameraButton.addEventListener('click', function () {
            const newState = !cameraActive;

            fetch('/toggle_stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enable: newState })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success' || data.status === 'info') {
                        cameraActive = newState;
                        updateCameraButton();

                        if (newState) {
                            showNotification('info', 'Camera activated');
                        } else {
                            showNotification('info', 'Camera deactivated');
                        }
                    } else {
                        showNotification('error', data.message || 'Failed to toggle camera');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('error', 'Failed to toggle camera');
                });
        });
    }

    // Trigger wrong password simulation
    if (wrongPasswordButton) {
        wrongPasswordButton.addEventListener('click', function () {
            showNotification('info', 'Simulating wrong password...');

            fetch('/wrong_password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        showNotification('success', 'Wrong password alert triggered!');
                        refreshAlerts();
                    } else {
                        showNotification('error', data.message || 'Failed to trigger wrong password alert');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('error', 'Failed to trigger wrong password alert');
                });
        });
    }

    // Test camera capture
    testCaptureButton.addEventListener('click', function () {
        showNotification('info', 'Capturing test image...');

        fetch('/test_capture', {
            method: 'POST',
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showNotification('success', 'Test image captured successfully!');
                    // Refresh alerts to show the new test image
                    refreshAlerts();
                } else {
                    showNotification('error', data.message || 'Failed to capture test image');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('error', 'Failed to capture test image');
            });
    });

    // Close notification
    notificationClose.addEventListener('click', function () {
        hideNotification();
    });

    // Auto-refresh alerts every 10 seconds
    setInterval(refreshAlerts, 10000);

    // Check system status on load and periodically
    checkSystemStatus();
    setInterval(checkSystemStatus, 30000);

    // Function to update UI based on monitoring status
    function updateMonitoringStatus(isActive) {
        if (isActive) {
            statusBadge.className = 'active';
            statusBadge.innerHTML = '<i class="fas fa-shield-alt"></i> MONITORING ACTIVE';
            startButton.disabled = true;
            stopButton.disabled = false;
        } else {
            statusBadge.className = 'inactive';
            statusBadge.innerHTML = '<i class="fas fa-shield-alt"></i> MONITORING INACTIVE';
            startButton.disabled = false;
            stopButton.disabled = true;
        }
    }

    // Function to update camera button based on state
    function updateCameraButton() {
        if (toggleCameraButton) {
            if (cameraActive) {
                toggleCameraButton.innerHTML = '<i class="fas fa-video-slash"></i> Turn Off Camera';
                toggleCameraButton.className = 'btn btn-red';
            } else {
                toggleCameraButton.innerHTML = '<i class="fas fa-video"></i> Turn On Camera';
                toggleCameraButton.className = 'btn btn-blue';
            }
        }
    }

    // Function to show notification
    function showNotification(type, message) {
        notification.className = 'notification show ' + type;

        // Set icon based on type
        let icon = '';
        if (type === 'success') {
            icon = '<i class="fas fa-check-circle"></i>';
        } else if (type === 'error') {
            icon = '<i class="fas fa-exclamation-circle"></i>';
        } else {
            icon = '<i class="fas fa-info-circle"></i>';
        }

        notificationMessage.innerHTML = icon + ' ' + message;

        // Auto-hide notification after 5 seconds
        setTimeout(hideNotification, 5000);
    }

    // Function to hide notification
    function hideNotification() {
        notification.className = 'notification';
    }

    // Function to check system status
    function checkSystemStatus() {
        fetch('/system_status')
            .then(response => response.json())
            .then(status => {
                updateMonitoringStatus(status.monitoring_active);
                cameraActive = status.stream_active;
                updateCameraButton();
            })
            .catch(error => {
                console.error('Error checking system status:', error);
            });
    }

    // Function to refresh alerts
    function refreshAlerts() {
        fetch('/get_alerts')
            .then(response => response.json())
            .then(data => {
                const alerts = data.alerts || [];
                console.log("Received alerts:", alerts);

                const alertsContainer = document.getElementById('alerts-container');
                if (!alertsContainer) {
                    console.error("Could not find alerts-container element");
                    return;
                }
                // Clear existing content safely
                alertsContainer.textContent = '';

                if (alerts && alerts.length > 0) {
                    alerts.forEach(alert => {
                        const isTest = alert.is_test || false;
                        const isSimulated = alert.is_simulated || false;
                        const cardClass = isTest ? 'test-alert' : isSimulated ? 'simulated-alert' : '';
                        const message = alert.message || (isTest ? 'Test Capture' : 'Intruder Detected!');

                        const card = document.createElement('div');
                        card.className = 'alert-card ' + cardClass;

                        const info = document.createElement('div');
                        info.className = 'alert-info';

                        const h3 = document.createElement('h3');
                        h3.textContent = message;

                        const timeP = document.createElement('p');
                        const clockIcon = document.createElement('i');
                        clockIcon.className = 'fas fa-clock';
                        timeP.appendChild(clockIcon);
                        timeP.appendChild(document.createTextNode(' ' + (alert.timestamp || '')));

                        const emailP = document.createElement('p');
                        const emailIcon = document.createElement('i');
                        emailIcon.className = 'fas fa-envelope';
                        emailP.appendChild(emailIcon);
                        emailP.appendChild(document.createTextNode(' Email: '));
                        const emailSpan = document.createElement('span');
                        emailSpan.className = alert.email_sent ? 'success' : 'not-sent';
                        emailSpan.textContent = alert.email_sent ? 'Sent' : 'Not Sent';
                        emailP.appendChild(emailSpan);

                        const smsP = document.createElement('p');
                        const smsIcon = document.createElement('i');
                        smsIcon.className = 'fas fa-sms';
                        smsP.appendChild(smsIcon);
                        smsP.appendChild(document.createTextNode(' SMS: '));
                        const smsSpan = document.createElement('span');
                        smsSpan.className = alert.sms_sid ? 'success' : 'not-sent';
                        smsSpan.textContent = alert.sms_sid ? 'Sent' : 'Not Sent';
                        smsP.appendChild(smsSpan);

                        info.appendChild(h3);
                        info.appendChild(timeP);
                        info.appendChild(emailP);
                        info.appendChild(smsP);

                        const imageDiv = document.createElement('div');
                        imageDiv.className = 'alert-image';
                        const img = document.createElement('img');
                        const imgSrc = '/static/' + String(alert.image_path || '').replace(/^static\//, '');
                        img.setAttribute('src', imgSrc);
                        img.setAttribute('alt', 'Intruder Image');
                        img.onerror = function() { this.src = '/static/images/no-image.png'; this.onerror = null; };
                        imageDiv.appendChild(img);

                        card.appendChild(info);
                        card.appendChild(imageDiv);
                        alertsContainer.appendChild(card);
                    });
                    console.log("Updated alerts container");
                } else {
                    const noAlerts = document.createElement('div');
                    noAlerts.className = 'no-alerts';
                    const checkIcon = document.createElement('i');
                    checkIcon.className = 'fas fa-check-circle';
                    const p = document.createElement('p');
                    p.textContent = 'No alerts detected yet. Your system is secure.';
                    noAlerts.appendChild(checkIcon);
                    noAlerts.appendChild(p);
                    alertsContainer.appendChild(noAlerts);
                }
            })
            .catch(error => {
                console.error('Error refreshing alerts:', error);
            });
    }
}); 