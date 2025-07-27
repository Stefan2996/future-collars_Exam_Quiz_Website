// Function to toggle the visibility of detailed questions
function toggleDetails() {
    const details = document.getElementById('questions-details');
    const toggleText = document.getElementById('toggle-text');
    const toggleIcon = document.getElementById('toggle-icon');

    if (details.style.display === 'none' || details.style.display === '') {
        details.style.display = 'block';
        toggleText.textContent = 'Hide details';
        toggleIcon.className = 'fas fa-chevron-up';
    } else {
        details.style.display = 'none';
        toggleText.textContent = 'Show details';
        toggleIcon.className = 'fas fa-chevron-down';
    }
}

// Ensure the functions are available globally if needed by onclick attributes,
// or refactor HTML to use event listeners after DOMContentLoaded.
// For now, keep them global to match current HTML usage.
window.toggleDetails = toggleDetails;


document.addEventListener("DOMContentLoaded", () => {
    const resultsDataScript = document.getElementById("results-data");
    if (!resultsDataScript) {
        console.error("Results data script tag not found.");
        return;
    }

    const resultsData = JSON.parse(resultsDataScript.textContent);

    function shareResult() {
        const score = resultsData.score;
        const total = resultsData.total_questions;
        const percentage = resultsData.percentage;
        const packTitle = resultsData.pack_title;

        const text = `I completed the quiz "${packTitle}" and scored ${score}/${total} points (${percentage}%)! 🎯`;

        if (navigator.share) {
            navigator.share({
                title: 'My QuizMaster Result',
                text: text,
                url: window.location.href
            });
        } else {
            copyResult(); // Fallback to copy if Web Share API is not available
            alert('Result copied to clipboard!');
        }
    }

    function copyResult() {
        const score = resultsData.score;
        const total = resultsData.total_questions;
        const percentage = resultsData.percentage;
        const packTitle = resultsData.pack_title;

        const text = `I completed the quiz "${packTitle}" and scored ${score}/${total} points (${percentage}%)! 🎯\n\nTry it too: ${window.location.origin}`;

        navigator.clipboard.writeText(text).then(() => {
            const notification = document.createElement('div');
            notification.className = 'copy-notification';
            notification.textContent = 'Result copied!';
            document.body.appendChild(notification);

            setTimeout(() => {
                notification.remove();
            }, 3000);
        }).catch(err => {
            console.error('Failed to copy text: ', err);
            alert('Failed to copy result. Please try manually.');
        });
    }

    // Attach these functions to the global window object so they can be called from onclick attributes
    window.shareResult = shareResult;
    window.copyResult = copyResult;
});