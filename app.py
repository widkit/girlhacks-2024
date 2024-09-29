from flask import Flask, jsonify, request, render_template
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import json
import google.generativeai as genai
from bson import json_util  # For MongoDB JSON serialization

# MongoDB connection
uri = "mongodb+srv://vmj:RuEIzEBBBpqoWj13@cluster0.eulfz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0&tls=true"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['ai_recipe_generator']
recipes_collection = db['recipes']

genai.configure(api_key="AIzaSyBqgBuWyNOy9qrEABYmgK1aJBR2FJ8CRSw")

# Create the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Fetch saved recipes from MongoDB
recipes = list(recipes_collection.find({}))

# Print recipes in a readable format
for recipe in recipes:
    print("Recipe ID:", recipe.get("_id"))
    print("Title:", recipe.get("title", "N/A"))
    print("Description:", recipe.get("description", "N/A"))
    print("Ingredients:", ", ".join(recipe.get("ingredients", [])))
    print("-" * 40)  # Separator between recipes

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

from bson import ObjectId  # Import this to handle ObjectId conversion

@app.route('/run-script', methods=['POST'])
def run_script():
    user_input = request.json.get('ingredients', '')  # Get ingredients from the request

    response = model.generate_content([
        "you are a program that will provide the user with recipes and stuff about kitchen in general. you will take user input and suggest them recipes from the ingredients they have provided. you will not provide any response or help or recipes on off topic conversations outside of kitchen. you will only respond as {invalid} and nothing else. if user is looking for suggestions, you will provide 3 recipe suggestions. each one has to have a title, a description and ingredients. but if they are specifically looking for one recipe, you will only provide one. also, provide the allergens and calories.",
        "output: ",
        user_input
    ])

    text_content = response._result.candidates[0].content.parts[0].text
    recipe_data = json.loads(text_content)

    # Save the recipe to MongoDB and capture the insert result

    insert_result = recipes_collection.insert_one(recipe_data)

    # Convert ObjectId to a string and include it in the response
    recipe_data['_id'] = str(insert_result.inserted_id)

    # Prepare a response message
    return jsonify({
        "message": "Recipe generated and saved successfully!",
        "data": recipe_data,
        "ingredients": user_input.split(',')  # Return the ingredients as a list
    })

@app.route('/save-recipe', methods=['POST'])
def save_recipe():
    data = request.json
    recipe_data = {
        "title": data.get('title'),
        "description": data.get('description'),
        "ingredients": data.get('ingredients')
    }

    # Insert the recipe into MongoDB
    insert_result = recipes_collection.insert_one(recipe_data)

    return jsonify({
        "message": "Recipe saved successfully!",
        "recipe_id": str(insert_result.inserted_id)
    })

@app.route('/show-saved-recipes', methods=['GET'])
def show_saved_recipes():
    # Fetch all saved recipes from MongoDB
    recipes = list(recipes_collection.find({}))
    
    # Convert MongoDB ObjectId to string and format data for JSON response
    for recipe in recipes:
        recipe['_id'] = str(recipe['_id'])
    
    return jsonify(recipes)

if __name__ == '__main__':
    app.run(debug=True)