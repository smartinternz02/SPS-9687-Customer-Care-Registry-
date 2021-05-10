from flask import Flask,render_template,request,url_for,session,redirect
from flask_mysqldb import MySQL
from sendmail import sendemail,forget_password_mail,updated_password_mail,solve_mail
from flask_oauthlib.client import OAuth
import json
import re
from random import randint
from datetime import date

app = Flask(__name__)

# database configuration
app.config['MYSQL_HOST'] = 'remotemysql.com'
app.config['MYSQL_USER'] = 'DB USERNAME'
app.config['MYSQL_PASSWORD'] = 'DB PASSWORD'
app.config['MYSQL_DB'] = 'DB NAME'
mysql = MySQL(app)

# Google authenticate configuration
app.config['GOOGLE_ID'] = 'GOOGLE API ID'
app.config['GOOGLE_SECRET'] = 'GOOGLE SECRET KEY'

app.secret_key = "customercareregistry"

oauth = OAuth()
# google client informations
google = oauth.remote_app(
    'google',
    consumer_key = app.config.get('GOOGLE_ID'),
    consumer_secret = app.config.get('GOOGLE_SECRET'),
    request_token_params = {
        'scope' : ['email','https://www.googleapis.com/auth/userinfo.profile'],
    },
    base_url='https://www.googleapis.com/oauth2/v2/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

oauth.init_app(app)
#home page
@app.route('/')
def home():
    today = date.today()
    current_date = today.strftime('%d/%m/%Y')
    if "google_token" in session:
        session["current_date"] = current_date
        return render_template('home.html')
    if "username" in session:
        session["current_date"] = current_date
        return render_template('home.html')
    return render_template('index.html')

# manually registration
@app.route('/register',methods=["POST"])
def register():
    if request.method == 'POST':
        name = request.form['uname']
        mail = request.form['mail']
        pwd = request.form['pwd']
        cpwd = request.form['confirmpwd']
        if not re.match(r'[^@]+@[^@]+\.[^@]+', mail):
            msg = 'Invalid email address !'
            return render_template('index.html',signupmsg=msg)
        if pwd != cpwd:
            msg = 'Please enter correct confirm password'
            return render_template('index.html',signupmsg=msg)
        # check account is exists or not
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM customerdeatils WHERE email LIKE % s',[mail])
        existing_user = cursor.fetchone()
        cursor.close()
        #exits 
        if existing_user:
            msg = 'Account already exists please login.'
            return render_template('index.html',signupmsg = msg)
        # not exists
        # send mail
        sendemail(mail,'Account_creation')
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO customerdeatils VALUES(null,% s,% s,% s)',(name,mail,pwd))
        mysql.connection.commit()
        cursor.close()
        msg = 'Your registration successfully completed.'
    return render_template('index.html',signupmsg = msg)
# admin page
@app.route('/admin/<which>')
def admin(which):
    if which == 'customers':
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM customerdeatils')
        data = cursor.fetchall()
        cursor.close()
        print(data[0])
        return render_template('admin.html',customers=data,complaints=None)
    if which == 'complaints':
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM complaints')
        data = cursor.fetchall()
        cursor.close()
        return render_template('admin.html',customers=None,complaints=data)
# admin delete
@app.route('/Delete/<type>/<id>')
def Delete(type,id):
    if type == 'customers':
        cursor = mysql.connection.cursor()
        cursor.execute('DELETE FROM customerdeatils WHERE id = % s',[id])
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('admin',which='customers'))
    if type == 'complaints':
        cursor = mysql.connection.cursor()
        cursor.execute('DELETE FROM complaints WHERE id = % s',[id])
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('admin',which='complaints'))
# manually login
@app.route('/login',methods=['POST','GET'])
def login():
    if request.method == 'POST':
        mail = request.form['mail1']
        password = request.form['pwd1']
        # login is admin or not
        if mail == "admin" and password == 'admin@1810':
            return redirect(url_for('admin',which='customers'))
        # check account is exists or not
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM customerdeatils WHERE email=% s AND password=% s',(mail,password))
        user = cursor.fetchone()
        cursor.close()
        #exists
        if user:
            session["username"] = user[1]
            session['mail'] = mail
            return render_template('home.html',username=session["username"],mail=session["mail"])
        else:
            msg = 'mail or password is not valid.'
            return render_template('index.html',signinmsg=msg)
    if request.method == "GET":
        return redirect(url_for('home'))
# google account through registration
@app.route('/google_signup')
def google_signup():
    return google.authorize(callback=url_for('google_signup_authorized',_external=True))

# google registration authorization
@app.route('/google_signup/google_signup_authorized')
def google_signup_authorized():
    resp = google.authorized_response()
    if resp:
        session['google_token'] = (resp['access_token'], '') 
        # fetch client information  
        p_json = json.dumps(google.get('userinfo').data) 
        # extract json file
        ex_json = json.loads(p_json)
        # random 6 digit password creation
        password = randint(10 ** 5,10**6)

        name = ex_json['name']
        mail = ex_json['email']
        # check account is already register or not
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM customerdeatils WHERE email LIKE % s',[mail])
        existing_user = cursor.fetchone()
        cursor.close()
        # exists
        if existing_user:
            msg = 'Account already exists please login.'
            return render_template('index.html',signupmsg = msg)
        # doesn't exist
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO customerdeatils VALUES(null,% s,% s,% s)',(name,mail,password))
        mysql.connection.commit()
        cursor.close()
        # send mail
        sendemail(mail,'Account_creation')
        msg = 'Your registration successfully completed. password is {} please go to login'.format(str(password))
        return render_template('index.html',signupmsg = msg)
    else:
        msg = "Invalid response from google please try again"
        return render_template('index.html',signupmsg = msg)

