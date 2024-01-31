from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask import flash
from flask import jsonify
from flask import send_from_directory
from markupsafe import Markup
from flask_babel import Babel
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import aliased
import validators
from werkzeug.utils import secure_filename
from flask_debugtoolbar import DebugToolbarExtension
from flask_caching import Cache
from PIL import Image
import os
import random
import uuid
import requests

app = Flask(__name__)

# Options
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads') # Do not touch this!
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'} # Images allowed extensions 
MAX_PREVIEW_SIZE_MB = 5  # 5MB
MAX_PREVIEW_SIZE_BYTES = MAX_PREVIEW_SIZE_MB * 1024 * 1024
MODERATION_API_URL = 'https://api.moderatecontent.com/moderate/'
MODERATION_API_KEY = '6360297f034edb6ac25e9df05adb9a10' # API key at https://moderatecontent.com/
MAX_MODERATION_SCORE = 90  # Define the maximum allowed moderation score (adjust as needed)
COMPRESSION_VALUE = 65  # Define the compression value for the media (adjust as needed)

# Configure Flask
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'fc322da701c206024136e117ce3f6ee')  # Do not touch this!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['BABEL_DEFAULT_LOCALE'] = 'en'  # Default language is English
app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'  # Admin theme
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DEBUG_TB_PROFILER_ENABLED'] = False
app.debug = False

# Configure Flask-Caching
app.config['CACHE_TYPE'] = 'simple'  # Can be 'simple', 'memcached', 'redis', etc.
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # Cache timeout in seconds
cache = Cache(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_folder():
    return str(uuid.uuid4())  # Use UUID to generate a unique folder name

# Format votes 
def format_votes(votes):
    if votes < 1000:
        return str(votes)
    elif votes < 1000000:
        return f"{votes / 1000:.1f}K"
    else:
        return f"{votes / 1000000:.1f}M"

class UnsafeImageError(Exception):
    pass

# Moderate the image before saving it to the server (Score 80-60 is good)
def moderate_image(image_path):
    # Prepare the files parameter
    files = {'file': open(image_path, 'rb')}

    # Prepare the payload with the API key
    payload = {'key': MODERATION_API_KEY}

    # Set content type to form-urlencoded
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    # Make the POST request
    response = requests.post(MODERATION_API_URL, files=files, data=payload)

    # Check the moderation response and take appropriate action
    #print(response.json()) # For debugging only
    moderation_result = response.json()
    if moderation_result['error_code'] == 0:
        rating_label = moderation_result['rating_label']
        if rating_label != 'everyone':
            # Check if adult content score exceeds 60 points
            adult_score = moderation_result['predictions']['adult']
            if adult_score <= MAX_MODERATION_SCORE:
                # Adult content is within the allowed limit, considered safe
                pass
            else:
                # Adult content score exceeds the allowed limit points, raise an exception
                raise UnsafeImageError('The uploaded image has a too high adult content score. Please try again with a different image.')
        elif rating_label == 'teen':
            pass
    else:
        # Moderation API error, raise an exception
        raise UnsafeImageError('Error in the moderation API. Please try again later.')

# Error message if the promo link provided is invalid
def redirect_to_error(promo_link):
    if promo_link:
        raise UnsafeImageError('Please provide a correct link format for the social link. Example: https://example.com/ or https://example.com/example')

# Setup DB and Flask-Admin
db = SQLAlchemy(app)
admin = Admin(app, name='Vice Girls', url='/admin', template_mode='bootstrap4')
babel = Babel(app)
toolbar = DebugToolbarExtension(app)

class Girl(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    votes = db.Column(db.Integer, default=1) # Set the default value to 1
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    image_url = db.Column(db.String(255))  # You can adjust the length based on your needs
    promo_link = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='active') # Set the default value to 'active'/ 'verified' if the girl identity is verified

class VoteLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voted_girl_id = db.Column(db.Integer, db.ForeignKey('girl.id'), nullable=False)
    other_girl_id = db.Column(db.Integer, db.ForeignKey('girl.id'), nullable=False)
    voted_date = db.Column(db.DateTime, default=datetime.utcnow)
    # voted_girl_name = db.Column(db.String(50), nullable=False)  # Not needed
    voted_girl = db.relationship('Girl', foreign_keys=[voted_girl_id], backref=db.backref('votes_received', lazy=True))
    other_girl = db.relationship('Girl', foreign_keys=[other_girl_id], backref=db.backref('votes_given', lazy=True))
   
    def __init__(self, voted_girl, other_girl):
        self.voted_girl_id = voted_girl.id
        self.other_girl_id = other_girl.id
        self.voted_girl_name = voted_girl.name

class VoterIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False)
    vote_log_id = db.Column(db.Integer, db.ForeignKey('vote_log.id'), nullable=False)
    vote_log = db.relationship('VoteLog', backref='voter_ip')

class UploadIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False)
    girl_name = db.Column(db.String(50), unique=True, nullable=False)

class Ad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False, unique=True)
    link = db.Column(db.String(200), nullable=True)

# Flask-Admin
admin.add_view(ModelView(Girl, db.session))
admin.add_view(ModelView(VoteLog, db.session))
admin.add_view(ModelView(VoterIP, db.session))
admin.add_view(ModelView(UploadIP, db.session))
admin.add_view(ModelView(Ad, db.session))

# Create database tables if they don't exist already
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    # Alias the Girl table to differentiate between voted_girl and other_girl
    voted_girl_alias = aliased(Girl, name='voted_girl')
    other_girl_alias = aliased(Girl, name='other_girl')
    
    # Fetch all girls ordered by votes
    girls = Girl.query.order_by(Girl.votes.desc()).all()

    # Fetch the latest votes
    latest_votes = (
        db.session.query(VoteLog, voted_girl_alias, other_girl_alias)
        .join(voted_girl_alias, VoteLog.voted_girl_id == voted_girl_alias.id)
        .join(other_girl_alias, VoteLog.other_girl_id == other_girl_alias.id)
        .order_by(VoteLog.voted_date.desc())
        .limit(10)
        .all()
    )

    # Extract relevant information from the latest votes
    latest_votes_info = [
        {
            'voted_girl_name': voted_girl.name,
            'voted_girl_image_url': voted_girl.image_url,
            'voted_girl_status': voted_girl.status,
            'other_girl_name': other_girl.name,
            'other_girl_image_url': other_girl.image_url,
            'other_girl_status': other_girl.status,
            'voted_date': vote_log.voted_date    
        } for vote_log, voted_girl, other_girl in latest_votes
    ]

    if len(girls) >= 2:
        # Randomly decide whether to use pure random or vote count-based selection
        use_vote_count_selection = random.choice([True, False])

        if use_vote_count_selection:
            # Split the girls into two groups based on the median votes
            median_index = len(girls) // 2
            high_vote_girls = girls[:median_index]
            low_vote_girls = girls[median_index:]

            # Randomly select one girl from each group
            girl1 = random.choice(high_vote_girls)
            girl2 = random.choice(low_vote_girls)
        else:
            # Pure random selection
            girl1, girl2 = random.sample(girls, 2)
    else:
        girl1, girl2 = None, None

    # Get the leaderboard with formatted votes
    leaderboard = Girl.query.order_by(Girl.votes.desc()).limit(10).all()
    for girl in leaderboard:
        girl.formatted_votes = format_votes(girl.votes)

    # Separate odd and even leaderboards
    odd_leaderboard = [girl for index, girl in enumerate(leaderboard) if index % 2 == 1]
    even_leaderboard = [girl for index, girl in enumerate(leaderboard) if index % 2 == 0]

    total_votes = sum([girl.votes for girl in girls])
    total_girls = len(girls)

    # Use the format_votes function to format the number of votes
    total_votes_formatted = format_votes(total_votes)
    total_girls_formatted = format_votes(total_girls)

    new_girls = Girl.query.order_by(Girl.added_date.desc()).limit(30).all()
    random_girls = Girl.query.order_by(func.random()).limit(30).all()

    # Ads system
    all_ads = Ad.query.all()
    random_ad = random.choice(all_ads)
    ad_path = url_for('static', filename='ads/{}'.format(random_ad.filename))
    ad_link = random_ad.link if random_ad.link else '#'  

    return render_template('index.html', girl1=girl1, girl2=girl2, leaderboard=leaderboard, total_votes=total_votes, latest_votes=latest_votes_info, odd_leaderboard=odd_leaderboard, even_leaderboard=even_leaderboard, total_girls=total_girls, new_girls=new_girls, random_girls=random_girls, total_votes_formatted=total_votes_formatted, total_girls_formatted=total_girls_formatted, ad_path=ad_path, ad_link=ad_link)

