import streamlit as st
from LLM_api import generate_workout_plan

st.title("Workout Plan Generator")

st.subheader("Personal Information")
name = st.text_input("Enter your name *")
age = st.number_input("Enter your age *",min_value = 12,value=None,key="age")
gender = st.selectbox("Select your gender",
                      options = ["Male", "Female", "Other"],
                      index =None, 
                      placeholder = "Select your gender")
height = st.number_input("Enter your height in cm *",
                         min_value = 0,
                         value = None,
                         key="height")
weight = st.number_input("Enter your weight in kg *",
                         min_value = 0,
                         value = None,
                         key="weight")

if name is None or age is None or height is None or weight is None:
    st.error("Please fill in all fields")
else:
    st.success("Thank you for providing your information!")


st.subheader("Workout Preferences")


st.write(f"Hello, {name}! Are you ready to get fit?")
    

st.write(
    "Please fill in all the required fields to generate your "
    "personalized workout plan."
)

fitness_goal = st.selectbox("Select your fitness goal *",
                            options = ["Build Muscle","Lose Fat","Lose weight","General fitness","Improve endurance","Other"],
                            index = None, 
                            placeholder = "Select your fitness goal")
custom_goal = None
if fitness_goal == "Other":
    custom_goal = st.text_input("Enter your custom fitness goal",key="custom_goal")



experience_level = st.selectbox("Select your experience level *",
                                options = ["Beginner","Intermediate","Advanced"],
                                index = None, 
                                placeholder = "Select your experience level",
                                key="experience_level")
days = st.slider("Select the number of days you want to work out *",
                 min_value = 1,
                 max_value = 7,
                 value = 3)
location = st.radio("Where do you wanna workout ? *" ,
                    options = ["Gym","Home","Outdoor"],
                    index = None)
equipment_access = st.multiselect("Select the equipment you have access to *",
                                  options = ["Dumbbells","Barbell","Resistance bands","Pull-up bar","Home dumbbells","Full gym","No equipment"])

activity_level = st.selectbox("Current activity level *",
                              options=["Sedentary","Lightly Active","Moderately Active","Very Active"],
                                index=None,
                                placeholder="Select your activity level"
)

workout_duration = st.selectbox("Preferred workout duration *",
    options=[
        "30 minutes",
        "45 minutes",
        "60 minutes",
        "90 minutes"
    ],
    index=None,
    placeholder="Select workout duration"
)

workout_style = st.multiselect(
    "Preferred workout style",
    [
        "Strength Training",
        "Cardio",
        "HIIT",
        "Functional Training",
        "Yoga / Mobility"
    ]
)
preferred_days = st.multiselect(
    "Which days do you prefer to work out?",
    [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]
)

if days != len(preferred_days):
    st.warning("The number of preferred workout days does not match the number of days selected.")

limitations = st.text_area(
    "Do you have any injuries, physical limitations, or exercises you want to avoid?",
    key="limitations"
)

additional_preferences = st.text_area("Enter any additional preferences or notes.", key="additional_preferences")
consent = st.checkbox("I understand that the information entered will be used to generate my workout plan")
user_data = {}
if st.button("Generate Workout Plan"):
    if not fitness_goal or not experience_level or not days or not location or not equipment_access or not consent or not workout_duration or not preferred_days or not activity_level:
        st.error("Please fill in all the required fields")
    else:

        user_data = {
            "name": name,
            "age": age,
            "gender": gender,
            "height": height,
            "weight": weight,
            "fitness_goal": fitness_goal,
            "custom_goal" : custom_goal,
            "experience_level": experience_level,
            "days": days,
            "location": location,
            "equipment_access": equipment_access,
            "activity_level": activity_level,
            "workout_duration": workout_duration,
            "workout_style": workout_style,
            "preferred_days": preferred_days,
            "limitations": limitations,
            "additional_preferences": additional_preferences

        }
        st.success("Your workout plan is being generated!")
        workout_plan = generate_workout_plan(user_data)
        if workout_plan:
            st.info("Your personalized workout plan is below:")
            st.markdown(workout_plan)
        else :
            st.error("Failed to generate workout plan.Please try again")