# google account through login
@app.route('/google_login')
def google_login():
    return google.authorize(callback=url_for('google_login_authorized',_external=True))

#google login authorization
@app.route('/google_login/google_login_authorized')
def google_login_authorized():
    resp = google.authorized_response()
    if resp:
        session['google_token'] = (resp['access_token'], '')   
        p_json = json.dumps(google.get('userinfo').data) 
        ex_json = json.loads(p_json)
        name = ex_json['name']
        email = ex_json['email']
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM customerdeatils WHERE email LIKE % s',[email])
        existing_user = cursor.fetchone()
        cursor.close()
        if not existing_user:
            msg = "Account doesn't exist please register"
            return render_template('index.html',signinmsg = msg)
        session["username"] = name
        session["mail"] = email
        return redirect(url_for('home'))
    else:
        msg = "Invalid response from google please try again"
    return render_template('index.html',signinmsg = msg)

@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')

# logout method
@app.route('/logout')
def logout():
    if "username" in session:
        session.pop("username")
    if "google_token" in session:
        session.pop("google_token")
        session.pop("mail")
    if "mail" in session:
        session.pop("mail")
    return redirect(url_for('home'))

# complaint register
@app.route('/complaint',methods=['POST'])
def complaint():
    if request.method == 'POST':
        complaint_name = request.form['complaint_name']
        name = request.form['name']
        mail = request.form['email']
        against_person = request.form['against_person']
        date = request.form["date"]
        des = request.form['complaint_des']
        cursor = mysql.connection.cursor()
        if not name == session["username"] or not mail == session["mail"]:
            msg = "please don't change username and mail."
            return render_template('home.html',msg=msg)
        cursor.execute("INSERT INTO complaints VALUES(NULL,% s,% s,% s,% s,% s,% s,% s)",(complaint_name,name,mail,against_person,des,date,'0'))
        mysql.connection.commit()
        cursor.close()
        sendemail(mail,'complaint_creation')
        msg = 'Complaint registerd you check out complaints section.'
        return render_template('home.html',msg=msg)

# show complaints and progress
@app.route('/showcomplaints')
def showcomplaints():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM complaints WHERE username= % s AND email=% s",(session["username"],session["mail"]))
    details = cursor.fetchall()
    cursor.close()
    return render_template('complaints.html',complaints=details)
# update complaint
@app.route('/solve',methods=["POST"])
def solve_complaint():
    if request.method == "POST":
        c_id = request.form['c_id']
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE complaints SET solved = % s WHERE id = % s",('1',c_id,))
        mysql.connection.commit()
        cursor.execute("SELECT * FROM complaints WHERE id = % s",[c_id])
        details = cursor.fetchone()
        cursor.close()
        solve_mail(details[3],'user')
        return redirect(url_for('showcomplaints'))
    return redirect(url_for('showcomplaints'))
# admin agent allot
@app.route('/solve_admin',methods=["POST"])
def solve_admin():
    if request.method == "POST":
        c_id = request.form['c_id']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM complaints WHERE id = % s",[c_id])
        details = cursor.fetchone()
        cursor.close()
        solve_mail(details[3],'admin')
        return redirect(url_for('admin',which='complaints'))
    return redirect(url_for('admin',which='complaints'))
# remove complaint
@app.route('/dismiss',methods=["POST"])
def dismiss_complaint():
    if request.method == "POST":
        c_id = request.form["c_id"]
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM complaints WHERE id = % s",[c_id])
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('showcomplaints'))
    return redirect(url_for('showcomplaints'))
# send otp in user mail id
@app.route('/send_otp',methods=["POST","GET"])
def send_otp():
    if request.method == "POST":
        mail = request.form["mail"]
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM customerdeatils WHERE email = % s",[mail])
        temp = cursor.fetchone()
        cursor.close()
        if not temp:
            return render_template('forget.html',type='otp',msg1='Your account doesn\'t exist please register')
        otp = randint(10 ** 5,10**6)
        forget_password_mail(mail,otp)
        session["otp"] = otp
        return render_template('forget.html',type='update_password',tempmail=mail)
# forget password method      
@app.route('/forgetpassword/<type>',methods=["POST","GET"])
def forgetpassword(type):
    if type == 'otp':
        return render_template('forget.html',type=type)
    if request.method == "POST":
        mail = request.form["mail"]
        otp = request.form["otp"]
        pwd = request.form["password"]
        c_pwd = request.form["con_pwd"]
        print(otp,session['otp'])
        if not pwd == c_pwd:
            msg = 'Please Enter Password properly'
            return render_template('forget.html',type='updatePassword',msg=msg)
        if not otp == str(session['otp']):
            msg = "Your OTP is Incorrect."
            return render_template('forget.html',type='updatePassword',msg=msg)
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE customerdeatils SET password = % s WHERE email = % s",(pwd,mail))
        mysql.connection.commit()
        cursor.close()
        msg = 'password updated successfully'
        updated_password_mail(mail)
        return render_template('forget.html',type='updatePassword',msg=msg)

        
if __name__ == '__main__':
    app.run(host = '0.0.0.0',port = 8080,debug=True)