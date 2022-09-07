from model.Vaccine import Vaccine
from model.Caregiver import Caregiver
from model.Patient import Patient
from util.Util import Util
from db.ConnectionManager import ConnectionManager
import pymssql
import datetime
import re

'''
objects to keep track of the currently logged-in user
Note: it is always true that at most one of currentCaregiver and currentPatient is not null
        since only one user can be logged-in at a time
'''
current_patient = None

current_caregiver = None

def create_patient(tokens):
    # create_patient <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Failed to create user.")
        return

    username = tokens[1]
    password = tokens[2]
    # check 2: check if the username has been taken already
    if username_exists(username, "patient"):
        print("Username taken, try again!")
        return

    # check 3: check if password is strong
    if not password_is_strong(password):
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the patient
    patient = Patient(username, salt=salt, hash=hash)

    # save to patient information to our database
    try:
        patient.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)


def create_caregiver(tokens):
    # create_caregiver <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Failed to create user.")
        return

    username = tokens[1]
    password = tokens[2]
    # check 2: check if the username has been taken already
    if username_exists(username, "caregiver"):
        print("Username taken, try again!")
        return

    # check 3: check if password is strong
    if not password_is_strong(password):
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the caregiver
    caregiver = Caregiver(username, salt=salt, hash=hash)

    # save to caregiver information to our database
    try:
        caregiver.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)


def username_exists(username, database):
    cm = ConnectionManager()
    conn = cm.create_connection()

    if database == "patient":
        select_username = "SELECT * FROM Patients WHERE Username = %s"    
    if database == "caregiver":
        select_username = "SELECT * FROM Caregivers WHERE Username = %s"
    
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def login_patient(tokens):
    # login_patient <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_patient
    if current_caregiver is not None or current_patient is not None:
        print("User already logged in.")
        print("Please log out first")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Login failed.")
        return

    username = tokens[1]
    password = tokens[2]

    patient = None
    try:
        patient = Patient(username, password=password).get()
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    # check if the login was successful
    if patient is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_patient = patient
    pass


def login_caregiver(tokens):
    # login_caregiver <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_caregiver
    if current_caregiver is not None or current_patient is not None:
        print("User already logged in.")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Login failed.")
        return

    username = tokens[1]
    password = tokens[2]

    caregiver = None
    try:
        caregiver = Caregiver(username, password=password).get()
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    # check if the login was successful
    if caregiver is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_caregiver = caregiver


def upload_availability(tokens):
    #  upload_availability <date>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        return

    date = tokens[1]
    # assume input is hyphenated in the format mm-dd-yyyy
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    try:
        d = datetime.datetime(year, month, day)
        current_caregiver.upload_availability(d)
    except pymssql.Error as e:
        print("Upload Availability Failed")
        print("Db-Error:", e)
        quit()
    except ValueError:
        print("Please enter a valid date!")
        return
    except Exception as e:
        print("Error occurred when uploading availability")
        print("Error:", e)
        return
    print("Availability uploaded!")


def add_doses(tokens):
    #  add_doses <vaccine> <number>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    #  check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    vaccine_name = tokens[1]
    doses = int(tokens[2])
    vaccine = None
    try:
        vaccine = Vaccine(vaccine_name, doses).get()
    except pymssql.Error as e:
        print("Error occurred when adding doses")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when adding doses")
        print("Error:", e)
        return

    # if the vaccine is not found in the database, add a new (vaccine, doses) entry.
    # else, update the existing entry by adding the new doses
    if vaccine is None:
        vaccine = Vaccine(vaccine_name, doses)
        try:
            vaccine.save_to_db()
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    else:
        # if the vaccine is not null, meaning that the vaccine already exists in our table
        try:
            vaccine.increase_available_doses(doses)
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    print("Doses updated!")


