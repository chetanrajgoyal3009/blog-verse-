from flask import Flask,render_template,request,redirect,url_for,session,flash,jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta,datetime,timezone
import base64
from werkzeug.security import generate_password_hash, check_password_hash


app=Flask(__name__)
app.secret_key="welcome"
app.permanent_session_lifetime=timedelta(minutes=40)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"check_same_thread": False}}
db=SQLAlchemy(app)

class Student(db.Model):
    __tablename__="usersTable"
    SI_NO=db.Column(db.Integer,primary_key=True) 
    name=db.Column(db.String(60))    
    email=db.Column(db.String(100))
    password_hash = db.Column(db.String(200), nullable=False)
    profile_picture = db.Column(db.LargeBinary, nullable=True)
    # location = db.Column(db.String(100), nullable=True,default="")
    

    def __init__(self,name,email):
        self.name=name
        self.email=email
    
    def save_hash_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_hash_password(self, password):
        return check_password_hash(self.password_hash, password)
        
        
class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))    
    image = db.Column(db.LargeBinary, nullable=True)
    likes = db.Column(db.Integer, default=0)
    
    def __init__(self, author, title, content,image):
        self.author = author
        self.title = title
        self.content = content
        self.image = image
        

        
class Bookmark(db.Model):
    __tablename__ = "bookmarks"
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(100), nullable=False)  # User who bookmarked
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))  # Post ID
    post = db.relationship("Post", backref=db.backref("bookmarked_by", lazy="dynamic"))

    def __init__(self, user_email, post_id):
        self.user_email = user_email
        self.post_id = post_id
        
        

class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(100), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)

    def __init__(self, user_email, post_id):
        self.user_email = user_email
        self.post_id = post_id
        
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)  # Link to Post
    user_email = db.Column(db.String(100), nullable=False)  # User who commented
    content = db.Column(db.Text, nullable=False)  # Comment text
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp

    def __init__(self, post_id, user_email, content):
        self.post_id = post_id
        self.user_email = user_email
        self.content = content


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

        # flash("Post created successfully!", "success")
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
            # flash("Post deleted successfully!", "success")
        else:
            # flash("You can only delete your own posts!", "danger")
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



@app.route("/bookmarks")
def bookmarks():
    if "session-user" not in session:
        flash("Please log in to view bookmarks.", "warning")
        return redirect(url_for("signin"))

    user_email = session["session-user"]
    saved_posts = Post.query.join(Bookmark, Bookmark.post_id == Post.id).filter(Bookmark.user_email == user_email).all()

    return render_template("bookmarks.html", saved_posts=saved_posts, base64=base64)  # ✅ Pass base64 to the template


@app.route("/bookmark/<int:post_id>", methods=["POST"])
def bookmark_post(post_id):
    if "session-user" not in session:
        flash("Please log in to bookmark posts.", "warning")
        return redirect(url_for("signin"))

    user_email = session["session-user"]
    existing_bookmark = Bookmark.query.filter_by(user_email=user_email, post_id=post_id).first()

    if existing_bookmark:
        db.session.delete(existing_bookmark)  # Remove bookmark if it already exists
        db.session.commit()
        flash("Bookmark removed!", "info")
    else:
        new_bookmark = Bookmark(user_email, post_id)
        db.session.add(new_bookmark)
        db.session.commit()
        # flash("Post bookmarked successfully!", "success")

    return redirect(url_for("home"))


@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):
    if "session-user" not in session:
        return "User not Found"
    user_email = session["session-user"]
    post = db.session.get(Post, post_id)
    if not post:
        return "Post not Found"
    existing_like = Like.query.filter_by(user_email=user_email, post_id=post_id).first()

    if existing_like:
        db.session.delete(existing_like)  # ✅ Unlike the post
        post.likes -= 1  # ✅ Decrease like count
        db.session.commit()
        return {"likes": post.likes, "liked": False}
    else:
        new_like = Like(user_email, post_id)
        db.session.add(new_like)
        post.likes += 1  # ✅ Increase like count
        db.session.commit()
        return {"likes": post.likes, "liked": True}


@app.route("/add_comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    if "session-user" not in session:
        return jsonify({"error": "Please log in to comment."}), 403

    user_email = session["session-user"]
    content = request.form.get("content")
    
    if not content:
        return jsonify({"error": "Comment cannot be empty."}), 400

    new_comment = Comment(user_email=user_email, post_id=post_id, content=content)
    db.session.add(new_comment)
    db.session.commit()

    return jsonify({"user": user_email, "content": content})


@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        flash("Post not found!", "danger")
        return redirect(url_for("home"))

    # Convert image to base64 if it exists
    
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
        # print("✅ Profile picture retrieved successfully!")
    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("home"))

    # Fetch user's posts only
    user_posts = Post.query.filter_by(author=user.name).order_by(Post.timestamp.desc()).all()

    # Fetch the latest blog by the user
    latest_blog = Post.query.filter_by(author=user.name).order_by(Post.timestamp.desc()).first()

    # Convert profile picture and blog image to base64
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
            user.profile_picture = image.read()  # ✅ Save image in DB
            db.session.commit()
            flash("Profile picture updated successfully!", "success")
            print("✅ Profile picture updated successfully!")  # Debugging

    return redirect(url_for("profile"))

@app.route("/categories")
def categories():
    return render_template("cat.html")


with app.app_context():
    db.create_all()  

if __name__=="__main__":
    app.run(debug=True)