import unittest


from common.variables import RESPONSE, ERROR, ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME
from client import get_answer, make_presence

class TestClient(unittest.TestCase):

    def setUp(self):
        self.test_request = make_presence()
        self.test_request[TIME] = 2.0

    def test_get_200_answer(self):
        self.assertEqual(get_answer({RESPONSE: 200}), '200 : OK')

    def test_get_400_answer(self):
        self.assertEqual(get_answer({RESPONSE: 400, ERROR: 'Bad request'}), '400 : Bad request')

    def test_empty_answer(self):
        self.assertRaises(ValueError,get_answer,'')

    def test_make_presence(self):
        self.assertEqual(self.test_request,{ACTION: PRESENCE, TIME: 2.0 ,USER: {ACCOUNT_NAME: 'Guest'}})



if __name__ == '__main__':
    unittest.main()