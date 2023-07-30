import os
import openai
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
import yaml
import os
import secrets
import time

print("Starting the application...")
app = Flask(__name__)
print("Initializing Flask application...")

app.secret_key = secrets.token_bytes(16) # <- random key , only used for cookie detection

openai.api_key = os.getenv("OPENAI_API_KEY")

# Load YAML settings file
#db_config = yaml.load(open('db.yaml'))
db_config = yaml.load(open('db.yaml'), Loader=yaml.FullLoader)

# set up MySQL connection
app.config['MYSQL_HOST'] = db_config['mysql_host']
app.config['MYSQL_USER'] = db_config['mysql_user']
app.config['MYSQL_PASSWORD'] = db_config['mysql_password']
app.config['MYSQL_DB'] = db_config['mysql_db']
mysql = MySQL(app)
print("Initializing MySQL connection...")
with app.app_context():
    cur = mysql.connection.cursor()
    print(cur)
time.sleep(5)  # add a 5 seconds delay

#*************************   
#**  Define Functions   **
#*************************

# create tables
print("Creating tables...")
def create_tables_if_not_exist():
    #mysql_local = MySQL(app)
    with app.app_context():
        # Create MySQL cursor
        cur = mysql.connection.cursor()
        print(cur)

        # create input_messages table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS input_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bot_id INT,
                message_1 TEXT,
                message_2 TEXT,
                message_3 TEXT,
                message_4 TEXT,
                message_5 TEXT,
                message_6 TEXT,
                message_7 TEXT,
                message_8 TEXT,
                message_9 TEXT,
                message_10 TEXT,
                message_11 TEXT,
                message_12 TEXT,
                used BOOL DEFAULT 0,
                created_at TIMESTAMP,
                source VARCHAR(255)
            )
        ''')

        # create output_messages table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS output_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bot_id INT,
                message TEXT,
                created_at TIMESTAMP,
                destination VARCHAR(255),
                success BOOL DEFAULT 0
            )
        ''')

        # create memory_info table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS memory_info (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bot_id INT,
                info_1 TEXT,
                info_2 TEXT,
                info_3 TEXT,
                info_4 TEXT,
                info_5 TEXT,
                info_6 TEXT,
                info_7 TEXT,
                info_8 TEXT,
                info_9 TEXT,
                info_10 TEXT
            )
        ''')

        mysql.connection.commit()

# Function to insert data to input_messages table
def insert_into_input_messages(bot_id, messages, source):
    with app.app_context():
        cur = mysql.connection.cursor()
        # Prepare SQL query
        sql = '''
            INSERT INTO input_messages 
            (bot_id, message_1, message_2, message_3, message_4, message_5, message_6, message_7, message_8, message_9, message_10, message_11, message_12, created_at, source)
            VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        '''
        params = [bot_id] + messages + [source]
        cur.execute(sql, params)
        mysql.connection.commit()

# Function to insert data to output_messages table
def insert_into_output_messages(bot_id, message, destination, success):
    with app.app_context():
        cur = mysql.connection.cursor()
        sql = '''
            INSERT INTO output_messages 
            (bot_id, message, created_at, destination, success)
            VALUES 
            (%s, %s, NOW(), %s, %s)
        '''
        params = [bot_id, message, destination, success]
        cur.execute(sql, params)
        mysql.connection.commit()

# Function to insert data to memory_info table
def insert_into_memory_info(bot_id, infos):
    with app.app_context():
        cur = mysql.connection.cursor()
        sql = '''
            INSERT INTO memory_info 
            (bot_id, info_1, info_2, info_3, info_4, info_5, info_6, info_7, info_8, info_9, info_10)
            VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        params = [bot_id] + infos
        cur.execute(sql, params)
        mysql.connection.commit()

# Function to read data from input_messages table
def read_from_input_messages(bot_id):
    with app.app_context():
        cur = mysql.connection.cursor()
        sql = "SELECT * FROM input_messages WHERE bot_id = %s AND used = 0"
        cur.execute(sql, [bot_id])
        result = cur.fetchall()
        return result

# Function to read data from output_messages table
def read_from_output_messages(bot_id):
    with app.app_context():
        cur = mysql.connection.cursor()
        sql = "SELECT * FROM output_messages WHERE bot_id = %s AND success = 1"
        cur.execute(sql, [bot_id])
        result = cur.fetchall()
        return result

