document.addEventListener('DOMContentLoaded', () => {
    // Helper to add class on scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });

    // Razorpay Subscription
    document.querySelectorAll('.plan-button').forEach(button => {
        button.addEventListener('click', handleSubscriptionClick);
    });

    // Dashboard Filtering
    const filterControls = document.querySelectorAll('.dashboard-filter');
    if (filterControls.length > 0) {
        filterControls.forEach(control => {
            control.addEventListener('change', handleLeadFilterChange);
        });
    }

    // Delegated event listener for lead status buttons
    const leadFeedContainer = document.getElementById('lead-feed');
    if (leadFeedContainer) {
        leadFeedContainer.addEventListener('click', handleLeadCardActions);
    }
});

/**
 * Handles clicks on lead card action buttons (e.g., mark as viewed)
 */
async function handleLeadCardActions(event) {
    const button = event.target.closest('.lead-status-button');
    if (!button) return;

    const leadCard = button.closest('.lead-card');
    const leadId = button.dataset.leadId;
    const newStatus = button.dataset.status;
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Optimistic UI update
    leadCard.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    leadCard.style.opacity = '0.5';
    button.disabled = true;
    button.textContent = 'Updating...';

    try {
        const response = await fetch(`/update-lead-status/${leadId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (response.ok) {
            // Animate out and remove
            leadCard.style.transform = 'scale(0.95)';
            leadCard.style.opacity = '0';
            setTimeout(() => leadCard.remove(), 500);
        } else {
            throw new Error('Failed to update status');
        }
    } catch (error) {
        console.error('Error updating lead status:', error);
        // Revert UI on failure
        leadCard.style.opacity = '1';
        button.disabled = false;
        button.textContent = `Mark as ${newStatus.charAt(0).toUpperCase() + newStatus.slice(1)}`;
        alert('Failed to update lead status. Please try again.');
    }
}

/**
 * Handles the change event for dashboard filter controls.
 */
function handleLeadFilterChange() {
    const streamId = document.getElementById('filter-stream').value;
    const platform = document.getElementById('filter-platform').value;
    const status = document.getElementById('filter-status').value;
    const leadFeedContainer = document.getElementById('lead-feed');
    const skeletonLoader = document.getElementById('skeleton-loader');

    // Show skeleton loader
    skeletonLoader.classList.remove('hidden');
    leadFeedContainer.innerHTML = ''; // Clear current leads

    const params = new URLSearchParams({
        stream_id: streamId,
        platform: platform,
        status: status,
    });

    fetch(`/filter-leads?${params.toString()}`)
        .then(response => response.text())
        .then(html => {
            skeletonLoader.classList.add('hidden');
            leadFeedContainer.innerHTML = html;
        })
        .catch(error => {
            console.error('Error fetching filtered leads:', error);
            skeletonLoader.classList.add('hidden');
            leadFeedContainer.innerHTML = `<div class="text-center p-8 bg-red-50 text-red-700 rounded-lg">
                <p><strong>Oops!</strong> Could not load leads. Please try again later.</p>
            </div>`;
        });
}

/**
 * Handles the subscription button click and initiates Razorpay checkout.
 */
async function handleSubscriptionClick(event) {
    const button = event.currentTarget;
    const planType = button.dataset.plan;
    const userEmail = button.dataset.userEmail;
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    if (!userEmail) {
        window.location.href = '/login';
        return;
    }

    button.disabled = true;
    button.innerHTML = `<i class="fas fa-spinner fa-spin mr-2"></i>Please wait...`;

    try {
        const response = await fetch('/create-subscription', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ plan_type: planType })
        });
        const data = await response.json();

        if (response.ok && data.subscription_id) {
            const options = {
                key: data.key_id,
                subscription_id: data.subscription_id,
                name: "Signal Stream",
                description: `${planType.charAt(0).toUpperCase() + planType.slice(1)} Plan`,
                image: "/static/images/logo.svg",
                handler: (response) => {
                    alert('Subscription successful! Redirecting to dashboard.');
                    window.location.href = '/dashboard';
                },
                prefill: {
                    name: data.user_name,
                    email: data.user_email
                },
                theme: { color: "#38B2AC" }
            };
            const rzp = new Razorpay(options);
            rzp.on('payment.failed', function (response){
                alert('Payment failed. Please try again.');
                console.error(response);
            });
            rzp.open();
        } else {
            throw new Error(data.error || 'Unknown subscription error');
        }
    } catch (error) {
        alert(`An error occurred: ${error.message}`);
        console.error('Error:', error);
    } finally {
        button.disabled = false;
        button.innerHTML = `Choose Plan`;
    }
}