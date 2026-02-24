// Load tenders on dashboard/tenders pages
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('dashboard') || window.location.pathname.includes('tenders')) {
        loadTenders();
    }
});

async function loadTenders(page = 1) {
    try {
        const response = await fetch(`/api/tenders?page=${page}`);
        const data = await response.json();
        
        displayTenders(data.tenders, data.is_premium);
    } catch (error) {
        console.error('Error loading tenders:', error);
    }
}

function displayTenders(tenders, isPremium) {
    const container = document.querySelector('.tenders-grid') || document.getElementById('tenders-container');
    if (!container) return;

    container.innerHTML = tenders.map(tender => `
        <div class="tender-card">
            <div class="tender-header">
                <span class="badge badge-site">${tender.site || 'Unknown'}</span>
                <span class="badge badge-premium">${tender.organisation}</span>
            </div>
            <h3 class="tender-title">${tender.details.work_details.Title}</h3>
            <div class="tender-meta">
                <p><strong>Published:</strong> ${tender.details.critical_dates['Published Date']}</p>
                <p><strong>Closes:</strong> ${tender.details.critical_dates['Bid Opening Date']}</p>
                <p><strong>Value:</strong> ${isPremium ? tender.details.work_details['Tender Value in ₹'] : '***PREMIUM***'}</p>
                ${isPremium ? '' : '<p class="premium-cta">Upgrade to Premium for Tender ID & Full Details</p>'}
            </div>
        </div>
    `).join('');
}

function subscribe() {
    if (confirm('Subscribe to Premium for ₹100/month? Unlock all tender details!')) {
        window.location.href = '/subscribe';
    }
}