@app.route('/submit', methods=['POST'])
def submit():
    girl_name = request.form.get('girl_name')
    image_file = request.files.get('image_file')
    promo_link = request.form.get('promo_link')

    # Remove spaces from the girl's name and convert to lowercase
    girl_name = girl_name.replace(' ', '').lower()

    girl_page_url = None  # URL of the girl page

    if girl_name:
        if len(girl_name) > 30:
            flash('Please provide a name with at most 30 characters!', 'error')
        else:
            # Case-insensitive query to check if the girl already exists
            existing_girl = Girl.query.filter(func.lower(Girl.name) == func.lower(girl_name)).first()
            if existing_girl:
                girl_page_url = url_for('girl_page', girl_name=girl_name, _external=True)
                flash(Markup('A Girl with the same name already exists! Check the girl page: <a href="{}">{}</a>'.format(girl_page_url, girl_page_url)), 'error')
            elif not image_file or not allowed_file(image_file.filename):
                flash('Please provide a valid image file for the girl (png, jpg, jpeg, gif, webp)!', 'error')
            else:
                image_data = image_file.read()
                if len(image_data) > MAX_PREVIEW_SIZE_BYTES:
                    flash('Please provide an image file smaller than {} MB!'.format(MAX_PREVIEW_SIZE_MB), 'error')
                elif len(image_data) == 0:
                    flash('Please provide an image file!', 'error')
                else:
                    try:
                        # Generate a unique folder name
                        unique_folder = generate_unique_folder()
                        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_folder)

                        # Create the unique folder if it doesn't exist
                        os.makedirs(upload_path, exist_ok=True)

                        # Save the uploaded file to the unique folder
                        filename = secure_filename(image_file.filename)
                        image_path = os.path.join(upload_path, filename)
                        with open(image_path, 'wb') as file:
                            file.write(image_data)
                        
                        # Determine the file format
                        file_format = filename.split('.')[-1].lower()
                        
                        # Compress the image
                        if file_format == 'gif' or file_format == 'webp':
                            pass
                        else:
                            compressed_image_path = os.path.join(upload_path, filename)
                            with Image.open(image_path) as img:
                                img.save(compressed_image_path, quality=COMPRESSION_VALUE, optimize=True)  # You can adjust the quality value as needed

                        # Moderation is done in a separate thread to avoid blocking the main thread
                        try:
                            # If moderation is successful, continue processing
                            moderate_image(image_path)

                            # Get the size of the saved file
                            file_size_bytes = os.path.getsize(image_path)
                            file_size_mb = file_size_bytes / (1024 * 1024)

                            # Setup the promo link if it is provided
                            if promo_link is not None:
                                promo_link = promo_link.strip()
                                if not validators.url(promo_link):
                                    # Redirect to an error message if the promotional link provided is invalid
                                    redirect_to_error(promo_link)
                            
                            # Save the girl information to the database with the image URL pointing to the uploaded file
                            new_girl = Girl(name=girl_name, image_url=url_for('uploaded_file', folder=unique_folder, filename=filename), promo_link=promo_link)
                            db.session.add(new_girl)
                            db.session.commit()
                                    
                            # Save the girl's IP address and name in the UploadIP table
                            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                            upload_ip = UploadIP(ip_address=ip_address, girl_name=girl_name)
                            db.session.add(upload_ip)
                            db.session.commit()
                                    
                            # Flash a success message with links to the girl page and the created girl's page
                            girl_page_url = url_for('girl_page', girl_name=girl_name, _external=True)
                            flash(Markup('Girl added successfully! Check the girl page: <a href="{}">{}</a>'.format(girl_page_url, girl_page_url)), 'success')

                            # Redirect to the girl page
                            return redirect(girl_page_url)

                        except UnsafeImageError as e:
                            # Delete the entire folder associated with the rejected image (Do not use this!)
                            flash(str(e), 'error')
                            #shutil.rmtree(upload_path, ignore_errors=True)
                            return redirect(url_for('index'))

                    except Exception as e:
                        # Handle other exceptions if any
                        #flash('An error occurred during image processing. Please try again later.', 'error')

                        #return redirect(url_for('index')) with message
                        girl_page_url = url_for('girl_page', girl_name=girl_name, _external=True)
                        flash(Markup('Girl added successfully! Check the girl page: <a href="{}">{}</a>'.format(girl_page_url, girl_page_url)), 'success')
                        return redirect(girl_page_url)

    return redirect(url_for('index'))

