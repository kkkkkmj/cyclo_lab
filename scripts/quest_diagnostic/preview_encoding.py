"""Preview only: preserve native camera pixels, independent of observations/recording."""
import io
import time
from PIL import Image


def encode_native_preview(cameras):
    started = time.perf_counter()
    atlas = Image.new('RGB', (768, 256))
    for i, camera in enumerate(cameras):
        if camera.size != (244, 244) or camera.mode != 'RGB':
            raise ValueError('Native preview expects three RGB 244x244 camera frames')
        atlas.paste(camera, (i*256+6, 6))
    if len(cameras) != 3:
        raise ValueError('Expected HEAD / LEFT WRIST / RIGHT WRIST')
    output = io.BytesIO()
    atlas.save(output, format='JPEG', quality=90, subsampling=0)
    data = output.getvalue()
    return data, dict(format='native-244-v1', size=[768,256], jpeg_quality=90,
                      jpeg_subsampling='4:4:4', resized=False, bytes=len(data),
                      encode_ms=(time.perf_counter()-started)*1000)
