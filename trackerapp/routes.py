from flask import render_template, url_for, flash, redirect, request, abort, jsonify, send_file
import secrets
import os
from datetime import datetime, timedelta
from PIL import Image
from trackerapp import app, db, bcrypt, mail
from trackerapp.forms import RegistrationForm, LoginForm, UpdateAccountForm, RequestResetForm, ResetPasswordForm
from trackerapp.models import User, Activity
from flask_login import login_user, current_user, logout_user, login_required
from collections import defaultdict
from flask_mail import Message
import matplotlib
import matplotlib.pyplot as plt
import json  

@app.route('/')
@app.route('/home')
def home():
    image_file = None

    if current_user.is_authenticated:
        # Retrieve the user's profile image URL when authenticated
        image_file = url_for('static', filename='profile_pics/' + current_user.image_file)

    if current_user.is_authenticated:
        
        return render_template('home_signed_in.html', title='Home', image_file=image_file)
    else:
        return render_template('home_signed_out.html', title='Home', image_file=image_file)


@app.route('/about')
def about():
    return render_template('about.html', title='About')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account has been created. You can now log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    logout_user()   
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    f_name, f_ext = os.path.splitext(form_picture.filename)
    picture_filename = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_filename)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_filename



def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)



@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)



@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Account has been updated', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email

    image_file = url_for('static', filename='profile_pics/'+ current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)



@app.route('/activity', methods=['GET', 'POST'])
@login_required
def allActivity():
    activities = Activity.query.all()
    return render_template('all_activity.html', title='Activity', activities=activities)



@app.route('/record_activity', methods=['POST'])
@login_required
def record_activity():
    if request.method == 'POST':
        start_time = datetime.now()  
        duration_str = request.json['duration']
        hours, minutes, seconds = map(int, duration_str.split(':'))
        duration = hours * 3600 + minutes * 60 + seconds
        end_time = start_time + timedelta(seconds=duration)
        activity = Activity(user_id=current_user.id, start_time=start_time, end_time=end_time)
        db.session.add(activity)
        db.session.commit()
        return jsonify({'message': 'Activity recorded successfully'})
    


def convert_minutes_to_hours_and_minutes(minutes):
    hours = int(minutes // 60)
    remaining_minutes = round(minutes % 60)  
    return f"{hours} hours and {remaining_minutes} minutes"



@app.route('/daychart')
@login_required
def daychart():
    today = datetime.today().date()
    activities = Activity.query.filter(Activity.start_time >= today).all()
    hourly_duration = {}
    for hour in range(24):
        hourly_duration[str(hour).zfill(2)] = 0
    for activity in activities:
        start_time = activity.start_time
        end_time = activity.end_time
        duration_minutes = (end_time - start_time).total_seconds() / 60
        hour_key = start_time.strftime('%H')
        hourly_duration[hour_key] += duration_minutes

    duration_data = list(hourly_duration.values())
    duration_data_json = json.dumps(duration_data)

    total_daily_minutes = sum((activity.end_time - activity.start_time).total_seconds() / 60 for activity in activities)
    total_daily_hours_and_minutes = convert_minutes_to_hours_and_minutes(total_daily_minutes)

    return render_template('/charts/daychart.html', duration_data_json=duration_data_json, total_daily_hours_and_minutes=total_daily_hours_and_minutes)


@app.route('/weekchart')
@login_required
def weekchart():
    today = datetime.today().date()
    start_of_week = today - timedelta(days=today.weekday())  
    end_of_week = start_of_week + timedelta(days=6)  

    activities = Activity.query.filter(
        Activity.start_time >= start_of_week,
        Activity.end_time <= end_of_week
    ).all()

    total_weekly_minutes = sum((activity.end_time - activity.start_time).total_seconds() / 3600 for activity in activities)
    
    daily_duration = {
        'Monday': 0,
        'Tuesday': 0,
        'Wednesday': 0,
        'Thursday': 0,
        'Friday': 0,
        'Saturday': 0,
        'Sunday': 0
    }

    for activity in activities:
        start_time = activity.start_time
        end_time = activity.end_time
        day_name = start_time.strftime('%A')  
        duration_minutes = (end_time - start_time).total_seconds() / 3600
        daily_duration[day_name] += duration_minutes

    
    duration_data = list(daily_duration.values())
    duration_data_json = json.dumps(duration_data)

    total_weekly_hours_and_minutes = convert_minutes_to_hours_and_minutes(total_weekly_minutes * 60)

    return render_template('/charts/weekchart.html', duration_data_json=duration_data_json, total_weekly_hours_and_minutes=total_weekly_hours_and_minutes)


@app.route('/monthchart')
@login_required
def monthchart():
    today = datetime.today()
    current_year = today.year
    activities = Activity.query.filter(
        db.extract('year', Activity.start_time) == current_year
    ).all()
    monthly_duration = [0] * 12
    for activity in activities:
        start_time = activity.start_time
        end_time = activity.end_time
        month = start_time.month
        duration_hours = (end_time - start_time).total_seconds() / 3600
        monthly_duration[month - 1] += duration_hours

    total_monthly_minutes = sum((activity.end_time - activity.start_time).total_seconds() / 60 for activity in activities)
    total_monthly_hours_and_minutes = convert_minutes_to_hours_and_minutes(total_monthly_minutes)


    return render_template('/charts/monthchart.html', monthly_duration=monthly_duration, total_monthly_hours_and_minutes=total_monthly_hours_and_minutes)



@app.route('/yearchart')
@login_required
def yearchart():
    today = datetime.today()
    current_year = today.year
    activities = Activity.query.filter(
        db.extract('year', Activity.start_time) >= current_year
    ).all()
    yearly_duration = {}
    for activity in activities:
        start_time = activity.start_time
        end_time = activity.end_time
        year = start_time.year
        duration_hours = (end_time - start_time).total_seconds() / 3600
        if year in yearly_duration:
            yearly_duration[year] += duration_hours
        else:
            yearly_duration[year] = duration_hours
    years = list(yearly_duration.keys())
    durations = list(yearly_duration.values())
    total_yearly_minutes = sum((activity.end_time - activity.start_time).total_seconds() / 60 for activity in activities)
    total_yearly_hours_and_minutes = convert_minutes_to_hours_and_minutes(total_yearly_minutes)


    return render_template('/charts/yearchart.html', years=years, durations=durations, total_yearly_hours_and_minutes=total_yearly_hours_and_minutes)