# Where the uploaded images are stored
@app.route('/uploads/<folder>/<filename>', methods=['GET'])
def uploaded_file(folder, filename):
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    file_path = os.path.join(upload_path, filename)

    # Check if file exists
    if not os.path.exists(file_path):
        # If the file is not found, return a 404 image
        return send_from_directory(app.static_folder, 'img/errorimg-min.gif')

    # If the file is found, resend it normally
    return send_from_directory(upload_path, filename)

# Voting system
@app.route('/vote/<string:girl_name>', methods=['POST'])
def vote(girl_name):
    other_girl_name = request.form.get('other_girl_name')

    # Remove spaces from the girl's names and convert to lowercase
    girl_name = girl_name.replace(' ', '').lower()
    other_girl_name = other_girl_name.replace(' ', '').lower()

    voted_girl = Girl.query.filter(func.lower(Girl.name) == girl_name).first()
    other_girl = Girl.query.filter(func.lower(Girl.name) == other_girl_name).first()

    if voted_girl and other_girl:
        voted_girl.votes += 1
        db.session.commit()

        # Log the vote in the VoteLog model
        vote_log = VoteLog(voted_girl=voted_girl, other_girl=other_girl)
        db.session.add(vote_log)
        db.session.commit()

        # Register the voter's IP address in the VoterIP class
        voter_ip = VoterIP(ip_address=request.remote_addr, vote_log=vote_log)
        db.session.add(voter_ip)
        db.session.commit()

        flash('Vote submitted successfully!', 'success')
    else:
        flash('Error submitting vote. Please try again.', 'error')

    return redirect(url_for('index'))

# Girls own pages 
@app.route('/girl/<girl_name>', methods=['GET'])
def girl_page(girl_name):
    girl = Girl.query.filter_by(name=girl_name).first()
    if not girl:
        random_girls = Girl.query.order_by(func.random()).limit(30).all()
        return render_template('error.html', error="404 - Girl not found", random_girls=random_girls), 404

    leaderboard = Girl.query.order_by(Girl.votes.desc()).all()
    total_girls = len(leaderboard)
    position = leaderboard.index(girl) + 1 if girl in leaderboard else None

    for girl_leaderboard in leaderboard:
        girl_leaderboard.formatted_votes = format_votes(girl_leaderboard.votes)

    girl.formatted_votes = format_votes(girl.votes)  # Format votes for the specific girl

    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    
    # Get the girl's promo link and remove spaces from it 
    girl_promo_link = girl.promo_link
    if girl_promo_link:
        girl_promo_link = girl_promo_link.replace(' ', '')
    
    # Ads system
    all_ads = Ad.query.all()
    random_ad = random.choice(all_ads)
    ad_path = url_for('static', filename='ads/{}'.format(random_ad.filename))
    ad_link = random_ad.link if random_ad.link else '#' 

    return render_template('girl_page.html', girl=girl, position=position, leaderboard=leaderboard, total_girls=total_girls, random_girls=random_girls, girl_promo_link=girl_promo_link, ad_path=ad_path, ad_link=ad_link)

# Top 100 of the best girls 
@app.route('/top100', methods=['GET'])
def top100():
    # Fetch the top 100 girls from the database and order them by votes
    all_girls = Girl.query.order_by(Girl.votes.desc()).limit(100).all()

    # Calculate total votes
    total_votes = sum([girl.votes for girl in all_girls])

    # Format votes for each girl
    for girl in all_girls:
        girl.formatted_votes = format_votes(girl.votes)

    random_girls = Girl.query.order_by(func.random()).limit(30).all()

    # Ads system
    all_ads = Ad.query.all()
    random_ad = random.choice(all_ads)
    ad_path = url_for('static', filename='ads/{}'.format(random_ad.filename))
    ad_link = random_ad.link if random_ad.link else '#' 

    return render_template('top100.html', all_girls=all_girls, total_votes=total_votes, random_girls=random_girls, ad_path=ad_path, ad_link=ad_link)

