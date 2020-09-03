from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, json
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, \
    EmptyForm, PostForm, ResetPasswordRequestForm, ResetPasswordForm, AddActivityForm
from app.models import User, Post, Activity, DataPoint
from app.email import send_password_reset_email
import ast


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    activities = Activity.query.all()
    return render_template('index.html', activities=activities)


@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Explore', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash('You are following {}!'.format(username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash('You are not following {}.'.format(username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/open_activities')
def get_open_activities():
    activities = [[a.id, a.name] for a in Activity.query.all()]
    nl_list  = to_logo_list_str(activities)
    response = app.response_class(
        response=json.dumps(nl_list),
        status=200,
        mimetype='application/json'
    )
    return  response

@app.route('/highscore/<act_id>', methods=['POST', 'GET'])
def highscore(act_id):
    activity = Activity.query.get(act_id)
    averages = []
    for point in activity.data_points:
        user_dict = {'name' : point.data['name']}
        user_dict.update(point.data['averages'])
        averages.append(user_dict)
    # this is ordered, so this is how they will appear in the high score, left to right
    table_keys = ['name', 'Population', 'Food Production', 'Cows', 'Pollution', 'Avg. Lifespan', 'Temperature', 'Forest', 'Grass']
    # make sure to sort these correctly first
    table_values = []
    table_values.append(table_keys)
    user_data = [[ inner[k] for k in table_keys] for inner in averages]
    print(user_data)
    table_values.append(list(user_data))
    print(table_values)
    return render_template('highscore.html', activity=activity, data=averages, table_data=table_values)

@app.route('/activity/<act_id>', methods=['POST', 'GET'])
def activity(act_id):
    activity = Activity.query.get(act_id)
    return render_template('activity.html', activity=activity)

@app.route('/add_activity', methods=['POST', 'GET'])
@login_required
def add_activity():
    form = AddActivityForm()
    if form.validate_on_submit():
        act = Activity(name = form.name.data, owner = current_user.id)
        db.session.add(act)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_activity.html', form=form)


## TODO: move this to a utils class
def to_json(astr):
    alist = ast.literal_eval(astr)
    cleaned_data = {sublist[0] : sublist[1] for sublist in alist}
    avgs = {}
    for k,v in cleaned_data.items() :
        if isinstance(v[1], float):
            avgs[k] = sum(v) / len(v)
    cleaned_data['averages'] = avgs
    return cleaned_data

@app.route('/add_data', methods=['POST', 'GET', 'PUT'])
def add_data_point():
    args = request.args.to_dict()
    if 'activity' in args:
        activity_id = int(float(args['activity']))
        if Activity.exists(activity_id):
            jargs = to_json(args['data'])
            dp = DataPoint(data = jargs, activity_id = activity_id)
            db.session.add(dp)
            db.session.commit()
            return(app.response_class(response=json.dumps("OK"), status=200, mimetype='application/json'))
        else:
            return(app.response_class(response=json.dumps("Activity doesnt exist"), status=400, mimetype='application/json'))

def to_logo_list_str(alist):
    ret_str = ""
    for char in str(alist):
        if char == "(":
            ret_str = ret_str + "["
        elif char == ")":
            ret_str = ret_str + "]"
        elif char == ",":
            ret_str = ret_str + " "
        elif char == "'":
            ret_str = ret_str + '"'
        else:
            ret_str = ret_str + char
    return(ret_str)
        


@app.route('/check_password', methods=['GET'])
def check_password():
    print(request.args.to_dict())
    act_id = request.args.get('activity', type=float)
    act_id = int(act_id)
    password = request.args.get('password', type=str)
    activity = Activity.query.get(act_id)
    pw_check = password == activity.password
    response = app.response_class(
        response=json.dumps(pw_check),
        status=200,
        mimetype='application/json'
    )
    return  response