def search_caregiver_schedule(tokens):
    #  search_caregiver_schedule <date>
    #  check 1: check if user is logged-in
    global current_caregiver
    global current_patient
    if current_caregiver == None and current_patient == None:
        print("Please login first!")
        return
    
    # check 2: the length for tokens 
    if len(tokens) != 2:
        print("Please try again!")
        return

    date = tokens[1]
    # assume input is hyphenated in the format mm-dd-yyyy
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])    

    d = datetime.datetime(year, month, day)
    search_schedule = "SELECT C.Username FROM Caregivers as C, Availabilities as A WHERE A.Username = C.Username AND Time = (%d) ORDER BY C.Username"
    check_doses = "SELECT * FROM Vaccines" 

    try:
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()
        
        print(cursor.execute(search_schedule, (d)))
        conn.commit()
    except pymssql.Error as e: ### this except block to be deleted
        print("pymssql.Error occurred when searching caregiver schedule")
        print("Db-Error:", e)
        raise
        quit()
    except ValueError: ### this except block to be deleted
        print("Please enter a valid date!")
        return
    except Exception as e:
        print("Please try again!")
        print(e)
        return
    finally:
        cm.close_connection()

    # check doses block
    try:
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()
        
        print(cursor.execute(check_doses))
        conn.commit()
    except pymssql.Error as e: ### this except block to be deleted
        print("pymssql.Error occurred when searching caregiver schedule: doses block")
        print("Db-Error:", e)
        raise
        quit()
    except Exception as e:
        print("Please try again!")
        print(e)
        return
    finally:
        cm.close_connection()
    pass
    

def reserve(tokens):
    #  reserve <date> <vaccine>
    #  check 1: check if user is logged-in
    global current_caregiver
    global current_patient

    if current_caregiver == None and current_patient == None:
        print("Please login first!")
        return
    if current_patient is None:
        print("Please login as a patient!")
        return
    
    # check 2: the length for tokens 
    if len(tokens) != 3:
        print("Please try again!")
        return

    date = tokens[1]
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    d = datetime.datetime(year, month, day)

    vaccine_name = tokens[2]

    # check for caregiver availability
    available_caregiver = get_available_caregiver(d)
    if available_caregiver == None:
        return
    # check for vaccine availability
    get_vaccine = "SELECT Name, Doses FROM Vaccines WHERE Name = (%s)"
        
    try:
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()
        cursor.execute(get_vaccine, (vaccine_name))
        doses = cursor.fetchone()
        
    except pymssql.Error as e: ### this except block to be deleted
        print("pymssql error")
        print("Db-Error:", e)
        quit()
    
    except Exception as e:
        print("Error occurred when making reservation")
        print("Error:", e)
        return
    if doses == None:
        print("This facility does not carry that brand of vaccines. Please try again!")
        return
    elif doses[1] == 0:
        print("Not enough available doses!")
        return


    # get appt id number
    appt_id = get_appt_id()     

    print(f"Appointment ID: {appt_id}, Caregiver username: {available_caregiver}")

    # update caregiver availability
    # actually, no, because caregivers can have multiple appointments in one day

    # update appointments
    add_appointment = "INSERT INTO Appointments VALUES (%s, %s, %s, %s, %s)"

    try:
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()
        cursor.execute(add_appointment, (appt_id, available_caregiver, current_patient.username, d, vaccine_name))
        conn.commit()
    except pymssql.Error:
        raise
    finally:
        cm.close_connection()

    # update vaccines

    # create the vaccine
    named_vaccine = Vaccine(vaccine_name,0)
    
    try:
        named_vaccine.get()
        doses_in_inventory = named_vaccine.available_doses
        vaccine = named_vaccine.decrease_available_doses(1)
    except pymssql.Error as e:
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when decreasing doses")
        print("Error:", e)
        return

    pass


def get_available_caregiver(date):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()
    
    # find available caregivers
    available_caregiver = "SELECT Username FROM Availabilities WHERE Time = (%s) ORDER BY Username"

    try:
        cursor.execute(available_caregiver, (date))
        caregiver_username = cursor.fetchone()
    except pymssql.Error:
        raise    
    finally:
        cm.close_connection()
    if caregiver_username == None:
        print("No Caregiver is available!")
        return
    else:
        return caregiver_username[0]


def get_appt_id():
    
    # check the last appointment id number
    get_last_appt_id = "SELECT MAX(ApptID) FROM Appointments"
    try:
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()
        cursor.execute(get_last_appt_id)
        last_appt_id = cursor.fetchone()[0]
        if last_appt_id == None:
            appt_id = 1    
        else: 
            appt_id = last_appt_id + 1
    except pymssql.Error:
        raise    
    finally:
        cm.close_connection()
    return appt_id