# Admin - Delete votes/girl/girl_image
# curl -X DELETE http://localhost:5000/xadmin/delete_votes/girl_name
@app.route('/xadmin/delete_votes/<string:girl_name>', methods=['DELETE'])
def delete_votes(girl_name):
    # Remove spaces from the girl's name and convert to lowercase
    girl_name = girl_name.replace(' ', '').lower()

    # Find the girl by name
    girl = Girl.query.filter(func.lower(Girl.name) == girl_name).first()

    if girl:
        # Delete all associated votes from VoteLog
        VoteLog.query.filter((VoteLog.voted_girl_id == girl.id) | (VoteLog.other_girl_id == girl.id)).delete()
        db.session.commit()

        return jsonify({'message': f'Votes for {girl.name} deleted successfully!'}), 200
    else:
        return jsonify({'error': 'Girl not found'}), 404
    
# curl -X DELETE http://localhost:5000/xadmin/delete_image/folder/filename
@app.route('/xadmin/delete_image/<string:folder>/<string:filename>', methods=['DELETE'])
def delete_image(folder, filename):
    try:
        # Construct the path to the image
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)

        # Delete the image file
        os.remove(image_path)

        # Remove the empty folder if needed
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        if os.path.exists(folder_path) and not os.listdir(folder_path):
            os.rmdir(folder_path)

        return jsonify({'message': f'Image {filename} and folder {folder} deleted successfully!'}), 200
    except FileNotFoundError:
        return jsonify({'error': 'Image not found'}), 404
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    
# curl -X DELETE http://localhost:5000/xadmin/delete_girl/girl_name
@app.route('/xadmin/delete_girl/<string:girl_name>', methods=['DELETE'])
def delete_girl(girl_name):
    # Remove spaces from the girl's name and convert to lowercase
    girl_name = girl_name.replace(' ', '').lower()

    # Find the girl by name
    girl = Girl.query.filter(func.lower(Girl.name) == girl_name).first()

    if girl:
        try:
            # Delete all associated votes from VoteLog
            VoteLog.query.filter((VoteLog.voted_girl_id == girl.id) | (VoteLog.other_girl_id == girl.id)).delete()

            # Delete the girl from the database
            db.session.delete(girl)
            db.session.commit()

            return jsonify({'message': f'Girl {girl.name} and associated votes deleted successfully!'}), 200
        except Exception as e:
            return jsonify({'error': f'An error occurred while deleting the girl: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Girl not found'}), 404

