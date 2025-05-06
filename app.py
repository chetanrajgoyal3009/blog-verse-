from flask import Flask,render_template,request,redirect,url_for,session,flash,jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta,datetime,timezone
import base64
from werkzeug.security import generate_password_hash, check_password_hash
import os

app=Flask(__name__)
app.secret_key="welcome"
app.permanent_session_lifetime=timedelta(minutes=40)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"check_same_thread": False}}
db=SQLAlchemy(app)

class Student(db.Model):
    _tablename_="usersTable"
    SI_NO=db.Column(db.Integer,primary_key=True) 
    name=db.Column(db.String(60))    
    email=db.Column(db.String(100))
    password_hash = db.Column(db.String(200), nullable=False)
    profile_picture = db.Column(db.LargeBinary, nullable=True)
    # location = db.Column(db.String(100), nullable=True,default="")
    

    def _init_(self,name,email):
        self.name=name
        self.email=email
    
    def save_hash_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_hash_password(self, password):
        return check_password_hash(self.password_hash, password)
        
        
class Post(db.Model):
    _tablename_ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))    
    image = db.Column(db.LargeBinary, nullable=True)
    likes = db.Column(db.Integer, default=0)
    
    def _init_(self, author, title, content,image):
        self.author = author
        self.title = title
        self.content = content
        self.image = image
        

@app.route("/")
def index():
    return render_template("landing.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/signup")
def signup():
    return render_template("login.html")

@app.route("/signin")
def signin():
    return render_template("login.html")


@app.route("/home")
def home():
    if "session-user" in session:
        posts = Post.query.order_by(Post.timestamp.desc()).all()
        for post in posts:
            if post.image:
                post.image = base64.b64encode(post.image).decode('utf-8')
        return render_template("home.html", posts=posts)
    else:
        flash("Please log in to access home.", "warning")
        return redirect(url_for("signup"))

    
    
@app.route("/create")
def create():
    if "session-user" in session:
        return render_template("create.html")  # Pass to template
    else:
        flash("Please log in to access create page.", "warning")
        return redirect(url_for("signup"))



@app.route("/signupRoute",methods=["GET","POST"])
def auth():
    if request.method == "POST":
        form_type = request.form.get("form_type")
        if form_type == "login":
            email = request.form.get("email")
            password = request.form.get("password")
            user = Student.query.filter_by(email=email).first()
            
            if user and user.check_hash_password(password):
                session["session-user"] = user.email
                session["user-name"] = user.name
                flash(f"Logged in successfully! Welcome, {user.name}!", "success")
                return redirect(url_for("home"))
            else:
                flash("Invalid email or password. Try again.", "danger")

        elif form_type == "signup":
            name = request.form.get("name")
            email = request.form.get("email")
            password = request.form.get("password")
            
            existing_user = Student.query.filter_by(email=email).first()
            if existing_user:
                flash("Email already registered! Please log in.", "warning")
            else:
                user = Student(name=name, email=email)
                user.save_hash_password(password)
                db.session.add(user)
                db.session.commit()
                flash("Signup successful! You can now log in.", "success")

    return render_template("login.html")
    
    
@app.route("/loginRoute", methods=["GET", "POST"])
def loginRoute():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = Student.query.filter_by(email=email).first()
        
        if user:
            if user.check_hash_password(password):
                session.permanent = True
                session["session-user"] = user.email  
                session["user-name"] = user.name  
                                
                flash(f"Logged in successfully! Welcome, {user.name}!", "success")
                return redirect(url_for("index"))
            else:
                flash("Incorrect password. Try again.", "danger")
        else:
            flash("Email not found. Please sign up.", "warning")

    return redirect(url_for("signup"))


        
@app.route("/logout")
def logout():
    session.pop("session-user", None)  
    session.pop("user-name", None)  
    flash("Logged out successfully!", "info")
    return redirect(url_for("home"))


@app.route("/add_post", methods=["POST"])
def add_post():
    if "session-user" in session:
        title = request.form.get("title")
        content = request.form.get("content")
        author = session["user-name"]
        image = request.files.get("image")
        image_data = None
        if image:
            image_data = image.read()  

        new_post = Post(author=author, title=title, content=content, image=image_data)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))

    else:
        flash("Please log in to create a post.", "danger")
        return redirect(url_for("signin"))

@app.route("/delete/<int:id>")
def deleteFunction(id):
    if "session-user" not in session:
        flash("Please log in to delete a post.", "danger")
        return redirect(url_for("signin"))
    post = db.session.get(Post, id)
    if post:
        if post.author == session["user-name"]:
            db.session.delete(post)
            db.session.commit()
        else:
            return redirect(url_for("home"))  
    else:
        flash("Post not found!", "danger")
    return redirect(url_for("home"))

@app.route("/update/<int:id>", methods=["POST", "GET"])
def updateFunction(id):
    if "session-user" not in session:
        return redirect(url_for("signup"))

    post = db.session.get(Post, id)
    if not post:
        return redirect(url_for("home"))

    if post.author != session["user-name"]:
        return redirect(url_for("home"))

    if request.method == "POST":
        post.title = request.form.get("title")
        post.content = request.form.get("content")
        image = request.files.get("image")

        if image:
            post.image = image.read()  

        db.session.commit()
        return redirect(url_for("home"))

    return render_template("updateFunction.html", data=post)



