import os

from flask import Flask, flash, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

from utils import gradcam, image_quality, pdf_report, prediction, risk_assessment, voice
from utils.auth import create_user, get_current_user, get_user_by_email, login_required, login_user, logout_user, verify_password
from utils.database import init_db, get_db_connection
from utils.history import create_screening, get_recent_screenings, get_screenings_for_user, get_screening_by_screening_id


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
MODEL_PATH = os.path.join(BASE_DIR, 'model', 'best_model_retinascan_v5.keras')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'change-me-for-production'

init_db()


def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


MODEL = None
try:
	MODEL = prediction.load_model(MODEL_PATH)
except Exception as e:
	print('Model load error:', e)


@app.route('/')
def landing():
	if get_current_user():
		return redirect(url_for('dashboard'))
	return render_template('landing.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
	if get_current_user():
		return redirect(url_for('dashboard'))

	if request.method == 'POST':
		email = (request.form.get('email') or '').strip().lower()
		password = request.form.get('password') or ''
		user = get_user_by_email(email)
		if not user or not verify_password(user['password_hash'], password):
			flash('Invalid email or password.', 'danger')
			return render_template('login.html', email=email)
		login_user(user)
		flash('Login successful.', 'success')
		return redirect(url_for('dashboard'))
	return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
	if get_current_user():
		return redirect(url_for('dashboard'))

	if request.method == 'POST':
		name = request.form.get('name', '').strip()
		email = (request.form.get('email') or '').strip().lower()
		password = request.form.get('password') or ''
		confirm_password = request.form.get('confirm_password') or ''
		if password != confirm_password:
			flash('Passwords do not match.', 'danger')
			return render_template('signup.html', name=name, email=email)
		try:
			user = create_user(name=name, email=email, password=password)
		except ValueError as exc:
			flash(str(exc), 'danger')
			return render_template('signup.html', name=name, email=email)
		login_user(user)
		flash('Account created successfully.', 'success')
		return redirect(url_for('dashboard'))
	return render_template('signup.html')


@app.route('/logout')
def logout():
	logout_user()
	flash('You have been logged out.', 'info')
	return redirect(url_for('landing'))


@app.route('/index')
def index():
	if get_current_user():
		return redirect(url_for('screening'))
	return redirect(url_for('landing'))


@app.route('/dashboard')
@login_required
def dashboard():
	user = get_current_user()
	recent = get_recent_screenings(user['id'], limit=3)
	# compute stats
	conn = get_db_connection()
	cur = conn.cursor()
	cur.execute('SELECT COUNT(*) FROM screenings WHERE user_id = ?', (user['id'],))
	total = cur.fetchone()[0]
	cur.execute('SELECT COUNT(*) FROM screenings WHERE user_id = ? AND risk_level = ?', (user['id'], 'High'))
	high = cur.fetchone()[0]
	cur.execute('SELECT COUNT(*) FROM screenings WHERE user_id = ? AND risk_level = ?', (user['id'], 'Moderate'))
	moderate = cur.fetchone()[0]
	cur.execute('SELECT COUNT(*) FROM screenings WHERE user_id = ? AND risk_level = ?', (user['id'], 'Low'))
	low = cur.fetchone()[0]
	conn.close()
	stats = {'total': total, 'high': high, 'moderate': moderate, 'low': low}
	return render_template('dashboard.html', recent=recent, stats=stats)


@app.route('/screening', methods=['GET', 'POST'])
@login_required
def screening():
	if request.method == 'POST':
		# Read patient info and language from the form
		age_str = (request.form.get('age') or '').strip()
		blood_sugar_str = (request.form.get('blood_sugar') or '').strip()
		blood_pressure_str = (request.form.get('blood_pressure') or '').strip()
		language = (request.form.get('language') or 'en').lower()

		# Server-side validation
		try:
			age = int(age_str)
		except Exception:
			flash('Age must be an integer')
			return render_template('screening.html', age=age_str, blood_sugar=blood_sugar_str, blood_pressure=blood_pressure_str, language=language)

		if age <= 0 or age > 130:
			flash('Age must be a reasonable positive number (1-130)')
			return render_template('screening.html', age=age_str, blood_sugar=blood_sugar_str, blood_pressure=blood_pressure_str, language=language)

		try:
			blood_sugar = float(blood_sugar_str)
		except Exception:
			flash('Blood Sugar must be a number')
			return render_template('screening.html', age=age_str, blood_sugar=blood_sugar_str, blood_pressure=blood_pressure_str, language=language)

		if blood_sugar <= 0:
			flash('Blood Sugar must be a positive number')
			return render_template('screening.html', age=age_str, blood_sugar=blood_sugar_str, blood_pressure=blood_pressure_str, language=language)

		# Blood pressure expected format systolic/diastolic
		import re
		bp_match = re.match(r"^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$", blood_pressure_str)
		if not bp_match:
			flash('Blood Pressure must use the format systolic/diastolic, e.g. 120/80')
			return render_template('index.html', age=age_str, blood_sugar=blood_sugar_str, blood_pressure=blood_pressure_str, language=language)

		if 'file' not in request.files:
			flash('No file part')
			return redirect(request.url)
		file = request.files['file']
		if file.filename == '':
			flash('No selected file')
			return redirect(request.url)
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
			save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
			file.save(save_path)
			# Mark this redirect as the initial save action so we create a screening record once
			return redirect(url_for('result', filename=filename, age=age_str, blood_sugar=blood_sugar_str, blood_pressure=blood_pressure_str, language=language, saved=1))
		flash('Invalid file type')
		return redirect(request.url)
	return render_template('screening.html')


@app.route('/result', methods=['GET', 'POST'])
@login_required
def result():
	filename = request.args.get('filename') or request.form.get('filename')
	if not filename:
		flash('No image provided')
		return redirect(url_for('screening'))

	image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
	if not os.path.exists(image_path):
		flash('Uploaded file not found')
		return redirect(url_for('screening'))

	language = (request.args.get('language') or request.form.get('language') or 'en').lower()
	age = request.args.get('age') or request.form.get('age')
	blood_sugar = request.args.get('blood_sugar') or request.form.get('blood_sugar')
	blood_pressure = request.args.get('blood_pressure') or request.form.get('blood_pressure')
	if language not in {'en', 'ta'}:
		language = 'en'

	quality_check = image_quality.validate_image_quality(image_path)
	if not quality_check.get('is_valid', False):
		flash(quality_check.get('reason', 'The uploaded image does not meet the basic quality check. Please upload a clearer retinal image.'))
		return render_template(
			'result.html',
			image_url=url_for('static', filename=f'uploads/{filename}'),
			filename=filename,
			language=language,
			age=age,
			blood_sugar=blood_sugar,
			blood_pressure=blood_pressure,
			quality_warning=quality_check.get('reason', 'Please upload a clearer retinal image.')
		)

	if MODEL is None:
		flash('Model not loaded; check server logs')
		return render_template('result.html', image_url=url_for('static', filename=f'uploads/{filename}'), filename=filename, language=language, age=age, blood_sugar=blood_sugar, blood_pressure=blood_pressure)

	try:
		res = prediction.predict_from_path(MODEL, image_path)
	except Exception as e:
		flash(f'Prediction error: {e}')
		return render_template('result.html', image_url=url_for('static', filename=f'uploads/{filename}'), filename=filename, language=language, age=age, blood_sugar=blood_sugar, blood_pressure=blood_pressure)

	gradcam_url = None
	gradcam_path = None
	try:
		predicted_idx = prediction.CLASS_NAMES.index(res['predicted_class'])
		grad_dir = os.path.join(BASE_DIR, 'static', 'gradcam')
		os.makedirs(grad_dir, exist_ok=True)
		grad_filename = f"gradcam_{os.path.splitext(filename)[0]}.jpg"
		gradcam_path = os.path.join(grad_dir, grad_filename)
		gradcam.generate_gradcam(MODEL, image_path, predicted_idx, gradcam_path)
		gradcam_url = url_for('static', filename=f'gradcam/{grad_filename}')
	except Exception as e:
		flash(f'Grad-CAM generation failed: {e}')

	audio_url = None
	audio_path = None
	try:
		voice_dir = os.path.join(BASE_DIR, 'static', 'audio')
		audio_path = voice.generate_voice_report(
			predicted_class=res['predicted_class'],
			confidence=res['confidence'],
			language=language,
			output_dir=voice_dir,
			filename_prefix=os.path.splitext(filename)[0]
		)
		audio_url = url_for('static', filename=f'audio/{os.path.basename(audio_path)}')
	except Exception as e:
		import traceback
		print(f"[voice] Voice report generation failed for {filename} ({language}): {e}")
		traceback.print_exc()
		flash(f'Voice report generation failed: {e}')

	risk_result = risk_assessment.calculate_risk_indication(
		predicted_class=res['predicted_class'],
		age=age,
		blood_sugar=blood_sugar,
		blood_pressure=blood_pressure
	)


	# Save screening if this request marked as initial save
	try:
		if request.args.get('saved') == '1' and get_current_user():
			user = get_current_user()
			created = create_screening(
				user_id=user['id'],
				patient_age=int(age) if age else None,
				blood_sugar=float(blood_sugar) if blood_sugar else None,
				blood_pressure=blood_pressure,
				predicted_class=res['predicted_class'],
				confidence=res['confidence'],
				probabilities=res['probabilities'],
				risk_level=risk_result['risk_level'],
				risk_score=risk_result['risk_score'],
				image_filename=filename,
				gradcam_filename=os.path.basename(gradcam_path) if gradcam_path else None,
				audio_filename=os.path.basename(audio_path) if audio_path else None,
				voice_language=language,
			)
			screening_id = created.get('screening_id')
			created_at = created.get('created_at')
		else:
			screening_id = None
			created_at = None
	except Exception as e:
		# Do not break the result view if saving fails; log and continue
			print('Screening save failed:', e)
			screening_id = None
			created_at = None

	return render_template('result.html',
					image_url=url_for('static', filename=f'uploads/{filename}'),
					filename=filename,
				screening_id=screening_id,
				created_at=created_at,
					predicted=res['predicted_class'],
					confidence=res['confidence'],
					probabilities=res['probabilities'],
					class_names=prediction.CLASS_NAMES,
					gradcam_url=gradcam_url,
					gradcam_path=gradcam_path,
					audio_url=audio_url,
					risk_result=risk_result,
					language=language,
					age=age,
					blood_sugar=blood_sugar,
					blood_pressure=blood_pressure,
					quality_warning=None)


@app.route('/download_report')
@login_required
def download_report():
	filename = request.args.get('filename')
	if not filename:
		flash('No report available')
		return redirect(url_for('screening'))

	image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
	if not os.path.exists(image_path):
		flash('Uploaded file not found')
		return redirect(url_for('screening'))

	language = (request.args.get('language') or 'en').lower()
	if language not in {'en', 'ta'}:
		language = 'en'

	age = request.args.get('age')
	blood_sugar = request.args.get('blood_sugar')
	blood_pressure = request.args.get('blood_pressure')

	quality_check = image_quality.validate_image_quality(image_path)
	if not quality_check.get('is_valid', False):
		flash('The uploaded image does not meet the basic quality check. Please upload a clearer retinal image.')
		return redirect(url_for('result', filename=filename, age=age, blood_sugar=blood_sugar, blood_pressure=blood_pressure, language=language))

	if MODEL is None:
		flash('Model not loaded; check server logs')
		return redirect(url_for('result', filename=filename, age=age, blood_sugar=blood_sugar, blood_pressure=blood_pressure, language=language))

	try:
		res = prediction.predict_from_path(MODEL, image_path)
	except Exception as e:
		flash(f'Prediction error: {e}')
		return redirect(url_for('result', filename=filename, age=age, blood_sugar=blood_sugar, blood_pressure=blood_pressure, language=language))

	gradcam_path = None
	try:
		predicted_idx = prediction.CLASS_NAMES.index(res['predicted_class'])
		grad_dir = os.path.join(BASE_DIR, 'static', 'gradcam')
		os.makedirs(grad_dir, exist_ok=True)
		grad_filename = f"gradcam_{os.path.splitext(filename)[0]}.jpg"
		gradcam_path = os.path.join(grad_dir, grad_filename)
		if not os.path.exists(gradcam_path):
			gradcam.generate_gradcam(MODEL, image_path, predicted_idx, gradcam_path)
	except Exception:
		gradcam_path = None

	risk_result = risk_assessment.calculate_risk_indication(
		predicted_class=res['predicted_class'],
		age=age,
		blood_sugar=blood_sugar,
		blood_pressure=blood_pressure
	)

	report_dir = os.path.join(BASE_DIR, 'static', 'reports')
	pdf_path = pdf_report.generate_screening_pdf(
		output_dir=report_dir,
		filename=filename,
		predicted_class=res['predicted_class'],
		confidence=res['confidence'],
		probabilities=res['probabilities'],
		risk_result=risk_result,
		age=age,
		blood_sugar=blood_sugar,
		blood_pressure=blood_pressure,
		language=language,
		original_image_path=image_path,
		gradcam_image_path=gradcam_path,
	)

	return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path))