# curl -X DELETE http://localhost:5000/xadmin/purge_girl/girl_name
@app.route('/xadmin/purge_girl/<string:girl_name>', methods=['DELETE'])
def purge_girl(girl_name):
    try:
        # Remove spaces from the girl's name and convert to lowercase
        girl_name = girl_name.replace(' ', '').lower()

        # Find the girl by name
        girl = Girl.query.filter(func.lower(Girl.name) == girl_name).first()

        if girl:
            # Delete all associated votes from VoteLog
            VoteLog.query.filter((VoteLog.voted_girl_id == girl.id) | (VoteLog.other_girl_id == girl.id)).delete()

            # Delete the girl's images from the file system
            # Extract folder and filename information from the image_url
            image_url_parts = girl.image_url.split('/')
            folder = image_url_parts[-2]  # Assuming the folder is the second-to-last part
            filename = image_url_parts[-1]

            # Retrieve image information for response
            deleted_images = [{'folder': folder, 'filename': filename}]

            # Retrieve and delete the girl's images from the file system
            for image_info in deleted_images:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_info['folder'], image_info['filename'])
                try:
                    os.remove(image_path)
                except FileNotFoundError:
                    pass  # Handle the case where the file is not found (optional)

                # Optional: You can also remove the empty folder if needed
                folder_path = os.path.join(app.config['UPLOAD_FOLDER'], image_info['folder'])
                if os.path.exists(folder_path) and not os.listdir(folder_path):
                    os.rmdir(folder_path)

            # Delete the girl from the database
            db.session.delete(girl)
            db.session.commit()

            return jsonify({'message': f'Girl {girl.name}, associated votes, and images deleted successfully!'}), 200
        else:
            return jsonify({'error': 'Girl not found'}), 404
    except FileNotFoundError:
        return jsonify({'error': 'Image not found'}), 404
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# curl -X DELETE http://localhost:5000/xadmin/clean_images Note: This will delete all images and folders not present in the database
@app.route('/xadmin/clean_images', methods=['DELETE'])
def clean_images():
    try:
        # Get all girl names from the database
        db_girl_names = set([girl.image_url.split('/')[2].lower() for girl in Girl.query.all()])

        # Get all folders in the UPLOAD_FOLDER directory
        upload_folder = app.config['UPLOAD_FOLDER']
        all_folders = [folder for folder in os.listdir(upload_folder) if os.path.isdir(os.path.join(upload_folder, folder))]

        # Find folders to delete (not in the database)
        folders_to_delete = [folder for folder in all_folders if folder.lower() not in db_girl_names]

        # Delete images and folders not present in the database
        for folder_to_delete in folders_to_delete:
            folder_path = os.path.join(upload_folder, folder_to_delete)

            # Delete all images in the folder
            for filename in os.listdir(folder_path):
                image_path = os.path.join(folder_path, filename)
                os.remove(image_path)

            # Delete the folder itself
            os.rmdir(folder_path)

        return jsonify({'message': 'Unused images and folders cleaned successfully!'}), 200
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    
#Static pages    
@app.route('/tos', methods=['GET'])
def about():
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    # Ads system
    all_ads = Ad.query.all()
    random_ad = random.choice(all_ads)
    ad_path = url_for('static', filename='ads/{}'.format(random_ad.filename))
    ad_link = random_ad.link if random_ad.link else '#' 
    return render_template('tos.html', random_girls=random_girls, ad_path=ad_path, ad_link=ad_link)

@app.route('/privacy', methods=['GET'])
def privacy():
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    # Ads system
    all_ads = Ad.query.all()
    random_ad = random.choice(all_ads)
    ad_path = url_for('static', filename='ads/{}'.format(random_ad.filename))
    ad_link = random_ad.link if random_ad.link else '#' 
    return render_template('privacy.html', random_girls=random_girls, ad_path=ad_path, ad_link=ad_link)

@app.route('/verify', methods=['GET'])
def verify():
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    # Ads system
    all_ads = Ad.query.all()
    random_ad = random.choice(all_ads)
    ad_path = url_for('static', filename='ads/{}'.format(random_ad.filename))
    ad_link = random_ad.link if random_ad.link else '#' 
    return render_template('verify.html', random_girls=random_girls, ad_path=ad_path, ad_link=ad_link)

@app.route('/api', methods=['GET'])
def api():
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    # Ads system
    all_ads = Ad.query.all()
    random_ad = random.choice(all_ads)
    ad_path = url_for('static', filename='ads/{}'.format(random_ad.filename))
    ad_link = random_ad.link if random_ad.link else '#' 
    return render_template('api.html', random_girls=random_girls, ad_path=ad_path, ad_link=ad_link)

@app.route('/currentlyonciawatchlist', methods=['GET'])
def currentlyonciawatchlist():
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    # Ads system
    all_ads = Ad.query.all()
    random_ad = random.choice(all_ads)
    ad_path = url_for('static', filename='ads/{}'.format(random_ad.filename))
    ad_link = random_ad.link if random_ad.link else '#' 
    return render_template('currentlyonciawatchlist.html', random_girls=random_girls, ad_path=ad_path, ad_link=ad_link)

# API routes 
# Get all girls
@app.route('/api/v1/girl', methods=['GET'])
def api_all_girls():
    # Fetch all the girls from the database
    all_girls = Girl.query.all()
    total_votes = sum([girl.votes for girl in all_girls])

    return jsonify({
        'girls': [
            {
                'name': girl.name,
                'status': girl.status,
                'image_url': girl.image_url,
                'votes': girl.votes,
                'added_date': girl.added_date.strftime('%Y-%m-%d')
            } for girl in all_girls
        ],
        'total_votes': total_votes
    })

