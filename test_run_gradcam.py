from pathlib import Path
BASE = Path(r"C:\Users\user\OneDrive\Desktop\RetinaScan")
UP = BASE / 'static' / 'uploads'
UP.mkdir(parents=True, exist_ok=True)
# find an existing image
imgs = list(UP.glob('*.jpg')) + list(UP.glob('*.jpeg')) + list(UP.glob('*.png'))
if imgs:
    sample = imgs[0]
else:
    # create a dummy RGB image
    from PIL import Image
    sample = UP / 'test_sample.jpg'
    img = Image.new('RGB', (512,512), (120,120,120))
    img.save(sample)
print('Using sample:', sample)

import app
from utils import prediction
from utils import gradcam

image_path = str(sample)
res = prediction.predict_from_path(app.MODEL, image_path)
print('PRED:', res)
idx = prediction.CLASS_NAMES.index(res['predicted_class'])

outdir = BASE / 'static' / 'gradcam'
outdir.mkdir(parents=True, exist_ok=True)
out = outdir / f'gradcam_test_{sample.stem}.jpg'
try:
    p = gradcam.generate_gradcam(app.MODEL, image_path, idx, str(out))
    print('Grad-CAM saved to', p)
except Exception as e:
    print('Grad-CAM ERROR:', type(e).__name__, e)