@app.route('/history')
@login_required
def history():
	user = get_current_user()
	q = request.args.get('q')
	risk = request.args.get('risk', 'All')
	stage = request.args.get('stage', 'All')
	order = request.args.get('order', 'newest')
	records = get_screenings_for_user(user['id'], q=q, risk=risk, stage=stage, order=order)
	return render_template('history.html', records=records, q=q or '', risk=risk, stage=stage, order=order)


@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/how-it-works')
def how_it_works():
	return render_template('how_it_works.html')

@app.route('/eye-health')
def eye_health():
	return render_template('eye_health.html')

@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    created_at = user.get('created_at') if user else None

    if created_at:
        created_at = str(created_at)

        # Handle: 2026-10-07 19:30:00
        try:
            date_part, time_part = created_at.split(' ', 1)

            year, month, day = date_part.split('-')
            hour, minute = time_part.split(':')[:2]

            hour = int(hour)

            period = 'AM' if hour < 12 else 'PM'
            display_hour = hour % 12

            if display_hour == 0:
                display_hour = 12

            created_at = (
                f"{day}/{month}/{year}, "
                f"{display_hour}:{minute} {period}"
            )

        except (ValueError, AttributeError):
            # If the stored value has an unexpected format,
            # show the original value instead of causing an error.
            pass

    return render_template(
        'profile.html',
        user_created_at=created_at
    )
