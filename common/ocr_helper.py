import pytesseract
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def get_screen_text(driver) -> str:
    png = driver.get_screenshot_as_png()
    img = Image.open(io.BytesIO(png))
    return pytesseract.image_to_string(img, lang='eng+kor')


def get_region_text(driver, left: float, top: float, w: float, h: float) -> str:
    """화면 비율(0.0~1.0)로 영역 지정해서 OCR"""
    png = driver.get_screenshot_as_png()
    img = Image.open(io.BytesIO(png))
    sw, sh = img.size
    box = (int(left * sw), int(top * sh), int((left + w) * sw), int((top + h) * sh))
    return pytesseract.image_to_string(img.crop(box), lang='eng+kor').strip()


def tap(driver, x_ratio: float, y_ratio: float) -> None:
    """화면 비율 좌표로 탭"""
    size = driver.get_window_size()
    driver.tap([(int(size['width'] * x_ratio), int(size['height'] * y_ratio))])
