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
    def __init__(self, id, name, number, role, input_source, output):
        print(f"Bot created with id: {id}, name: {name}, number: {number}, role: {role}, input_source: {input_source}, output: {output}")
        self.id = id
        self.name = name
        self.number = number
        self.role = role
        self.input_source = input_source
        self.output = output

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
            print(f"Bot created with id: {id}, name: {name}, number: {number}, role: {role}, input_source: {input_source}, output: {output}")
            return bot

        return None



@app.route('/')
def index():
    return render_template('index.html')

####################################
####           Bot 1            ####
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

    # Redirect to the page_1
    return redirect(url_for('page_1'))
    
@app.route('/page_1', methods=['GET', 'POST'])
def page_1():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Bot ORDER BY id DESC LIMIT 1")
    bot = cur.fetchone()
    cur.close()

    #bot = Bot(*bot_data) if bot_data else None
    if not bot:
        bot = Bot.get_bot_by_number("1")
    print(f"Bot at 104 with id: {bot.id}, name: {bot.name}, number: {bot.number}, role: {bot.role}, input_source: {bot.input_source}, output: {bot.output}")
    #print(f"Bot at line 103: {bot.__dict__}")
    
    user_text = ""
    response = ""
    
    print(f"Bot at 110 with id: {bot.id}, name: {bot.name}, number: {bot.number}, role: {bot.role}, input_source: {bot.input_source}, output: {bot.output}")
    #print(f"Bot at line 108: {bot.__dict__}")
    
    if request.method == 'POST':
        user_text = request.form.get('text')
        # Add any processing of the user text you want here
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=generate_prompt_1(user_text),
            temperature=0.6,
            max_tokens=1000,
        )
        response=response.choices[0].text.strip()
    return render_template('page_1.html', bot=bot, user_text=user_text, response=response)
    
def generate_prompt_1(user_text):
    return """Identify the Neurolinguistic Programming meta program in the message.

User Text: Hi, I'm thinking about Global Macro topics today.
Response: Big Picture Meta Program
User Text: I enjoy considering all possible outcomes before I make a decision.
Response: Options Meta Program
User Text: The government is crazy to control the wider economy. 
Response: Big Picture Meta Program
User Text: I'm concerned with the small detail that affects me, my mortgage will cost more today. Your message is indicative of Small
Response: Details Meta Program

User Text: {}
Response:""".format(
        user_text.capitalize()
    )

####################################
####           Bot 2            ####
####################################
@app.route('/page_2', methods=['GET', 'POST'])
def page_2():
    bot_name = "User Response Bot"
    bot_number = "2"
    bot_role = "Reply to user message with NLP context and memories from database"
    bot_input_source = "user text input"
    bot_output = "display text on web page"
    user_text = ""
    response = ""
    if request.method == 'POST':
        user_text = request.form.get('text')
        # Add any processing of the user text you want here
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=generate_prompt_2(user_text),
            temperature=0.6,
            max_tokens=500,
        )
        user_text = ""  # Clear user_text after form submission
        response=response.choices[0].text
    return render_template('page_2.html', user_text=user_text, response=response)

def generate_prompt_2(user_text):
    return """Reply to message in two parts. First part is a conversational response to the user that considers the NLP meta program they are using. The next part will describe why the response is using that meta program.  

User Text: Hi, I'm thinking about Global Macro topics today.
NLP Meta Program: Big Picture Meta Program
Response: Let's discuss the overall view. (This is a Big Picture Meta Program reply because it keeps the focus on the big picture for the user)
User Text: I enjoy considering all possible outcomes before I make a decision.
NLP Meta Program: Options Meta Program
Response: Let's consider each one. Tell me the first one. (This is a Options Meta Program reply because it keeps the focus on the options for the user)
User Text: The government is crazy to control the wider economy. 
NLP Meta Program: Big Picture Meta Program
Response: Yes,what do you think is the high level impact of this(This is a Big Picture Meta Program reply because it keeps the focus on the big picture for the user)
User Text: I'm concerned with the small detail that affects me, my mortgage will cost more today.
NLP Meta Program: Details Meta Program
Response: That sounds challenging, how much more will this cost then last month? (This is a Details Meta Program reply because it drills down to the details for the user) 

User Text: {}
Response:""".format(
        user_text.capitalize()
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
