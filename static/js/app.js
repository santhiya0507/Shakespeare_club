// Shakespeare Club Communication App JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, 5000);
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });

            if (!isValid) {
                e.preventDefault();
                showAlert('Please fill in all required fields.', 'danger');
            }
        });
    });

    // Practice submission handling
    const practiceForm = document.querySelector('form[action*="submit_practice"]');
    if (practiceForm) {
        practiceForm.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.innerHTML = '<span class="loading"></span> Analyzing...';
            submitBtn.disabled = true;
        });
    }
});

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function generateAnalytics() {
    showAlert('AI analytics generation started. This may take a few moments...', 'info');
    // This would typically make an AJAX call to generate analytics
}

// Practice type selection helper
function updatePracticeDescription(selectElement) {
    const descriptions = {
        'listening': 'Focus on audio comprehension and listening skills.',
        'observation': 'Enhance visual analysis and observational abilities.',
        'speaking': 'Develop verbal communication and presentation skills.',
        'writing': 'Improve written expression and communication clarity.'
    };
    
    const descriptionElement = document.getElementById('practice-description-help');
    if (descriptionElement) {
        descriptionElement.textContent = descriptions[selectElement.value] || '';
    }
}