# Get Info about a girl
@app.route('/api/v1/girl/<girl_name>', methods=['GET'])
def api_girl(girl_name):
    girl = Girl.query.filter_by(name=girl_name).first()
    if not girl:
        return jsonify({'error': 'Girl not found'}), 404

    return jsonify({
        'name': girl.name,
        'image_url': girl.image_url,
        'votes': girl.votes,
        'status': girl.status,
        'added_date': girl.added_date.strftime('%Y-%m-%d')
    })

# Get Top 100
@app.route('/api/v1/top100', methods=['GET'])
def api_leaderboard():
    # Fetch the top 100 girls from the database and order them by votes
    leaderboard = Girl.query.order_by(Girl.votes.desc()).limit(100).all()

    # Calculate total votes
    total_votes = sum([girl.votes for girl in leaderboard])

    return jsonify({
        'leaderboard': [
            {
                'name': girl.name,
                'votes': girl.votes,
                'status': girl.status,
                'added_date': girl.added_date.strftime('%Y-%m-%d')
            } for girl in leaderboard
        ],
        'total_votes': total_votes
    })

# Get Latest votes
@app.route('/api/v1/latestvotes', methods=['GET'])
def api_latest_votes():
    # Fetch the 100 latest votes from the database and order them by vote_date
    latest_votes = VoteLog.query.order_by(VoteLog.voted_date.desc()).limit(100).all()

    # Prepare the response data
    response_data = {
        'latest_votes': [
            {
                'voted_girl': vote.voted_girl.name,
                'vote_date': vote.voted_date.strftime('%Y-%m-%d %H:%M:%S'),
            } for vote in latest_votes
        ]
    }

    return jsonify(response_data)

# Get latest Added Girls
@app.route('/api/v1/latestgirls', methods=['GET'])
def latest_girls():
    # Fetch the top 100 girls from the database and order them by votes
    latest_girls = Girl.query.order_by(Girl.added_date.desc()).limit(100).all()

    # Calculate total votes
    total_votes = sum([girl.votes for girl in latest_girls])

    return jsonify({
        'latest_girls': [
            {
                'name': girl.name,
                'votes': girl.votes,
                'status': girl.status,
                'added_date': girl.added_date.strftime('%Y-%m-%d')
            } for girl in latest_girls
        ],
        'total_votes': total_votes
    })

# Get only verified girls
@app.route('/api/v1/onlyverified', methods=['GET'])
def api_verified_girls():
    # Fetch all the girls from the database
    all_girls = Girl.query.all()
    total_votes = sum([girl.votes for girl in all_girls])

    # Filter only verified girls
    verified_girls = Girl.query.filter_by(status='verified').all()

    return jsonify({
      'verified_girls': [
            {
                'name': girl.name,
                'image_url': girl.image_url,
                'votes': girl.votes,
                        'added_date': girl.added_date.strftime('%Y-%m-%d')
            } for girl in verified_girls
                                                ],
        'total_votes': total_votes
    })

#Root favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path,'static'), 'img/favicon.ico', mimetype='image/vnd.microsoft.icon')    

#errors handlers
@app.errorhandler(404)
def not_found_error(error):
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    return render_template('error.html', error="404 - Page not found", random_girls=random_girls), 404

@app.errorhandler(403)
def forbidden_error(error):
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    return render_template('error.html', error="403 - Forbidden", random_girls=random_girls), 403

@app.errorhandler(405)
def not_found_error(error):
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    return render_template('error.html', error="405 - Method Not Allowed", random_girls=random_girls), 405

@app.errorhandler(500)
def internal_server_error(error):
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    return render_template('error.html', error="500 - Internal Server Error", random_girls=random_girls), 500

@app.errorhandler(502)
def bad_gateway_error(error):
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    return render_template('error.html', error="502 - Bad Gateway", random_girls=random_girls), 502

@app.errorhandler(503)
def service_unavailable_error(error):
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    return render_template('error.html', error="503 - Service Unavailable", random_girls=random_girls), 503

@app.errorhandler(504)
def gateway_timeout_error(error):
    random_girls = Girl.query.order_by(func.random()).limit(30).all()
    return render_template('error.html', error="504 - Gateway Timeout", random_girls=random_girls), 504

# Run the app in debug mode and it's just works 
#if __name__ == '__main__':
#    app.run(debug=False, host='0.0.0.0', port=5000)