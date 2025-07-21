// Password toggle functionality (оставляем без изменений)
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

// Auto-hide flash messages (оставляем без изменений)
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

// Add slideOut animation (оставляем без изменений)
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

// --- Quiz functionality (Client-side management) ---
// Этот блок полностью отвечает за логику квиза на фронтенде
document.addEventListener("DOMContentLoaded", () => {
    const quizDataScript = document.getElementById("quiz-data")
    // Проверяем, что мы на странице квиза и данные загружены
    if (!quizDataScript) {
        return // Если тега нет, значит, это не страница квиза, выходим
    }

    const quizData = JSON.parse(quizDataScript.textContent)
    const questions = quizData.questions // Список вопросов
    const packId = quizData.pack_id     // ID пака

    let currentQuestionIndex = 0
    // Массив для хранения объектов { questionId: ID_вопроса, selectedAnswerIndex: выбранный_индекс }
    const userAnswers = []

    const questionTextElement = document.getElementById("question-text")
    const answersContainer = document.getElementById("answers-container")
    const selectedAnswerInput = document.getElementById("selected-answer-input") // Временное хранение выбранного ответа
    const nextQuestionBtn = document.getElementById("next-question-btn")
    const finishQuizBtn = document.getElementById("finish-quiz-btn") // Эта кнопка пока скрыта
    const questionCounter = document.getElementById("question-counter")
    const progressPercentageSpan = document.getElementById("progress-percentage")
    const progressBarFill = document.querySelector(".progress-bar .progress-fill")

    function renderQuestion() {
        // Если вопросы закончились, завершаем квиз
        if (currentQuestionIndex >= questions.length) {
            showResults(); // Вызываем функцию завершения
            return;
        }

        const currentQuestion = questions[currentQuestionIndex]
        questionTextElement.textContent = currentQuestion.question // Устанавливаем текст вопроса

        answersContainer.innerHTML = "" // Очищаем контейнер от предыдущих ответов
        currentQuestion.options.forEach((option, index) => {
            const button = document.createElement("button")
            button.type = "button"
            button.classList.add("answer-btn")
            button.dataset.answerIndex = index // Храним индекс варианта ответа
            button.dataset.questionId = currentQuestion.id // Храним ID вопроса
            button.innerHTML = `<span class="answer-letter">${String.fromCharCode(65 + index)}.</span><span class="answer-text">${option}</span>`

            // Добавляем слушатель кликов для каждой кнопки ответа
            button.addEventListener("click", () => {
                // Убираем класс 'selected' со всех кнопок
                answersContainer.querySelectorAll(".answer-btn").forEach(btn => btn.classList.remove("selected"))
                // Добавляем класс 'selected' к нажатой кнопке
                button.classList.add("selected")
                // Записываем выбранный индекс ответа в скрытое поле
                selectedAnswerInput.value = button.dataset.answerIndex
                // Активируем кнопку "Следующий вопрос"
                nextQuestionBtn.disabled = false
            })
            answersContainer.appendChild(button)
        })

        // Сбрасываем состояние для нового вопроса
        selectedAnswerInput.value = "" // Очищаем выбранный ответ
        nextQuestionBtn.disabled = true // Деактивируем кнопку "Следующий вопрос"

        updateProgress() // Обновляем прогресс-бар и счетчик вопросов

        // Обновляем текст кнопки "Следующий вопрос" на "Завершить квиз", если это последний вопрос
        if (currentQuestionIndex === questions.length - 1) {
            nextQuestionBtn.textContent = "Завершить квиз"
        } else {
            nextQuestionBtn.textContent = "Следующий вопрос"
        }
    }

    function updateProgress() {
        const total = questions.length
        // current + 1, потому что индекс начинается с 0, а счет вопросов с 1
        const current = currentQuestionIndex
        const percentage = total > 0 ? (current / total) * 100 : 0

        questionCounter.textContent = `Вопрос ${current + 1} из ${total}`
        progressPercentageSpan.textContent = `Прогресс: ${percentage.toFixed(0)}%`
        progressBarFill.style.width = `${percentage}%`
    }

    // Функция, вызываемая по завершении квиза
    function showResults() {
        // Очищаем интерфейс квиза
        questionTextElement.textContent = "Квиз завершен! Сохранение результатов...";
        answersContainer.innerHTML = "";
        nextQuestionBtn.style.display = "none"; // Скрываем кнопку
        finishQuizBtn.style.display = "none"; // Скрываем резервную кнопку
        selectedAnswerInput.value = "";

        questionCounter.textContent = "Квиз завершен!";
        progressPercentageSpan.textContent = "Прогресс: 100%";
        progressBarFill.style.width = "100%";

        submitQuizResults(); // Отправляем результаты на сервер
    }

    // Отправка результатов на сервер
    async function submitQuizResults() {
        try {
            const response = await fetch("/submit_quiz", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    pack_id: packId, // Передаем ID пака
                    answers: userAnswers, // Передаем массив всех ответов пользователя
                }),
            });

            const result = await response.json(); // Получаем ответ от сервера

            if (result.success) { // Проверяем поле 'success' из ответа сервера
                // Если успешно, перенаправляем на страницу результатов, используя redirect_url
                window.location.href = result.redirect_url;
            } else {
                // Если ошибка, показываем сообщение и перенаправляем на страницу паков
                alert(`Ошибка: ${result.message}`);
                window.location.href = `/packs`;
            }
        } catch (error) {
            console.error("Error submitting quiz:", error);
            alert("Произошла ошибка при отправке результатов квиза.");
            window.location.href = `/packs`;
        }
    }

    // Слушатель для кнопки "Следующий вопрос" / "Завершить квиз"
    nextQuestionBtn.addEventListener("click", () => {
        const selectedAnswer = selectedAnswerInput.value // Получаем индекс выбранного ответа
        // Получаем текущий вопрос, чтобы взять его ID
        const currentQuestion = questions[currentQuestionIndex];

        // Проверяем, выбран ли ответ
        if (selectedAnswer === "") {
            // Этого не должно произойти, так как кнопка деактивирована,
            // но на всякий случай оставляем проверку.
            return;
        }

        // Сохраняем ID вопроса и выбранный индекс ответа
        userAnswers.push({
            questionId: currentQuestion.id,
            selectedAnswerIndex: parseInt(selectedAnswer)
        });

        currentQuestionIndex++; // Переходим к следующему вопросу
        renderQuestion(); // Рендерим следующий вопрос
    })

    // Инициализация: рендерим первый вопрос при загрузке страницы
    renderQuestion()
})