@app.route('/history/<screening_id>')
@login_required
def history_view(screening_id):
	user = get_current_user()
	rec = get_screening_by_screening_id(user['id'], screening_id)
	if not rec:
		return render_template('404.html'), 404
	# Build paths for images
	image_url = url_for('static', filename=f'uploads/{rec.get("image_filename")}') if rec.get('image_filename') else None
	gradcam_url = url_for('static', filename=f'gradcam/{rec.get("gradcam_filename")}') if rec.get('gradcam_filename') else None
	audio_url = url_for('static', filename=f'audio/{rec.get("audio_filename")}') if rec.get('audio_filename') else None

	probabilities = [
		rec.get('mild_probability') or 0.0,
		rec.get('moderate_probability') or 0.0,
		rec.get('no_dr_probability') or 0.0,
		rec.get('proliferate_dr_probability') or 0.0,
		rec.get('severe_probability') or 0.0,
	]

	return render_template('result.html',
		image_url=image_url,
		filename=rec.get('image_filename'),
		screening_id=rec.get('screening_id'),
		created_at=rec.get('created_at'),
		predicted=rec.get('predicted_class'),
		confidence=rec.get('confidence'),
		probabilities=probabilities,
		class_names=prediction.CLASS_NAMES,
		gradcam_url=gradcam_url,
		gradcam_path=None,
		audio_url=audio_url,
		risk_result={
			'risk_level': rec.get('risk_level'),
			'risk_score': rec.get('risk_score'),
			'factors': [],
			'explanation': 'Historical screening note.',
			'recommendation': risk_assessment.get_follow_up_recommendation(rec.get('risk_level')),
		},
		language=rec.get('voice_language') or 'en',
		age=rec.get('patient_age'),
		blood_sugar=rec.get('blood_sugar'),
		blood_pressure=rec.get('blood_pressure'),
		quality_warning=None)


