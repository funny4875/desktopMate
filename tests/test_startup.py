import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock
import app

class StartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = app.QApplication.instance() or app.QApplication([])

    def test_only_conversation_models_are_offered(self):
        models = [SimpleNamespace(name='models/gemini-flash', supported_actions=['generateContent']),
                  SimpleNamespace(name='models/embedding', supported_actions=['embedContent']),
                  SimpleNamespace(name='models/gemini-image', supported_actions=['generateContent']),
                  SimpleNamespace(name='models/gemini-tts', supported_actions=['generateContent']),
                  SimpleNamespace(name=None, supported_actions=['generateContent'])]
        self.assertEqual([app.model_api_name(m) for m in app.conversation_models(models)], ['gemini-flash'])

    def test_invalid_key_emits_error_and_closes_client(self):
        client = Mock()
        client.models.list.side_effect = ValueError('invalid secret-test-key')
        worker = app.ModelValidationWorker('secret-test-key')
        errors = []
        worker.failed.connect(errors.append)
        with patch.object(app.genai, 'Client', return_value=client):
            worker.run()
        client.close.assert_called_once()
        self.assertEqual(len(errors), 1)
        self.assertNotIn('secret-test-key', errors[0])

    def test_model_list_failure_keeps_start_disabled(self):
        with patch.object(app, 'load_settings', return_value={}):
            dialog = app.GeminiSetupDialog()
        self.assertFalse(dialog.start_button.isEnabled())
        self.assertFalse(dialog.models.isEnabled())
        dialog.key_input.setText('test-key')
        client = Mock()
        dialog.validation_succeeded(client, [SimpleNamespace(name='models/gemini-flash', display_name='Flash')])
        self.assertTrue(dialog.start_button.isEnabled())
        self.assertEqual(dialog.models.currentData(), 'gemini-flash')
        dialog.key_input.setText('changed-key')
        self.assertFalse(dialog.start_button.isEnabled())
        client.close.assert_called_once()

    def test_saved_selection_is_restored_and_saved_after_success(self):
        with patch.object(app, 'load_settings', return_value={'model': 'gemini-pro'}):
            dialog = app.GeminiSetupDialog()
        dialog.key_input.setText('test-key')
        dialog.validation_succeeded(Mock(), [SimpleNamespace(name='models/gemini-flash', display_name='Flash'),
                                            SimpleNamespace(name='models/gemini-pro', display_name='Pro')])
        self.assertEqual(dialog.models.currentData(), 'gemini-pro')
        with patch.object(app, 'save_settings') as save:
            dialog.start_character()
        self.assertEqual(dialog.result(), app.QDialog.Accepted)
        save.assert_called_once_with({'api_key': 'test-key', 'model': 'gemini-pro'})

if __name__ == '__main__':
    unittest.main()