@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        flash("Post not found!", "danger")
        return redirect(url_for("home"))
    post_image = base64.b64encode(post.image).decode("utf-8")
    return render_template("post.html", post=post, post_image=post_image)

@app.route("/profile")
def profile():
    if "session-user" not in session:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for("signin"))
    user_email = session["session-user"]
    user = Student.query.filter_by(email=user_email).first()

    profile_picture = None
    if user.profile_picture:
        profile_picture = base64.b64encode(user.profile_picture).decode("utf-8")
    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("home"))

    user_posts = Post.query.filter_by(author=user.name).order_by(Post.timestamp.desc()).all()
    latest_blog = Post.query.filter_by(author=user.name).order_by(Post.timestamp.desc()).first()
    profile_picture = None
    if user.profile_picture:
        profile_picture = base64.b64encode(user.profile_picture).decode("utf-8")

    latest_blog_image = None
    if latest_blog and latest_blog.image:
        latest_blog_image = base64.b64encode(latest_blog.image).decode("utf-8")
        
    return render_template("profile.html",user=user,posts=user_posts,profile_picture=profile_picture,latest_blog_image=latest_blog_image)
    
    
@app.route("/update_profile_picture", methods=["POST"])
def update_profile_picture():
    if "session-user" not in session:
        flash("Please log in to change your profile picture.", "warning")
        return redirect(url_for("signin"))

    user_email = session["session-user"]
    user = Student.query.filter_by(email=user_email).first()

    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("profile"))

    if "profile_picture" in request.files:
        image = request.files["profile_picture"]
        if image:
            user.profile_picture = image.read()
            db.session.commit()
            flash("Profile picture updated successfully!", "success")
            print("Profile picture updated successfully!")

    return redirect(url_for("profile"))

@app.route("/categories")
def categories():
    return render_template("cat.html")

@app.route("/api/students", methods=["GET"])
def get_all_students():
    students = Student.query.all()
    result = []
    for s in students:
        result.append({
            "id": s.SI_NO,
            "name": s.name,
            "email": s.email,
            "password": s.password_hash
        })
    return jsonify(result)



@app.route("/api/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    student = Student.query.get_or_404(student_id)
    return jsonify({
        "id": student.SI_NO,
        "name": student.name,
        "email": student.email,
        "password": student.password_hash,
        "profile_picture": base64.b64encode(student.profile_picture).decode("utf-8") if getattr(student, 'profile_picture', None) else None,
    })

@app.route("/api/students", methods=["POST"])
def create_student():
    data = request.get_json()
    hashed_pw = generate_password_hash(data["password"])
    student = Student(name=data["name"], email=data["email"], password_hash=hashed_pw)
    db.session.add(student)
    db.session.commit()
    return jsonify({"message": "Student created", "SI_NO": student.SI_NO})

@app.route("/api/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    student = Student.query.get_or_404(student_id)
    data = request.get_json()
    student.name = data.get("name", student.name)
    student.email = data.get("email", student.email)
    if "password" in data:
        student.password_hash = generate_password_hash(data["password"])
    db.session.commit()
    return jsonify({"message": "Student updated"})

@app.route("/api/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    return jsonify({"message": "Student deleted"})


@app.route("/api/posts", methods=["GET"])
def get_all_posts():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    result = []
    for post in posts:
        result.append({
            "id": post.id,
            "author": post.author,
            "title": post.title,
            "content": post.content,
            "timestamp": post.timestamp.isoformat(),
            "likes": post.likes,
            "image": base64.b64encode(post.image).decode("utf-8") if post.image else None
        })
    return jsonify(result)


@app.route("/api/posts/<int:post_id>", methods=["GET"])
def get_post(post_id):
    post = Post.query.get_or_404(post_id)
    return jsonify({
        "id": post.id,
        "author": post.author,
        "title": post.title,
        "content": post.content,
        "timestamp": post.timestamp.isoformat(),
        "likes": post.likes,
        "image": base64.b64encode(post.image).decode("utf-8") if post.image else None
    })

@app.route("/api/posts", methods=["POST"])
def create_post():
    data = request.get_json()
    author = data.get("author")
    title = data.get("title")
    content = data.get("content")
    image = data.get("image")  # base64 encoded string (optional)

    image_data = base64.b64decode(image) if image else None

    new_post = Post(author=author, title=title, content=content, image=image_data)
    db.session.add(new_post)
    db.session.commit()
    return jsonify({"message": "Post created", "id": new_post.id}), 201


@app.route("/api/posts/<int:post_id>", methods=["PUT"])
def update_post(post_id):
    # Check what format of image is expected here
    post = Post.query.get_or_404(post_id)
    data = request.get_json()

    post.title = data.get("title", post.title)
    post.content = data.get("content", post.content)

    if "image" in data:
        post.image = base64.b64decode(data["image"]) if data["image"] else None

    db.session.commit()
    return jsonify({"message": "Post updated"})

@app.route("/api/posts/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post deleted"})


with app.app_context():
    db.create_all()  

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000)) 
    app.run(host='0.0.0.0', port=port)
