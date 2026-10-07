from jinja2 import Environment, FileSystemLoader
import os, traceback, sys

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
env.globals['url_for'] = lambda endpoint, filename=None, **kwargs: (f"/static/{filename}" if filename else f"/{endpoint}")
env.globals['session'] = {'user_id': 1, 'user_name': 'Demo User', 'user_email': 'demo@example.com'}
env.globals['get_flashed_messages'] = lambda with_categories=False: []
env.globals.update({
    'predicted': 'Moderate',
    'confidence': 0.84,
    'risk_result': {'risk_level': 'Moderate', 'risk_score': 12, 'factors': ['Age: 45 years', 'Blood Sugar: 110 mg/dL'], 'explanation': 'Project-defined', 'recommendation': 'Discuss with an eye-care professional.'},
    'filename': 'test.png',
    'age': 45,
    'blood_sugar': 95,
    'blood_pressure': '120/80',
    'language': 'en',
    'image_url': '/static/uploads/test.png',
    'gradcam_url': '/static/gradcam/test_gradcam.png',
    'probabilities': [0.12, 0.41, 0.14, 0.28, 0.05],
    'class_names': ['Mild', 'Moderate', 'No_DR', 'Proliferate_DR', 'Severe'],
    'audio_url': None,
})

files = ['base.html', 'landing.html', 'screening.html', 'about.html', 'how_it_works.html', 'profile.html', 'result.html', 'history.html']
required_strings = {
    'landing.html': ['AI-POWERED EYE SCREENING', 'Early Eye Screening', 'Start Screening'],
    'screening.html': ['Upload a retinal fundus image', 'Analyze Retina', 'Blood Sugar'],
    'result.html': ['Screening Result', 'Model Visual Explanation', 'All Class Probabilities'],
}

ok = True
for name in files:
    try:
        tmpl = env.get_template(name)
        rendered = tmpl.render()
        for text in required_strings.get(name, []):
            if text not in rendered:
                raise AssertionError(f"Missing expected text '{text}' in {name}")
        print('OK', name)
    except Exception as e:
        ok = False
        print('ERR', name, e)
        traceback.print_exc()

sys.exit(0 if ok else 2)
