// Password toggle functionality
function togglePassword(inputId) {
    const input = document.getElementById(inputId)
    const icon = input.nextElementSibling.querySelector("i")

    if (input.type === "password") {
        input.type = "text"
        icon.className = "fas fa-eye-slash"
    } else {
        input.type = "password"
        icon.className = "fas fa-eye"
    }
}

// Auto-hide flash messages
document.addEventListener("DOMContentLoaded", () => {
    const flashMessages = document.querySelectorAll(".flash-message")
    flashMessages.forEach((message) => {
        setTimeout(() => {
            message.style.animation = "slideOut 0.3s ease forwards"
            setTimeout(() => {
                message.remove()
            }, 300)
        }, 5000)
    })
})

// Add slideOut animation
const style = document.createElement("style")
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`
document.head.appendChild(style)