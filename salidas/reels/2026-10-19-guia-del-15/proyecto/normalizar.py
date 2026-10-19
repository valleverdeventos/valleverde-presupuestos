# Blanquea el papel de una ilustración (para fundirla con la hoja vía multiply) y genera su versión lápiz
import sys
from PIL import Image, ImageOps, ImageFilter
import numpy as np
src, nombre = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB'); a = np.asarray(im).astype(float)
bg = np.asarray(im.filter(ImageFilter.GaussianBlur(60))).astype(float)
corner = np.median(a[:120, :120].reshape(-1, 3), axis=0)
paper = np.where(bg.mean(-1, keepdims=True) > corner.mean() * 0.93, bg, corner)
n = np.clip(a / paper * 255 * 1.02, 0, 255).astype('uint8')
Image.fromarray(n).save(f'assets/img/{nombre}-n.jpg', quality=93)
g = np.asarray(ImageOps.grayscale(Image.fromarray(n))).astype(float) / 255
Image.fromarray((np.repeat((g ** 1.5)[..., None], 3, -1) * 255).astype('uint8')).save(f'assets/img/{nombre}-n-lapiz.jpg', quality=93)
print(nombre, im.size)
