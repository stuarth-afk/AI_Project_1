import os
import openai
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
import yaml
import os
import secrets


app = Flask(__name__)
app.secret_key = secrets.token_bytes(16) # <- random key , only used for cookie detection

openai.api_key = os.getenv("OPENAI_API_KEY")

# Load YAML settings file
db_config = yaml.load(open('db.yaml'))
#db_config = yaml.load(open('db.yaml'), Loader=yaml.FullLoader)

app.config['MYSQL_HOST'] = db_config['mysql_host']
app.config['MYSQL_USER'] = db_config['mysql_user']
app.config['MYSQL_PASSWORD'] = db_config['mysql_password']
app.config['MYSQL_DB'] = db_config['mysql_db']

mysql = MySQL(app)

# Additional Bot model fields
bot_fields = ['name', 'ai_model', 'system_prompt', 'db_read_script', 'db_write_script', 'reference_data', 'output_destination']


class Bot:
    def __init__(self, id, name, ai_model, system_prompt, db_read_script, db_write_script, reference_data, output_destination, number):
        self.id = id
        self.name = name
        self.ai_model = ai_model
        self.system_prompt = system_prompt
        self.db_read_script = db_read_script
        self.db_write_script = db_write_script
        self.reference_data = reference_data
        self.output_destination = output_destination
        self.number = number

    @staticmethod
    def get_bot_by_number(number):
        print(f"Getting bot with number: {number}")
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Bot WHERE number = %s", [number])
        result = cur.fetchone()
        print(f"SQL Query Result: {result}")

        if result:
            bot = Bot(*result)
            #print(f"Bot created: {bot.__dict__}")
            #print(f"Bot created with id: {bot.id}, name: {bot.name}, number: {bot.number}, role: {bot.role}, input_source: {bot.input_source}, output: {bot.output}")
            #print(f"Bot created with id: {id}, name: {name}, number: {number}, role: {role}, input_source: {input_source}, output: {output}")
            return bot

        return None



@app.route('/')
def index():
    return render_template('index.html')

####################################
####           Bot x            ####
####################################
@app.route('/submit_config', methods=['POST'])
def submit_config():
    # Get form data
    data = {field: request.form.get(field) for field in bot_fields}

    # Create MySQL cursor
    cur = mysql.connection.cursor()

    # Prepare SQL query
    placeholders = ', '.join(['%s'] * len(data))
    columns = ', '.join(data.keys())
    sql = "INSERT INTO Bot (%s) VALUES (%s)" % (columns, placeholders)

    # Execute SQL query
    cur.execute(sql, list(data.values()))

    # Commit the transaction
    mysql.connection.commit()

    # Close the cursor
    cur.close()

    # Flash a success message
    flash("Configuration submitted successfully!", 'success')

    bot_number = data.get('number', None)
    if bot_number is None:
        # handle error
        flash("Number is not provided in the form", 'error')
        return redirect(url_for('index'))



    # Redirect to the page number
    return redirect(url_for('page', number=bot_number))
    
@app.route('/bot/<int:number>', methods=['GET', 'POST'])
def page(number):
    bot = Bot.get_bot_by_number(number)
    
    # if bot is None, return an error page
    if not bot:
        return render_template('error.html', message="Bot not found"), 404

    user_text = ""
    response = ""
    
    
    if request.method == 'POST':
        user_text = request.form.get('text')
        # Add any processing of the user text you want here
        response = openai.Completion.create(
            model=bot.ai_model,       #"text-davinci-003",
            prompt=generate_prompt(user_text),
            temperature=0.6,
            max_tokens=1000,
        )
        response=response.choices[0].text.strip()
    return render_template('page_1.html', bot=bot, user_text=user_text, response=response)
    
def generate_prompt(user_text):
    return bot.system_prompt

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
