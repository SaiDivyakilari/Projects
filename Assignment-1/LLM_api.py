from http import client

from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()




def generating_prompt(user_data : dict) -> str:
    prompt = f"""
            You are a professional personal trainer.

            Using the user's information and workout preferences below,
            create a highly personalized weekly workout plan.

            Do not create a generic workout plan. Every recommendation should
            take into account the user's goal, experience level, workout
            location, available equipment, preferred workout duration,
            preferred workout days, activity level, and physical limitations.

            USER INFORMATION

            Name: {user_data["name"]}
            Age: {user_data["age"]}
            Gender: {user_data["gender"]}
            Height: {user_data["height"]} feet and inches
            Weight: {user_data["weight"]} kg

            WORKOUT PREFERENCES

            Fitness goal: {user_data["fitness_goal"]}
            Custom fitness goal: {user_data["custom_goal"]}
            Experience level: {user_data["experience_level"]}
            Number of workout days per week: {user_data["days"]}
            Workout location: {user_data["location"]}
            Available equipment: {user_data["equipment_access"]}
            Current activity level: {user_data["activity_level"]}
            Preferred workout duration: {user_data["workout_duration"]}
            Preferred workout style: {user_data["workout_style"]}
            Preferred workout days: {user_data["preferred_days"]}
            Injuries or physical limitations: {user_data["limitations"]}
            Additional preferences: {user_data["additional_preferences"]}

            INSTRUCTIONS

            Create a weekly workout plan that:

            1. Uses only exercises appropriate for the user's experience level.
            2. Uses equipment actually available to the user.
            3. Respects the user's preferred workout location.
            4. Fits within the user's preferred workout duration.
            5. Schedules workouts on the user's preferred workout days.
            6. Supports the user's primary fitness goal.
            7. Avoids or modifies exercises that may conflict with injuries
            or physical limitations.
            8. Includes appropriate rest and recovery.
            9. Provides realistic sets, repetitions, and rest periods.
            10. Includes warm-up and cool-down recommendations.
            11. Includes progression guidance explaining how the user can
                gradually improve over time.

            For every workout day include:

            - day
            - workout focus
            - estimated duration
            - warm-up
            - exercises
            - sets
            - reps
            - rest time
            - cool-down
        Please provide the workout plan in a clear and structured text format.
        Do not return Json and avoid preamble text.

"""
    
    return prompt
from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()


def generating_prompt(user_data: dict) -> str:

    prompt = f"""
    You are a professional personal trainer.

    Using the user's information and workout preferences below,
    create a highly personalized weekly workout plan.

    Do not create a generic workout plan. Every recommendation should
    take into account the user's goal, experience level, workout
    location, available equipment, preferred workout duration,
    preferred workout days, activity level, and physical limitations.

    USER INFORMATION

    Name: {user_data["name"]}
    Age: {user_data["age"]}
    Gender: {user_data["gender"]}
    Height: {user_data["height"]} feet and inches
    Weight: {user_data["weight"]} kg

    WORKOUT PREFERENCES

    Fitness goal: {user_data["fitness_goal"]}
    Custom fitness goal: {user_data["custom_goal"]}
    Experience level: {user_data["experience_level"]}
    Number of workout days per week: {user_data["days"]}
    Workout location: {user_data["location"]}
    Available equipment: {user_data["equipment_access"]}
    Current activity level: {user_data["activity_level"]}
    Preferred workout duration: {user_data["workout_duration"]}
    Preferred workout style: {user_data["workout_style"]}
    Preferred workout days: {user_data["preferred_days"]}
    Injuries or physical limitations: {user_data["limitations"]}
    Additional preferences: {user_data["additional_preferences"]}

    INSTRUCTIONS

    Create a weekly workout plan that:

    1. Uses only exercises appropriate for the user's experience level.
    2. Uses equipment actually available to the user.
    3. Respects the user's preferred workout location.
    4. Fits within the user's preferred workout duration.
    5. Schedules workouts on the user's preferred workout days.
    6. Supports the user's primary fitness goal.
    7. Avoids or modifies exercises that may conflict with injuries
       or physical limitations.
    8. Includes appropriate rest and recovery.
    9. Provides realistic sets, repetitions, and rest periods.
    10. Includes warm-up and cool-down recommendations.
    11. Includes progression guidance explaining how the user can
        gradually improve over time.
    12. Do not make medical diagnoses or medical claims.
    13. If an injury or physical limitation is provided, include a
        short safety disclaimer.

    For every workout day include:

    - Day
    - Workout focus
    - Estimated duration
    - Warm-up
    - Exercises
    - Sets
    - Reps
    - Rest time
    - Cool-down

    Please provide the workout plan in a clear and structured text format.
    Do not return JSON and avoid preamble text.
    """

    return prompt


def generate_workout_plan(user_data: dict) -> str | None:

    try:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY is missing.")

        client = Groq(api_key=api_key)

        prompt = generating_prompt(user_data)

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            top_p=1,
        )

        workout_plan = response.choices[0].message.content

        if not workout_plan or not workout_plan.strip():
            raise ValueError("The model returned an empty response.")

        return workout_plan

    except Exception as e:
        print(f"Error generating workout plan: {e}")
        return None
    

