# QuizMaster - Quiz Game Website

A web application for conducting interactive quizzes with a full-fledged registration system, detailed statistics tracking, and unique achievements.

-----

## Features

  * 🎯 **Diverse Quiz Packs with Difficulty Levels**
      * A wide selection of topics (e.g., Programming, Movies, History).
      * Each quiz pack is categorized by its difficulty level: **Easy, Medium, Hard, Expert**.
      * Includes an **estimated completion time** and **customizable colors** for visual distinction.
  * 👤 **User System**
      * A complete authentication system: registration, secure login, and personalized profiles.
  * 📊 **Detailed Statistics**
      * Comprehensive tracking of each user's progress, including the number of correct answers and total games finished.
  * 🏆 **Achievement System**
      * Motivating rewards and badges for various in-game successes.
  * 📱 **Responsive Design**
      * A fully adaptive interface for comfortable use on any device.

-----

## Installation and Setup

To run the application on your local machine, follow these steps:

1.  **Clone the repository**:

    ```bash
    git clone <YOUR_REPOSITORY_URL>
    cd quizmaster
    ```

2.  **Install the necessary Python dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

3.  **Initialize the database and run migrations**:

      * Ensure Alembic is configured (if used).
      * Run migrations to create tables and fields, including the new difficulty, time, and color fields for `QuizPack`:
        ```bash
        flask db migrate -m "Add difficulty, time, and color to QuizPack"
        flask db upgrade
        ```
      * If you're using `init_database.py` to create initial data, ensure it's updated to populate these new fields.

4.  **Run the Flask application**:

    ```bash
    python app.py
    ```

5.  **Open your web browser** and navigate to:
    [http://localhost:5000](https://www.google.com/search?q=http://localhost:5000)

-----

## Admin Panel

QuizMaster includes a powerful admin panel for convenient content management.

### How to Access the Admin Panel:

1.  Register a new user or log in with an existing account.
2.  In the current implementation, **any registered user has access to the admin panel**. In a real-world project, a robust role-based access control system (e.g., checking `current_user.is_admin`) should be implemented here.
3.  Navigate to the URL: [http://localhost:5000/admin](https://www.google.com/search?q=http://localhost:5000/admin)

### Adding and Managing Packs:

From the admin panel, you can:

  * **Create new quiz packs**: Specify the title, description, **color**, **difficulty level**, and **estimated completion time**.
  * **Edit existing quiz packs**: Modify their data.
  * **Add, edit, and delete questions** for each quiz pack.
  * **Delete entire quiz packs**, which also removes all associated questions and user statistics for that pack.

-----

## Technologies

  * **Backend**: **Python Flask** with **SQLAlchemy**.
  * **Frontend**: **HTML5**, **CSS3**, and **JavaScript**.
  * **Database**: **SQLite** with **Alembic** for migrations.
  * **Styling**: Fully **custom CSS** with gradients and animations.
  * **Icons**: **Font Awesome**.
  * **Templating**: **Jinja2**.

-----

## Functionality

### Application Pages:

  * **Home** - An appealing landing page.
  * **Register/Login** - A secure authentication system.
  * **Quiz Packs** - A list of all available packs with information on **difficulty, color, and time**.
  * **Quiz** - Interactive mode for answering questions.
  * **Profile** - A personalized user page with statistics and achievements.
  * **Admin Panel** - A section for managing quiz packs and questions, including their **difficulty, time, and color**.

### Additional Features:

  * **Automatic Result Saving**.
  * **Progress and Achievement System**.
  * **Responsive Design for Mobile Devices**.
  * **Flash Messages for Notifications**.
  * **Secure Password Storage (Hashing)**.
  * **Reliable Display of Question and Answer Content**.
  * **Convenient Content Management** via the Admin Panel.

-----

## Future Plans

We plan to expand QuizMaster's functionality by adding the following features:

  * **Enhanced Pack Management**: Ability to reorder quiz packs.
  * **User Personalization**: Adding user avatar upload functionality.
  * **Improved Statistics**: Collecting aggregated statistics across thematic groups of packs.
  * **Increased Gameplay Complexity**:
      * Implementing a "lives" system (e.g., 3 lives).
      * Expanding difficulty level mechanics with experience point accumulation for completion.
      * Setting a "passing score" (e.g., 80%) for successful quiz completion.
  * **New Game Modes**: Creating a "Random Quiz" mode.
  * **Continuous Improvement**: Regular bug fixing and overall website polishing.

-----
