# QuizMaster - Quiz Game Website

A web application for conducting interactive quizzes with a full-fledged registration system, statistics tracking, and unique achievements.

## Features

-   🎯 **Diverse Quizzes with Difficulty Levels** - A selection of topics (Programming, Movies, etc.), with each quiz pack categorized by difficulty levels: **Easy, Medium, Hard, Expert**.
-   👤 **User System** - A complete authentication system: new user registration, secure login, and personalized profiles.
-   📊 **Detailed Statistics** - Comprehensive tracking of each user's progress across completed quiz packs, including the number of correct answers and games finished.
-   🏆 **Achievement System** - Motivating rewards and badges for various in-game successes and milestones.
-   📱 **Responsive Design** - A fully adaptive interface ensuring comfortable use on any device, from desktops to mobile phones.

## Installation and Setup

To run the application on your local machine, follow these steps:

1.  Clone the repository (if you haven't already):
    ```bash
    git clone <YOUR_REPOSITORY_URL>
    cd quiz-game
    ```

2.  Install the necessary Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Initialize the database (if this is the first run or you want to reset data):
    ```bash
    # You might need to run the command from the scripts/ folder or specify the full path
    # python scripts/init_database.py
    # Or via Alembic, if used for migrations: flask db upgrade
    ```
    *Note: Ensure your SQLite database is created and initialized according to your scripts.*

4.  Run the Flask application:
    ```bash
    python app.py
    ```

5.  Open your web browser and navigate to:
    [http://localhost:5000](http://localhost:5000)

## Technologies

-   **Backend**: Python Flask, a powerful and flexible micro-framework for web development, using SQLAlchemy for database interaction.
-   **Frontend**: Modern web technologies - HTML5 for structure, CSS3 for styling, and JavaScript for interactivity.
-   **Database**: SQLite, a lightweight file-based database, ideal for small to medium applications, with a configured migration system (if Alembic is used).
-   **Styling**: Fully custom CSS utilizing gradients, animations, and other modern techniques to create a unique user interface.
-   **Icons**: Font Awesome for a wide range of vector icons.
-   **Templating**: Jinja2 - a powerful and secure templating engine for rendering HTML pages.

## Functionality

### Application Pages:
-   **Home** - An appealing landing page introducing users to the application.
-   **Register/Login** - A secure (hashed) and convenient user authentication system.
-   **Quiz Packs** - Displays a list of all available quiz packs, each indicating its topic and difficulty level.
-   **Quiz** - An interactive mode for answering questions, showing progress and answer options.
-   **Profile** - A personalized user page with statistics, game history, and achievements.
-   **Admin Panel** - A specialized section for administrators to add, modify, and delete quiz packs and questions, as well as manage their difficulty levels.

### Features:
-   **Automatic Result Saving** - User progress is saved automatically.
-   **Progress and Achievement System** - Tracking user success and rewarding completed tasks.
-   **Responsive Design for Mobile Devices** - Optimized display and interaction on smartphones and tablets.
-   **Flash Messages for Notifications** - Dynamic notifications for the user (success, error, information).
-   **Secure Password Storage (Hashing)** - User passwords are stored in hashed form for maximum security.
-   **Reliable Display of Question and Answer Content** - Built-in handling and escaping of special HTML characters (`&lt;`, `&gt;`, etc.) for correct rendering of code, HTML tags, and other symbols in questions and answer options.
-   **Convenient Content Management** - The Admin Panel allows easy updating of quiz pack data, including their difficulty levels, ensuring accuracy and correct display.