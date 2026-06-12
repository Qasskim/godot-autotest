from appium import webdriver
from appium.options.android import UiAutomator2Options

capabilities = dict(
    platformName='Android',
    automationName='uiautomator2',
    deviceName='emulator-5554',
    appPackage='com.example.rhythmgame_new',
    appActivity='com.godot.game.GodotApp',
    noReset=False,
    autoGrantPermissions=True,
)

appium_server_url = 'http://localhost:4723'


def create_driver() -> webdriver.Remote:
    return webdriver.Remote(appium_server_url, options=UiAutomator2Options().load_capabilities(capabilities))
