import unittest


from common.variables import RESPONSE, ERROR, ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME
from server import check_message


class TestServer(unittest.TestCase):
    def setUp(self):
        self.bad_response= {RESPONSE:400, ERROR: 'Bad request'}
        self.good_response = {RESPONSE:200}
        self.request = {ACTION: PRESENCE, TIME: 2.0, USER: {ACCOUNT_NAME: 'Guest'}}

    def test_no_action(self):
        self.assertEqual(check_message({TIME: 2.0, USER: {ACCOUNT_NAME: 'Guest'}}), self.bad_response)

    def test_wrong_action(self):
        self.assertEqual(check_message({ACTION: 'no_presense', TIME: 2.0, USER: {ACCOUNT_NAME: 'Guest'}}), self.bad_response)

    def test_no_time(self):
        self.assertEqual(check_message({ACTION: PRESENCE, USER: {ACCOUNT_NAME: 'Guest'}}), self.bad_response)

    def test_no_user(self):
        self.assertEqual(check_message({ACTION: PRESENCE, TIME: 2.0,}), self.bad_response)

    def test_bad_account_user(self):
        self.assertEqual(check_message({ACTION: PRESENCE, TIME: 2.0, USER: {ACCOUNT_NAME: 'Bad'}}), self.bad_response)

    def test_good_request(self):
        self.assertEqual(check_message(self.request), self.good_response)
        

if __name__ == '__main__':
    unittest.main()