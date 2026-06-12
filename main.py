import time
import unittest
from common.driver_setup import create_driver, capabilities
from common.result_writer import init_workbook
from tests import test_autoplay, test_result_screen, test_navigation


class RhythmGameTest(unittest.TestCase):

    def setUp(self) -> None:
        self.driver = create_driver()
        self.wb, self.ws = init_workbook(capabilities['deviceName'])

    def test_rhythm_game(self) -> None:
        case_num = 0

        # 오토플레이 테스트 (앱 실행 ~ 결과 화면 진입까지)
        case_num = test_autoplay.run(self.driver, self.wb, self.ws, case_num)

        # 결과 화면 검증 (결과 화면이 열린 상태에서 실행)
        case_num = test_result_screen.run(self.driver, self.wb, self.ws, case_num)

        # 화면 전환 검증 (결과 → 곡선택 → 설정)
        case_num = test_navigation.run(self.driver, self.wb, self.ws, case_num)

    def tearDown(self) -> None:
        if self.driver:
            self.driver.quit()


if __name__ == '__main__':
    unittest.main()
