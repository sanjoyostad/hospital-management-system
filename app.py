from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Doctor, Patient, Appointment

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sanjoy_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'

# Initialize Extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- DATABASE CREATION & ADMIN SETUP ---
# This runs only once to create the DB and the default Admin
with app.app_context():
    db.create_all()
    # Check if admin exists, if not, create one
    if not User.query.filter_by(role='admin').first():
        admin = User(
            username='admin', 
            password=generate_password_hash('admin123'), 
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("Default Admin Created Successfully!")

# --- ROUTES ---

@app.route('/')
def home():
    # Renders the beautiful landing page
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid credentials')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Logic to register PATIENTS only (Admins/Doctors are added by Admin)
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw, role='patient')
        db.session.add(new_user)
        db.session.commit()
        
        # Create Patient Profile
        new_patient = Patient(user_id=new_user.id, full_name=full_name)
        db.session.add(new_patient)
        db.session.commit()
        
        flash('Registration Successful! Please Login.')
        return redirect(url_for('login'))
    return render_template('register.html')

# --- ADMIN ROUTES ---
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access Denied')
        return redirect(url_for('home'))
    
    doctors = Doctor.query.all()
    patients = Patient.query.all()
    # Passing empty list for appointments for now, or you can query them if needed
    appointments = Appointment.query.all() 
    return render_template('admin/dashboard.html', doctors=doctors, patients=patients, appointments=appointments)

@app.route('/add_doctor', methods=['POST'])
@login_required
def add_doctor():
    if current_user.role == 'admin':
        username = request.form.get('username')
        password = generate_password_hash(request.form.get('password'))
        full_name = request.form.get('full_name')
        specialization = request.form.get('specialization')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            new_user = User(username=username, password=password, role='doctor')
            db.session.add(new_user)
            db.session.commit()
            
            new_doc = Doctor(user_id=new_user.id, full_name=full_name, specialization=specialization)
            db.session.add(new_doc)
            db.session.commit()
            flash('Doctor Added Successfully')
        
    return redirect(url_for('admin_dashboard'))

# --- PATIENT ROUTES ---
@app.route('/patient')
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        flash('Access Denied')
        return redirect(url_for('home'))
        
    doctors = Doctor.query.all()
    my_appts = Appointment.query.filter_by(patient_id=current_user.patient_profile.id).all()
    return render_template('patient/dashboard.html', doctors=doctors, appointments=my_appts)

@app.route('/book_appointment/<int:doctor_id>', methods=['POST'])
@login_required
def book_appointment(doctor_id):
    date = request.form.get('date')
    time = request.form.get('time')
    
    # Check if doctor is available (basic check)
    existing = Appointment.query.filter_by(doctor_id=doctor_id, date=date, time=time).first()
    if existing:
        flash('Doctor is already booked for this slot!')
    else:
        new_appt = Appointment(
            patient_id=current_user.patient_profile.id,
            doctor_id=doctor_id,
            date=date,
            time=time
        )
        db.session.add(new_appt)
        db.session.commit()
        flash('Appointment Booked Successfully!')
    return redirect(url_for('patient_dashboard'))

# --- DOCTOR ROUTES ---
@app.route('/doctor')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash('Access Denied')
        return redirect(url_for('home'))
        
    my_appts = Appointment.query.filter_by(doctor_id=current_user.doctor_profile.id).all()
    return render_template('doctor/dashboard.html', appointments=my_appts)

@app.route('/update_treatment/<int:appt_id>', methods=['POST'])
@login_required
def update_treatment(appt_id):
    appt = Appointment.query.get(appt_id)
    if appt and appt.doctor_id == current_user.doctor_profile.id:
        appt.diagnosis = request.form.get('diagnosis')
        appt.prescription = request.form.get('prescription')
        appt.status = 'Completed'
        db.session.commit()
        flash('Treatment Updated')
    else:
        flash('Unauthorized')
    return redirect(url_for('doctor_dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)