@app.route('/history/<screening_id>/download')
@login_required
def history_download(screening_id):
	user = get_current_user()
	rec = get_screening_by_screening_id(user['id'], screening_id)
	if not rec:
		return render_template('404.html'), 404

	image_path = os.path.join(BASE_DIR, 'static', 'uploads', rec.get('image_filename')) if rec.get('image_filename') else None
	gradcam_path = os.path.join(BASE_DIR, 'static', 'gradcam', rec.get('gradcam_filename')) if rec.get('gradcam_filename') else None

	report_dir = os.path.join(BASE_DIR, 'static', 'reports')
	pdf_path = pdf_report.generate_screening_pdf(
		output_dir=report_dir,
		filename=rec.get('image_filename') or f"{rec.get('screening_id')}.png",
		predicted_class=rec.get('predicted_class'),
		confidence=rec.get('confidence'),
		probabilities=[rec.get('mild_probability') or 0, rec.get('moderate_probability') or 0, rec.get('no_dr_probability') or 0, rec.get('proliferate_dr_probability') or 0, rec.get('severe_probability') or 0],
		risk_result={
			'risk_level': rec.get('risk_level'),
			'risk_score': rec.get('risk_score'),
			'factors': [],
			'explanation': 'Historical screening note.',
			'recommendation': risk_assessment.get_follow_up_recommendation(rec.get('risk_level')),
		},
		age=rec.get('patient_age'),
		blood_sugar=rec.get('blood_sugar'),
		blood_pressure=rec.get('blood_pressure'),
		language=rec.get('voice_language') or 'en',
		original_image_path=image_path,
		gradcam_image_path=gradcam_path,
	)

	return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path))
if __name__ == '__main__':
	app.run(debug=True)