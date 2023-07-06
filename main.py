from flask import Flask, render_template, redirect, url_for, flash, request, abort
from functools import wraps
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from date import Date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, CreateFlaskForm, LoginForm, CommentForm

dt = Date()

# configure the flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
db = SQLAlchemy(app)
session = db.session

# For Authentication
login_manager = LoginManager()
login_manager.init_app(app)


# CONFIGURE TABLES
class NewUser(UserMixin, db.Model):
    __tablename__ = "Registerd_new_user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    posts = relationship("BlogPost", back_populates="author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("Registerd_new_user.id"))
    author = relationship("NewUser", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


db.create_all()


# all the routes the website has
def admin_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return wrapper


@login_manager.user_loader
def load_user(user_id):
    return NewUser.query.get(int(user_id))


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, authenticated=current_user.is_authenticated,
                           user=current_user)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = CreateFlaskForm()
    if form.validate_on_submit():
        uzr = NewUser.query.filter_by(email=form.Email.data).first()
        if uzr:
            flash("user already exists please login instead.")
            return redirect(url_for('login'))
        new_user = NewUser(email=form.Email.data,
                           password=generate_password_hash(form.Password.data, method='pbkdf2:sha256', salt_length=8),
                           name=form.Name.data)
        session.add(new_user)
        session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == "POST":
        email = form.email.data
        password = form.password.data

        user = session.query(NewUser).filter_by(email=email).first()

        if not user:
            flash("The User doesn't exist. sign up instead.")
            return redirect(url_for("register"))
        elif not check_password_hash(user.password, password):
            flash("The password was incorrect. please try again.")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>")
def show_post(post_id):
    editor = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if editor.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login first to See inside the post.")
            return redirect(url_for('login'))

    return render_template("post.html", post=requested_post, user=current_user, form=editor,
                           authenticated=current_user.is_authenticated)


@app.route("/about")
def about():
    return render_template("about.html", authenticated=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", authenticated=current_user.is_authenticated)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=dt.date
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=False)
