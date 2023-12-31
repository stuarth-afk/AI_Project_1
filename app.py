import os
import openai
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
import yaml
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
#time.sleep(5)  # add a 5 seconds delay for debug

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
        #print(cur)

        # create input_messages table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS input_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bot_id INT,
                message_1 TEXT,
                message_2 TEXT,
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
                info_10 TEXT,
                created_at TIMESTAMP,
                INDEX bot_id_created_at_idx (bot_id, created_at DESC)
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

        # After inserting into input_messages, insert into memory_info as well
        for message in messages:
            insert_into_memory_info(bot_id, message, "")

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

        # After inserting into output_messages, insert into memory_info as well
        insert_into_memory_info(bot_id, "", message)

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
def read_from_input_messages(bot_id, limit=12):
    with app.app_context():
        cur = mysql.connection.cursor()
        sql = "SELECT * FROM input_messages WHERE bot_id = %s AND used = 0 ORDER BY created_at DESC LIMIT %s"
        cur.execute(sql, [bot_id, limit])
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
        
        # Get last 10 messages from the memory_info table for the given bot_id
        sql = "SELECT * FROM memory_info WHERE bot_id = %s ORDER BY created_at DESC LIMIT 10"
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

def insert_output_message(bot_id, user_message, bot_message, destination, db_read_script, db_write_script):
    with app.app_context():
        cur = mysql.connection.cursor()

        # Save bot response to the output_messages table
        cur.execute("INSERT INTO output_messages (bot_id, message, created_at, destination) VALUES (%s, %s, NOW(), %s)", 
                    (bot_id, bot_message, destination))

        # Prepare data to be inserted into the memory_info table
        info_1_data = user_message if db_read_script else None
        info_2_data = bot_message if db_write_script else None

        # If at least one field is not None, insert the record into the memory_info table
        if info_1_data is not None or info_2_data is not None:
            cur.execute("INSERT INTO memory_info (bot_id, info_1, info_2, created_at) VALUES (%s, %s, %s, NOW())",
                        (bot_id, info_1_data, info_2_data))

        mysql.connection.commit()

def update_input_messages_used(bot_id):
    with app.app_context():
        # Create MySQL cursor
        cur = mysql.connection.cursor()

        # Update all rows for this bot_id where used = 0, set used to 1
        cur.execute("UPDATE input_messages SET used = 1 WHERE bot_id = %s AND used = 0", (bot_id,))

        mysql.connection.commit()

# Function to insert data to memory_info table
def insert_into_memory_info(bot_id, info_1, info_2):
    with app.app_context():
        cur = mysql.connection.cursor()

        # Ensure only last 10 messages are stored
        cur.execute("SELECT COUNT(*) FROM memory_info WHERE bot_id = %s", [bot_id])
        count = cur.fetchone()[0]
        if count >= 10:
            cur.execute("DELETE FROM memory_info WHERE bot_id = %s ORDER BY id ASC LIMIT 1", [bot_id])

        sql = '''
            INSERT INTO memory_info 
            (bot_id, info_1, info_2)
            VALUES 
            (%s, %s, %s)
        '''
        params = [bot_id, info_1, info_2]
        cur.execute(sql, params)
        mysql.connection.commit()

# Function to read last 10 data from memory_info table
def read_last_10_from_memory_info(bot_id):
    with app.app_context():
        cur = mysql.connection.cursor()
        sql = "SELECT * FROM memory_info WHERE bot_id = %s ORDER BY id DESC LIMIT 10"
        cur.execute(sql, [bot_id])
        result = cur.fetchall()
        return result

def generate_prompt(bot, user_text):
    input_messages = read_from_input_messages(bot.id)
    messages = []
    if input_messages:
        for row in input_messages:
            for i in range(2, 14):  # column indices for message_1 through message_12
                if row[i] is not None:
                    messages.append(row[i])
        # Once we've used the messages, update the `used` field to True.
        update_input_messages_used(bot.id)

    prompt = f"\n\"role\" : \"system\" , \"content\" : \"{bot.system_prompt}\" , \n"
    for message in messages:
        prompt += f"{message} , \n"
    prompt += f"\"role\" : \"user\" , \"content\" : \"{user_text}\" , \n"
    
    print("DEBUG PROMPT : "+ prompt )
    #time.sleep(5)  # add a 5 seconds delay for debug

    return prompt


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

        # If the user is talking to Bot 1, loop through Bots 2 to 7.
        if number == 1:
            for i in range(2, 8):  # loop for Bots 2 to 7
                temp_bot = Bot.get_bot_by_number(i)

                # Ensure temp_bot is not None before proceeding
                if temp_bot:
                    # Process user message with this bot
                    temp_response = openai.Completion.create(
                        model=temp_bot.ai_model,
                        prompt=generate_prompt(temp_bot, user_text),
                        temperature=0.6,
                        max_tokens=3500,
                    ).choices[0].text.strip()

                    # Assuming you want to update the database tables for these bots as well
                    formatted_user_message_temp = "\n\"role\" : \"user\" , \"content\" : \"" + user_text + "\"\n"
                    formatted_output_message_temp = temp_response + " , \n"
                    db_read_script_bool_temp = temp_bot.db_read_script.lower() == 'true'
                    db_write_script_bool_temp = temp_bot.db_write_script.lower() == 'true'
                    insert_output_message(temp_bot.id, formatted_user_message_temp, formatted_output_message_temp, temp_bot.output_destination, db_read_script_bool_temp, db_write_script_bool_temp)
                    destination_bot_id_temp = int(temp_bot.output_destination)
                    update_input_messages(destination_bot_id_temp, formatted_output_message_temp)

        # Now let the original bot (including Bot 1) process the user message
        response = openai.Completion.create(
            model=bot.ai_model,
            prompt=generate_prompt(bot, user_text),
            temperature=0.6,
            max_tokens=1000,
        ).choices[0].text.strip()

        formatted_user_message = "\n\"role\" : \"user\" , \"content\" : \"" + user_text + "\"\n"
        formatted_output_message = response + " , \n"
        
        db_read_script_bool = bot.db_read_script.lower() == 'true'
        db_write_script_bool = bot.db_write_script.lower() == 'true'

        insert_output_message(bot.id, formatted_user_message, formatted_output_message, bot.output_destination, db_read_script_bool, db_write_script_bool)

        # Update the input_messages table for the destination bot
        destination_bot_id = int(bot.output_destination)
        update_input_messages(destination_bot_id, formatted_output_message)
    return render_template('page_1.html', bot=bot, user_text=user_text, response=response)
    


print("Running the application...")
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