# Function to read data from memory_info table
def read_from_memory_info(bot_id):
    with app.app_context():
        cur = mysql.connection.cursor()
        sql = "SELECT * FROM memory_info WHERE bot_id = %s"
        cur.execute(sql, [bot_id])
        result = cur.fetchall()
        return result

def update_input_messages(bot_id, user_text):
    with app.app_context():
        # Create MySQL cursor
        cur = mysql.connection.cursor()

        # Find the next available slot in the input_messages table
        cur.execute("SELECT * FROM input_messages WHERE bot_id = %s AND used = 0 ORDER BY id", (bot_id,))
        result = cur.fetchone()
        if result is not None:
            # We have a row to update
            row_id = result[0]
            # Find the next available message slot
            for i in range(2, 14):  # column indices for message_1 through message_12
                if result[i] is None:
                    # We've found a slot, update it with the message
                    cur.execute(f"UPDATE input_messages SET message_{i-1} = %s WHERE id = %s", (user_text, row_id))
                    break
        else:
            # We need to insert a new row
            cur.execute("INSERT INTO input_messages (bot_id, message_1) VALUES (%s, %s)", (bot_id, user_text))

        mysql.connection.commit()

def insert_output_message(bot_id, message, destination):
    with app.app_context():
        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO output_messages (bot_id, message, created_at, destination) VALUES (%s, %s, NOW(), %s)", 
                    (bot_id, message, destination))

        mysql.connection.commit()

def generate_prompt(bot, user_text):
    #return bot.system_prompt
    return f"\n\"role\" : \"system\" , \"content\" : \"{bot.system_prompt}\" , \n\"role\" : \"user\" , \"content\" : \"{user_text}\" , \n"




#***********************
#**  Define Classes   **
#***********************
# Global List of Bot model fields for Bot Class
bot_fields = ['name', 'ai_model', 'system_prompt', 'db_read_script', 'db_write_script', 'reference_data', 'output_destination','number']

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




#**********************************
#**  First Scan Function Calls   **
#**********************************
create_tables_if_not_exist()



#****************************
#**  Define Flask Routes   **
#****************************
# register routes
print("Registering routes...")

@app.route('/')
def index():
    return render_template('index.html')

# Configure Bot - Flask Route
@app.route('/submit_config', methods=['POST'])
def submit_config():
    # print form data for debugging
    print(f"Form data: {request.form}")
    
    # Get form data
    data = {field: request.form.get(field) for field in bot_fields}
    
    print("Data to be updated: ", data) # Debug line

    # Check if the number is provided from the form
    bot_number = data.get('number', None)
    if bot_number is None:
        # handle error
        flash("Number is not provided in the form", 'error')
        return redirect(url_for('index'))

    # Print data for debugging
    print(f"Data to be inserted/updated: {data}")
    
    # Create MySQL cursor
    cur = mysql.connection.cursor()

    # Prepare SQL query
    placeholders = ', '.join(['%s'] * len(data))
    update_stmt = ', '.join([f'{col} = %s' for col in data.keys()])
    sql = f"UPDATE Bot SET {update_stmt} WHERE number = %s"
    params = list(data.values()) + [bot_number]

    print("SQL query: ", sql) # Debug line
    print("Params: ", params) # Debug line
    
    # Execute SQL query
    try:
        cur.execute(sql, params)
        # Commit the transaction
        mysql.connection.commit()
    except Exception as e:
        print("Database Error:", e)
        flash("Failed to update configuration due to database error.", 'error')
        return redirect(url_for('page', number=bot_number))

    # Close the cursor
    cur.close()

    # Flash a success message
    flash("Configuration submitted successfully!", 'success')

    # Redirect to the page number
    return redirect(url_for('page', number=bot_number))
    
# Define User Message Action - Flask Route    
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
            prompt=generate_prompt(bot, user_text),
            temperature=0.6,
            max_tokens=1000,
        )
        response=response.choices[0].text.strip()
        print(f"Bot model: {bot.ai_model}")
        print(f"Bot prompt: {bot.system_prompt}")

        # Update the output_messages table with the combined response
        combined_message = "\n\"role\" : \"user\" , \"content\" : \"" + user_text + "\"\n" + response + " ,\n"
        insert_output_message(bot.id, combined_message, bot.output_destination)

        # Update the input_messages table for the destination bot
        destination_bot_id = int(bot.output_destination)  # This is the bot id of the destination
        update_input_messages(destination_bot_id, combined_message)

    return render_template('page_1.html', bot=bot, user_text=user_text, response=response)
    #return redirect(url_for('page', number=bot.number))


print("Running the application...")
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
