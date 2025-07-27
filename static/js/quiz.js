document.addEventListener("DOMContentLoaded", () => {
    const quizDataScript = document.getElementById("quiz-data");
    if (!quizDataScript) {
        return; // Not on the quiz page
    }

    const quizData = JSON.parse(quizDataScript.textContent);
    const questions = quizData.questions;
    const packId = quizData.pack_id;

    let currentQuestionIndex = 0;
    const userAnswers = []; // [{questionId: ID, selectedAnswerIndex: INDEX}, ...]
    let quizStartTime = Date.now(); // Record quiz start time

    const questionTextElement = document.getElementById("question-text");
    const questionImageContainer = document.getElementById("question-image-container"); // New element
    const answersContainer = document.getElementById("answers-container");
    const selectedAnswerInput = document.getElementById("selected-answer-input");
    const nextQuestionBtn = document.getElementById("next-question-btn");
    const finishQuizBtn = document.getElementById("finish-quiz-btn");
    const questionCounter = document.getElementById("question-counter");
    const progressPercentageSpan = document.getElementById("progress-percentage");
    const progressBarFill = document.querySelector(".progress-bar .progress-fill");

    function renderQuestion() {
        if (currentQuestionIndex >= questions.length) {
            showResults();
            return;
        }

        const currentQuestion = questions[currentQuestionIndex];
        questionTextElement.textContent = currentQuestion.question;

        // --- Add logic for displaying the image ---
        questionImageContainer.innerHTML = ""; // Clear previous image
        if (currentQuestion.image_url) {
            const img = document.createElement("img");
            const cleanImageUrl = currentQuestion.image_url.startsWith('/static/') ?
                                  currentQuestion.image_url.substring(7) :
                                  currentQuestion.image_url;

            fetch(`/static_url?filename=${encodeURIComponent(cleanImageUrl)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.url) {
                        img.src = data.url;
                        img.alt = "Question image";
                        img.style.maxWidth = "100%";
                        img.style.height = "auto";
                        img.style.maxHeight = "300px";
                        questionImageContainer.appendChild(img);
                    }
                })
                .catch(error => console.error("Error fetching image URL:", error));
        }
        // --- End logic for displaying the image ---

        answersContainer.innerHTML = "";
        currentQuestion.options.forEach((option, index) => {
            const button = document.createElement("button");
            button.type = "button";
            button.classList.add("answer-btn");
            button.dataset.answerIndex = index;
            button.dataset.questionId = currentQuestion.id;
            button.innerHTML = `<span class="answer-letter">${String.fromCharCode(65 + index)}.</span><span class="answer-text">${option}</span>`;

            button.addEventListener("click", () => {
                answersContainer.querySelectorAll(".answer-btn").forEach(btn => btn.classList.remove("selected"));
                button.classList.add("selected");
                selectedAnswerInput.value = button.dataset.answerIndex;
                nextQuestionBtn.disabled = false;
            });
            answersContainer.appendChild(button);
        });

        selectedAnswerInput.value = "";
        nextQuestionBtn.disabled = true;

        updateProgress();

        if (currentQuestionIndex === questions.length - 1) {
            nextQuestionBtn.textContent = "Finish Quiz";
        } else {
            nextQuestionBtn.textContent = "Next Question";
        }
    }

    function updateProgress() {
        const total = questions.length;
        const current = currentQuestionIndex;
        const percentage = total > 0 ? (current / total) * 100 : 0;

        questionCounter.textContent = `Question ${current + 1} of ${total}`;
        progressPercentageSpan.textContent = `Progress: ${percentage.toFixed(0)}%`;
        progressBarFill.style.width = `${percentage}%`;
    }

    function showResults() {
        questionTextElement.textContent = "Quiz completed! Saving results...";
        questionImageContainer.innerHTML = "";
        answersContainer.innerHTML = "";
        nextQuestionBtn.style.display = "none";
        finishQuizBtn.style.display = "none";
        selectedAnswerInput.value = "";

        questionCounter.textContent = "Quiz completed!";
        progressPercentageSpan.textContent = "Progress: 100%";
        progressBarFill.style.width = "100%";

        submitQuizResults();
    }

    async function submitQuizResults() {
        const quizEndTime = Date.now();
        const totalTimeTaken = (quizEndTime - quizStartTime) / 1000;

        try {
            // NOTE: url_for cannot be used directly in external JS files.
            // You will need to define a global variable in your HTML template
            // or pass the URL differently. For now, I'll use a placeholder.
            // A common approach is to set `const submitUrl = "{{ url_for('quiz.submit_quiz') }}";`
            // in a small inline script tag BEFORE this external script.
            const submitUrl = quizData.submit_url; // Assuming you'll add this to quizData from Flask
            const packsUrl = quizData.packs_url; // Assuming you'll add this to quizData from Flask

            const response = await fetch(submitUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    pack_id: packId,
                    answers: userAnswers,
                    totalTimeTaken: totalTimeTaken
                }),
            });

            const result = await response.json();

            if (result.success) {
                window.location.href = result.redirect_url;
            } else {
                alert(`Error: ${result.message}`);
                window.location.href = packsUrl;
            }
        } catch (error) {
            console.error("Error submitting quiz:", error);
            alert("An error occurred while submitting quiz results.");
            window.location.href = packsUrl;
        }
    }

    nextQuestionBtn.addEventListener("click", () => {
        const selectedAnswer = selectedAnswerInput.value;
        const currentQuestion = questions[currentQuestionIndex];

        if (selectedAnswer === "") {
            return;
        }

        userAnswers.push({
            questionId: currentQuestion.id,
            selectedAnswerIndex: parseInt(selectedAnswer)
        });

        currentQuestionIndex++;
        renderQuestion();
    });

    renderQuestion();
});