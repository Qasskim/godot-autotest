from appium import webdriver
from appium.options.android import UiAutomator2Options

capabilities = dict(
    platformName='Android',
    automationName='uiautomator2',
    deviceName='R3CR501XHAJ',
    appPackage='com.example.rhythmgame_new',
    appActivity='com.godot.game.GodotApp',
    noReset=True,           # main.py에서 직접 adb install 처리하므로 재설치 방지
    autoGrantPermissions=True,
    newCommandTimeout=0,
)

appium_server_url = 'http://localhost:4723'


def create_driver() -> webdriver.Remote:
    return webdriver.Remote(appium_server_url, options=UiAutomator2Options().load_capabilities(capabilities))