def show_appointments(tokens):
    #  check 1: check if user is logged-in
    global current_caregiver
    global current_patient
    if current_caregiver is None and current_patient is None:
        print("Please login first!")
        return
    
    if len(tokens) != 1:
        print("Please try again!")
        return

    try:
        if current_caregiver: 
            appointments = current_caregiver.show_appointments()
        else:
            appointments = current_patient.show_appointments()
    except pymssql.Error as e:
        print("pymmsql Db-Error:", e)
        quit()
    except ValueError:
        print("Please enter a valid date!")
        return
    except Exception as e:
        print("Error:", e)
        return
    print(appointments)
    pass


def logout(tokens):
    #  check 1: check if user is logged-in
    global current_caregiver
    global current_patient
    if len(tokens) != 1:
        print("Please try again!")
        return
    if current_caregiver == None and current_patient == None:
        print("Please login first!")
        return
    else:
        current_caregiver = None
        current_patient = None
        print("Successfully logged out!")
    pass


def password_is_strong(password):
    if len(password) < 8:
        print("Password must be at least 8 characters")
        return False
    if password.islower() or password.isupper():
        print("Password must be a mixture of both uppercase and lowercase letters.")
        return False
    if not (re.search('[a-zA-Z]', password) and re.search('[0-9]', password)):
        print("Password must be a mixture of letters and numbers.")
        return False
    if not (re.search('[!@#?]', password)):
        print("Password must contain at least one special character from !, @, #, ?.")
        return False
    return True


def cancel(tokens):
    """
    TODO: Extra Credit
    """
    pass


def start():
    stop = False
    while not stop:
        print()
        print(" *** Please enter one of the following commands *** ")
        print("> create_patient <username> <password>")  # //TODO: implement create_patient (Part 1)
        print("> create_caregiver <username> <password>")
        print("> login_patient <username> <password>")  #// TODO: implement login_patient (Part 1)
        print("> login_caregiver <username> <password>")
        print("> search_caregiver_schedule <date>")  #// TODO: implement search_caregiver_schedule (Part 2)
        print("> reserve <date> <vaccine>") #// TODO: implement reserve (Part 2)
        print("> upload_availability <date>")
        print("> cancel <appointment_id>") #// TODO: implement cancel (extra credit)
        print("> add_doses <vaccine> <number>")
        print("> show_appointments")  #// TODO: implement show_appointments (Part 2)
        print("> logout") #// TODO: implement logout (Part 2)
        print("> Quit")
        print()
        response = ""
        print("> Enter: ", end='')

        try:
            response = str(input())
        except ValueError:
            print("Type in a valid argument")
            break

        response_lowered = response.lower()
        tokens = response_lowered.split(" ")
        if len(tokens) == 0:
            ValueError("Try Again")
            continue

        operation = tokens[0]
        if operation == "create_patient":
            tokens[-1] = response.split(" ")[-1]
            create_patient(tokens)
        elif operation == "create_caregiver":
            tokens[-1] = response.split(" ")[-1]
            create_caregiver(tokens)
        elif operation == "login_patient":
            login_patient(tokens)
        elif operation == "login_caregiver":
            login_caregiver(tokens)
        elif operation == "search_caregiver_schedule":
            search_caregiver_schedule(tokens)
        elif operation == "reserve":
            reserve(tokens)
        elif operation == "upload_availability":
            upload_availability(tokens)
        elif operation == cancel:
            cancel(tokens)
        elif operation == "add_doses":
            add_doses(tokens)
        elif operation == "show_appointments":
            show_appointments(tokens)
        elif operation == "logout":
            logout(tokens)
        elif operation == "quit":
            print("Thank you for using the scheduler, Goodbye!")
            stop = True
        else:
            print("Invalid Argument")


if __name__ == "__main__":
    '''
    // pre-define the three types of authorized vaccines
    // note: it's a poor practice to hard-code these values, but we will do this ]
    // for the simplicity of this assignment
    // and then construct a map of vaccineName -> vaccineObject
    '''

    # start command line
    print()
    print("Welcome to the COVID-19 Vaccine Reservation Scheduling Application!")

    start()
