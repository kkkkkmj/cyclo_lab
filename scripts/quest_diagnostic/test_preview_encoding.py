import io
import unittest
from PIL import Image,JpegImagePlugin
from preview_encoding import encode_native_preview

class NativePreviewTests(unittest.TestCase):
    def test_native_full_tiles_and_compression(self):
        cameras=[Image.new('RGB',(244,244),c) for c in [(220,30,50),(30,220,50),(50,30,220)]]
        data,meta=encode_native_preview(cameras)
        image=Image.open(io.BytesIO(data))
        self.assertEqual(image.size,(768,256))
        self.assertEqual(JpegImagePlugin.get_sampling(image),0)
        self.assertFalse(meta['resized']);self.assertEqual(meta['jpeg_quality'],90)
        for i,camera in enumerate(cameras):
            for x,y in [(10,10),(128,128),(240,240)]:
                actual=image.getpixel((i*256+x,y))
                self.assertLessEqual(max(abs(a-b) for a,b in zip(actual,camera.getpixel((0,0)))),3)
    def test_unexpected_source_size_fails_explicitly(self):
        with self.assertRaises(ValueError):encode_native_preview([Image.new('RGB',(300,300))]*3)

if __name__=='__main__':unittest.main()
